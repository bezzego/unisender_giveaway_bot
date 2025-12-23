from __future__ import annotations

import logging

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db import SessionMaker
from app.models import Participant
from app.services.unisender import unisender
from app.services.rewards import RewardService
from app.utils.validators import normalize_email
from app.bot.keyboards import kb_retry_check
from app.config import settings
from app.repositories.participants import ParticipantRepo

log = logging.getLogger(__name__)
router = Router()


WELCOME = (
    "Привет! 👋\n\n"
    "Чтобы получить подарок, отправь email, который ты указал при подписке на рассылку.\n\n"
    "Важно: сначала подтверди подписку в письме (кнопка/ссылка подтверждения)."
)


@router.message(CommandStart())
async def start(m: Message) -> None:
    await m.answer(WELCOME)


@router.callback_query(F.data == "check_again")
async def check_again(cb: CallbackQuery) -> None:
    await cb.answer()
    await cb.message.answer("Ок! Пришли email ещё раз (или тот же).")


@router.message(F.text)
async def email_flow(m: Message) -> None:
    tg_id = m.from_user.id if m.from_user else 0
    if tg_id == 0:
        await m.answer("Не смог определить ваш Telegram ID. Попробуйте ещё раз.")
        return

    # 1) validate email
    try:
        email = normalize_email(m.text or "")
    except ValueError:
        await m.answer("Похоже, это не email. Пришли адрес в формате name@example.com")
        return

    # 2) check Unisender confirmation + list membership
    try:
        status = await unisender.check_confirmed_in_list(email=email, list_id=settings.unisender_list_id)
    except Exception as e:
        log.exception("Unisender check failed")
        await m.answer("Сервис проверки подписки временно недоступен. Попробуй чуть позже.")
        return

    # confirmed means: email active + in list + list status active
    confirmed = (status.email_status == "active") and status.in_list and (status.list_status == "active")

    if not confirmed:
        # explain precisely based on statuses (invited is the typical "not confirmed yet")  [oai_citation:3‡Unisender](https://www.unisender.com/ru/support/api/contacts/getcontact/)
        if status.email_status == "invited":
            reason = (
                "❗ Подписка ещё не подтверждена.\n"
                "Проверь почту: открой письмо и нажми «Подтвердить подписку».\n\n"
                "После подтверждения вернись сюда и нажми «Проверить ещё раз»."
            )
        elif status.email_status in {"new", None}:
            reason = (
                "❗ Я не вижу подтверждённую подписку по этому email.\n"
                "Проверь, что ты подписывался именно этим адресом и подтвердил подписку."
            )
        elif status.email_status in {"unsubscribed", "blocked", "inactive"}:
            reason = (
                f"❗ Этот email имеет статус: {status.email_status}.\n"
                "Подарок выдаётся только активным подтверждённым подписчикам."
            )
        else:
            reason = (
                f"❗ Сейчас подписка не подходит по условиям.\n"
                f"Статус email: {status.email_status}\n"
                f"В списке: {status.in_list}, статус в списке: {status.list_status}"
            )

        await m.answer(reason, reply_markup=kb_retry_check())
        return

    # 3) confirmed: DB transaction: create participant + assign reward atomically
    async with SessionMaker() as session:
        async with session.begin():
            participant = await ParticipantRepo.create_if_missing(session, telegram_id=tg_id, email=email)

            # if already rewarded — show the same
            if participant.reward_type:
                if participant.reward_type == "cinema":
                    await m.answer(
                        "✅ Ты уже получал подарок.\n\n"
                        f"🎟 Промокод на кино: <code>{participant.promo_code}</code>"
                    )
                    return
                if participant.reward_type == "promo":
                    await m.answer(
                        "✅ Ты уже получал подарок.\n\n"
                        f"🎁 Промокод: <code>{participant.promo_code}</code>"
                    )
                    return
                if participant.reward_type == "guide":
                    await m.answer(
                        "✅ Ты уже получал подарок.\n\n"
                        f"🎭 Гайд: {settings.guide_link}"
                    )
                    return

            # assign new reward
            reward = await RewardService.assign_reward(session, participant_id=participant.id)
            participant.reward_type = reward.reward_type
            participant.promo_code = reward.promo_code

        # committed
        await m.answer(reward.message)