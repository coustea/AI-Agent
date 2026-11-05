"""``write`` —— 写入文件（覆盖）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.shared.tools.registry import Tool
from app.shared.tools.sandbox import resolve


class WriteArgs(BaseModel):
    """写入文件（覆盖）。"""

    path: str = Field(min_length=1, description="相对工作目录的文件路径")
    content: str = Field(description="完整文件内容")


def build(workdir: Path) -> Tool:
    """构造 write 工具。"""

    async def write(path: str, content: str) -> dict[str, Any]:
        try:
            target = resolve(workdir, path)
        except ValueError as exc:
            return {"text": str(exc), "status": "failed"}
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {"text": f"已写入 {path}（{len(content)} 字符）", "status": "ok"}

    return Tool(
        name="write",
        description="写入文件（覆盖已有内容）。父目录会自动创建。",
        args_model=WriteArgs,
        handler=write,
    )
