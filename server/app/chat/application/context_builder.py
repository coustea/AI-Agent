"""ChatContextBuilder — 从数据库构建 LangChain 消息列表。

职责：
- 读取历史消息（排除本轮用户消息）
- 转换为 LangChain Message (HumanMessage/AIMessage/ToolMessage/SystemMessage)
- 校验 tool_calls 与 ToolMessage 的对应关系
- 控制最大历史数量
- 清理无效工具链
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage, ToolMessage

from app.chat.memory.service import get_chat_memory_service
from app.config import CHAT_HISTORY_LIMIT
from app.infra.logging import get_logger

logger = get_logger(__name__)

IMAGE_EXTENSIONS = frozenset(["jpg", "jpeg", "png", "gif", "webp", "bmp"])


def build_user_content(text: str, attachments: list[str]) -> list[dict[str, Any]]:
    """构建 OpenAI 格式的用户消息 content"""
    content: list[dict[str, Any]] = []
    if text.strip():
        content.append({"type": "text", "text": text.strip()})
    for url in attachments:
        ext = url.rsplit(".", 1)[-1].lower().split("?")[0] if "." in url else ""
        if ext in IMAGE_EXTENSIONS:
            content.append({"type": "image_url", "image_url": {"url": url}})
        else:
            content.append({"type": "file", "file": {"filename": url.split("/")[-1], "file_id": url}})
    return content


def extract_text_from_content(content: list[dict[str, Any]] | str | Any) -> str:
    """从 list content 或 str 中提取纯文本。"""
    if isinstance(content, list):
        return "".join(
            part["text"] for part in content
            if isinstance(part, dict) and part.get("type") == "text" and "text" in part
        )
    return str(content or "")


def normalize_tool_calls(tool_calls: list[dict] | None) -> list[dict]:
    """标准化工具调用格式，确保字段存在且类型正确。"""
    normalized: list[dict] = []
    for tc in tool_calls or []:
        if not isinstance(tc, dict):
            continue
        normalized.append({
            "id": str(tc.get("id", "")),
            "name": str(tc.get("name", "")),
            "args": tc.get("args", {}) if isinstance(tc.get("args", {}), dict) else {},
            "type": "tool_call",
        })
    return normalized


def convert_stored_message(message: Any) -> AnyMessage | None:
    """将单条数据库消息转换为 LangChain Message。

    Returns None 表示该消息应被忽略（空内容、孤立 ToolMessage 等）。
    """
    role = getattr(message, "role", "")
    raw_content = getattr(message, "content", "")
    tool_calls = getattr(message, "tool_calls", None)
    tool_call_id = getattr(message, "tool_call_id", None)

    if role == "user":
        if isinstance(raw_content, list) and raw_content:
            return HumanMessage(content=raw_content)
        text = str(raw_content or "").strip()
        return HumanMessage(content=text) if text else None
    if role in {"assistant", "ai"}:
        text_content = extract_text_from_content(raw_content).strip()
        if tool_calls:
            normalized_tc = normalize_tool_calls(tool_calls)
            if normalized_tc:
                return AIMessage(content=text_content, tool_calls=normalized_tc)
            if text_content:
                return AIMessage(content=text_content)
            return None
        if text_content:
            return AIMessage(content=text_content)
        return None
    if role == "system":
        text_content = extract_text_from_content(raw_content).strip()
        return SystemMessage(content=text_content) if text_content else None
    if role == "tool" and tool_call_id:
        text_content = extract_text_from_content(raw_content).strip()
        tc_id_str = str(tool_call_id)
        return ToolMessage(content=text_content or "", tool_call_id=tc_id_str)
    return None


def sanitize_tool_message_chain(messages: list[AnyMessage]) -> list[AnyMessage]:
    """校验 tool_calls 与 ToolMessage 的对应关系，清理无效工具链。"""
    result: list[AnyMessage] = []
    valid_tool_call_ids: set[str] = set()

    for msg in messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            # 记录合法的 tool_call ID
            for tc in msg.tool_calls:
                tc_id = str(tc.get("id", "")).strip()
                tc_name = str(tc.get("name", "")).strip()
                if tc_id and tc_name:
                    valid_tool_call_ids.add(tc_id)
            # 保留有效的 tool_calls
            valid_tc = [tc for tc in msg.tool_calls
                       if str(tc.get("id", "")).strip() in valid_tool_call_ids]
            if valid_tc or msg.content:
                result.append(AIMessage(content=msg.content or "", tool_calls=valid_tc if valid_tc else None))
        elif isinstance(msg, ToolMessage):
            # 只保留有对应 tool_call 的 ToolMessage
            if msg.tool_call_id in valid_tool_call_ids:
                result.append(msg)
        else:
            result.append(msg)

    return result


class ChatContextBuilder:
    """从数据库构建对话上下文（LangChain Message 列表）。"""

    async def build_history(
        self,
        user_id: int,
        session_id: str,
        *,
        exclude_message_id: int | None = None,
    ) -> list[AnyMessage]:
        """构建历史消息列表，自动排除本轮用户消息。"""
        svc = get_chat_memory_service()
        raw_messages = await svc.list_messages(
            user_id=user_id, session_id=session_id, limit=CHAT_HISTORY_LIMIT,
        )

        if exclude_message_id is not None:
            raw_messages = [m for m in raw_messages if getattr(m, "id", None) != exclude_message_id]

        if raw_messages and getattr(raw_messages[0], "role", "") != "user":
            first_user_index = next(
                (i for i, m in enumerate(raw_messages) if getattr(m, "role", "") == "user"),
                len(raw_messages),
            )
            raw_messages = raw_messages[first_user_index:]

        messages: list[AnyMessage] = []
        for msg in raw_messages:
            converted = convert_stored_message(msg)
            if converted is not None:
                messages.append(converted)

        return messages

    async def build_session_context(self, user_id: int, session_id: str) -> str:
        """获取会话摘要上下文。"""
        svc = get_chat_memory_service()
        return await svc.get_session_summary_context(user_id=user_id, session_id=session_id)
