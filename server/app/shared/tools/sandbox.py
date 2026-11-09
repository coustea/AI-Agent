"""工作目录沙箱路径解析与工具输出截断。"""

from __future__ import annotations

from pathlib import Path

MAX_OUTPUT_CHARS = 30_000
MAX_READ_LINES = 2_000
MAX_GREP_RESULTS = 200
MAX_GLOB_RESULTS = 500
BASH_TIMEOUT_S = 180


def resolve_sandbox_path(workdir: Path, rel: str) -> Path:
    """把相对路径解析到 workdir 内；越界时抛出 PermissionError。"""
    root = workdir.resolve()
    clean = (rel or "").strip().lstrip("/")
    target = (root / clean).resolve()
    if target != root and root not in target.parents:
        raise PermissionError(f"路径越界（必须位于工作目录内）: {rel}")
    return target


def truncate_output(text: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    """超过上限时截断并附上剩余字符提示。"""
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... [truncated, {len(text) - limit} more chars]"


__all__ = [
    "BASH_TIMEOUT_S",
    "MAX_GLOB_RESULTS",
    "MAX_GREP_RESULTS",
    "MAX_OUTPUT_CHARS",
    "MAX_READ_LINES",
    "resolve_sandbox_path",
    "truncate_output",
]
