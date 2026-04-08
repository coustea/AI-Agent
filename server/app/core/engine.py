import os
from collections.abc import AsyncGenerator
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

# .env 在 server 目录下
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# ── MySQL ──
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Aa123456")
DB_NAME = os.getenv("DB_NAME", "agent")
DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"

mysql_url = f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_async_engine(
    mysql_url,
    echo=DB_ECHO,
    pool_pre_ping=True,
)

APP_DEBUG = os.getenv("APP_DEBUG", "false").lower() == "true"


async def init_db() -> None:
    """导入所有模型并创建表"""
    import app.models  # noqa: F401

    if APP_DEBUG:
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(engine) as session:
        yield session
