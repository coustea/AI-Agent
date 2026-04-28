"""统一 LLM 管理器。

职责：
- 创建模型
- 缓存模型
- 获取模型
- 控制并发
- 异步调用（ainvoke）
- 异步流式调用（astream）
"""

from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Any, AsyncIterator, Hashable

from langchain_openai import ChatOpenAI

from app.config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_API_BASE,
    DEEPSEEK_CHAT_MODEL,
    DEEPSEEK_MODEL,
    GLM_API_KEY,
    GLM_VISION_MODEL,
    SPARK_MAX_API_PASSWORD,
    SPARK_MAX_API_BASE,
    SPARK_X_API_PASSWORD,
    SPARK_X_API_BASE,
)
from app.infra.logging import get_logger

logger = get_logger(__name__)


class LLMConcurrencyBusyError(Exception):
    """LLM 并发繁忙异常。"""


class LlmManager:
    """极简统一 LLM 管理器。"""

    DEFAULT_TIMEOUT_SECONDS = 10.0
    DEFAULT_CONCURRENCY_LIMITS: dict[str, int] = {
        "spark": 10,
        "spark_x": 20,
    }

    def __init__(
        self,
        *,
        concurrency_limits: dict[str, int] | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._models: dict[tuple[str, tuple[tuple[str, Hashable], ...]], Any] = {}
        self._limits = dict(self.DEFAULT_CONCURRENCY_LIMITS)
        if concurrency_limits:
            self._limits.update(concurrency_limits)
        self._semaphores: dict[str, asyncio.Semaphore] = {
            model_type: asyncio.Semaphore(limit)
            for model_type, limit in self._limits.items()
            if limit > 0
        }
        self._timeout_seconds = timeout_seconds

    @staticmethod
    def _freeze(value: Any) -> Hashable:
        if isinstance(value, dict):
            return tuple((k, LlmManager._freeze(v)) for k, v in sorted(value.items()))
        if isinstance(value, (list, tuple)):
            return tuple(LlmManager._freeze(v) for v in value)
        if isinstance(value, set):
            return tuple(sorted(LlmManager._freeze(v) for v in value))
        return value

    def _cache_key(self, model_type: str, kwargs: dict[str, Any]) -> tuple[str, tuple[tuple[str, Hashable], ...]]:
        frozen_kwargs = tuple((k, self._freeze(v)) for k, v in sorted(kwargs.items()))
        return model_type, frozen_kwargs

    def _has_available_slot(self, model_type: str) -> bool:
        """检查指定模型类型是否有可用并发槽位。"""
        semaphore = self._semaphores.get(model_type)
        if semaphore is None:
            return True  # 无限制的模型类型
        return semaphore._value > 0

    def _create_model(self, model_type: str, **kwargs: Any) -> Any:
        model = kwargs.pop("model", None)
        temperature = kwargs.pop("temperature", 0.3)
        streaming = kwargs.pop("streaming", False)
        max_tokens = kwargs.pop("max_tokens", None)
        max_retries = kwargs.pop("max_retries", 2)
        timeout = kwargs.pop("timeout", None)

        if model_type == "spark":
            return ChatOpenAI(
                model=model or "spark-max",
                api_key=SPARK_MAX_API_PASSWORD,
                base_url=SPARK_MAX_API_BASE,
                temperature=temperature,
                streaming=streaming,
                max_tokens=max_tokens,
                max_retries=max_retries,
                timeout=timeout,
                **kwargs,
            )

        if model_type == "spark_x":
            return ChatOpenAI(
                model=model or "spark-x",
                api_key=SPARK_X_API_PASSWORD,
                base_url=SPARK_X_API_BASE,
                temperature=temperature,
                streaming=streaming,
                max_tokens=max_tokens,
                max_retries=max_retries,
                timeout=timeout,
                **kwargs,
            )

        if model_type == "deepseek":
            return ChatOpenAI(
                model=model or DEEPSEEK_MODEL,
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_API_BASE,
                temperature=temperature,
                streaming=streaming,
                max_tokens=max_tokens,
                max_retries=max_retries,
                timeout=timeout,
                **kwargs,
            )

        if model_type == "deepseek_reasoner":
            return ChatOpenAI(
                model=model or DEEPSEEK_CHAT_MODEL,
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_API_BASE,
                temperature=1.0,  # reasoner 固定 1.0
                streaming=streaming,
                max_tokens=max_tokens,
                max_retries=max_retries,
                timeout=timeout,
                **kwargs,
            )

        if model_type == "glm_vision":
            return ChatOpenAI(
                model=model or GLM_VISION_MODEL,
                api_key=GLM_API_KEY,
                base_url="https://open.bigmodel.cn/api/paas/v4/",
                temperature=temperature,
                **kwargs,
            )

        raise ValueError(f"Unsupported model_type: {model_type}")

    def get_model(self, model_type: str, **kwargs: Any) -> Any:
        """获取模型实例（缓存命中则复用）。

        当 spark/spark_x 并发已满时，自动溢出到 deepseek。
        """
        # 检查是否需要溢出
        overflow_types = ("spark", "spark_x")
        if model_type in overflow_types and not self._has_available_slot(model_type):
            logger.info("[LLM] %s 并发已满，溢出到 deepseek", model_type)
            model_type = "deepseek"

        # 原有缓存逻辑
        key = self._cache_key(model_type, kwargs)
        model = self._models.get(key)
        if model is not None:
            return model

        logger.debug("[LLM] 创建模型: type=%s kwargs=%s", model_type, kwargs)
        model = self._create_model(model_type, **kwargs)
        self._models[key] = model
        return model

    async def _acquire(self, model_type: str, timeout: float | None = None) -> asyncio.Semaphore | None:
        semaphore = self._semaphores.get(model_type)
        if semaphore is None:
            return None

        effective_timeout = self._timeout_seconds if timeout is None else timeout
        try:
            await asyncio.wait_for(semaphore.acquire(), timeout=effective_timeout)
        except asyncio.TimeoutError as exc:
            raise LLMConcurrencyBusyError(
                f"LLM 并发繁忙: model_type={model_type}, timeout={effective_timeout}s"
            ) from exc
        return semaphore

    async def ainvoke(
        self,
        model_type: str,
        input_data: Any,
        *,
        timeout: float | None = None,
        model_kwargs: dict[str, Any] | None = None,
        **invoke_kwargs: Any,
    ) -> Any:
        """通过 manager 异步调用 LLM。"""
        llm = self.get_model(model_type, **(model_kwargs or {}))
        semaphore = await self._acquire(model_type, timeout=timeout)
        try:
            return await llm.ainvoke(input_data, **invoke_kwargs)
        finally:
            if semaphore is not None:
                semaphore.release()

    async def ainvoke_runnable(
        self,
        runnable: Any,
        input_data: Any,
        *,
        model_type: str | None = None,
        timeout: float | None = None,
        **invoke_kwargs: Any,
    ) -> Any:
        """通过 manager 异步调用 Runnable（如 bind_tools/structured_output 返回对象）。"""
        semaphore: asyncio.Semaphore | None = None
        if model_type is not None:
            semaphore = await self._acquire(model_type, timeout=timeout)
        try:
            return await runnable.ainvoke(input_data, **invoke_kwargs)
        finally:
            if semaphore is not None:
                semaphore.release()

    async def astream(
        self,
        model_type: str,
        input_data: Any,
        *,
        timeout: float | None = None,
        model_kwargs: dict[str, Any] | None = None,
        **stream_kwargs: Any,
    ) -> AsyncIterator[Any]:
        """通过 manager 异步流式调用 LLM。"""
        llm = self.get_model(model_type, **(model_kwargs or {}))
        semaphore = await self._acquire(model_type, timeout=timeout)
        try:
            async for chunk in llm.astream(input_data, **stream_kwargs):
                yield chunk
        finally:
            if semaphore is not None:
                semaphore.release()

    async def astream_runnable(
        self,
        runnable: Any,
        input_data: Any,
        *,
        model_type: str | None = None,
        timeout: float | None = None,
        **stream_kwargs: Any,
    ) -> AsyncIterator[Any]:
        """通过 manager 异步流式调用 Runnable。"""
        semaphore: asyncio.Semaphore | None = None
        if model_type is not None:
            semaphore = await self._acquire(model_type, timeout=timeout)
        try:
            async for chunk in runnable.astream(input_data, **stream_kwargs):
                yield chunk
        finally:
            if semaphore is not None:
                semaphore.release()

    def bind_tools(
        self,
        model_type: str,
        tools: list[Any],
        *,
        model_kwargs: dict[str, Any] | None = None,
    ) -> Any:
        """创建已绑定工具的 Runnable。"""
        llm = self.get_model(model_type, **(model_kwargs or {}))
        return llm.bind_tools(tools)

    def with_structured_output(
        self,
        model_type: str,
        schema: type[Any],
        *,
        model_kwargs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        """创建结构化输出 Runnable。"""
        llm = self.get_model(model_type, **(model_kwargs or {}))
        return llm.with_structured_output(schema, **kwargs)


@lru_cache(maxsize=1)
def get_llm_manager() -> LlmManager:
    """LlmManager 单例。"""
    return LlmManager()
