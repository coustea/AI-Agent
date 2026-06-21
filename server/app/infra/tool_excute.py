"""项目自有的模型工具定义、注册、调用与执行。"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from pydantic import BaseModel

from app.infra.logging import get_logger


logger = get_logger(__name__)

ToolHandler = Callable[..., Awaitable[Any]]
ToolCall = dict[str, Any]
ToolRuntimeEvent = dict[str, Any]
ToolEventHandler = Callable[[ToolRuntimeEvent], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class Tool:
    """一个可供模型选择并由应用执行的工具。"""

    name: str
    description: str
    args_model: type[BaseModel]
    handler: ToolHandler

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Tool name cannot be empty")
        if not self.description.strip():
            raise ValueError(f"Tool description cannot be empty: {self.name}")

    def description_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.args_model.model_json_schema(),
            },
        }


class ToolExcute:
    """注册工具，并直接使用 ChatOpenAI 的原生 tools 参数完成调用。"""

    def __init__(
        self,
        model: Any,
        tools: Sequence[Tool] | None = None,
        event_handler: ToolEventHandler | None = None,
    ) -> None:
        self.model = model
        self._event_handler = event_handler
        self._tools: dict[str, Tool] = {}
        if tools:
            self.register_many(tools)

    def register(self, tool: Tool) -> Tool:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool
        return tool

    def register_many(self, tools: Sequence[Tool]) -> None:
        for tool in tools:
            self.register(tool)

    def get_tool(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Unknown tool: {name}") from exc

    def get_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def get_tools_description(self) -> list[dict[str, Any]]:
        return [tool.description_schema() for tool in self._tools.values()]

    def subset(self, names: Sequence[str]) -> ToolExcute:
        """创建保留当前模型与事件回调的工具子集。"""
        return ToolExcute(
            self.model,
            [self.get_tool(name) for name in names],
            event_handler=self._event_handler,
        )

    async def invoke(
        self,
        messages: Any,
        *,
        tool_choice: Any | None = None,
        **model_kwargs: Any,
    ) -> tuple[Any, list[ToolCall]]:
        kwargs = {**model_kwargs, "tools": self.get_tools_description()}
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice
        response = await self.model.ainvoke(messages, **kwargs)
        return response, self._normalize_response_calls(response)

    async def execute(self, tool_call: Mapping[str, Any]) -> Any:
        name = str(tool_call.get("name") or "").strip()
        if not name:
            raise ValueError("Tool call name cannot be empty")
        raw_args = tool_call.get("args", {})
        if not isinstance(raw_args, Mapping):
            raise ValueError(f"Tool arguments must be an object: {name}")
        tool = self.get_tool(name)
        validated = tool.args_model.model_validate(dict(raw_args))
        arguments = validated.model_dump()
        activity_id = str(tool_call.get("id") or f"call-{uuid4().hex}")
        started_at = time.perf_counter()
        await self._emit_event("running", activity_id, name, arguments)
        try:
            result = await tool.handler(**arguments)
        except Exception as exc:
            await self._emit_event(
                "failed",
                activity_id,
                name,
                arguments,
                error=str(exc),
                duration_ms=int((time.perf_counter() - started_at) * 1000),
            )
            raise
        await self._emit_event(
            "done",
            activity_id,
            name,
            arguments,
            result=result,
            duration_ms=int((time.perf_counter() - started_at) * 1000),
        )
        return result

    async def execute_all(self, tool_calls: Sequence[Mapping[str, Any]]) -> list[Any]:
        return list(
            await asyncio.gather(
                *(self.execute(call) for call in tool_calls),
                return_exceptions=True,
            )
        )

    async def _emit_event(
        self,
        status: str,
        activity_id: str,
        tool_name: str,
        arguments: Mapping[str, Any],
        *,
        result: Any = None,
        error: str | None = None,
        duration_ms: int | None = None,
    ) -> None:
        if self._event_handler is None:
            return
        try:
            await self._event_handler(
                {
                    "activity_id": activity_id,
                    "status": status,
                    "tool_name": tool_name,
                    "arguments": dict(arguments),
                    "result": result,
                    "error": error,
                    "duration_ms": duration_ms,
                }
            )
        except Exception as exc:
            logger.warning(
                "[ToolExcute] event handler failed: tool=%s status=%s error=%s",
                tool_name,
                status,
                exc,
            )

    @classmethod
    def _normalize_response_calls(cls, response: Any) -> list[ToolCall]:
        normalized = getattr(response, "tool_calls", None)
        if normalized:
            raw_calls = normalized if isinstance(normalized, list) else [normalized]
            return [cls._normalize_call(call) for call in raw_calls]

        additional = getattr(response, "additional_kwargs", None) or {}
        raw = additional.get("tool_calls") if isinstance(additional, Mapping) else None
        if not raw:
            return []
        raw_calls = raw if isinstance(raw, list) else [raw]
        return [cls._normalize_call(call) for call in raw_calls]

    @staticmethod
    def _normalize_call(raw_call: Any) -> ToolCall:
        if not isinstance(raw_call, Mapping):
            raise ValueError("Tool call must be an object")
        function = raw_call.get("function")
        source = function if isinstance(function, Mapping) else raw_call
        name = str(source.get("name") or "").strip()
        if not name:
            raise ValueError("Tool call name cannot be empty")
        arguments = source.get("arguments", source.get("args", {}))
        if arguments in (None, ""):
            arguments = {}
        elif isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON arguments for tool {name}") from exc
        if not isinstance(arguments, Mapping):
            raise ValueError(f"Tool arguments must be an object: {name}")
        return {
            "id": str(raw_call.get("id") or f"call-{uuid4().hex}"),
            "name": name,
            "args": dict(arguments),
        }
