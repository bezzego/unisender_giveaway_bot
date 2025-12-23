from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.repositories.participants import ParticipantRepo
from app.repositories.promo_codes import PromoCodeRepo


@dataclass(frozen=True)
class RewardResult:
    reward_type: str  # cinema|guide|promo
    promo_code: str | None
    message: str


class RewardService:
    @staticmethod
    async def assign_reward(session: AsyncSession, participant_id: int) -> RewardResult:
        """
        Must be called inside a DB transaction.
        Priority:
        1) cinema if winners < limit AND there is free cinema code
        2) promo if FALLBACK_PROMO set
        3) guide
        """
        winners = await ParticipantRepo.count_cinema_winners(session)
        if winners < settings.cinema_limit:
            code = await PromoCodeRepo.get_free_code_for_update(session, kind="cinema")
            if code:
                await PromoCodeRepo.mark_used(session, promo_code_id=code.id, participant_id=participant_id)
                return RewardResult(
                    reward_type="cinema",
                    promo_code=code.code,
                    message=(
                        "🎉 Вы в числе первых подтверждённых подписчиков!\n\n"
                        f"🎟 Промокод на кино: <code>{code.code}</code>\n\n"
                        "Условия использования:\n"
                        "• 1 промокод = 1 подарок (как вы договоритесь с кинотеатром)\n"
                        "• не передавайте код третьим лицам, если это запрещено правилами\n"
                        "• если код не применится — напишите в поддержку\n"
                    ),
                )

        if settings.fallback_promo:
            return RewardResult(
                reward_type="promo",
                promo_code=settings.fallback_promo,
                message=(
                    "🎁 Основные билеты закончились, но подарок для вас есть!\n\n"
                    f"Промокод: <code>{settings.fallback_promo}</code>\n"
                ),
            )

        return RewardResult(
            reward_type="guide",
            promo_code=None,
            message=(
                "🎭 Билеты в кино уже закончились, но для вас есть подарок!\n\n"
                f"Вот бесплатный театральный гайд: {settings.guide_link}\n"
            ),
        )