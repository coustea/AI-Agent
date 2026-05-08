"""Database engine and session factory.

This is the single database bootstrap implementation used by the application.
Environment loading is handled in ``app.main`` only.

职责：
  - 校验数据库配置完整性
  - 创建全局异步引擎（连接池）
  - 提供表自动创建（init_db）和会话工厂（get_session）
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.exc import OperationalError, DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import (
    APP_DEBUG,
    DATABASE_URL,
    DB_ECHO,
    DB_INIT_MAX_RETRIES,
    DB_INIT_RETRY_DELAY_SEC,
    DB_MAX_OVERFLOW,
    DB_POOL_RECYCLE,
    DB_POOL_SIZE,
    DB_POOL_TIMEOUT,
)
from app.infra.logging import get_logger
from app.infra.models import import_all_models

logger = get_logger(__name__)


def _validate_database_settings() -> None:
    """校验数据库配置必填项。"""
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is required. Set it in .env before starting the app."
        )
    logger.debug("[Database] 使用 DATABASE_URL: %s", DATABASE_URL[:50] + "...")


_validate_database_settings()

engine = create_async_engine(
    DATABASE_URL,
    echo=DB_ECHO,
    pool_pre_ping=True,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_recycle=DB_POOL_RECYCLE,
    pool_timeout=DB_POOL_TIMEOUT,
)


async def _test_connection() -> bool:
    """测试数据库连接是否可用。

    Returns:
        True 如果连接成功，False 如果连接失败
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except (OperationalError, DBAPIError, ConnectionRefusedError, OSError) as exc:
        logger.error(
            "[Database] 数据库连接测试失败: url=%s error_type=%s error=%s",
            engine.url.render_as_string(hide_password=True),
            type(exc).__name__,
            exc,
        )
        return False
    except Exception as exc:
        logger.error(
            "[Database] 数据库连接测试发生未知异常: url=%s error_type=%s error=%s",
            engine.url.render_as_string(hide_password=True),
            type(exc).__name__,
            exc,
        )
        return False


async def init_db() -> None:
    """创建数据库表。在应用启动时由 lifespan 调用。

    首先测试数据库连接，如果连接失败则记录错误并抛出异常。
    APP_DEBUG=true 时会先 DROP ALL 再 CREATE，仅用于开发环境。
    """
    max_retries = DB_INIT_MAX_RETRIES
    retry_delay_sec = DB_INIT_RETRY_DELAY_SEC

    # 先测试连接
    if not await _test_connection():
        logger.error(
            "[Database] 无法建立数据库连接，请检查数据库服务是否运行: url=%s",
            engine.url.render_as_string(hide_password=True),
        )

    import_all_models()

    async def _ensure_legacy_columns() -> None:
        """Best-effort schema patch for legacy DBs missing recently added columns."""
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    ALTER TABLE IF EXISTS user_profiles
                    ADD COLUMN IF NOT EXISTS profile_score_json JSONB
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE IF EXISTS user_profile_history
                    ADD COLUMN IF NOT EXISTS profile_score_json JSONB
                    """
                )
            )

    async def _run_once() -> None:
        if APP_DEBUG:
            logger.warning("[Database] APP_DEBUG=true，将删除并重建所有表！")
            async with engine.begin() as conn:
                # PostgreSQL requires CASCADE to drop tables with foreign key dependencies
                # Get all table names and drop them with CASCADE
                result = await conn.execute(
                    text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
                )
                table_names = [row[0] for row in result.fetchall()]
                if table_names:
                    for table_name in table_names:
                        await conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}" CASCADE'))
                    logger.info("[Database] 已删除 %d 个表", len(table_names))
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                "[Database] 开始初始化数据库: url=%s debug=%s attempt=%s/%s",
                engine.url.render_as_string(hide_password=True),
                APP_DEBUG,
                attempt,
                max_retries,
            )
            await _run_once()
            await _ensure_legacy_columns()
            logger.info(
                "[Database] 数据库表初始化完成: url=%s debug=%s attempt=%s/%s",
                engine.url.render_as_string(hide_password=True),
                APP_DEBUG,
                attempt,
                max_retries,
            )
            return
        except (OperationalError, DBAPIError, ConnectionRefusedError, OSError) as exc:
            if attempt >= max_retries:
                logger.exception(
                    "[Database] 初始化失败且重试耗尽: attempts=%s error_type=%s error=%s",
                    max_retries,
                    type(exc).__name__,
                    exc,
                )
                raise
            logger.warning(
                "[Database] 初始化失败，准备重试: attempt=%s/%s retry_after=%.1fs error_type=%s error=%s",
                attempt,
                max_retries,
                retry_delay_sec,
                type(exc).__name__,
                exc,
            )
            await asyncio.sleep(retry_delay_sec)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入用的会话工厂（async generator 形式）。
    expire_on_commit=False 防止 commit 后访问属性触发懒加载报错。"""
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session
    except OperationalError as exc:
        logger.warning("[Database] 会话关闭时检测到连接异常，已忽略清理异常: %s", exc)


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    """供非 DI 场景显式创建短生命周期会话。"""
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session
    except OperationalError as exc:
        logger.warning("[Database] 显式会话关闭时检测到连接异常，已忽略清理异常: %s", exc)
