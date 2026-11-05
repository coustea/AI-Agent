"""内置工具集装配 — 供 chat、resource、ppt、cartoon 等全系统 Agent 共享。"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from app.shared.tools.builtin import bash, edit, glob, grep, read, view_image, write
from app.shared.tools.registry import Tool

_ALL_BUILDERS = {
    "bash": bash.build,
    "read": read.build,
    "write": write.build,
    "edit": edit.build,
    "glob": glob.build,
    "grep": grep.build,
    "view_image": view_image.build,
}


def build_builtin_tools(
    workdir: Path,
    *,
    include: Sequence[str] | None = None,
    exclude: Sequence[str] | None = None,
    include_bash: bool = True,
    include_view_image: bool = True,
    include_glob_grep: bool = True,
    bash_timeout_s: float = 180.0,
) -> list[Tool]:
    """返回绑定到 workdir 的内置沙箱工具列表。"""
    _ = bash_timeout_s
    root = workdir.resolve()
    root.mkdir(parents=True, exist_ok=True)

    allowed = set(include) if include is not None else set(_ALL_BUILDERS.keys())
    blocked = set(exclude) if exclude is not None else set()
    if not include_bash:
        blocked.add("bash")
    if not include_view_image:
        blocked.add("view_image")
    if not include_glob_grep:
        blocked.update({"glob", "grep"})

    tools: list[Tool] = []
    for name, builder in _ALL_BUILDERS.items():
        if name in allowed and name not in blocked:
            tools.append(builder(root))
    return tools


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
