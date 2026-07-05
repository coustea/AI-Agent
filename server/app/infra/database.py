"""数据库引擎、会话工厂与启动初始化。

职责:
    - 校验数据库配置完整性
    - 创建全局异步引擎（连接池）
    - 初始化数据库（init_db）— 验证连接 + 按需导入种子数据
    - 提供会话工厂（get_session）和显式会话（session_scope）
    - 启动健康检测（check_all）

表结构和扩展由外部管理（init_schema.sql），后端仅负责 CRUD。
"""

from __future__ import annotations

import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import (
    DB_ECHO,
    DB_MAX_OVERFLOW,
    DB_POOL_RECYCLE,
    DB_POOL_SIZE,
    DB_POOL_TIMEOUT,
    DB_URL,
)
from app.infra.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ServiceStatus:
    """单个服务的健康状态。"""

    name: str
    ok: bool = False
    latency_ms: int = 0
    error: str = ""


@dataclass
class HealthReport:
    """健康检测报告，包含所有服务状态。"""

    services: list[ServiceStatus] = field(default_factory=list)

    @property
    def status(self) -> str:
        """返回整体状态。"""
        if all(s.ok for s in self.services):
            return "ok"
        if any(s.ok for s in self.services):
            return "degraded"
        return "error"


def _validate_database_settings() -> None:
    """校验数据库配置必填项。"""
    if not DB_URL:
        raise RuntimeError(
            "DB_URL is required. Set it in config.yaml before starting the app."
        )


_validate_database_settings()

# 创建全局异步数据库引擎（连接池）
engine = create_async_engine(
    DB_URL,
    echo=DB_ECHO,
    pool_pre_ping=True,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_recycle=DB_POOL_RECYCLE,
    pool_timeout=DB_POOL_TIMEOUT,
    connect_args={"prepared_statement_cache_size": 0},
)


async def _test_connection() -> bool:
    """测试数据库连接是否可用。

    Returns:
        True 如果连接成功，False 如果连接失败。
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except (OperationalError, ConnectionRefusedError, OSError) as exc:
        logger.error(
            "[Database] 连接测试失败: url=%s error_type=%s error=%s",
            engine.url.render_as_string(hide_password=True),
            type(exc).__name__,
            exc,
        )
        return False
    except Exception as exc:
        logger.error(
            "[Database] 连接测试发生未知异常: url=%s error_type=%s error=%s",
            engine.url.render_as_string(hide_password=True),
            type(exc).__name__,
            exc,
        )
        return False


async def check_all() -> HealthReport:
    """检测数据库服务，返回健康报告。

    在应用启动时由 lifespan 调用。
    """
    t0 = time.monotonic()
    try:
        ok = await _test_connection()
        ms = int((time.monotonic() - t0) * 1000)
        result = ServiceStatus(
            name="database",
            ok=ok,
            latency_ms=ms if ok else 0,
            error="" if ok else "连接测试失败",
        )
    except Exception as exc:
        result = ServiceStatus(name="database", error=f"{type(exc).__name__}: {exc}")

    report = HealthReport([result])

    for s in report.services:
        if s.ok:
            logger.info("[Health] %s: ok (%dms)", s.name, s.latency_ms)
        else:
            logger.error("[Health] %s: FAIL - %s", s.name, s.error)

    return report


async def init_db() -> None:
    """初始化数据库。

    验证连接后，按需导入种子数据（学校、408题库、编程题）。
    已存在则跳过。
    """
    if not await _test_connection():
        logger.error(
            "[Database] 无法建立数据库连接: url=%s",
            engine.url.render_as_string(hide_password=True),
        )
        raise OperationalError("数据库连接失败", {}, None)

    logger.info(
        "[Database] 连接验证通过: url=%s",
        engine.url.render_as_string(hide_password=True),
    )

    # 启动时自动导入种子数据
    await _seed_initial_data()


async def _seed_initial_data() -> None:
    """启动时自动导入种子数据。

    分别检查学校、408题库、编程题数据是否为空，为空则导入。
    """
    from app.importers.import_quiz import import_408_quiz
    from app.importers.import_leetcode import import_leetcode
    from app.importers.import_schools import import_schools

    logger.info("[Database] 开始检查种子数据...")

    # 导入学校数据
    await import_schools()

    # 导入 408 题库
    await import_408_quiz()

    # 导入编程题
    await import_leetcode()

    logger.info("[Database] 种子数据检查完成")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入用的会话工厂。

    expire_on_commit=False 防止 commit 后访问属性触发懒加载报错。
    不自动 commit — 服务层自行决定何时 commit。
    """
    yielded_exception = False
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            try:
                yield session
            except GeneratorExit:
                raise
            except BaseException:
                yielded_exception = True
                raise
    except OperationalError as exc:
        if yielded_exception:
            raise
        logger.warning("[Database] 会话关闭时连接已不可用: %s", exc)


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    """供非 DI 场景显式创建短生命周期会话。

    yield 后自动 commit；异常时 rollback。
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
