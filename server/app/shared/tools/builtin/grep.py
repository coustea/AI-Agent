"""``grep`` —— 按正则搜索文件内容。"""

from __future__ import annotations

import fnmatch
from pathlib import Path
import re
from typing import Any

from pydantic import BaseModel, Field

from app.shared.tools.registry import Tool
from app.shared.tools.sandbox import MAX_GREP_RESULTS, truncate


class GrepArgs(BaseModel):
    """按内容搜索。"""

    pattern: str = Field(min_length=1, description="正则表达式")
    include: str = Field(default="", description="只搜匹配该 glob 的文件，如 '*.html'")


def build(workdir: Path) -> Tool:
    """构造 grep 工具。"""

    async def grep(pattern: str, include: str = "") -> dict[str, Any]:
        try:
            regex = re.compile(pattern)
        except re.error as exc:
            return {"text": f"正则无效: {exc}", "status": "failed"}

        results: list[str] = []
        for p in sorted(workdir.rglob(include or "*")):
            if not p.is_file():
                continue
            if include and not fnmatch.fnmatch(p.name, include):
                continue
            try:
                for lineno, line in enumerate(
                    p.read_text(encoding="utf-8", errors="replace").splitlines(), 1
                ):
                    if regex.search(line):
                        results.append(f"{p.relative_to(workdir)}:{lineno}: {line[:300]}")
                        if len(results) >= MAX_GREP_RESULTS:
                            break
            except OSError:
                continue
            if len(results) >= MAX_GREP_RESULTS:
                break

        if not results:
            return {"text": f"没有匹配 {pattern} 的行。", "status": "ok"}
        return {"text": truncate("\n".join(results)), "status": "ok", "count": len(results)}

    return Tool(
        name="grep",
        description="按正则搜索文件内容，返回 文件:行号: 内容。",
        args_model=GrepArgs,
        handler=grep,
    )
