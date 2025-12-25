from __future__ import annotations

import logging

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

from app.db import SessionMaker
from app.services.unisender import unisender
from app.services.rewards import RewardService
from app.services.texts import TextService
from app.utils.validators import normalize_email
from app.bot.keyboards import kb_retry_check, kb_main
from app.config import settings
from app.repositories.participants import ParticipantRepo

log = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def start(m: Message) -> None:
    log.info("Start command received", extra={"telegram_id": m.from_user.id if m.from_user else None})
    text = await TextService.get_text_global("welcome")
    is_admin = m.from_user and m.from_user.id in settings.admin_ids
    await m.answer(text, reply_markup=kb_main(bool(is_admin)))


@router.callback_query(F.data == "check_again")
async def check_again(cb: CallbackQuery) -> None:
    log.info(
        "Check again callback",
        extra={"telegram_id": cb.from_user.id if cb.from_user else None},
    )
    await cb.answer()
    text = await TextService.get_text_global("check_again_prompt")
    await cb.message.answer(text)


@router.message(F.text)
async def email_flow(m: Message) -> None:
    if (m.text or "").strip() == "Админ панель":
        return
    tg_id = m.from_user.id if m.from_user else 0
    if tg_id == 0:
        log.error("Telegram ID not found in message")
        text = await TextService.get_text_global("telegram_id_missing")
        await m.answer(text)
        return

    # 1) validate email
    try:
        email = normalize_email(m.text or "")
    except ValueError:
        log.warning("Invalid email received", extra={"telegram_id": tg_id, "text": m.text})
        text = await TextService.get_text_global("invalid_email")
        await m.answer(text)
        return
    log.info("Email received", extra={"telegram_id": tg_id, "email": email})

    # 2) check Unisender confirmation + list membership
    try:
        status = await unisender.check_confirmed_in_list(email=email, list_id=settings.unisender_list_id)
    except Exception:
        log.exception("Unisender check failed")
        text = await TextService.get_text_global("unisender_unavailable")
        await m.answer(text)
        return
    log.debug(
        "Unisender status fetched",
        extra={
            "email": email,
            "email_status": status.email_status,
            "in_list": status.in_list,
            "list_status": status.list_status,
        },
    )

    # confirmed means: email active + in list + list status active
    confirmed = (status.email_status == "active") and status.in_list and (status.list_status == "active")

    if not confirmed:
        log.warning("Email not confirmed", extra={"email": email, "status": status})
        # explain precisely based on statuses (invited is the typical "not confirmed yet")  [oai_citation:3‡Unisender](https://www.unisender.com/ru/support/api/contacts/getcontact/)
        if status.email_status == "invited":
            template = await TextService.get_text_global("not_confirmed_invited")
            reason = template
        elif status.email_status in {"new", None}:
            template = await TextService.get_text_global("not_confirmed_new")
            reason = template
        elif status.email_status in {"unsubscribed", "blocked", "inactive"}:
            template = await TextService.get_text_global("not_confirmed_unsubscribed")
            reason = template.format(email_status=status.email_status)
        else:
            template = await TextService.get_text_global("not_confirmed_other")
            reason = template.format(
                email_status=status.email_status,
                in_list=status.in_list,
                list_status=status.list_status,
            )

        await m.answer(reason, reply_markup=kb_retry_check())
        return

    # 3) confirmed: DB transaction: create participant + assign reward atomically
    async with SessionMaker() as session:
        async with session.begin():
            log.info("Creating or loading participant", extra={"telegram_id": tg_id, "email": email})
            participant = await ParticipantRepo.create_if_missing(session, telegram_id=tg_id, email=email)

            # if already rewarded — show the same
            if participant.reward_type:
                log.info(
                    "Participant already rewarded",
                    extra={
                        "participant_id": participant.id,
                        "reward_type": participant.reward_type,
                    },
                )
                reward_message = await RewardService.render_message(
                    session=session,
                    reward_type=participant.reward_type,
                    promo_code=participant.promo_code,
                )
                prefix = await TextService.get_text(session, "already_rewarded")
                await m.answer(prefix.format(reward_message=reward_message))
                return

            # assign new reward
            log.info("Assigning new reward", extra={"participant_id": participant.id})
            reward = await RewardService.assign_reward(session, participant_id=participant.id)
            participant.reward_type = reward.reward_type
            participant.promo_code = reward.promo_code

        # committed
        log.info(
            "Reward assigned and committed",
            extra={"participant_id": participant.id, "reward_type": reward.reward_type},
        )
        await m.answer(reward.message)
