"""统一 LLM 管理器。

职责：
- 创建模型：根据 model_type 创建对应的 ChatOpenAI 实例
- 缓存模型：使用 LRU 缓存避免重复创建相同配置的模型
- 获取模型：通过 get_model() 获取缓存的模型实例
- 控制并发：使用 Semaphore 限制每种模型的并发调用数
- 异步调用（ainvoke）：非流式调用，返回完整响应
- 异步流式调用（astream）：流式调用，逐块返回响应

支持的模型类型：
- spark_max：讯飞星火大模型 generalv3.5（主要对话模型）
- spark_x：讯飞星火大模型 spark-x（高并发场景）
- glm_vision：智谱 GLM 视觉模型（图像理解）

使用方式：
    manager = get_llm_manager()  # 获取单例
    
    # 简单调用
    response = await manager.ainvoke("spark_max", [HumanMessage(content="你好")])
    
    # 流式调用
    for chunk in manager.astream("spark_max", messages):
        print(chunk.content)
    
    # 结构化输出（JSON）
    result = await manager.ainvoke_structured("spark_max", MySchema, messages)
"""

from __future__ import annotations

import asyncio
import json
from collections import OrderedDict
from functools import lru_cache
from typing import Any, AsyncIterator, Hashable

from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from app.config import (
    GLM_API_KEY,
    GLM_VISION_MODEL,
    LLM_TIMEOUT,
    SPARK_MAX_API_PASSWORD,
    SPARK_MAX_API_BASE,
    SPARK_X_API_PASSWORD,
    SPARK_X_API_BASE,
    SPARK_X2_FLASH_API_PASSWORD,
    SPARK_X2_FLASH_API_BASE,
)
from app.infra.logging import get_logger
from app.utils.json import parse_first_json_object, preview_for_log

logger = get_logger(__name__)


# ----------------------------
# 异常定义
# ----------------------------

class LLMConcurrencyBusyError(Exception):
    """并发超限时抛出。"""


class LLMStructuredOutputError(Exception):
    """结构化输出解析或校验失败时抛出。"""

    def __init__(
        self,
        *,
        model_type: str,
        schema_name: str,
        function_name: str,
        stage: str,
        message: str,
        payload: Any = None,
    ) -> None:
        payload_text = ""
        if payload is not None:
            payload_text = f", payload={preview_for_log(payload)}"
        super().__init__(
            f"LLM structured output failed: model_type={model_type}, "
            f"schema={schema_name}, function_name={function_name}, "
            f"stage={stage}, error={message}{payload_text}"
        )
        self.model_type = model_type
        self.schema_name = schema_name
        self.function_name = function_name
        self.stage = stage
        self.payload = payload


# ----------------------------
# LLM 工厂类
# ----------------------------

class LlmFactory:
    """根据 model_type 创建 ChatOpenAI 实例。"""

    @staticmethod
    def _require_non_empty(name: str, value: str) -> None:
        """检查配置项非空。"""
        if not (value or "").strip():
            raise ValueError(f"Missing required config: {name}")

    @classmethod
    def create(cls, model_type: str, **kwargs: Any) -> Any:
        """创建 ChatOpenAI 实例。

        Args:
            model_type: 模型类型，支持 spark_max / spark_x / glm_vision
            **kwargs: 传递给 ChatOpenAI 的参数

        Returns:
            ChatOpenAI 实例
        """
        kwargs.pop("model", None)  # 忽略外部传入的 model 参数

        # 提取通用参数
        temperature = kwargs.pop("temperature", 0.3)
        streaming = kwargs.pop("streaming", False)
        max_tokens = kwargs.pop("max_tokens", None)
        max_retries = kwargs.pop("max_retries", 2)
        timeout = kwargs.pop("timeout", None)

        # spark_max: 讯飞星火 generalv3.5（主力模型）
        if model_type == "spark_max":
            cls._require_non_empty("SPARK_MAX_API_PASSWORD", SPARK_MAX_API_PASSWORD)
            cls._require_non_empty("SPARK_MAX_API_BASE", SPARK_MAX_API_BASE)
            return ChatOpenAI(
                model="generalv3.5",
                api_key=SPARK_MAX_API_PASSWORD,
                base_url=SPARK_MAX_API_BASE,
                temperature=temperature,
                streaming=streaming,
                max_tokens=max_tokens,
                max_retries=max_retries,
                timeout=timeout,
                **kwargs,
            )

        # spark_x: 讯飞星火 spark-x（高并发场景）
        if model_type == "spark_x":
            cls._require_non_empty("SPARK_X_API_PASSWORD", SPARK_X_API_PASSWORD)
            cls._require_non_empty("SPARK_X_API_BASE", SPARK_X_API_BASE)
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

        # spark_x2_flash: 讯飞星火 spark-x2-flash（轻量快速模型，用于标题生成等）
        if model_type == "spark_x2_flash":
            cls._require_non_empty("SPARK_X2_FLASH_API_PASSWORD", SPARK_X2_FLASH_API_PASSWORD)
            cls._require_non_empty("SPARK_X2_FLASH_API_BASE", SPARK_X2_FLASH_API_BASE)
            return ChatOpenAI(
                model="spark-x2-flash",
                api_key=SPARK_X2_FLASH_API_PASSWORD,
                base_url=SPARK_X2_FLASH_API_BASE,
                temperature=temperature,
                streaming=streaming,
                max_tokens=max_tokens,
                max_retries=max_retries,
                timeout=timeout,
                **kwargs,
            )

        # glm_vision: 智谱 GLM 视觉模型（图像理解）
        if model_type == "glm_vision":
            cls._require_non_empty("GLM_API_KEY", GLM_API_KEY)
            cls._require_non_empty("GLM_VISION_MODEL", GLM_VISION_MODEL)
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


# ----------------------------
# LLM 管理器
# ----------------------------

class LlmManager:
    """统一 LLM 管理器，提供模型缓存、并发控制、异步调用能力。"""

    DEFAULT_TIMEOUT_SECONDS = float(LLM_TIMEOUT)
    DEFAULT_MODEL_CACHE_SIZE = 64  # LRU 缓存大小

    # 各模型类型的并发限制
    DEFAULT_CONCURRENCY_LIMITS: dict[str, int] = {
        "spark_max": 10,  # 主力模型，并发较低
        "spark_x": 20,    # 高并发场景
        "spark_x2_flash": 20,  # 轻量模型，高并发
    }

    def __init__(
        self,
        *,
        concurrency_limits: dict[str, int] | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        model_cache_size: int = DEFAULT_MODEL_CACHE_SIZE,
    ) -> None:
        """初始化管理器。

        Args:
            concurrency_limits: 自定义并发限制，会覆盖默认值
            timeout_seconds: 获取并发槽位的超时时间
            model_cache_size: 模型 LRU 缓存大小
        """
        # 模型缓存：key=(model_type, frozen_kwargs), value=ChatOpenAI
        self._models: OrderedDict[tuple[str, tuple[tuple[str, Hashable], ...]], Any] = OrderedDict()
        self._model_cache_size = max(1, model_cache_size)

        # 合并默认和自定义并发限制
        self._limits = dict(self.DEFAULT_CONCURRENCY_LIMITS)
        if concurrency_limits:
            self._limits.update(concurrency_limits)
        
        # 为每种模型创建 Semaphore
        self._semaphores: dict[str, asyncio.Semaphore] = {
            model_type: asyncio.Semaphore(limit)
            for model_type, limit in self._limits.items()
            if limit > 0
        }

        self._timeout_seconds = timeout_seconds

    @staticmethod
    def _freeze(value: Any) -> Hashable:
        """将任意值转换为可哈希类型，用于生成缓存 key。"""
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
        """生成缓存 key。"""
        frozen_kwargs = tuple((k, self._freeze(v)) for k, v in sorted(kwargs.items()))
        return model_type, frozen_kwargs

    def _get_model(
        self,
        model_type: str,
        **kwargs: Any,
    ) -> Any:
        """获取模型实例（带 LRU 缓存）。"""
        kwargs.pop("model", None)

        key = self._cache_key(model_type, kwargs)
        model = self._models.get(key)
        if model is not None:
            self._models.move_to_end(key)  # LRU: 移到队尾
            return model

        # 缓存未命中，创建新模型
        logger.debug("[LLM] 创建模型: type=%s kwargs=%s", model_type, kwargs)
        model = LlmFactory.create(model_type, **kwargs)
        self._models[key] = model
        if len(self._models) > self._model_cache_size:
            self._models.popitem(last=False)  # LRU: 删除队首

        return model

    def get_model(self, model_type: str, **kwargs: Any) -> Any:
        """获取模型实例。"""
        return self._get_model(model_type, **kwargs)

    async def _acquire(
        self,
        model_type: str,
        timeout: float | None = None,
    ) -> asyncio.Semaphore | None:
        """获取并发槽位，超时抛出 LLMConcurrencyBusyError。"""
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
        """异步调用 LLM（非流式）。"""
        semaphore = await self._acquire(model_type, timeout=timeout)
        llm = self._get_model(model_type, **(model_kwargs or {}))

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
        """异步调用 Runnable（如 bind_tools/structured_output 返回的对象）。"""
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
        """异步流式调用 LLM。"""
        semaphore = await self._acquire(model_type, timeout=timeout)
        llm = self._get_model(model_type, **(model_kwargs or {}))

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
        """异步流式调用 Runnable。"""
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
        """绑定工具到模型，返回 Runnable。"""
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

    @staticmethod
    def _tool_call_name(tool_call: Any) -> str | None:
        """兼容 LangChain/OpenAI 常见 tool_call 结构，提取函数名。"""
        if isinstance(tool_call, dict):
            if isinstance(tool_call.get("name"), str):
                return tool_call["name"]
            function = tool_call.get("function")
            if isinstance(function, dict) and isinstance(function.get("name"), str):
                return function["name"]
            return None
        name = getattr(tool_call, "name", None)
        return name if isinstance(name, str) else None

    @staticmethod
    def _tool_call_args(tool_call: Any) -> Any:
        """兼容 LangChain/OpenAI 常见 tool_call 结构，提取函数参数。"""
        if isinstance(tool_call, dict):
            if "args" in tool_call:
                return tool_call.get("args")
            function = tool_call.get("function")
            if isinstance(function, dict):
                return function.get("arguments")
            return None
        if hasattr(tool_call, "args"):
            return getattr(tool_call, "args")
        function = getattr(tool_call, "function", None)
        if function is not None:
            return getattr(function, "arguments", None)
        return None

    @staticmethod
    def _coerce_structured_payload(raw_payload: Any) -> dict[str, Any]:
        """把模型返回的工具参数转换为 dict；字符串走非正则 JSON 解析。"""
        if isinstance(raw_payload, dict):
            return raw_payload
        if isinstance(raw_payload, str):
            return parse_first_json_object(raw_payload)
        if raw_payload is None:
            return {}
        if hasattr(raw_payload, "model_dump"):
            dumped = raw_payload.model_dump()
            if isinstance(dumped, dict):
                return dumped
        if isinstance(raw_payload, bytes):
            return parse_first_json_object(raw_payload.decode("utf-8"))
        raise TypeError(f"expected structured payload dict or JSON string, got {type(raw_payload).__name__}")

    def _select_tool_call(self, tool_calls: list[Any], tool_name: str) -> Any | None:
        """优先按函数名选择 tool_call，缺少 name 时回退第一个。"""
        for tool_call in tool_calls:
            if self._tool_call_name(tool_call) == tool_name:
                return tool_call
        if len(tool_calls) == 1:
            return tool_calls[0]
        return None

    def _validate_structured_payload(
        self,
        *,
        schema: type[Any],
        payload: Any,
        model_type: str,
        tool_name: str,
        stage: str,
    ) -> Any:
        try:
            coerced = self._coerce_structured_payload(payload)
            return schema.model_validate(coerced)
        except (json.JSONDecodeError, TypeError, ValueError, ValidationError) as exc:
            raise LLMStructuredOutputError(
                model_type=model_type,
                schema_name=schema.__name__,
                function_name=tool_name,
                stage=stage,
                message=str(exc),
                payload=payload,
            ) from exc

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
        fallback_to_json: bool = True,
        model_kwargs: dict[str, Any] | None = None,
        **invoke_kwargs: Any,
    ) -> Any:
        """使用 function calling 获取结构化输出（JSON）。

        通过 bind_tools + tool_choice="required" 强制模型调用指定函数。
        若 provider 没有返回 tool_calls，默认退回普通 JSON 文本解析。
        """
        semaphore = await self._acquire(model_type, timeout=timeout)
        base_model_kwargs = dict(model_kwargs or {})
        llm = self._get_model(model_type, **base_model_kwargs)

        # 构建 function calling 工具定义
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
            structured_error: LLMStructuredOutputError | None = None
            try:
                runnable = llm.bind_tools(tools, tool_choice="required")
                response = await runnable.ainvoke(input_data, **invoke_kwargs)
                tool_calls = getattr(response, "tool_calls", []) or []
                selected_tool_call = self._select_tool_call(tool_calls, tool_name)
                if selected_tool_call is not None:
                    payload = self._tool_call_args(selected_tool_call)
                    try:
                        return self._validate_structured_payload(
                            schema=schema,
                            payload=payload,
                            model_type=model_type,
                            tool_name=tool_name,
                            stage="tool_args",
                        )
                    except LLMStructuredOutputError as exc:
                        structured_error = exc
                else:
                    # 某些模型（如讯飞星火）即使设置了 tool_choice="required" 也不返回
                    # tool_calls，而是直接将 JSON 放在 response.content 中。先尝试从
                    # content 提取 JSON 作为快速回退，避免多一次网络调用。
                    response_content = getattr(response, "content", "") or ""
                    content_parsed = parse_first_json_object(response_content)
                    if content_parsed:
                        try:
                            return self._validate_structured_payload(
                                schema=schema,
                                payload=content_parsed,
                                model_type=model_type,
                                tool_name=tool_name,
                                stage="content_json",
                            )
                        except LLMStructuredOutputError as exc:
                            structured_error = exc
                    else:
                        structured_error = LLMStructuredOutputError(
                            model_type=model_type,
                            schema_name=schema.__name__,
                            function_name=tool_name,
                            stage="no_tool_calls",
                            message="model returned no matching tool_calls for structured output",
                            payload=tool_calls,
                        )
            except Exception as exc:
                structured_error = LLMStructuredOutputError(
                    model_type=model_type,
                    schema_name=schema.__name__,
                    function_name=tool_name,
                    stage="tool_call_failed",
                    message=str(exc),
                )

            if not fallback_to_json:
                raise structured_error

            fallback_model_kwargs = {
                **base_model_kwargs,
                "streaming": False,
                "model_kwargs": {"response_format": {"type": "json_object"}},
            }
            fallback_llm = self._get_model(model_type, **fallback_model_kwargs)
            fallback_response = await fallback_llm.ainvoke(input_data, **invoke_kwargs)
            raw_content = getattr(fallback_response, "content", fallback_response)
            try:
                return self._validate_structured_payload(
                    schema=schema,
                    payload=raw_content,
                    model_type=model_type,
                    tool_name=tool_name,
                    stage="json_fallback",
                )
            except LLMStructuredOutputError as exc:
                raise LLMStructuredOutputError(
                    model_type=model_type,
                    schema_name=schema.__name__,
                    function_name=tool_name,
                    stage="fallback_failed",
                    message=f"{structured_error}; {exc}",
                    payload=raw_content,
                ) from exc
        finally:
            if semaphore is not None:
                semaphore.release()


# ----------------------------
# 单例获取
# ----------------------------

@lru_cache(maxsize=1)
def get_llm_manager() -> LlmManager:
    """获取 LlmManager 单例。"""
    return LlmManager()
