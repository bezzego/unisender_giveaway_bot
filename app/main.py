from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import settings
from app.logging_cfg import setup_logging
from app.bot.router import router
from app.db import engine
from app.models import Base


log = logging.getLogger(__name__)


async def init_db() -> None:
    log.info("Initializing database")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("Database initialized")


async def main() -> None:
    setup_logging(settings.log_level)

    log.info("Application starting")
    await init_db()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()
    dp.include_router(router)

    log.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
