from __future__ import annotations

from dataclasses import dataclass
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.repositories.participants import ParticipantRepo
from app.repositories.promo_codes import PromoCodeRepo
from app.repositories.bot_config import BotConfigRepo
from app.services.texts import TextService


log = logging.getLogger(__name__)

WINNER_PROMO_PLACEHOLDER = "ХХХХХХХХ"


@dataclass(frozen=True)
class RewardResult:
    reward_type: str  # cinema|guide|promo
    promo_code: str | None
    message: str


class RewardService:
    @staticmethod
    def format_promo_code(promo_code: str) -> str:
        if " " in promo_code:
            return promo_code
        if promo_code.isdigit() and len(promo_code) == 10:
            return f"{promo_code[:2]} {promo_code[2:]}"
        return promo_code

    @staticmethod
    async def render_message(session: AsyncSession, reward_type: str, promo_code: str | None) -> str:
        log.debug("Rendering reward message", extra={"reward_type": reward_type})
        if reward_type in {"cinema", "promo"}:
            if promo_code:
                code = RewardService.format_promo_code(promo_code)
            else:
                code = WINNER_PROMO_PLACEHOLDER
            template = await TextService.get_text(session, "winner_message")
            return template.format(promo_code=code)
        template = await TextService.get_text(session, "non_winner_message")
        return template.format(guide_link=settings.guide_link)

    @staticmethod
    async def assign_reward(session: AsyncSession, participant_id: int) -> RewardResult:
        """
        Must be called inside a DB transaction.
        Priority:
        1) cinema if winners < limit AND there is free cinema code
        2) promo if FALLBACK_PROMO set
        3) guide
        """
        log.info("Assigning reward", extra={"participant_id": participant_id})
        winners = await ParticipantRepo.count_cinema_winners(session)
        cinema_limit_record = await BotConfigRepo.get(session, "cinema_limit")
        cinema_limit = int(cinema_limit_record.value) if cinema_limit_record else settings.cinema_limit
        log.debug("Cinema winners count", extra={"winners": winners, "limit": cinema_limit})
        if winners < cinema_limit:
            code = await PromoCodeRepo.get_free_code_for_update(session, kind="cinema")
            if code:
                log.info("Cinema promo code assigned", extra={"promo_code_id": code.id})
                await PromoCodeRepo.mark_used(session, promo_code_id=code.id, participant_id=participant_id)
                return RewardResult(
                    reward_type="cinema",
                    promo_code=code.code,
                    message=await RewardService.render_message(session, "cinema", code.code),
                )

        if settings.fallback_promo:
            log.warning("Cinema limit reached or no codes; using fallback promo", extra={"participant_id": participant_id})
            return RewardResult(
                reward_type="promo",
                promo_code=settings.fallback_promo,
                message=await RewardService.render_message(session, "promo", settings.fallback_promo),
            )

        log.warning("Cinema limit reached or no codes; using guide", extra={"participant_id": participant_id})
        return RewardResult(
            reward_type="guide",
            promo_code=None,
            message=await RewardService.render_message(session, "guide", None),
        )
