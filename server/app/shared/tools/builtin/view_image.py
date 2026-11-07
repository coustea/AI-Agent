"""``view_image`` —— 读取图片并调用多模态视觉模型进行理解与问答。"""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.infra.logging import get_logger
from app.shared.tools.registry import Tool
from app.shared.tools.sandbox import resolve_sandbox_path

logger = get_logger(__name__)

_DEFAULT_QUESTION = "详细描述这张图片的内容、文字信息、关键主体以及任何需要关注的视觉细节。"


class ViewImageArgs(BaseModel):
    """查看图片并由视觉模型解答针对该图像的具体问题。"""

    path: str = Field(min_length=1, description="相对工作目录的图片路径")
    question: str = Field(
        default=_DEFAULT_QUESTION,
        description=(
            "由你（智能体）根据当前上下文提出的具体问题。请明确指出你想从图片中获取什么信息，"
            "例如提取文本/公式、解析图表数据、检查排版与视觉缺陷、分析画面元素等。"
        ),
    )


def _locate(workdir: Path, ref: str) -> Path | None:
    """按静态上传 URL、工作区相对路径、会话上传目录三种来源定位图片文件。"""
    if ref.startswith("/static/"):
        from app.config import WORKPLACE_DIR

        root = WORKPLACE_DIR.resolve()
        candidate = (root / ref.removeprefix("/static/")).resolve()
        if candidate.is_relative_to(root) and candidate.is_file():
            return candidate
    try:
        candidate = resolve_sandbox_path(workdir, ref)
    except PermissionError:
        candidate = None
    if candidate is not None and candidate.is_file():
        return candidate
    uploaded = workdir.parent / "uploads" / Path(ref).name
    return uploaded.resolve() if uploaded.is_file() else None


def build(workdir: Path) -> Tool:
    """构造 view_image 工具。"""

    async def view_image(path: str, question: str = "") -> dict[str, Any]:
        """读取工作区图片并调用视觉模型回答针对图像的具体问题。"""
        target = _locate(workdir, (path or "").strip())
        if target is None:
            return {"text": f"图片不存在: {path}", "status": "failed"}

        mime = mimetypes.guess_type(target.name)[0] or "image/png"
        if not mime.startswith("image/"):
            return {"text": f"不是图片文件: {path}", "status": "failed"}

        target_question = question.strip() if question else _DEFAULT_QUESTION

        try:
            from app.infra.llm import chat_vision

            encoded = base64.b64encode(target.read_bytes()).decode("ascii")
            data_url = f"data:{mime};base64,{encoded}"
            description = await chat_vision(
                target_question,
                image_url=data_url,
            )
        except Exception as exc:
            logger.warning("[ViewImage] 分析失败: %s", exc)
            return {"text": f"图片分析失败: {exc}", "status": "failed"}

        return {"text": description, "status": "ok", "path": path}

    return Tool(
        name="view_image",
        description=(
            "读取图片并调用多模态视觉模型进行理解与问答。调用时应结合当前任务目标在 question 中明确"
            "提出你想了解的具体内容（例如提取题目与公式、读取图表数据、核对排版缺陷或特定视觉细节）。"
        ),
        args_model=ViewImageArgs,
        handler=view_image,
    )
