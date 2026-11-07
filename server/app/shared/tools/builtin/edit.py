"""``edit`` —— 精确替换文件中的一段文本。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.shared.tools.registry import Tool
from app.shared.tools.sandbox import resolve_sandbox_path


class EditArgs(BaseModel):
    """精确替换文件内容。"""

    path: str = Field(min_length=1, description="相对工作目录的文件路径")
    old_string: str = Field(min_length=1, description="要被替换的原文，必须唯一出现")
    new_string: str = Field(description="替换后的文本，空串表示删除")


def build(workdir: Path) -> Tool:
    """构造 edit 工具。"""

    async def edit(path: str, old_string: str, new_string: str) -> dict[str, Any]:
        """对指定文件内容进行精确字符串查找替换。"""
        try:
            target = resolve_sandbox_path(workdir, path)
        except PermissionError as exc:
            return {"text": str(exc), "status": "failed"}
        if not target.is_file():
            return {"text": f"文件不存在: {path}", "status": "failed"}

        text = target.read_text(encoding="utf-8")
        count = text.count(old_string)
        if count == 0:
            return {"text": f"{path} 里找不到要替换的文本。", "status": "failed"}
        if count > 1:
            return {
                "text": f"要替换的文本在 {path} 里出现 {count} 次，不唯一。请提供更长的上下文。",
                "status": "failed",
            }
        target.write_text(text.replace(old_string, new_string, 1), encoding="utf-8")
        return {"text": f"已更新 {path}", "status": "ok"}

    return Tool(
        name="edit",
        description=(
            "精确替换文件中的一段文本。old_string 必须在文件中唯一出现，"
            "否则会失败并要求提供更长上下文。"
        ),
        args_model=EditArgs,
        handler=edit,
    )
