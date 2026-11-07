"""内置工作区工具集 — 供 chat、ppt、cartoon 等全系统 Agent 共享。"""

from __future__ import annotations

from pathlib import Path

from app.shared.tools.builtin import bash, edit, glob, grep, read, view_image, write
from app.shared.tools.registry import Tool
from app.shared.tools.sandbox import BASH_TIMEOUT_S


def build_builtin_tools(workdir: Path, *, timeout_s: float = BASH_TIMEOUT_S) -> list[Tool]:
    """返回绑定到 workdir 的工作区工具列表。"""
    root = workdir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    return [
        bash.build(root, timeout_s=timeout_s),
        read.build(root),
        write.build(root),
        edit.build(root),
        glob.build(root),
        grep.build(root),
        view_image.build(root),
    ]


__all__ = [
    "bash",
    "build_builtin_tools",
    "edit",
    "glob",
    "grep",
    "read",
    "view_image",
    "write",
]
