"""Database engine, session factory, and startup health check.

This is the single database bootstrap implementation used by the application.
Environment loading is handled in ``app.main`` only.

职责：
  - 校验数据库配置完整性
  - 创建全局异步引擎（连接池）
  - 提供表自动创建（init_db）和会话工厂（get_session）
  - 启动健康检测（check_all）
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.exc import OperationalError, DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import (
    DEBUG,
    DB_URL,
    DB_ECHO,
    DB_INIT_RETRIES,
    DB_INIT_RETRY_DELAY,
    DB_MAX_OVERFLOW,
    DB_POOL_RECYCLE,
    DB_POOL_SIZE,
    DB_POOL_TIMEOUT,
)
from app.infra.logging import get_logger
from app.infra.models import import_all_models

logger = get_logger(__name__)


# ============ Health check data structures ============


@dataclass
class ServiceStatus:
    name: str
    ok: bool = False
    latency_ms: int = 0
    error: str = ""


@dataclass
class HealthReport:
    services: list[ServiceStatus] = field(default_factory=list)

    @property
    def status(self) -> str:
        if all(s.ok for s in self.services):
            return "ok"
        if any(s.ok for s in self.services):
            return "degraded"
        return "error"

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "services": {
                s.name: {
                    "status": "ok" if s.ok else "error",
                    **({"latency_ms": s.latency_ms} if s.ok else {}),
                    **({"error": s.error} if s.error else {}),
                }
                for s in self.services
            },
        }


# ============ Config validation ============


def _validate_database_settings() -> None:
    """校验数据库配置必填项。"""
    if not DB_URL:
        raise RuntimeError(
            "DB_URL is required. Set it in config.yaml before starting the app."
        )


_validate_database_settings()

engine = create_async_engine(
    DB_URL,
    echo=DB_ECHO,
    pool_pre_ping=True,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_recycle=DB_POOL_RECYCLE,
    pool_timeout=DB_POOL_TIMEOUT,
)


# ============ Connection test & health check ============


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


async def check_all() -> HealthReport:
    """检测数据库服务，返回健康报告。在应用启动时由 lifespan 调用。"""
    t0 = time.monotonic()
    try:
        ok = await _test_connection()
        ms = int((time.monotonic() - t0) * 1000)
        result = ServiceStatus("database", ok=ok, latency_ms=ms if ok else 0,
                               error="" if ok else "连接测试失败")
    except Exception as exc:
        result = ServiceStatus("database", error=f"{type(exc).__name__}: {exc}")

    report = HealthReport([result])

    for s in report.services:
        if s.ok:
            logger.info("[Health] %s: ok (%dms)", s.name, s.latency_ms)
        else:
            logger.error("[Health] %s: FAIL - %s", s.name, s.error)

    return report


# ============ Database initialization ============


async def init_db() -> None:
    """创建数据库表。在应用启动时由 lifespan 调用。

    首先测试数据库连接，如果连接失败则记录错误并抛出异常。
    DEBUG=true 时会先 DROP ALL 再 CREATE，仅用于开发环境。
    """
    max_retries = DB_INIT_RETRIES
    retry_delay_sec = DB_INIT_RETRY_DELAY

    # 先测试连接
    if not await _test_connection():
        logger.error(
            "[Database] 无法建立数据库连接，请检查数据库服务是否运行: url=%s",
            engine.url.render_as_string(hide_password=True),
        )

    import_all_models()

    async def _run_once() -> None:
        async with engine.begin() as conn:
            if DEBUG:
                logger.warning("[Database] DEBUG=true，将删除并重建所有表！")
                # 先终止所有其他连接，避免 DROP SCHEMA 被阻塞
                result = await conn.execute(
                    text(
                        "SELECT pid, pg_terminate_backend(pid) "
                        "FROM pg_stat_activity "
                        "WHERE datname = current_database() AND pid <> pg_backend_pid()"
                    )
                )
                terminated = [row[0] for row in result.fetchall()]
                if terminated:
                    logger.info(
                        "[Database] 已终止 %d 个阻塞连接: pids=%s",
                        len(terminated), terminated,
                    )
                await conn.execute(text("DROP SCHEMA public CASCADE"))
                await conn.execute(text("CREATE SCHEMA public"))
                logger.info("[Database] 已删除并重建 public schema")
            await conn.run_sync(SQLModel.metadata.create_all)

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                "[Database] 开始初始化数据库: url=%s debug=%s attempt=%s/%s",
                engine.url.render_as_string(hide_password=True),
                DEBUG,
                attempt,
                max_retries,
            )
            await _run_once()

            # 导入学校数据
            from app.auth.school_import import import_schools
            async with AsyncSession(engine, expire_on_commit=False) as session:
                await import_schools(session)

            logger.info(
                "[Database] 数据库表初始化完成: url=%s debug=%s attempt=%s/%s",
                engine.url.render_as_string(hide_password=True),
                DEBUG,
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


# ============ Session factories ============


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
