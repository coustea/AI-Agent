"""Shared agent-layer tool helpers."""

from __future__ import annotations

from typing import Any


def save_with_tool(
    tool_obj: Any,
    *,
    sub_dir: str,
    topic: str,
    content: str,
    ext: str = "md",
) -> str:
    payload = {
        "sub_dir": sub_dir,
        "topic": topic,
        "content": content,
        "ext": ext,
    }

    if callable(tool_obj):
        return tool_obj(**payload)

    invoke = getattr(tool_obj, "invoke", None)
    if callable(invoke):
        return invoke(payload)

    run = getattr(tool_obj, "run", None)
    if callable(run):
        return run(payload)

    raise TypeError("save_to_workplace 既不是可调用函数，也不是支持 invoke/run 的工具对象")


__all__ = ["save_with_tool"]
