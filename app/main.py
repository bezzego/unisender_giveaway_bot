from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from app.config import settings
from app.logging_cfg import setup_logging
from app.bot.router import router
from app.db import engine
from app.models import Base


log = logging.getLogger(__name__)


async def init_db() -> None:
    # Minimal schema init (for production лучше миграции Alembic, но для быстрого старта ок)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def main() -> None:
    setup_logging(settings.log_level)

    await init_db()

    bot = Bot(token=settings.bot_token, parse_mode=ParseMode.HTML)
    dp = Dispatcher()
    dp.include_router(router)

    log.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())