"""``read`` —— 读取文本文件并返回带行号的内容。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.shared.tools.registry import Tool
from app.shared.tools.sandbox import MAX_READ_LINES, resolve, truncate


class ReadArgs(BaseModel):
    """读取文件。"""

    path: str = Field(min_length=1, description="相对工作目录的文件路径")
    offset: int = Field(default=1, ge=1, description="起始行号，从 1 开始")
    limit: int = Field(default=MAX_READ_LINES, ge=1, le=MAX_READ_LINES, description="最多读取行数")


def build(workdir: Path) -> Tool:
    """构造 read 工具。"""

    async def read(path: str, offset: int = 1, limit: int = MAX_READ_LINES) -> dict[str, Any]:
        try:
            target = resolve(workdir, path)
        except ValueError as exc:
            return {"text": str(exc), "status": "failed"}
        if not target.is_file():
            return {"text": f"文件不存在: {path}", "status": "failed"}

        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        chunk = lines[offset - 1 : offset - 1 + limit]
        numbered = "\n".join(f"{offset + i:>5}\t{line}" for i, line in enumerate(chunk))
        return {
            "text": truncate(numbered) or "(空文件)",
            "status": "ok",
            "total_lines": len(lines),
        }

    return Tool(
        name="read",
        description="读取文本文件，返回带行号的内容。大文件用 offset/limit 分段读。",
        args_model=ReadArgs,
        handler=read,
    )
