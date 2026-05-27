"""TutorAgent 对话轮次的运行时准备辅助函数。

为 TutorAgent 对话轮次准备运行时状态和上下文。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage

from app.chat.request import ChatHistoryMessage
from app.chat.schemas import TutorAgentContext, TutorState

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


@dataclass(frozen=True)
class UserMessageRecord:
    """用户消息记录。

    包含消息内容和附件信息。
    """
    content: str  # 消息文本内容
    attachments: list[dict[str, Any]] | None  # 附件列表


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


def prepare_tutor_state(context: TutorAgentContext, history: list[ChatHistoryMessage]) -> TutorState:
    """根据已初始化的代理上下文和提供的历史记录构建 LangGraph 状态。"""
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
        "need_teaching_diagram": context.need_teaching_diagram,
        "teaching_diagram": None,
        "teaching_diagram_error": None,
        "diagram_type": context.preferred_diagram_type,
        "route": "",
        "execution_mode": "",
        "retrieved_profile_context": "",
        "retrieved_memory_context": "",
        "session_summary_context": context.session_summary_context,
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


def _is_image_url(url: str) -> bool:
    """判断URL是否指向图片文件。

    Args:
        url: 文件URL。

    Returns:
        True 表示是图片URL。
    """
    suffix = url.rsplit(".", 1)[-1].lower() if "." in url else ""
    return suffix in IMAGE_EXTENSIONS
