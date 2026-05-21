"""启动健康检测。

启动时并行检测数据库和 LLM 可用性，失败时记录日志但不阻塞应用运行。
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from app.infra.database import _test_connection
from app.infra.llm import get_llm
from app.infra.logging import get_logger

logger = get_logger(__name__)

LLM_TEST_TIMEOUT = 15


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


async def _check_db() -> ServiceStatus:
    t0 = time.monotonic()
    try:
        ok = await _test_connection()
        ms = int((time.monotonic() - t0) * 1000)
        if ok:
            return ServiceStatus("database", ok=True, latency_ms=ms)
        return ServiceStatus("database", error="连接测试失败")
    except Exception as exc:
        return ServiceStatus("database", error=f"{type(exc).__name__}: {exc}")


async def _check_llm() -> ServiceStatus:
    t0 = time.monotonic()
    try:
        llm = get_llm()
        if not llm._text_model:
            return ServiceStatus("llm_text", error="文本模型未配置")
        await asyncio.wait_for(
            llm._text_model.ainvoke("hi"),
            timeout=LLM_TEST_TIMEOUT,
        )
        ms = int((time.monotonic() - t0) * 1000)
        return ServiceStatus("llm_text", ok=True, latency_ms=ms)
    except asyncio.TimeoutError:
        return ServiceStatus("llm_text", error=f"超时 ({LLM_TEST_TIMEOUT}s)")
    except Exception as exc:
        return ServiceStatus("llm_text", error=f"{type(exc).__name__}: {exc}")


async def check_all() -> HealthReport:
    """并行检测所有服务，返回健康报告。"""
    results = await asyncio.gather(_check_db(), _check_llm())
    report = HealthReport(list(results))

    for s in report.services:
        if s.ok:
            logger.info("[Health] %s: ok (%dms)", s.name, s.latency_ms)
        else:
            logger.error("[Health] %s: FAIL - %s", s.name, s.error)

    return report
