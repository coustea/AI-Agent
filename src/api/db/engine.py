"""Database engine configuration for MySQL and Redis."""

import os
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from api.services.redis_service import RedisService

# MySQL configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "agent")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

DATABASE_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

mysql_engine = create_async_engine(DATABASE_URL, echo=True, pool_pre_ping=True)

async_session_maker = async_sessionmaker(
    mysql_engine, class_=AsyncSession, expire_on_commit=False
)

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD") or None

_redis_client: Optional[RedisService] = None


def get_redis() -> RedisService:
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisService(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
        )
    return _redis_client


async def get_db():
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_engines():
    global _redis_client

    _redis_client = RedisService(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD,
    )

    async with mysql_engine.begin() as conn:
        from api.db.models import Base

        await conn.run_sync(Base.metadata.create_all)
