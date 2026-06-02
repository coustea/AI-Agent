"""Database engine, session factory, and startup initialization.

职责：
  - 校验数据库配置完整性
  - 创建全局异步引擎（连接池）
  - 初始化数据库（init_db）— 验证连接 + 按需导入学校数据
  - 提供会话工厂（get_session）和显式会话（session_scope）
  - 启动健康检测（check_all）

表结构由人工运行 init_schema.sql 管理，后端不负责创建/删除表。
"""

from __future__ import annotations

import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import (
    DEBUG,
    DB_URL,
    DB_ECHO,
    DB_MAX_OVERFLOW,
    DB_POOL_RECYCLE,
    DB_POOL_SIZE,
    DB_POOL_TIMEOUT,
)
from app.infra.logging import get_logger

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
    except (OperationalError, ConnectionRefusedError, OSError) as exc:
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
    """初始化数据库：验证连接 + 按需导入学校数据。

    表结构由人工运行 init_schema.sql 管理，后端不负责创建/删除表。
    学校数据仅在表为空时导入，已有数据则跳过。
    """
    if not await _test_connection():
        logger.error(
            "[Database] 无法建立数据库连接，请检查数据库服务是否运行: url=%s",
            engine.url.render_as_string(hide_password=True),
        )
        raise OperationalError("数据库连接失败", {}, None)

    logger.info("[Database] 数据库连接验证通过: url=%s debug=%s",
                engine.url.render_as_string(hide_password=True), DEBUG)

    # 按需导入学校数据（表为空时才导入）
    try:
        from app.auth.school_import import import_schools
        async with AsyncSession(engine, expire_on_commit=False) as session:
            count = await import_schools(session)
            if count > 0:
                logger.info("[Database] 学校数据导入完成: count=%d", count)
            else:
                logger.info("[Database] 学校数据已存在，跳过导入")
    except Exception as exc:
        logger.warning("[Database] 学校数据导入失败（非致命）: %s", exc)


# ============ Session factories ============


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入用的会话工厂（async generator 形式）。

    expire_on_commit=False 防止 commit 后访问属性触发懒加载报错。
    不自动 commit — 服务层自行决定何时 commit。
    上下文管理器退出时自动 close session。
    """
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    """供非 DI 场景显式创建短生命周期会话。

    yield 后自动 commit；异常时 rollback。
    用于后台任务等无法使用 FastAPI DI 的场景。
    """
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield session
        await session.commit()
    except Exception:
        if session.in_transaction():
            await session.rollback()
        raise
    finally:
        await session.close()