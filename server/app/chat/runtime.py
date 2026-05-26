"""Runtime preparation helpers for TutorAgent chat turns.

为 TutorAgent 对话轮次准备运行时状态和上下文。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Protocol

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage

from app.chat.request import ChatHistoryMessage
from app.chat.schemas import TutorAgentContext, TutorState
from app.prompts import registry

# 支持的图片扩展名集合
IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def _classify_attachments(attachments: list[str]) -> tuple[list[str], list[str]]:
    """按扩展名将附件分为图片和文档两类"""
    image_urls, file_urls = [], []
    for url in attachments:
        ext = url.rsplit(".", 1)[-1].lower().split("?")[0] if "." in url else ""
        if ext in IMAGE_EXTENSIONS:
            image_urls.append(url)
        else:
            file_urls.append(url)
    return image_urls, file_urls


class TutorContextService(Protocol):
    """辅导上下文服务协议。

    定义构建各类上下文的方法签名，供依赖注入使用。
    """

    async def build_recent_chat_context(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str,
        attachments: list[str],
    ) -> tuple[list[AnyMessage], str]:
        """构建近期对话上下文。"""
        ...

    @staticmethod
    def build_file_context(attachments: list[str]) -> str:
        """构建文件上下文。"""
        ...


@dataclass(frozen=True)
class UserMessageRecord:
    """用户消息记录。

    包含消息内容和附件信息。
    """
    content: str  # 消息文本内容
    attachments: list[dict[str, Any]] | None  # 附件列表


@dataclass(frozen=True)
class PreparedTutorTurn:
    """准备好的对话轮次。

    包含会话ID、附件URL、用户消息记录和初始状态。
    """
    session_id: str  # 会话ID
    attachments: list[str]  # 附件URL列表
    user_record: UserMessageRecord  # 用户消息记录
    initial_state: TutorState  # LangGraph 初始状态


def resolve_session_id(user_id: int, session_id: str | None) -> str:
    """解析会话ID，为空则生成默认会话ID。

    Args:
        user_id: 用户ID。
        session_id: 可选的会话ID。

    Returns:
        有效的会话ID。
    """
    return session_id or f"user-{user_id}-default-mentor"


def build_user_message_record(
    user_message: str,
    *,
    attachments: list[str],
) -> UserMessageRecord:
    """构建用户消息记录。

    将附件信息追加到消息内容中，并构建附件列表。

    Args:
        user_message: 用户消息文本。
        attachments: 附件URL列表。

    Returns:
        用户消息记录对象。
    """
    image_urls, file_urls = _classify_attachments(attachments)
    content = user_message
    if image_urls:
        content += f" [Attached Images: {', '.join(image_urls)}]"
    if file_urls:
        content += f" [Attached Files: {', '.join(file_urls)}]"

    if not attachments:
        return UserMessageRecord(content=content, attachments=None)

    # 构建附件信息列表
    attachment_records = [
        {
            "url": url,
            "type": "image" if _is_image_url(url) else "document",
            "name": url.split("/")[-1],
        }
        for url in attachments
    ]
    return UserMessageRecord(
        content=content,
        attachments=attachment_records,
    )


async def prepare_tutor_turn(
    *,
    ctx_service: TutorContextService,
    user_id: int,
    user_message: str,
    session_id: str | None,
    attachments: list[str] | None,
    enable_search: bool,
    enable_long_term_memory: bool,
    need_teaching_diagram: bool | None,
    attachment_analysis: dict[str, Any] | None,
) -> PreparedTutorTurn:
    """准备 TutorAgent 对话轮次。

    并行构建用户画像、长期记忆上下文，组装初始状态。

    Args:
        ctx_service: 上下文服务。
        user_id: 用户ID。
        user_message: 用户消息。
        session_id: 可选的会话ID。
        attachments: 附件URL列表。
        enable_search: 是否启用搜索。
        need_teaching_diagram: 是否生成教学图解。
        attachment_analysis: 附件预分析结果。

    Returns:
        准备好的对话轮次对象。
    """
    effective_session = resolve_session_id(user_id, session_id)
    normalized_attachments = list(attachments or [])

    user_record = build_user_message_record(
        user_message,
        attachments=normalized_attachments,
    )

    file_info_str = ctx_service.build_file_context(attachments=normalized_attachments)
    attachment_analysis_context = str((attachment_analysis or {}).get("analysis_context", "")).strip()
    # 构建近期对话上下文
    initial_messages, recent_chat_context = await ctx_service.build_recent_chat_context(
        user_id=user_id,
        session_id=effective_session,
        user_message=user_message,
        attachments=normalized_attachments,
    )

    # 拼接附件预分析上下文
    analysis_hint = (
        f"\n\n### 附件并行预分析结果\n{attachment_analysis_context}\n"
        if attachment_analysis_context
        else ""
    )
    system_prompt = registry.get("chat/tutor_system").format(
        recent_chat_context=recent_chat_context,
    ) + analysis_hint

    # 组装初始状态
    initial_state: TutorState = {
        "user_id": user_id,
        "session_id": effective_session,
        "attachments": normalized_attachments,
        "resource_mode": "none",
        "enable_search": bool(enable_search),
        "enable_long_term_memory": bool(enable_long_term_memory),
        "need_teaching_diagram": bool(need_teaching_diagram),
        "teaching_diagram": None,
        "teaching_diagram_error": None,
        "diagram_type": None,
        "route": "",
        "execution_mode": "",
        "recent_chat_context": recent_chat_context,
        "file_context": file_info_str,
        "attachment_analysis_context": attachment_analysis_context,
        "attachment_analysis": attachment_analysis or {},
        "system_prompt": system_prompt,
        "messages": initial_messages,
        "answer_text": "",
        "termination_reason": "",
    }

    return PreparedTutorTurn(
        session_id=effective_session,
        attachments=normalized_attachments,
        user_record=user_record,
        initial_state=initial_state,
    )


def prepare_tutor_state(context: TutorAgentContext, history: list[ChatHistoryMessage]) -> TutorState:
    """Build LangGraph state from initialized agent context and provided history."""
    messages = history_to_langchain_messages(history)
    attachment_context = (
        context.attachment_analysis_context
        or str((context.attachment_analysis or {}).get("analysis_context", "")).strip()
    )
    return {
        "user_id": context.user_id,
        "session_id": context.session_id,
        "attachments": list(context.attachments),
        "resource_mode": context.resource_mode,
        "enable_search": context.enable_search,
        "enable_long_term_memory": False,
        "need_teaching_diagram": context.need_teaching_diagram,
        "teaching_diagram": None,
        "teaching_diagram_error": None,
        "diagram_type": context.preferred_diagram_type,
        "route": "",
        "execution_mode": "",
        "recent_chat_context": context.recent_chat_context,
        "file_context": context.file_context,
        "attachment_analysis_context": attachment_context,
        "attachment_analysis": context.attachment_analysis,
        "system_prompt": context.system_prompt,
        "messages": messages,
        "answer_text": "",
        "retrieved_docs": [],
        "termination_reason": "",
    }


def history_to_langchain_messages(history: list[ChatHistoryMessage]) -> list[AnyMessage]:
    messages: list[AnyMessage] = []
    for item in history:
        content = (item.content or "").strip()
        if not content:
            continue
        if item.role == "user":
            messages.append(HumanMessage(content=content))
        elif item.role in {"assistant", "ai"}:
            messages.append(AIMessage(content=content))
        elif item.role == "system":
            messages.append(SystemMessage(content=content))
    return messages


def latest_user_message(history: list[ChatHistoryMessage]) -> str:
    for item in reversed(history):
        if item.role == "user" and (item.content or "").strip():
            return item.content.strip()
    return ""


def render_recent_chat_context(history: list[ChatHistoryMessage], char_budget: int = 4000) -> str:
    lines: list[str] = []
    used = 0
    for item in reversed(history):
        if item.role not in {"user", "assistant", "ai"}:
            continue
        content = (item.content or "").strip()
        if not content:
            continue
        role_label = "用户" if item.role == "user" else "助手"
        line = f"- {role_label}: {content}"
        next_size = len(line) + 1
        if lines and used + next_size > char_budget:
            break
        lines.append(line)
        used += next_size
    if not lines:
        return "本次请求未提供历史对话。"
    return "\n".join(reversed(lines))


def _is_image_url(url: str) -> bool:
    """判断URL是否指向图片文件。

    Args:
        url: 文件URL。

    Returns:
        True 表示是图片URL。
    """
    suffix = url.rsplit(".", 1)[-1].lower() if "." in url else ""
    return suffix in IMAGE_EXTENSIONS
