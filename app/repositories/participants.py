from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Participant


class ParticipantRepo:
    @staticmethod
    async def get_by_telegram_id(session: AsyncSession, telegram_id: int) -> Participant | None:
        res = await session.execute(select(Participant).where(Participant.telegram_id == telegram_id))
        return res.scalar_one_or_none()

    @staticmethod
    async def get_by_email(session: AsyncSession, email: str) -> Participant | None:
        res = await session.execute(select(Participant).where(Participant.email == email))
        return res.scalar_one_or_none()

    @staticmethod
    async def create_if_missing(session: AsyncSession, telegram_id: int, email: str) -> Participant:
        existing = await ParticipantRepo.get_by_email(session, email)
        if existing:
            # If same email used by different tg — we keep first issuer; you can change this rule if needed.
            return existing

        existing_tg = await ParticipantRepo.get_by_telegram_id(session, telegram_id)
        if existing_tg:
            # update email if user changed it
            existing_tg.email = email
            return existing_tg

        obj = Participant(telegram_id=telegram_id, email=email)
        session.add(obj)
        await session.flush()
        return obj

    @staticmethod
    async def count_cinema_winners(session: AsyncSession) -> int:
        res = await session.execute(
            select(func.count()).select_from(Participant).where(Participant.reward_type == "cinema")
        )
        return int(res.scalar_one())