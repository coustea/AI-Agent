"""``glob`` —— 按文件名模式查找文件。"""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.shared.tools.registry import Tool
from app.shared.tools.sandbox import MAX_GLOB_RESULTS


class GlobArgs(BaseModel):
    """按文件名模式查找。"""

    pattern: str = Field(min_length=1, description="glob 模式，如 '**/*.html'")


def build(workdir: Path) -> Tool:
    """构造 glob 工具。"""

    async def glob(pattern: str) -> dict[str, Any]:
        matches = [
            str(p.relative_to(workdir))
            for p in workdir.rglob("*")
            if p.is_file() and fnmatch.fnmatch(str(p.relative_to(workdir)), pattern)
        ]
        matches.sort()
        if not matches:
            return {"text": f"没有匹配 {pattern} 的文件。", "status": "ok"}
        shown = matches[:MAX_GLOB_RESULTS]
        text = "\n".join(shown)
        if len(matches) > len(shown):
            text += f"\n...（共 {len(matches)} 个）"
        return {"text": text, "status": "ok", "count": len(matches)}

    return Tool(
        name="glob",
        description="按文件名模式查找文件，如 '**/*.html'。",
        args_model=GlobArgs,
        handler=glob,
    )
