from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PromoCode


class PromoCodeRepo:
    @staticmethod
    async def get_free_code_for_update(session: AsyncSession, kind: str = "cinema") -> PromoCode | None:
        """
        Selects one unused code with FOR UPDATE to avoid races.
        Works reliably inside a transaction.
        """
        stmt = (
            select(PromoCode)
            .where(PromoCode.kind == kind, PromoCode.is_used.is_(False))
            .order_by(PromoCode.id.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def mark_used(session: AsyncSession, promo_code_id: int, participant_id: int) -> None:
        await session.execute(
            update(PromoCode)
            .where(PromoCode.id == promo_code_id, PromoCode.is_used.is_(False))
            .values(
                is_used=True,
                used_by_participant_id=participant_id,
                used_at=datetime.now(tz=timezone.utc),
            )
        )