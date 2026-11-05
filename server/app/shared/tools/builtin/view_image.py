"""``view_image`` —— 读图片并让视觉模型描述（截图/缩略图网格审查）。"""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.infra.logging import get_logger
from app.shared.tools.registry import Tool
from app.shared.tools.sandbox import resolve

logger = get_logger(__name__)


class ViewImageArgs(BaseModel):
    """查看图片并让视觉模型描述。"""

    path: str = Field(min_length=1, description="相对工作目录的图片路径")
    question: str = Field(
        default="描述这张图片的内容、布局、配色，以及任何明显的问题（文字溢出、元素重叠、留白过多）。",
        description="要问视觉模型的问题",
    )


def build(workdir: Path) -> Tool:
    """构造 view_image 工具。"""

    async def view_image(path: str, question: str = "") -> dict[str, Any]:
        try:
            target = resolve(workdir, path)
        except ValueError as exc:
            return {"text": str(exc), "status": "failed"}
        if not target.is_file():
            return {"text": f"图片不存在: {path}", "status": "failed"}

        mime = mimetypes.guess_type(target.name)[0] or "image/png"
        if not mime.startswith("image/"):
            return {"text": f"不是图片文件: {path}", "status": "failed"}

        try:
            from app.infra.llm import chat_vision

            encoded = base64.b64encode(target.read_bytes()).decode("ascii")
            data_url = f"data:{mime};base64,{encoded}"
            description = await chat_vision(
                question or "描述这张图片的内容、布局、配色及任何明显问题。",
                image_url=data_url,
            )
        except Exception as exc:
            logger.warning("[ViewImage] 分析失败: %s", exc)
            return {"text": f"图片分析失败: {exc}", "status": "failed"}

        return {"text": description, "status": "ok", "path": path}

    return Tool(
        name="view_image",
        description=(
            "查看图片并让视觉模型描述。用于确认截图效果：布局是否合理、"
            "文字有无溢出、配色是否协调。"
        ),
        args_model=ViewImageArgs,
        handler=view_image,
    )
