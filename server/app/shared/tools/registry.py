"""模型工具的定义、注册与执行分派。

``Tool`` 同时承载 JSON Schema 来源与执行入口，``ToolRegistry`` 按名称分派调用。
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
import json
from typing import Any

from pydantic import BaseModel

ToolHandler = Callable[..., Awaitable[Any]]


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
            prefix = "[Error] " if raw.get("status") == "failed" else ""
            return f"{prefix}{raw['text']}"
        return json.dumps(dict(raw), ensure_ascii=False, indent=2)
    return str(raw)


@dataclass(frozen=True, slots=True)
class Tool:
    """一个可供模型选择并由应用执行的工具。"""

    name: str
    description: str
    args_model: type[BaseModel]
    handler: ToolHandler

    def __post_init__(self) -> None:
        """校验工具名、描述与处理函数非空。"""
        if not self.name.strip():
            raise ValueError("Tool name cannot be empty")
        if not self.description.strip():
            raise ValueError(f"Tool description cannot be empty: {self.name}")
        if self.handler is None:
            raise ValueError(f"Tool handler cannot be None: {self.name}")

    def to_openai_schema(self) -> dict[str, Any]:
        """生成 OpenAI function-calling schema。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.args_model.model_json_schema(),
            },
        }


def tool(
    name: str | None = None,
    description: str | None = None,
    args_model: type[BaseModel] | None = None,
) -> Callable[[ToolHandler], Tool]:
    """装饰器：将异步函数转换为统一的 Tool 实例。"""
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
    """工具注册与执行分派器。"""

    def __init__(self, tools: Sequence[Tool] | None = None) -> None:
        """按名称建立工具索引，重名直接报错。"""
        self._tools: dict[str, Tool] = {}
        for item in tools or ():
            if item.name in self._tools:
                raise ValueError(f"Tool already registered: {item.name}")
            self._tools[item.name] = item

    def openai_schemas(self) -> list[dict[str, Any]]:
        """返回全部工具的 OpenAI function-calling schema 列表。"""
        return [tool.to_openai_schema() for tool in self._tools.values()]

    async def execute(self, name: str, args: Mapping[str, Any] | str = "") -> Any:
        """按名称执行工具：参数先经 args_model 校验再调用 handler。"""
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(f"Unknown tool: {name}")
        if isinstance(args, str):
            payload = json.loads(args) if args.strip() else {}
        else:
            payload = dict(args)
        return await tool.handler(**tool.args_model.model_validate(payload).model_dump())
