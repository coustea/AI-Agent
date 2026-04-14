import os
from collections.abc import AsyncGenerator
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text, inspect
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
import app.modules
# .env 在 server 目录下
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# ── MySQL ──
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Aa123456")
DB_NAME = os.getenv("DB_NAME", "agent")
DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))

mysql_url = f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_async_engine(
    mysql_url,
    echo=DB_ECHO,
    pool_pre_ping=True,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_recycle=DB_POOL_RECYCLE,
    pool_timeout=DB_POOL_TIMEOUT,
)

APP_DEBUG = os.getenv("APP_DEBUG", "false").lower() == "true"


async def init_db() -> None:
    """导入所有模型并创建表"""

    if APP_DEBUG:
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        await _apply_schema_patches(conn)


async def _apply_schema_patches(conn) -> None:
    """轻量表结构补丁：自动补齐新增字段，避免手动执行 SQL。"""
    required_columns = {
        "chat_sessions": {
            "memory_token_count": "INT NOT NULL DEFAULT 0",
            "profile_token_count": "INT NOT NULL DEFAULT 0",
        },
        "user_memory": {
            "evidence_count": "INT NOT NULL DEFAULT 1",
            "last_seen_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
        },
    }

    def _get_columns(sync_conn, table_name: str) -> set[str]:
        inspector = inspect(sync_conn)
        return {col["name"] for col in inspector.get_columns(table_name)}

    for table_name, columns in required_columns.items():
        existing_cols = await conn.run_sync(_get_columns, table_name)
        for col_name, col_def in columns.items():
            if col_name in existing_cols:
                continue
            await conn.execute(
                text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def}")
            )


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
