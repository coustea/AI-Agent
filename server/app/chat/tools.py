"""Chat 领域工具定义与装配 —— 基于 learn-claude-code s02 & s04。"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.chat.files import (
    MAX_FILE_CONTENT_CHARS,
    read_uploaded_file_content,
    resolve_uploaded_path,
)
from app.chat.memory import compact_text, get_memory_markdown
from app.config import user_chat_dir, user_chat_uploads_dir
from app.infra.logging import get_logger
from app.profile.service import get_profile_service
from app.shared.cartoon.tool import build_cartoon_tool
from app.shared.ppt.tool import build_ppt_tool
from app.shared.tools import Tool, build_builtin_tools, resolve_sandbox_path, tool

logger = get_logger(__name__)

SubagentProgressHandler = Callable[[str, str], Awaitable[None]]

LongTermMemoryCategory = Literal[
    "learning_background",
    "long_term_goals",
    "learning_preferences",
    "stable_weaknesses",
    "interaction_rules",
    "effective_strategies",
    "corrections",
]

class GetLearnerProfileArgs(BaseModel):
    """学习者画像查询工具参数。"""

    reason: str = Field(
        default="",
        description="简要说明为什么当前问题需要查阅学习者画像。",
    )


class GetLongTermMemoryArgs(BaseModel):
    """长期记忆查询工具参数。"""

    category: LongTermMemoryCategory | None = Field(
        default=None,
        description="长期记忆分类名，如 learning_background、stable_weaknesses、learning_preferences。",
    )
    reason: str = Field(
        default="",
        description="简要说明为什么当前问题需要查阅长期学习记忆。",
    )


class ReadDocumentArgs(BaseModel):
    """读取用户上传文档（PDF/Word/Excel/CSV/TXT/MD）的工具参数。"""

    path: str = Field(
        min_length=1,
        description="上传文档的 URL（如 /static/...）或文件名（如 report.pdf）。",
    )
    max_chars: int = Field(
        default=MAX_FILE_CONTENT_CHARS,
        ge=500,
        le=40000,
        description="最多读取的字符数上限。",
    )


def build_user_context_tools(user_id: int) -> list[Tool]:
    """构建绑定当前 user_id 的学习者画像与长期记忆读取工具。"""

    @tool(
        name="get_learner_profile",
        description="读取当前学生的学习者画像（基础水平、目标、学习风格与薄弱点）。",
        args_model=GetLearnerProfileArgs,
    )
    async def get_learner_profile(reason: str = "") -> str:
        """读取指定用户的学习者画像 Markdown。"""
        svc = get_profile_service()
        try:
            markdown = await svc.build_profile_markdown(user_id=user_id)
            return compact_text(f"画像读取原因: {reason or '个性化辅导'}\n{markdown}")
        except Exception as exc:
            logger.warning("[get_learner_profile] 失败: %s", exc)
            return "暂时无法读取学习者画像。"

    @tool(
        name="get_long_term_memory",
        description="读取跨会话长期学习记忆（学习背景、长期目标、偏好、稳定薄弱点、有效策略、历史纠正）。",
        args_model=GetLongTermMemoryArgs,
    )
    async def get_long_term_memory(category: LongTermMemoryCategory | None = None, reason: str = "") -> str:
        """按分类读取指定用户的长期学习记忆 Markdown。"""
        try:
            markdown = await get_memory_markdown(user_id, category=category)
            return compact_text(f"长期记忆读取原因: {reason or '历史上下文参考'}\n{markdown}")
        except Exception as exc:
            logger.warning("[get_long_term_memory] 失败: %s", exc)
            return "暂时无法读取长期学习记忆。"

    return [get_learner_profile, get_long_term_memory]


def build_read_document_tool(*, username: str, session_id: str, workdir: Path) -> Tool:
    """构造绑定当前会话的 read_document 工具，支持读取上传的 PDF/Docx/Excel/CSV/文本文件。"""
    uploads_dir = user_chat_uploads_dir(username, session_id).resolve()

    async def read_document(path: str, max_chars: int = MAX_FILE_CONTENT_CHARS) -> dict[str, Any]:
        """定位并解析用户上传的文档或工作区文档内容。"""
        ref = (path or "").strip()
        target: Path | None = None

        if ref.startswith("/static/"):
            resolved = resolve_uploaded_path(ref)
            if resolved is not None and resolved[0] == username:
                target = Path(resolved[1])
        if target is None:
            candidate_upload = (uploads_dir / Path(ref).name).resolve()
            if candidate_upload.is_relative_to(uploads_dir) and candidate_upload.is_file():
                target = candidate_upload
        if target is None:
            try:
                candidate_ws = resolve_sandbox_path(workdir, ref)
                if candidate_ws.is_file():
                    target = candidate_ws
            except PermissionError:
                target = None

        if target is None or not target.is_file():
            return {"status": "failed", "text": f"文档不存在或无权访问: {path}"}

        content = await asyncio.to_thread(read_uploaded_file_content, str(target), max_content_chars=max_chars)
        return {
            "status": "ok",
            "text": content,
            "path": target.name,
        }

    return Tool(
        name="read_document",
        description="读取学生上传的文档内容（支持 .pdf, .docx, .xlsx, .xls, .csv, .tsv, .txt, .md, .log）。",
        args_model=ReadDocumentArgs,
        handler=read_document,
    )


def build_tutor_tools(
    *,
    user_id: int,
    username: str,
    session_id: str,
    workdir: Path | None = None,
    on_subagent_progress: SubagentProgressHandler | None = None,
) -> list[Tool]:
    """装配本轮对话完整工具集，并为重型子智能体注入实时进度回调。"""
    effective_workdir = workdir or user_chat_dir(username, session_id) / "workspace"

    async def _ppt_progress(msg: str, _pct: int) -> None:
        """转发 PPT 子智能体内部进度。"""
        if on_subagent_progress is not None:
            await on_subagent_progress("generate_ppt_deck", msg)

    async def _video_progress(msg: str, _pct: int) -> None:
        """转发教学视频子智能体内部进度。"""
        if on_subagent_progress is not None:
            await on_subagent_progress("generate_teaching_video", msg)

    return [
        *build_builtin_tools(effective_workdir),
        build_read_document_tool(username=username, session_id=session_id, workdir=effective_workdir),
        *build_user_context_tools(user_id),
        build_ppt_tool(
            username=username,
            session_id=session_id,
            progress=_ppt_progress if on_subagent_progress else None,
        ),
        build_cartoon_tool(
            username=username,
            session_id=session_id,
            progress=_video_progress if on_subagent_progress else None,
        ),
    ]
