from __future__ import annotations

import logging
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BotText

log = logging.getLogger(__name__)


class BotTextRepo:
    @staticmethod
    async def get(session: AsyncSession, key: str) -> BotText | None:
        log.debug("Fetching bot text", extra={"key": key})
        res = await session.execute(select(BotText).where(BotText.key == key))
        return res.scalar_one_or_none()

    @staticmethod
    async def set(session: AsyncSession, key: str, value: str) -> None:
        existing = await BotTextRepo.get(session, key)
        if existing:
            log.info("Updating bot text", extra={"key": key})
            await session.execute(
                update(BotText)
                .where(BotText.key == key)
                .values(value=value)
            )
            return
        log.info("Creating bot text", extra={"key": key})
        session.add(BotText(key=key, value=value))

    @staticmethod
    async def list_keys(session: AsyncSession) -> list[str]:
        res = await session.execute(select(BotText.key).order_by(BotText.key.asc()))
        return [row[0] for row in res.fetchall()]
