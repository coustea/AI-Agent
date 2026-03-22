"""
工具集合与调用辅助函数。
"""

from __future__ import annotations

from typing import Any, Iterable

from langchain_core.tools import BaseTool

from .builtin import AGENT_TOOLS

__all__ = ["AGENT_TOOLS", "get_tools", "call_tool"]


def get_tools() -> list[BaseTool]:
    return list(AGENT_TOOLS)


async def call_tool(name: str, arguments: dict[str, Any] | None = None) -> Any:
    arguments = arguments or {}
    tool = _find_tool(get_tools(), name)
    return await tool.ainvoke(arguments)


def _find_tool(tools: Iterable[BaseTool], name: str) -> BaseTool:
    for tool in tools:
        if tool.name == name:
            return tool
    raise KeyError(f"Tool not found: {name}")
