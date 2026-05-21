"""LLM 管理器。

职责：
- 从 config.yaml 加载模型配置
- 提供统一的文本生成和结构化输出接口
- 并发控制：Semaphore 限制并发调用

使用方式：
    llm = get_llm()

    # 文本生成
    response = await llm.ainvoke(messages)

    # 使用 LangChain 原生工具绑定
    tool_model = llm.model.bind_tools(tools)
    response = await llm.ainvoke(messages, model=tool_model)

    # 结构化 JSON 输出
    result = await llm.ainvoke_json(MySchema, messages)

    # 流式输出
    async for chunk in llm.astream(messages):
        ...

    # 图片理解
    response = await llm.vision(messages)
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator

from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from app.config import get
from app.infra.errors import ServiceError
from app.infra.logging import get_logger
from app.utils.json import parse_first_json_object

logger = get_logger(__name__)


# ============ LLM 管理器 ============

class Llm:
    """统一 LLM 管理器。

    提供四种核心方法：
    - ainvoke(): 异步文本生成
    - astream(): 异步流式输出
    - ainvoke_json(): 异步结构化 JSON 输出
    - vision(): 图片理解
    """

    def __init__(self):
        self._text_model: ChatOpenAI | None = None
        self._vision_model: ChatOpenAI | None = None
        self._text_semaphore: asyncio.Semaphore | None = None
        self._vision_semaphore: asyncio.Semaphore | None = None
        self._agent_models: dict[str, ChatOpenAI] = {}
        self._init()

    @property
    def model(self) -> Any:
        """默认文本模型，供调用方使用 LangChain 原生 bind/bind_tools。"""
        if not self._text_model:
            raise ServiceError("文本模型配置缺失")
        return self._text_model

    def _init(self):
        """初始化模型和并发控制。"""
        # 文本模型配置
        text_cfg = get("models", {})
        text_cfg = {k: v for k, v in text_cfg.items() if k != "vision"}

        if text_cfg and "model_name" in text_cfg:
            self._text_model = ChatOpenAI(
                model=text_cfg["model_name"],
                api_key=text_cfg["api_key"],
                base_url=text_cfg["base_url"].rstrip("/chat/completions").rstrip("/"),
                temperature=0.3,
                streaming=False,
                max_retries=text_cfg.get("max_retries", 2),
                timeout=text_cfg.get("timeout", 300),
            )
            limit = text_cfg.get("concurrency", 10)
            if limit > 0:
                self._text_semaphore = asyncio.Semaphore(limit)

        # 图片理解模型配置
        vision_cfg = get("models.vision", {})
        if vision_cfg and "model_name" in vision_cfg:
            self._vision_model = ChatOpenAI(
                model=vision_cfg["model_name"],
                api_key=vision_cfg["api_key"],
                base_url=vision_cfg["base_url"].rstrip("/chat/completions").rstrip("/"),
                temperature=0.3,
                streaming=False,
                max_retries=vision_cfg.get("max_retries", 2),
                timeout=vision_cfg.get("timeout", 300),
            )
            limit = vision_cfg.get("concurrency", 10)
            if limit > 0:
                self._vision_semaphore = asyncio.Semaphore(limit)

    async def _acquire(self, sem: asyncio.Semaphore | None) -> asyncio.Semaphore | None:
        """获取并发槽位。"""
        if not sem:
            return None
        try:
            await asyncio.wait_for(sem.acquire(), timeout=300)
        except asyncio.TimeoutError as e:
            raise ServiceError("并发超限") from e
        return sem

    # ============ 核心方法 ============

    def _bind_text_model(
        self,
        *,
        model: Any | None = None,
        temperature: float = 0.3,
        max_tokens: int | None = None,
    ) -> Any:
        """按调用参数绑定文本模型。"""
        runnable = model or self.model

        bind_kwargs: dict[str, Any] = {}
        if temperature != 0.3:
            bind_kwargs["temperature"] = temperature
        if max_tokens is not None:
            bind_kwargs["max_tokens"] = max_tokens
        if not bind_kwargs:
            return runnable
        return runnable.bind(**bind_kwargs)

    async def ainvoke(
        self,
        input_data,
        *,
        model: Any | None = None,
        temperature: float = 0.3,
        max_tokens: int | None = None,
    ) -> Any:
        """异步文本生成。

        Args:
            input_data: 输入数据（消息列表或提示词）。
            temperature: 温度参数。
            max_tokens: 最大 token 数。

        Returns:
            模型响应。
        """
        sem = await self._acquire(self._text_semaphore)
        try:
            runnable = self._bind_text_model(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return await runnable.ainvoke(input_data)
        finally:
            if sem:
                sem.release()

    async def astream(
        self,
        input_data,
        *,
        model: Any | None = None,
        temperature: float = 0.3,
        max_tokens: int | None = None,
    ) -> AsyncIterator[Any]:
        """异步流式生成。

        Args:
            input_data: 输入数据。
            temperature: 温度参数。
            max_tokens: 最大 token 数。

        Yields:
            流式响应块。
        """
        sem = await self._acquire(self._text_semaphore)
        try:
            runnable = self._bind_text_model(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            async for chunk in runnable.astream(input_data):
                yield chunk
        finally:
            if sem:
                sem.release()

    async def ainvoke_json(
        self,
        schema: type,
        input_data,
        *,
        temperature: float = 0.3,
        function_name: str | None = None,
        function_description: str | None = None,
    ) -> Any:
        """异步结构化 JSON 输出。

        Args:
            schema: Pydantic 模型类。
            input_data: 输入数据。
            temperature: 温度参数。
            function_name: 函数名（可选，默认使用 schema 类名）。
            function_description: 函数描述（可选）。

        Returns:
            验证后的 schema 实例。
        """
        sem = await self._acquire(self._text_semaphore)
        try:
            model = self._bind_text_model(temperature=temperature)

            name = function_name or schema.__name__
            desc = function_description or f"Return {schema.__name__}"

            tools = [{
                "type": "function",
                "function": {
                    "name": name,
                    "description": desc,
                    "strict": True,
                    "parameters": schema.model_json_schema(),
                },
            }]

            errors: list[str] = []

            # 方式1: 使用 function calling
            try:
                runnable = model.bind_tools(tools, tool_choice="required")
                resp = await runnable.ainvoke(input_data)
                tool_calls = getattr(resp, "tool_calls", []) or []

                for tool_call in tool_calls:
                    call_name = tool_call.get("name") if isinstance(tool_call, dict) else getattr(tool_call, "name", None)
                    if call_name and call_name != name:
                        continue
                    args = tool_call.get("args") if isinstance(tool_call, dict) else getattr(tool_call, "args", None)
                    if args:
                        if isinstance(args, str):
                            args = json.loads(args)
                        return schema.model_validate(args)

                # 尝试从 content 解析
                content = getattr(resp, "content", "") or ""
                if content:
                    parsed = parse_first_json_object(content)
                    if parsed:
                        return schema.model_validate(parsed)
            except Exception as exc:
                errors.append(f"tool_call={type(exc).__name__}: {exc}")

            # 方式2: 使用 response_format fallback
            try:
                fallback = model.bind(response_format={"type": "json_object"})
                resp = await fallback.ainvoke(input_data)
                parsed = parse_first_json_object(getattr(resp, "content", "") or "")
                return schema.model_validate(parsed)
            except Exception as e:
                errors.append(f"fallback={type(e).__name__}: {e}")
                raise ServiceError(f"[{schema.__name__}] 结构化输出失败: {'; '.join(errors)}")

        finally:
            if sem:
                sem.release()

    async def vision(
        self,
        input_data,
        *,
        temperature: float = 0.3,
    ) -> Any:
        """图片理解生成。

        Args:
            input_data: 输入数据（包含图片的消息）。
            temperature: 温度参数。

        Returns:
            模型响应。
        """
        if not self._vision_model:
            raise ServiceError("图片理解模型配置缺失")

        sem = await self._acquire(self._vision_semaphore)
        try:
            model = self._vision_model
            if temperature != 0.3:
                model = model.bind(temperature=temperature)
            return await model.ainvoke(input_data)
        finally:
            if sem:
                sem.release()

# ============ 单例 ============

from functools import lru_cache

@lru_cache(maxsize=1)
def get_llm() -> Llm:
    """获取 LLM 单例。"""
    return Llm()
