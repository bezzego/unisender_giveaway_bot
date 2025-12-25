from __future__ import annotations

import logging
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BotConfig

log = logging.getLogger(__name__)


class BotConfigRepo:
    @staticmethod
    async def get(session: AsyncSession, key: str) -> BotConfig | None:
        log.debug("Fetching bot config", extra={"key": key})
        res = await session.execute(select(BotConfig).where(BotConfig.key == key))
        return res.scalar_one_or_none()

    @staticmethod
    async def set(session: AsyncSession, key: str, value: str) -> None:
        existing = await BotConfigRepo.get(session, key)
        if existing:
            log.info("Updating bot config", extra={"key": key})
            await session.execute(
                update(BotConfig)
                .where(BotConfig.key == key)
                .values(value=value)
            )
            return
        log.info("Creating bot config", extra={"key": key})
        session.add(BotConfig(key=key, value=value))
