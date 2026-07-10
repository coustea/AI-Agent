"""项目自有的模型工具定义、注册、调用与执行。"""

# 本模块定义 Tool 数据结构与 ToolExcute 执行器：负责工具注册、校验参数与运行
from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from pydantic import BaseModel

from app.infra.logging import get_logger


logger = get_logger(__name__)

ToolHandler = Callable[..., Awaitable[Any]]
ToolRuntimeEvent = dict[str, Any]
ToolEventHandler = Callable[[ToolRuntimeEvent], Awaitable[None]]


# 工具定义：名称、描述、参数模型与处理函数
@dataclass(frozen=True, slots=True)
class Tool:
    """一个可供模型选择并由应用执行的工具。"""

    name: str
    description: str
    args_model: type[BaseModel]
    handler: ToolHandler

    def __post_init__(self) -> None:
        # 校验工具名称与描述非空
        if not self.name.strip():
            raise ValueError("Tool name cannot be empty")
        if not self.description.strip():
            raise ValueError(f"Tool description cannot be empty: {self.name}")

    def description_schema(self) -> dict[str, Any]:
        # 生成供模型使用的 OpenAI function-calling 描述结构
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.args_model.model_json_schema(),
            },
        }


# 工具执行器：注册、查询并执行工具，不负责调用模型
class ToolExcute:
    """注册、查询并执行工具，不负责调用模型或解析模型响应。"""

    def __init__(
        self,
        tools: Sequence[Tool] | None = None,
        event_handler: ToolEventHandler | None = None,
    ) -> None:
        # 初始化执行器，注册初始工具并保存事件回调
        self._event_handler = event_handler
        self._tools: dict[str, Tool] = {}
        if tools:
            self.register_many(tools)

    def register(self, tool: Tool) -> Tool:
        # 注册单个工具，名称重复则报错
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool
        return tool

    def register_many(self, tools: Sequence[Tool]) -> None:
        # 批量注册多个工具
        for tool in tools:
            self.register(tool)

    def get_tool(self, name: str) -> Tool:
        # 按名称查找工具，未知名称抛 KeyError
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Unknown tool: {name}") from exc

    def get_tools(self) -> list[Tool]:
        # 返回所有已注册工具的列表
        return list(self._tools.values())

    def get_tools_description(self) -> list[dict[str, Any]]:
        # 返回所有工具的 function-calling 描述结构列表
        return [tool.description_schema() for tool in self._tools.values()]

    def subset(self, names: Sequence[str]) -> ToolExcute:
        """创建保留当前事件回调的工具子集。"""
        # 基于指定名称创建保留事件回调的工具子集
        return ToolExcute(
            tools=[self.get_tool(name) for name in names],
            event_handler=self._event_handler,
        )

    async def execute(self, tool_call: Mapping[str, Any]) -> Any:
        # 执行单个工具调用：校验参数、计时、发出运行/完成/失败事件
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
        # 并发执行多个工具调用，单个失败不中断其余调用
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
        # 向事件回调发送工具运行事件，回调异常仅告警不中断
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
