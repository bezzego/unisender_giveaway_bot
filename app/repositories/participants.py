from __future__ import annotations

import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Participant


log = logging.getLogger(__name__)


class ParticipantRepo:
    @staticmethod
    async def get_by_telegram_id(session: AsyncSession, telegram_id: int) -> Participant | None:
        log.debug("Fetching participant by telegram_id", extra={"telegram_id": telegram_id})
        res = await session.execute(select(Participant).where(Participant.telegram_id == telegram_id))
        return res.scalar_one_or_none()

    @staticmethod
    async def get_by_email(session: AsyncSession, email: str) -> Participant | None:
        log.debug("Fetching participant by email", extra={"email": email})
        res = await session.execute(select(Participant).where(Participant.email == email))
        return res.scalar_one_or_none()

    @staticmethod
    async def create_if_missing(session: AsyncSession, telegram_id: int, email: str) -> Participant:
        log.debug("Create participant if missing", extra={"telegram_id": telegram_id, "email": email})
        existing = await ParticipantRepo.get_by_email(session, email)
        if existing:
            # If same email used by different tg — we keep first issuer; you can change this rule if needed.
            log.info("Participant found by email", extra={"participant_id": existing.id, "email": email})
            return existing

        existing_tg = await ParticipantRepo.get_by_telegram_id(session, telegram_id)
        if existing_tg:
            # update email if user changed it
            log.info("Participant found by telegram_id, updating email", extra={"participant_id": existing_tg.id})
            existing_tg.email = email
            return existing_tg

        obj = Participant(telegram_id=telegram_id, email=email)
        session.add(obj)
        await session.flush()
        log.info("Participant created", extra={"participant_id": obj.id})
        return obj

    @staticmethod
    async def count_cinema_winners(session: AsyncSession) -> int:
        log.debug("Counting cinema winners")
        res = await session.execute(
            select(func.count()).select_from(Participant).where(Participant.reward_type == "cinema")
        )
        count = int(res.scalar_one())
        log.debug("Cinema winners count fetched", extra={"count": count})
        return count

    @staticmethod
    async def list_all(session: AsyncSession) -> list[Participant]:
        log.debug("Listing all participants")
        res = await session.execute(select(Participant).order_by(Participant.id.asc()))
        return list(res.scalars().all())
