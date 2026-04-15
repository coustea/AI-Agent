"""Database engine and session factory.

This is the single database bootstrap implementation used by the application.
Environment loading is handled in ``app.main`` only.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from urllib.parse import quote_plus

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import (
    APP_DEBUG,
    DB_ECHO,
    DB_HOST,
    DB_MAX_OVERFLOW,
    DB_NAME,
    DB_PASSWORD,
    DB_POOL_RECYCLE,
    DB_POOL_SIZE,
    DB_POOL_TIMEOUT,
    DB_PORT,
    DB_USER,
)
from app.infra.models import import_all_models


def _validate_database_settings() -> None:
    missing = []
    if not DB_HOST:
        missing.append("DB_HOST")
    if not DB_PORT:
        missing.append("DB_PORT")
    if not DB_USER:
        missing.append("DB_USER")
    if not DB_PASSWORD:
        missing.append("DB_PASSWORD")
    if not DB_NAME:
        missing.append("DB_NAME")

    if missing:
        raise RuntimeError(
            "Missing required database settings: "
            + ", ".join(missing)
            + ". Load them through .env before starting the app."
        )


_validate_database_settings()

mysql_url = (
    "mysql+aiomysql://"
    f"{quote_plus(DB_USER)}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine = create_async_engine(
    mysql_url,
    echo=DB_ECHO,
    pool_pre_ping=True,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_recycle=DB_POOL_RECYCLE,
    pool_timeout=DB_POOL_TIMEOUT,
)


async def init_db() -> None:
    """Create database tables after explicit model registration."""
    import_all_models()

    if APP_DEBUG:
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
