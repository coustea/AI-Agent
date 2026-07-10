"""OpenAI 兼容嵌入模型封装。

使用 langchain_openai.OpenAIEmbeddings 通过 OpenAI 兼容 API 生成查询向量，
嵌入模型配置独立于全局 LLM 配置。

切换嵌入模型只需修改 config.yaml 中的 knowledge.embed_model、
knowledge.embed_base_url 和 knowledge.embed_api_key，下次启动时自动感知：
  - manifest 中记录的 embedding_model 与当前配置不同 → 触发重建
  - _get_embeddings_client() 每次读取最新配置，无缓存过时问题
"""

from __future__ import annotations

import time

from langchain_openai import OpenAIEmbeddings

from app.config import KB_EMBED_API_KEY, KB_EMBED_BASE_URL, KB_EMBED_MODEL
from app.infra.logging import get_logger

logger = get_logger(__name__)

# 嵌入请求超时秒数（批量嵌入 32 条长文本时需较长等待）
_REQUEST_TIMEOUT = 30

# 熔断器：连续失败后暂时停止请求
_BREAKER_COOLDOWN_SECONDS = 300.0
_BREAKER_MAX_FAILS = 3
_fail_count: int = 0
_breaker_until: float = 0.0


# 熔断器是否处于打开（冷却）状态
def _breaker_open() -> bool:
    return _breaker_until > time.monotonic()


# 记录一次失败，连续失败达阈值则开启熔断
def _record_failure(reason: str) -> None:
    global _fail_count, _breaker_until
    _fail_count += 1
    if _fail_count >= _BREAKER_MAX_FAILS:
        _breaker_until = time.monotonic() + _BREAKER_COOLDOWN_SECONDS
        logger.warning(
            "[embeddings] %d consecutive failures (%s); dense retrieval disabled for %.0fs",
            _fail_count,
            reason,
            _BREAKER_COOLDOWN_SECONDS,
        )


# 记录一次成功，重置连续失败计数
def _record_success() -> None:
    global _fail_count
    _fail_count = 0


# 重置熔断器状态（构建索引前调用，避免旧熔断阻塞新构建）
def reset_breaker() -> None:
    """重置熔断器状态（构建前调用，避免旧熔断阻止新构建）。"""
    global _fail_count, _breaker_until
    _fail_count = 0
    _breaker_until = 0.0


# 创建嵌入客户端（每次读取最新配置，模型切换无需重启）
def _get_embeddings_client() -> OpenAIEmbeddings:
    """创建嵌入客户端。每次读取最新配置，模型切换后无需重启。

    不使用 lru_cache：config.yaml 修改 embed_model/embed_base_url/embed_api_key 后
    应立即生效，缓存会导致继续使用旧模型。
    """
    return OpenAIEmbeddings(
        model=KB_EMBED_MODEL,
        api_key=KB_EMBED_API_KEY,
        base_url=KB_EMBED_BASE_URL,
        check_embedding_ctx_length=False,
        request_timeout=_REQUEST_TIMEOUT,
    )


# 请求嵌入模型生成单条查询向量
def embed_query(query: str) -> list[float] | None:
    """请求嵌入模型生成查询向量。

    Returns:
        嵌入向量列表，失败时返回 None。
    """
    # 熔断中则直接返回失败
    if _breaker_open():
        return None

    try:
        client = _get_embeddings_client()
        result = client.embed_query(query)
        _record_success()
        return result
    except Exception as exc:
        # 嵌入失败则记录并触发熔断计数
        _record_failure(exc.__class__.__name__)
        logger.warning("[embeddings] embed_query failed: %s", exc)
        return None


# 批量请求嵌入模型生成文档向量
def embed_documents(texts: list[str]) -> list[list[float]] | None:
    """批量嵌入文档文本。

    Returns:
        嵌入向量列表，失败时返回 None。
    """
    # 熔断中则直接返回失败
    if _breaker_open():
        return None

    try:
        client = _get_embeddings_client()
        result = client.embed_documents(texts)
        _record_success()
        return result
    except Exception as exc:
        # 批量嵌入失败则记录并触发熔断计数
        _record_failure(exc.__class__.__name__)
        logger.warning("[embeddings] embed_documents failed: %s", exc)
        return None
