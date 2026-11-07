"""Chat 领域工具定义、装配与前端语义化描述器 —— 基于 learn-claude-code s02 & s04。"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.chat.context import (
    MAX_FILE_CONTENT_CHARS,
    read_uploaded_file_content,
    resolve_uploaded_path,
)
from app.chat.memory import LTM_CATEGORIES, LTM_CATEGORY_NAMES, compact_text, get_memory_markdown
from app.chat.schemas import StepKind
from app.config import user_chat_dir, user_chat_uploads_dir
from app.infra.logging import get_logger
from app.profile.service import get_profile_service
from app.rag.tools import build_knowledge_tool
from app.shared.cartoon.tool import build_cartoon_subagent_tool
from app.shared.ppt.tool import build_ppt_subagent_tool
from app.shared.tools import Tool, build_builtin_tools, resolve_sandbox_path, tool

logger = get_logger(__name__)

SubagentProgressHandler = Callable[[str, str, int], Awaitable[None]]

LongTermMemoryCategory = Literal[
    "learning_background",
    "long_term_goals",
    "learning_preferences",
    "stable_weaknesses",
    "interaction_rules",
    "effective_strategies",
    "corrections",
]

LONG_TERM_MEMORY_CATEGORY_ALIASES: dict[str, str] = {
    "goals_progress": "long_term_goals",
}


class GetLearnerProfileArgs(BaseModel):
    """学习者画像查询工具参数。"""

    dimension: str | None = Field(
        default=None,
        description="需要重点查看的画像维度，如 goals、preferences、weaknesses。",
    )
    reason: str = Field(
        default="",
        description="简要说明为什么当前问题需要查阅学习者画像。",
    )


class GetLongTermMemoryArgs(BaseModel):
    """长期记忆查询工具参数。"""

    category: LongTermMemoryCategory | str | None = Field(
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


def build_user_context_tools(
    user_id: int,
    *,
    profile_service: Any | None = None,
) -> list[Tool]:
    """构建绑定当前 user_id 的学习者画像与长期记忆读取工具。"""

    @tool(
        name="get_learner_profile",
        description="读取当前学生的学习者画像（基础水平、目标、学习风格与薄弱点）。",
        args_model=GetLearnerProfileArgs,
    )
    async def get_learner_profile(dimension: str | None = None, reason: str = "") -> str:
        """读取指定用户的学习者画像 Markdown。"""
        svc = profile_service or get_profile_service()
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
    async def get_long_term_memory(category: str | None = None, reason: str = "") -> str:
        """按分类读取指定用户的长期学习记忆 Markdown。"""
        raw_cat = str(category or "").strip()
        category_value = LONG_TERM_MEMORY_CATEGORY_ALIASES.get(raw_cat, raw_cat) or None
        if category_value and category_value not in LTM_CATEGORIES:
            return f"长期记忆分类无效: {category_value}"
        try:
            markdown = await get_memory_markdown(user_id, category=category_value)
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

        content = read_uploaded_file_content(str(target), max_content_chars=max_chars)
        is_err = content.startswith(("文件不存在:", "路径不是文件:", "不支持的文件类型:"))
        return {
            "status": "failed" if is_err else "ok",
            "text": content,
            "path": target.name,
        }

    return Tool(
        name="read_document",
        description="读取学生上传的文档内容（支持 .pdf, .docx, .xlsx, .xls, .csv, .tsv, .txt, .md, .log）。",
        args_model=ReadDocumentArgs,
        handler=read_document,
    )


def _default_workdir(username: str, session_id: str) -> Path:
    """返回并确保当前会话的沙箱工作区目录存在。"""
    path = user_chat_dir(username, session_id) / "workspace"
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_tutor_tools(
    *,
    user_id: int,
    username: str,
    session_id: str,
    workdir: Path | None = None,
    on_subagent_progress: SubagentProgressHandler | None = None,
) -> list[Tool]:
    """装配本轮对话完整工具集，并为重型子智能体注入实时进度回调。"""
    effective_workdir = workdir or _default_workdir(username, session_id)

    async def _ppt_progress(msg: str, pct: int) -> None:
        """转发 PPT 子智能体内部进度。"""
        if on_subagent_progress is not None:
            await on_subagent_progress("generate_ppt_deck", msg, pct)

    async def _video_progress(msg: str, pct: int) -> None:
        """转发教学视频子智能体内部进度。"""
        if on_subagent_progress is not None:
            await on_subagent_progress("generate_teaching_video", msg, pct)

    return [
        *build_builtin_tools(effective_workdir),
        build_read_document_tool(username=username, session_id=session_id, workdir=effective_workdir),
        *build_user_context_tools(user_id),
        build_knowledge_tool(),
        build_ppt_subagent_tool(
            username=username,
            session_id=session_id,
            progress=_ppt_progress if on_subagent_progress else None,
        ),
        build_cartoon_subagent_tool(
            username=username,
            session_id=session_id,
            progress=_video_progress if on_subagent_progress else None,
        ),
    ]


def _short(value: Any, limit: int = 72) -> str:
    """将任意值转换为单行简短摘要。"""
    text = " ".join(str(value or "").strip().split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def describe_tool_call(name: str, args: dict[str, Any]) -> tuple[StepKind, str, str]:
    """将工具名称与参数映射为前端可直观展示的 (StepKind, 中文主标题, 意图副标题)。"""
    if name in {"search_knowledge_base", "knowledge_search"}:
        query = _short(args.get("query") or "课程核心概念")
        subject = _short(args.get("subject") or "", 24)
        sub = f"检索：{query}" + (f" ({subject})" if subject else "")
        return "knowledge", "检索课程知识库", sub

    if name == "get_learner_profile":
        reason = _short(args.get("reason") or args.get("dimension") or "个性化背景与薄弱点")
        return "memory", "查阅学习者画像", reason

    if name == "get_long_term_memory":
        cat = str(args.get("category") or "").strip()
        cat_cn = LTM_CATEGORY_NAMES.get(cat, cat)
        reason = _short(args.get("reason") or cat_cn or "历史学习记录与偏好")
        sub = f"{cat_cn} · {reason}" if cat_cn and cat_cn not in reason else reason
        return "memory", "读取长期学习记忆", sub

    if name == "view_image":
        raw_path = str(args.get("path") or "图片")
        filename = raw_path.rsplit("/", 1)[-1]
        question = _short(args.get("question") or "识别画面细节与文字信息", 60)
        return "vision", f"视觉理解图片 · {filename}", question

    if name in {"read_document", "read"}:
        raw_path = str(args.get("path") or "文档")
        filename = raw_path.rsplit("/", 1)[-1]
        return "document", "读取文件内容", filename

    if name in {"glob", "grep"}:
        pattern = _short(args.get("pattern") or args.get("path") or "*")
        return "document", "搜索工作区文件", f"匹配：{pattern}"

    if name in {"write", "edit"}:
        raw_path = str(args.get("path") or "文件")
        filename = raw_path.rsplit("/", 1)[-1]
        return "code", "编写工作区文件", filename

    if name == "bash":
        cmd = _short(args.get("command") or "", 64)
        return "code", "执行命令与环境检查", cmd

    if name == "generate_ppt_deck":
        topic = _short(args.get("topic") or "教学课件", 48)
        return "subagent", "生成 PPT 教学课件", f"主题：{topic}"

    if name == "generate_teaching_video":
        topic = _short(args.get("topic") or "教学动画视频", 48)
        return "subagent", "制作教学动画视频", f"主题：{topic}"

    return "tool", f"执行工具 {name}", _short(args, 60)


__all__ = [
    "GetLearnerProfileArgs",
    "GetLongTermMemoryArgs",
    "LONG_TERM_MEMORY_CATEGORY_ALIASES",
    "LongTermMemoryCategory",
    "ReadDocumentArgs",
    "SubagentProgressHandler",
    "build_read_document_tool",
    "build_tutor_tools",
    "build_user_context_tools",
    "describe_tool_call",
]
