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

from sqlalchemy.exc import OperationalError
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


async def init_db() -> None:
    """创建数据库表。在应用启动时由 lifespan 调用。
    APP_DEBUG=true 时会先 DROP ALL 再 CREATE，仅用于开发环境。"""
    max_retries = DB_INIT_MAX_RETRIES
    retry_delay_sec = DB_INIT_RETRY_DELAY_SEC

    import_all_models()

    async def _run_once() -> None:
        if APP_DEBUG:
            logger.warning("[Database] APP_DEBUG=true，将删除并重建所有表！")
            async with engine.begin() as conn:
                await conn.run_sync(SQLModel.metadata.drop_all)
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
            logger.info(
                "[Database] 数据库表初始化完成: url=%s debug=%s attempt=%s/%s",
                engine.url.render_as_string(hide_password=True),
                APP_DEBUG,
                attempt,
                max_retries,
            )
            return
        except OperationalError as exc:
            if attempt >= max_retries:
                logger.exception(
                    "[Database] 初始化失败且重试耗尽: attempts=%s error=%s",
                    max_retries,
                    exc,
                )
                raise
            logger.warning(
                "[Database] 初始化失败，准备重试: attempt=%s/%s retry_after=%.1fs error=%s",
                attempt,
                max_retries,
                retry_delay_sec,
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
