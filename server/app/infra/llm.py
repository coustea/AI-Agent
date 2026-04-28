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


class LlmFactory:
    """LLM 工厂类：根据 model_type 创建 ChatOpenAI 实例。"""

    @staticmethod
    def _spark_model_name(base_url: str) -> str:
        """根据讯飞 OpenAI 兼容网关地址选择匹配的模型名。"""
        normalized = (base_url or "").rstrip("/")

        # 讯飞 X1.5/X2 推理网关只接受 spark-x。
        if normalized.endswith("/v2") or normalized.endswith("/x2"):
            return "spark-x"

        # 语言模型网关（/v1）兼容 Spark Max / Ultra 一类模型名。
        return "generalv3.5"

    @classmethod
    def create(cls, model_type: str, **kwargs: Any) -> Any:
        """根据 model_type 创建 ChatOpenAI 实例。"""
        # 禁止外部传入 model，统一由 model_type 决定真实模型名称
        kwargs.pop("model", None)

        # 提取通用模型参数，剩余 kwargs 继续透传给 ChatOpenAI
        temperature = kwargs.pop("temperature", 0.3)
        streaming = kwargs.pop("streaming", False)
        max_tokens = kwargs.pop("max_tokens", None)
        max_retries = kwargs.pop("max_retries", 2)
        timeout = kwargs.pop("timeout", None)

        # 提取 extra_body，DeepSeek 会在内部强制覆盖 enable_thinking
        user_extra_body = kwargs.pop("extra_body", None) or {}

        # 兼容讯飞不同代际网关：/x2、/v2 仅接受 spark-x；/v1 接受 generalv3.5 等模型名。
        if model_type == "spark":
            return ChatOpenAI(
                model=cls._spark_model_name(SPARK_MAX_API_BASE),
                api_key=SPARK_MAX_API_PASSWORD,
                base_url=SPARK_MAX_API_BASE,
                temperature=temperature,
                streaming=streaming,
                max_tokens=max_tokens,
                max_retries=max_retries,
                timeout=timeout,
                **kwargs,
            )

        # 创建 Spark X 模型
        if model_type == "spark_x":
            return ChatOpenAI(
                model="spark-x",
                api_key=SPARK_X_API_PASSWORD,
                base_url=SPARK_X_API_BASE,
                temperature=temperature,
                streaming=streaming,
                max_tokens=max_tokens,
                max_retries=max_retries,
                timeout=timeout,
                **kwargs,
            )

        # 创建 DeepSeek 快速模型，关闭思考模式
        if model_type == "deepseek":
            return ChatOpenAI(
                model="deepseek-chat",
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_API_BASE,
                temperature=temperature,
                streaming=streaming,
                max_tokens=max_tokens,
                max_retries=max_retries,
                timeout=timeout,
                extra_body={
                    **user_extra_body,
                    "enable_thinking": False,
                },
                **kwargs,
            )

        # 创建 DeepSeek 快速模型，开启思考模式
        if model_type == "deepseek_reasoner":
            return ChatOpenAI(
                model="deepseek-reasoner",
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_API_BASE,
                temperature=temperature,
                streaming=streaming,
                max_tokens=max_tokens,
                max_retries=max_retries,
                timeout=timeout,
                extra_body={
                    **user_extra_body,
                    "enable_thinking": True,
                },
                **kwargs,
            )

        # 创建 GLM 视觉模型
        if model_type == "glm_vision":
            return ChatOpenAI(
                model=GLM_VISION_MODEL,
                api_key=GLM_API_KEY,
                base_url="https://open.bigmodel.cn/api/paas/v4/",
                temperature=temperature,
                streaming=streaming,
                max_tokens=max_tokens,
                max_retries=max_retries,
                timeout=timeout,
                **kwargs,
            )

        raise ValueError(f"Unsupported model_type: {model_type}")


class LlmManager:
    """极简统一 LLM 管理器。"""

    DEFAULT_TIMEOUT_SECONDS = 10.0

    # 不同模型类型的默认并发上限
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
        # 缓存已经创建过的模型实例，避免重复初始化
        self._models: dict[tuple[str, tuple[tuple[str, Hashable], ...]], Any] = {}

        # 合并默认并发配置和外部传入的并发配置
        self._limits = dict(self.DEFAULT_CONCURRENCY_LIMITS)
        if concurrency_limits:
            self._limits.update(concurrency_limits)

        # 为有限流配置的模型类型创建信号量
        self._semaphores: dict[str, asyncio.Semaphore] = {
            model_type: asyncio.Semaphore(limit)
            for model_type, limit in self._limits.items()
            if limit > 0
        }

        # 默认获取并发槽位的超时时间
        self._timeout_seconds = timeout_seconds

    @staticmethod
    def _freeze(value: Any) -> Hashable:
        # 将 dict/list/set 等不可哈希参数转换成可哈希结构，用于生成缓存 key
        if isinstance(value, dict):
            return tuple((k, LlmManager._freeze(v)) for k, v in sorted(value.items()))

        if isinstance(value, (list, tuple)):
            return tuple(LlmManager._freeze(v) for v in value)

        if isinstance(value, set):
            return tuple(sorted(LlmManager._freeze(v) for v in value))

        return value

    def _cache_key(
        self,
        model_type: str,
        kwargs: dict[str, Any],
    ) -> tuple[str, tuple[tuple[str, Hashable], ...]]:
        # 根据真实模型类型和模型参数生成唯一缓存 key
        frozen_kwargs = tuple((k, self._freeze(v)) for k, v in sorted(kwargs.items()))
        return model_type, frozen_kwargs

    def _has_available_slot(self, model_type: str) -> bool:
        """检查指定模型类型是否有可用并发槽位。"""
        semaphore = self._semaphores.get(model_type)
        if semaphore is None:
            return True  # 没有配置并发限制的模型默认认为可用

        # 直接检查当前信号量剩余值，用于判断是否需要溢出
        return semaphore._value > 0

    def _resolve_model_type(self, model_type: str) -> str:
        """根据当前并发情况解析真实使用的模型类型。"""
        actual_model_type = model_type

        # Spark 系列模型并发已满时，自动切换到普通 deepseek
        overflow_types = ("spark", "spark_x")
        if actual_model_type in overflow_types and not self._has_available_slot(actual_model_type):
            logger.info("[LLM] %s 并发已满，溢出到 deepseek", actual_model_type)
            actual_model_type = "deepseek"

        return actual_model_type

    def get_model(self, model_type: str, **kwargs: Any) -> tuple[str, Any]:
        """获取模型实例（缓存命中则复用）。

        当 spark/spark_x 并发已满时，自动溢出到 deepseek。

        Returns:
            tuple[str, Any]: 真实使用的模型类型和模型实例。
        """
        # 获取真实使用的模型类型
        actual_model_type = self._resolve_model_type(model_type)

        # 禁止 model 参数参与缓存 key，避免传错 model 导致缓存污染
        kwargs.pop("model", None)

        # 优先从缓存中获取已创建的模型实例
        key = self._cache_key(actual_model_type, kwargs)
        model = self._models.get(key)
        if model is not None:
            return actual_model_type, model

        # 缓存未命中时通过工厂创建新模型实例
        logger.debug("[LLM] 创建模型: type=%s kwargs=%s", actual_model_type, kwargs)
        model = LlmFactory.create(actual_model_type, **kwargs)
        self._models[key] = model

        return actual_model_type, model

    async def _acquire(
        self,
        model_type: str,
        timeout: float | None = None,
    ) -> asyncio.Semaphore | None:
        # 获取当前模型类型对应的并发信号量
        semaphore = self._semaphores.get(model_type)
        if semaphore is None:
            return None

        # 优先使用调用方传入的 timeout，否则使用默认超时时间
        effective_timeout = self._timeout_seconds if timeout is None else timeout

        try:
            # 在指定时间内等待获取并发槽位
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
        # 获取真实使用的模型类型和模型实例
        actual_model_type, llm = self.get_model(model_type, **(model_kwargs or {}))

        # 按真实模型类型进行并发控制
        semaphore = await self._acquire(actual_model_type, timeout=timeout)

        try:
            # 执行 LangChain 模型的异步调用
            return await llm.ainvoke(input_data, **invoke_kwargs)
        finally:
            # 无论调用成功或失败，都释放真实模型对应的并发槽位
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

        # 如果传入 model_type，则对 Runnable 调用也启用并发控制
        if model_type is not None:
            actual_model_type = self._resolve_model_type(model_type)
            semaphore = await self._acquire(actual_model_type, timeout=timeout)

        try:
            # 执行 Runnable 的异步调用
            return await runnable.ainvoke(input_data, **invoke_kwargs)
        finally:
            # 调用完成后释放并发槽位
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
        # 获取真实使用的模型类型和模型实例
        actual_model_type, llm = self.get_model(model_type, **(model_kwargs or {}))

        # 按真实模型类型进行并发控制
        semaphore = await self._acquire(actual_model_type, timeout=timeout)

        try:
            # 持续产出模型流式返回的 chunk
            async for chunk in llm.astream(input_data, **stream_kwargs):
                yield chunk
        finally:
            # 流式结束或异常中断后释放真实模型对应的并发槽位
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

        # 如果传入 model_type，则对 Runnable 流式调用也启用并发控制
        if model_type is not None:
            actual_model_type = self._resolve_model_type(model_type)
            semaphore = await self._acquire(actual_model_type, timeout=timeout)

        try:
            # 持续产出 Runnable 流式返回的 chunk
            async for chunk in runnable.astream(input_data, **stream_kwargs):
                yield chunk
        finally:
            # 流式结束后释放并发槽位
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
        # 获取模型后绑定工具，返回可调用的 Runnable
        _, llm = self.get_model(model_type, **(model_kwargs or {}))
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
        # 获取模型后绑定结构化输出 schema
        _, llm = self.get_model(model_type, **(model_kwargs or {}))
        return llm.with_structured_output(schema, **kwargs)

    async def ainvoke_structured(
        self,
        model_type: str,
        schema: type[Any],
        input_data: Any,
        *,
        timeout: float | None = None,
        strict: bool = True,
        function_name: str | None = None,
        function_description: str | None = None,
        model_kwargs: dict[str, Any] | None = None,
        **invoke_kwargs: Any,
    ) -> Any:
        """使用 function calling strict 调用模型，并将 tool args 校验为 schema。"""
        actual_model_type, llm = self.get_model(model_type, **(model_kwargs or {}))
        semaphore = await self._acquire(actual_model_type, timeout=timeout)

        tool_name = function_name or schema.__name__
        tool_description = function_description or f"Return a structured {schema.__name__} object."
        tools = [
            {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool_description,
                    "strict": strict,
                    "parameters": schema.model_json_schema(),
                },
            }
        ]

        try:
            runnable = llm.bind_tools(tools, tool_choice="required")
            response = await runnable.ainvoke(input_data, **invoke_kwargs)
            tool_calls = getattr(response, "tool_calls", []) or []
            if not tool_calls:
                raise ValueError("model returned no tool_calls for structured output")
            payload = tool_calls[0].get("args") or {}
            return schema.model_validate(payload)
        finally:
            if semaphore is not None:
                semaphore.release()


@lru_cache(maxsize=1)
def get_llm_manager() -> LlmManager:
    """LlmManager 单例。"""
    # 使用 lru_cache 确保整个进程中只创建一个 LlmManager 实例
    return LlmManager()
