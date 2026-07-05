"""Ollama 嵌入模型封装。

提供统一接口获取查询向量，包含超时控制和熔断机制。
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.config import KB_EMBED_MODEL, KB_EMBED_TIMEOUT_SECONDS, KB_OLLAMA_BASE_URL
from app.infra.logging import get_logger

logger = get_logger(__name__)

# 熔断器：Ollama 连续失败后暂时停止请求
_BREAKER_COOLDOWN_SECONDS = 900.0
_breaker_until: float = 0.0


def _breaker_open() -> bool:
    return _breaker_until > time.monotonic()


def _open_breaker(reason: str) -> None:
    global _breaker_until
    now = time.monotonic()
    next_until = now + _BREAKER_COOLDOWN_SECONDS
    if _breaker_until <= now:
        logger.warning(
            "[embeddings] Ollama unavailable (%s); dense retrieval disabled for %.0fs",
            reason,
            _BREAKER_COOLDOWN_SECONDS,
        )
    _breaker_until = max(_breaker_until, next_until)


def embed_query(query: str) -> list[float] | None:
    """请求 Ollama 生成查询向量。

    Returns:
        嵌入向量列表，失败时返回 None。
    """
    if _breaker_open():
        return None

    timeout = float(KB_EMBED_TIMEOUT_SECONDS)
    try:
        response = httpx.post(
            f"{KB_OLLAMA_BASE_URL}/api/embed",
            json={"model": KB_EMBED_MODEL, "input": query},
            timeout=timeout,
            trust_env=False,
        )
        response.raise_for_status()
        data = response.json()
        # Ollama /api/embed 返回 {"embeddings": [[...]]}
        raw = data.get("embeddings")
        if isinstance(raw, list) and raw and isinstance(raw[0], list):
            return [float(v) for v in raw[0]]
        return None
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code >= 500:
            _open_breaker(f"ollama status {exc.response.status_code}")
        else:
            logger.warning("[embeddings] request rejected: status=%s", exc.response.status_code)
        return None
    except httpx.RequestError as exc:
        _open_breaker(exc.__class__.__name__)
        return None
    except Exception as exc:
        logger.warning("[embeddings] failed: %s", exc)
        return None
