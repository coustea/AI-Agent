"""LLM 管理器。

职责：
- 从 config.yaml 加载模型配置
- 按生成类型路由：不同类型使用不同模型
- 模型缓存：LRU 缓存避免重复创建
- 并发控制：Semaphore 限制并发调用

使用方式：
    manager = get_llm_manager()

    # 按生成类型调用
    await manager.generate(messages)  # 默认 spark_x
    await manager.chat(messages)      # 聊天 spark_max
    await manager.generate_json(MySchema, messages)  # JSON spark_max
    await manager.generate_light(messages)  # 轻量 spark_flash

    # 流式输出
    async for chunk in manager.stream(messages):
        ...

    # 直接指定模型（内部使用）
    await manager.ainvoke("spark_max", messages)
"""

from __future__ import annotations

import asyncio
import json
from collections import OrderedDict
from enum import Enum
from functools import lru_cache
from typing import Any, AsyncIterator

from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from app.config import get
from app.infra.logging import get_logger
from app.utils.json import parse_first_json_object

logger = get_logger(__name__)


# ============ 异常 ============

class LLMBusyError(Exception):
    """并发超限。"""


class LLMOutputError(Exception):
    """结构化输出失败。"""

    def __init__(self, model: str, schema: str, msg: str):
        super().__init__(f"[{model}] {schema}: {msg}")


class LLMConfigError(Exception):
    """模型配置缺失。"""


# ============ 生成类型枚举 ============

class GenerateType(Enum):
    """生成类型枚举。

    - DEFAULT: 普通生成（Markdown、Mermaid、课程内容等）→ spark_x
    - CHAT: 聊天模块专用 → spark_max
    - JSON: 结构化 JSON 输出 → spark_max
    - TOOLS: 工具调用 → spark_max
    - LIGHT: 轻量任务（摘要、标题等）→ spark_flash
    """
    DEFAULT = "default"
    CHAT = "chat"
    JSON = "json"
    TOOLS = "tools"
    LIGHT = "light"


# 默认策略配置
_DEFAULT_POLICY = {
    "default": "spark_x",
    "chat": "spark_max",
    "json": "spark_max",
    "tools": "spark_max",
    "light": "spark_flash",
}


def _model_for_type(generate_type: GenerateType) -> str:
    """根据生成类型获取模型名称。"""
    policy = get("models.policy", {}) or {}
    return policy.get(generate_type.value, _DEFAULT_POLICY[generate_type.value])


# ============ LLM 管理器 ============

class LlmManager:
    """统一 LLM 管理器。

    按生成类型路由模型，提供统一的生成接口。
    """

    CACHE_SIZE = 64

    def __init__(self):
        self._models: OrderedDict = OrderedDict()
        self._semaphores: dict[str, asyncio.Semaphore] = {}
        self._init()

    def _init(self):
        """初始化并发控制。"""
        for name, cfg in get("models", {}).items():
            if name in ("cloud", "policy"):
                continue
            limit = cfg.get("concurrency", 10)
            if limit > 0:
                self._semaphores[name] = asyncio.Semaphore(limit)

    def _cache_key(self, name: str, kwargs: dict) -> tuple:
        """生成缓存 key。"""
        def freeze(v):
            if isinstance(v, dict):
                return tuple(sorted((k, freeze(v)) for k, v in v.items()))
            if isinstance(v, (list, tuple)):
                return tuple(freeze(x) for x in v)
            return v
        return (name, tuple(sorted((k, freeze(v)) for k, v in kwargs.items())))

    def _get_model(self, name: str, **kwargs) -> ChatOpenAI:
        """获取模型实例（带缓存）。"""
        kwargs.pop("model", None)
        key = self._cache_key(name, kwargs)

        if key in self._models:
            self._models.move_to_end(key)
            return self._models[key]

        cfg = get(f"models.{name}", {})
        if not cfg:
            raise LLMConfigError(f"模型配置缺失: {name}")

        model = ChatOpenAI(
            model=cfg["model_name"],
            api_key=cfg["api_key"],
            base_url=cfg["base_url"].rstrip("/chat/completions").rstrip("/"),
            temperature=kwargs.pop("temperature", 0.3),
            streaming=kwargs.pop("streaming", False),
            max_tokens=kwargs.pop("max_tokens", None),
            max_retries=kwargs.pop("max_retries", 2),
            timeout=kwargs.pop("timeout", 300),
            **kwargs,
        )

        self._models[key] = model
        if len(self._models) > self.CACHE_SIZE:
            self._models.popitem(last=False)
        return model

    async def _acquire(self, name: str) -> asyncio.Semaphore | None:
        """获取并发槽位。"""
        sem = self._semaphores.get(name)
        if not sem:
            return None
        try:
            await asyncio.wait_for(sem.acquire(), timeout=300)
        except asyncio.TimeoutError as e:
            raise LLMBusyError(f"并发超限: {name}") from e
        return sem

    # ============ 核心生成方法 ============

    async def generate(
        self,
        input_data,
        generate_type: GenerateType = GenerateType.DEFAULT,
        *,
        module: str | None = None,
        **kwargs
    ) -> Any:
        """统一生成入口。

        Args:
            input_data: 输入数据（消息列表或提示词）。
            generate_type: 生成类型，决定使用哪个模型。
            module: 模块名（仅用于日志，不参与模型选择）。
            **kwargs: 传递给模型的参数（temperature, max_tokens 等）。

        Returns:
            模型响应。
        """
        model = _model_for_type(generate_type)
        if module:
            logger.debug("[LlmManager] generate type=%s model=%s module=%s",
                         generate_type.value, model, module)
        return await self.ainvoke(model, input_data, **kwargs)

    async def stream(
        self,
        input_data,
        generate_type: GenerateType = GenerateType.DEFAULT,
        *,
        module: str | None = None,
        **kwargs
    ) -> AsyncIterator[Any]:
        """流式生成。

        Args:
            input_data: 输入数据。
            generate_type: 生成类型。
            module: 模块名（仅用于日志）。
            **kwargs: 传递给模型的参数。

        Yields:
            流式响应块。
        """
        model = _model_for_type(generate_type)
        if module:
            logger.debug("[LlmManager] stream type=%s model=%s module=%s",
                         generate_type.value, model, module)
        async for chunk in self.astream(model, input_data, **kwargs):
            yield chunk

    # ============ 便捷方法 ============

    async def generate_json(
        self,
        schema: type,
        input_data,
        *,
        module: str | None = None,
        **kwargs
    ) -> Any:
        """结构化 JSON 输出。

        使用 spark_max 进行结构化输出。

        Args:
            schema: Pydantic 模型类。
            input_data: 输入数据。
            module: 模块名（仅用于日志）。
            **kwargs: 传递给模型的参数。

        Returns:
            验证后的 schema 实例。
        """
        model = _model_for_type(GenerateType.JSON)
        if module:
            logger.debug("[LlmManager] generate_json model=%s module=%s", model, module)
        return await self.ainvoke_structured(model, schema, input_data, **kwargs)

    async def generate_light(
        self,
        input_data,
        *,
        module: str | None = None,
        **kwargs
    ) -> Any:
        """轻量任务生成。

        使用 spark_flash 进行轻量级生成（摘要、标题等）。

        Args:
            input_data: 输入数据。
            module: 模块名（仅用于日志）。
            **kwargs: 传递给模型的参数。

        Returns:
            模型响应。
        """
        model = _model_for_type(GenerateType.LIGHT)
        if module:
            logger.debug("[LlmManager] generate_light model=%s module=%s", model, module)
        return await self.ainvoke(model, input_data, **kwargs)

    async def chat(
        self,
        input_data,
        *,
        module: str = "chat",
        **kwargs
    ) -> Any:
        """聊天模块专用生成。

        使用 spark_max 进行聊天对话。

        Args:
            input_data: 输入数据。
            module: 模块名（默认 chat）。
            **kwargs: 传递给模型的参数。

        Returns:
            模型响应。
        """
        model = _model_for_type(GenerateType.CHAT)
        logger.debug("[LlmManager] chat model=%s module=%s", model, module)
        return await self.ainvoke(model, input_data, **kwargs)

    async def chat_stream(
        self,
        input_data,
        *,
        module: str = "chat",
        **kwargs
    ) -> AsyncIterator[Any]:
        """聊天模块流式输出。

        使用 spark_max 进行流式聊天。

        Args:
            input_data: 输入数据。
            module: 模块名（默认 chat）。
            **kwargs: 传递给模型的参数。

        Yields:
            流式响应块。
        """
        model = _model_for_type(GenerateType.CHAT)
        logger.debug("[LlmManager] chat_stream model=%s module=%s", model, module)
        async for chunk in self.astream(model, input_data, **kwargs):
            yield chunk

    async def chat_json(
        self,
        schema: type,
        input_data,
        *,
        module: str = "chat",
        **kwargs
    ) -> Any:
        """聊天模块结构化输出。

        使用 spark_max 进行结构化输出。

        Args:
            schema: Pydantic 模型类。
            input_data: 输入数据。
            module: 模块名（默认 chat）。
            **kwargs: 传递给模型的参数。

        Returns:
            验证后的 schema 实例。
        """
        model = _model_for_type(GenerateType.JSON)
        logger.debug("[LlmManager] chat_json model=%s module=%s", model, module)
        return await self.ainvoke_structured(model, schema, input_data, **kwargs)

    # ============ 工具调用 ============

    def bind_tools(
        self,
        tools: list,
        *,
        module: str | None = None,
        **kwargs
    ) -> Any:
        """绑定工具到模型。

        使用 spark_max 进行工具调用。

        Args:
            tools: 工具列表。
            module: 模块名（仅用于日志）。
            **kwargs: 传递给模型的参数。

        Returns:
            绑定工具后的 Runnable。
        """
        model = _model_for_type(GenerateType.TOOLS)
        if module:
            logger.debug("[LlmManager] bind_tools model=%s module=%s", model, module)
        return self._get_model(model, **kwargs).bind_tools(tools)

    async def generate_with_tools(
        self,
        tools: list,
        input_data,
        *,
        module: str | None = None,
        **kwargs
    ) -> Any:
        """带工具调用的生成。

        使用 spark_max 进行工具调用生成。

        Args:
            tools: 工具列表。
            input_data: 输入数据。
            module: 模块名（仅用于日志）。
            **kwargs: 传递给模型的参数。

        Returns:
            模型响应。
        """
        model = _model_for_type(GenerateType.TOOLS)
        if module:
            logger.debug("[LlmManager] generate_with_tools model=%s module=%s", model, module)
        runnable = self._get_model(model, **kwargs).bind_tools(tools, tool_choice="required")
        return await runnable.ainvoke(input_data, **kwargs)

    # ============ 底层方法（直接指定模型）============

    async def ainvoke(self, name: str, input_data, model_kwargs: dict = None, **kwargs) -> Any:
        """异步调用模型，直接返回完整响应。

        Args:
            name: 模型名称（spark_max, spark_x, spark_flash 等）。
            input_data: 输入数据。
            model_kwargs: 模型参数。
            **kwargs: 其他参数。

        Returns:
            模型响应。
        """
        sem = await self._acquire(name)
        model = self._get_model(name, **(model_kwargs or {}))
        try:
            return await model.ainvoke(input_data, **kwargs)
        finally:
            if sem:
                sem.release()

    async def ainvoke_structured(
        self,
        name: str,
        schema: type,
        input_data,
        model_kwargs: dict = None,
        **kwargs
    ) -> Any:
        """异步调用模型，返回结构化输出（JSON）。

        Args:
            name: 模型名称。
            schema: Pydantic 模型类。
            input_data: 输入数据。
            model_kwargs: 模型参数。
            **kwargs: 其他参数。

        Returns:
            验证后的 schema 实例。

        Raises:
            LLMOutputError: 结构化输出失败。
        """
        sem = await self._acquire(name)
        model = self._get_model(name, **(model_kwargs or {}))

        function_name = kwargs.pop("function_name", schema.__name__)
        function_description = kwargs.pop("function_description", f"Return {schema.__name__}")

        tools = [{
            "type": "function",
            "function": {
                "name": function_name,
                "description": function_description,
                "strict": True,
                "parameters": schema.model_json_schema(),
            },
        }]

        try:
            runnable = model.bind_tools(tools, tool_choice="required")
            resp = await runnable.ainvoke(input_data, **kwargs)
            tool_calls = getattr(resp, "tool_calls", []) or []

            if tool_calls:
                args = tool_calls[0].get("args") if isinstance(tool_calls[0], dict) else getattr(tool_calls[0], "args", None)
                if args:
                    return schema.model_validate(args)

            content = getattr(resp, "content", "") or ""
            parsed = parse_first_json_object(content)
            if parsed:
                return schema.model_validate(parsed)

            fallback = self._get_model(name, model_kwargs={"response_format": {"type": "json_object"}})
            resp = await fallback.ainvoke(input_data, **kwargs)
            return schema.model_validate(parse_first_json_object(resp.content))

        except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as e:
            raise LLMOutputError(name, schema.__name__, str(e))
        finally:
            if sem:
                sem.release()

    async def astream(self, name: str, input_data, model_kwargs: dict = None, **kwargs) -> AsyncIterator[Any]:
        """异步流式调用模型。

        Args:
            name: 模型名称。
            input_data: 输入数据。
            model_kwargs: 模型参数。
            **kwargs: 其他参数。

        Yields:
            流式响应块。
        """
        sem = await self._acquire(name)
        model = self._get_model(name, **(model_kwargs or {}))
        try:
            async for chunk in model.astream(input_data, **kwargs):
                yield chunk
        finally:
            if sem:
                sem.release()

    def get_model(self, name: str, **kwargs) -> ChatOpenAI:
        """获取模型实例。

        Args:
            name: 模型名称。
            **kwargs: 模型参数。

        Returns:
            ChatOpenAI 实例。
        """
        return self._get_model(name, **kwargs)


@lru_cache(maxsize=1)
def get_llm_manager() -> LlmManager:
    """获取单例。"""
    return LlmManager()
