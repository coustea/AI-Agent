"""Chat 对话轮次的运行时辅助函数。

负责处理附件分类、历史消息转换，以及构造持久化所需的用户消息记录。
图片 URL 会追加 [Attached Images:] 标记供模型理解。

三个核心函数的调用关系：
  - _classify_attachments     — 附件分类，被 agent.py 和 stages.py 调用
  - build_user_message_record — 构建用户消息记录，被 service.py 调用做持久化
  - history_to_langchain_messages — 历史消息转为 LangChain 格式，被 agent.py 调用进推理 prompt
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage, ToolMessage

from app.chat.schemas import ChatHistoryMessage

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


def history_to_langchain_messages(history: list[ChatHistoryMessage]) -> list[AnyMessage]:
    def _normalize_tool_calls(tool_calls: list[dict] | None) -> list[dict]:
        normalized: list[dict] = []
        for tool_call in tool_calls or []:
            if not isinstance(tool_call, dict):
                continue
            normalized.append(
                {
                    "id": str(tool_call.get("id", "")),
                    "name": str(tool_call.get("name", "")),
                    "args": tool_call.get("args", {}) if isinstance(tool_call.get("args", {}), dict) else {},
                    "type": "tool_call",
                }
            )
        return normalized

    messages: list[AnyMessage] = []
    for item in history:
        content = (item.content or "").strip()
        if item.role == "user" and content:
            messages.append(HumanMessage(content=content))
        elif item.role in {"assistant", "ai"} and (content or item.tool_calls):
            messages.append(AIMessage(content=content, tool_calls=_normalize_tool_calls(item.tool_calls)))
        elif item.role == "system" and content:
            messages.append(SystemMessage(content=content))
        elif item.role == "tool" and item.tool_call_id:
            messages.append(ToolMessage(content=content, tool_call_id=item.tool_call_id))
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
