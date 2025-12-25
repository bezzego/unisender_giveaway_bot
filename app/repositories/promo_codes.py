from __future__ import annotations

from datetime import datetime, timezone
import logging
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PromoCode


log = logging.getLogger(__name__)


class PromoCodeRepo:
    @staticmethod
    async def get_free_code_for_update(session: AsyncSession, kind: str = "cinema") -> PromoCode | None:
        """
        Selects one unused code with FOR UPDATE to avoid races.
        Works reliably inside a transaction.
        """
        log.debug("Selecting free promo code", extra={"kind": kind})
        stmt = (
            select(PromoCode)
            .where(PromoCode.kind == kind, PromoCode.is_used.is_(False))
            .order_by(PromoCode.id.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        res = await session.execute(stmt)
        code = res.scalar_one_or_none()
        log.debug("Promo code selected", extra={"found": bool(code), "promo_code_id": code.id if code else None})
        return code

    @staticmethod
    async def mark_used(session: AsyncSession, promo_code_id: int, participant_id: int) -> None:
        log.info(
            "Marking promo code as used",
            extra={"promo_code_id": promo_code_id, "participant_id": participant_id},
        )
        await session.execute(
            update(PromoCode)
            .where(PromoCode.id == promo_code_id, PromoCode.is_used.is_(False))
            .values(
                is_used=True,
                used_by_participant_id=participant_id,
                used_at=datetime.now(tz=timezone.utc),
            )
        )

    @staticmethod
    async def stats(session: AsyncSession, kind: str = "cinema") -> dict[str, int]:
        total_res = await session.execute(
            select(PromoCode.id).where(PromoCode.kind == kind)
        )
        total = len(total_res.fetchall())
        used_res = await session.execute(
            select(PromoCode.id).where(PromoCode.kind == kind, PromoCode.is_used.is_(True))
        )
        used = len(used_res.fetchall())
        free = total - used
        return {"total": total, "used": used, "free": free}
