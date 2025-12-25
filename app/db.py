from __future__ import annotations

import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import settings

log = logging.getLogger(__name__)

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionMaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

log.debug("Database engine initialized")
