"""全系统统一的模型工具定义、注册表与执行器 — 基于 learn-claude-code s02_tool_use。

所有模块（chat、resource、ppt、cartoon、path）共享同一套 ``Tool`` 与 ``ToolRegistry``（兼容别名 ``ToolExcute``）。
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
import json
import time
from typing import Any
from uuid import uuid4

from pydantic import BaseModel

from app.infra.logging import get_logger

logger = get_logger(__name__)

ToolHandler = Callable[..., Awaitable[Any]]
ToolRuntimeEvent = dict[str, Any]
ToolEventHandler = Callable[[ToolRuntimeEvent], Awaitable[None]]


def format_tool_output(raw: Any) -> str:
    """将工具返回的任意结构（dict / str / BaseModel）归一化为回灌给 LLM 的文本。"""
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    if isinstance(raw, BaseModel):
        return raw.model_dump_json(indent=2)
    if isinstance(raw, Mapping):
        if set(raw.keys()) <= {"text", "status", "total_lines", "count", "path"} and "text" in raw:
            status = raw.get("status", "ok")
            prefix = "[Error] " if status == "failed" else ""
            return f"{prefix}{raw['text']}"
        return json.dumps(dict(raw), ensure_ascii=False, indent=2)
    return str(raw)


@dataclass(frozen=True, slots=True)
class Tool:
    """一个可供模型选择并由应用执行的工具（同时支持 Pydantic args_model 或 JSON Schema parameters）。"""

    name: str
    description: str
    args_model: type[BaseModel] | None = None
    handler: ToolHandler | None = None
    parameters: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Tool name cannot be empty")
        if not self.description.strip():
            raise ValueError(f"Tool description cannot be empty: {self.name}")
        if self.handler is None:
            raise ValueError(f"Tool handler cannot be None: {self.name}")
        if self.args_model is None and self.parameters is None:
            object.__setattr__(self, "parameters", {"type": "object", "properties": {}})

    def description_schema(self) -> dict[str, Any]:
        """生成 OpenAI function-calling schema。"""
        schema = (
            self.args_model.model_json_schema()
            if self.args_model is not None
            else (self.parameters or {"type": "object", "properties": {}})
        )
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": schema,
            },
        }

    def to_openai_schema(self) -> dict[str, Any]:
        """description_schema 的别名。"""
        return self.description_schema()


def tool(
    name: str | None = None,
    description: str | None = None,
    args_model: type[BaseModel] | None = None,
) -> Callable[[ToolHandler], Tool]:
    """装饰器：将异步函数转换为统一的 Tool 实例。

    支持：
    @tool("name", "description", args_model=MyArgs)
    async def handler(**kwargs): ...
    """
    def decorator(fn: ToolHandler) -> Tool:
        tool_name = (name or fn.__name__).strip()
        tool_desc = (description or fn.__doc__ or "").strip()
        if not tool_desc:
            tool_desc = f"Tool {tool_name}"
        return Tool(
            name=tool_name,
            description=tool_desc,
            args_model=args_model,
            handler=fn,
        )
    return decorator


class ToolRegistry:
    """工具注册、查找与执行分发器（learn-claude-code s02 dispatch map 模式）。"""

    def __init__(
        self,
        tools: Sequence[Tool] | None = None,
        event_handler: ToolEventHandler | None = None,
    ) -> None:
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

    def has_tool(self, name: str) -> bool:
        return name in self._tools

    @property
    def tool_names(self) -> list[str]:
        return list(self._tools.keys())

    def get_tools_description(self) -> list[dict[str, Any]]:
        return [tool.description_schema() for tool in self._tools.values()]

    async def execute(self, tool_call: Mapping[str, Any]) -> Any:
        """执行单个工具调用并返回原始结果（供 chat 流式事件等结构化消费）。"""
        name = str(tool_call.get("name") or "").strip()
        if not name:
            raise ValueError("Tool call name cannot be empty")
        raw_args = tool_call.get("args", {})
        if not isinstance(raw_args, Mapping):
            raise ValueError(f"Tool arguments must be an object: {name}")
        tool = self.get_tool(name)
        if tool.args_model is not None:
            validated = tool.args_model.model_validate(dict(raw_args))
            arguments = validated.model_dump()
        else:
            arguments = dict(raw_args)
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

    async def execute_as_text(self, name: str, raw_args: Mapping[str, Any] | str, call_id: str = "") -> str:
        """执行单个工具调用并将结果格式化为纯文本字符串（供 s01 Agent 循环直接回灌）。"""
        if isinstance(raw_args, str):
            try:
                parsed = json.loads(raw_args) if raw_args.strip() else {}
                args_dict = parsed if isinstance(parsed, Mapping) else {}
            except json.JSONDecodeError:
                args_dict = {}
        else:
            args_dict = dict(raw_args)

        if not self.has_tool(name):
            return f"Error: Unknown tool '{name}'. Available: {', '.join(self.tool_names)}"
        try:
            raw_res = await self.execute({"id": call_id, "name": name, "args": args_dict})
            return format_tool_output(raw_res)
        except Exception as exc:
            logger.warning("[ToolRegistry] 执行工具 %s 异常: %s", name, exc)
            return f"Error executing {name}: {exc}"

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
                "[ToolRegistry] event handler failed: tool=%s status=%s error=%s",
                tool_name,
                status,
                exc,
            )


__all__ = [
    "Tool",
    "ToolEventHandler",
    "ToolHandler",
    "ToolRegistry",
    "ToolRuntimeEvent",
    "format_tool_output",
    "tool",
]
