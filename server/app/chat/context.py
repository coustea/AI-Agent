"""ChatContextBuilder — 从数据库构建对话消息列表。

职责：
- 读取历史消息（排除本轮用户消息）
- 转换为 Message (user/assistant/tool/system)
- 校验 tool_calls 与 tool 消息的对应关系
- 控制最大历史数量
- 清理无效工具链
"""

from __future__ import annotations

import json
from typing import Any

from app.infra.llm import (
    AIMessage,
    HumanMessage,
    Message,
    SystemMessage,
    ToolCall,
    ToolMessage,
)

from app.chat.memory.types import extract_content_text
from app.chat.memory.service import get_chat_memory_service
from app.config import CHAT_HISTORY_LIMIT
from app.infra.logging import get_logger

logger = get_logger(__name__)



# 构建用户消息 content：文本段 + 图片/文件附件段
def build_user_content(text: str, attachments: list[Any]) -> list[dict[str, Any]]:
    """构建用户消息；原始附件展示信息直接保存在 content 中。"""
    content: list[dict[str, Any]] = []
    if text.strip():
        content.append({"type": "text", "text": text.strip()})
    for attachment in attachments:
        def value(name: str, default: Any = None) -> Any:
            if isinstance(attachment, dict):
                return attachment.get(name, default)
            return getattr(attachment, name, default)

        url = str(value("url", "") or "")
        file_type = str(value("file_type", "") or "")
        item = {
            "type": "image_url" if file_type == "image" else "file",
            "url": url,
            "file_type": file_type,
            "original_name": str(value("original_name", "") or url.rsplit("/", 1)[-1]),
            "mime_type": value("mime_type"),
            "size_bytes": int(value("size_bytes", 0) or 0),
        }
        if file_type == "image":
            item["image_url"] = {"url": url}
        else:
            item["file"] = {
                "filename": item["original_name"],
                "file_id": url,
            }
        content.append(item)
    return content


# 标准化工具调用格式，确保 id/name/args 字段齐全且类型正确
def normalize_tool_calls(tool_calls: list[dict] | None) -> list[ToolCall]:
    """标准化工具调用格式，确保字段存在且类型正确。"""
    normalized: list[ToolCall] = []
    for tc in tool_calls or []:
        if not isinstance(tc, dict):
            continue
        tool_id = str(tc.get("id", ""))
        tool_name = str(tc.get("name", ""))
        if not tool_id or not tool_name:
            continue
        raw_args = tc.get("args", {})
        normalized.append(
            ToolCall(
                id=tool_id,
                name=tool_name,
                args=raw_args if isinstance(raw_args, dict) else {},
                raw_arguments=json.dumps(raw_args, ensure_ascii=False) if isinstance(raw_args, dict) else "",
            )
        )
    return normalized


# 将单条数据库消息转换为 Message（孤立/空消息返回 None）
def convert_stored_message(message: Any) -> Message | None:
    """将单条数据库消息转换为 Message。

    Returns None 表示该消息应被忽略（空内容、孤立 ToolMessage 等）。
    """
    role = getattr(message, "role", "")
    raw_content = getattr(message, "content", "")
    tool_calls = getattr(message, "tool_calls", None)
    tool_call_id = getattr(message, "tool_call_id", None)

    metadata = getattr(message, "usage_metadata", None)
    if isinstance(metadata, dict) and metadata.get("response_mode") == "video":
        return None

    # 用户消息：将结构化 content 转为 HumanMessage（文本/图片/文件）
    if role == "user":
        if isinstance(raw_content, list) and raw_content:
            model_content: list[dict[str, Any]] = []
            for part in raw_content:
                if not isinstance(part, dict):
                    continue
                part_type = part.get("type")
                if part_type == "text":
                    model_content.append({"type": "text", "text": str(part.get("text") or "")})
                elif part_type == "image_url" and isinstance(part.get("image_url"), dict):
                    model_content.append({"type": "image_url", "image_url": part["image_url"]})
                elif part_type == "file" and isinstance(part.get("file"), dict):
                    model_content.append({"type": "file", "file": part["file"]})
            return HumanMessage(content=model_content) if model_content else None
        text = str(raw_content or "").strip()
        return HumanMessage(content=text) if text else None
    # 助手消息：含工具调用则转 AIMessage（带 tool_calls），否则转纯文本
    if role in {"assistant", "ai"}:
        text_content = extract_content_text(raw_content).strip()
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
    # 系统消息：转 SystemMessage
    if role == "system":
        text_content = extract_content_text(raw_content).strip()
        return SystemMessage(content=text_content) if text_content else None
    # 工具消息：转 ToolMessage（需有 tool_call_id）
    if role == "tool" and tool_call_id:
        text_content = extract_content_text(raw_content).strip()
        tc_id_str = str(tool_call_id)
        return ToolMessage(content=text_content or "", tool_call_id=tc_id_str)
    return None


# 校验 tool_calls 与 ToolMessage 的对应关系，剔除孤立/无效的工具链
def sanitize_tool_message_chain(messages: list[Message]) -> list[Message]:
    """校验 tool_calls 与 ToolMessage 的对应关系，清理无效工具链。"""
    # 收集所有合法 tool_call 的 ID
    result: list[Message] = []
    valid_tool_call_ids: set[str] = set()

    for msg in messages:
        # 按 role 判定（Message 是 dataclass，不能用 isinstance 区分角色）
        if msg.role == "assistant" and msg.tool_calls:
            # 记录合法的 tool_call ID
            for tc in msg.tool_calls:
                if tc.id and tc.name:
                    valid_tool_call_ids.add(tc.id)
            # 保留有效的 tool_calls
            valid_tc = tuple(tc for tc in msg.tool_calls if tc.id in valid_tool_call_ids)
            if valid_tc or msg.content:
                result.append(AIMessage(msg.content or "", tool_calls=valid_tc))
        elif msg.role == "tool":
            # 只保留有对应 tool_call 的 ToolMessage
            if msg.tool_call_id in valid_tool_call_ids:
                result.append(msg)
        else:
            result.append(msg)

    # 返回清理后的消息链
    return result


# ChatContextBuilder：从数据库读取并组装对话历史为 Message 列表
class ChatContextBuilder:
    """从数据库构建对话上下文（Message 列表）。"""

    # 构建历史消息列表，自动排除本轮用户消息并注入附件分析上下文
    async def build_history(
        self,
        user_id: int,
        session_id: str,
        *,
        exclude_message_id: int | None = None,
    ) -> list[Message]:
        """构建历史消息列表，自动排除本轮用户消息。"""
        logger.info(
            "[ChatContext] build_history 开始: user_id=%s session_id=%s exclude_message_id=%s",
            user_id, session_id, exclude_message_id,
        )
        # 读取原始消息、压缩摘要块与附件分析
        svc = get_chat_memory_service()
        raw_messages = await svc.list_messages(
            user_id=user_id, session_id=session_id, limit=CHAT_HISTORY_LIMIT,
        )
        summary_blocks = await svc.list_summary_blocks(
            user_id=user_id,
            session_id=session_id,
        )
        # 计算已压缩到的消息 ID，跳过被压缩覆盖的早期消息
        summarized_through_id = max(
            (int(block.end_message_id or 0) for block in summary_blocks),
            default=0,
        )
        if summarized_through_id:
            raw_messages = [
                message
                for message in raw_messages
                if int(getattr(message, "id", 0) or 0) > summarized_through_id
            ]
        # 仅保留未被压缩且属于会话的附件分析，按消息 ID 分组
        analyses = await svc.list_attachment_analyses(
            user_id=user_id,
            session_id=session_id,
            completed_only=True,
        )
        analyses_by_message_id: dict[int, list[Any]] = {}
        for analysis in analyses:
            if int(analysis.user_message_id or 0) <= summarized_through_id:
                continue
            analyses_by_message_id.setdefault(analysis.user_message_id, []).append(analysis)

        # 排除本轮用户消息及其附件分析
        if exclude_message_id is not None:
            raw_messages = [m for m in raw_messages if getattr(m, "id", None) != exclude_message_id]
            analyses_by_message_id.pop(exclude_message_id, None)

        video_request_ids = {
            int(message.user_message_id)
            for message in raw_messages
            if getattr(message, "role", "") == "assistant"
            and isinstance(getattr(message, "usage_metadata", None), dict)
            and message.usage_metadata.get("response_mode") == "video"
            and getattr(message, "user_message_id", None) is not None
        }
        if video_request_ids:
            raw_messages = [
                message for message in raw_messages
                if getattr(message, "id", None) not in video_request_ids
                and getattr(message, "user_message_id", None) not in video_request_ids
            ]
            for message_id in video_request_ids:
                analyses_by_message_id.pop(message_id, None)

        # 若历史不以用户消息开头，截断到首个用户消息
        if raw_messages and getattr(raw_messages[0], "role", "") != "user":
            first_user_index = next(
                (i for i, m in enumerate(raw_messages) if getattr(m, "role", "") == "user"),
                len(raw_messages),
            )
            raw_messages = raw_messages[first_user_index:]

        # 转换每条消息，并为带附件分析的用户消息注入上下文 SystemMessage
        messages: list[Message] = []
        for msg in raw_messages:
            converted = convert_stored_message(msg)
            if converted is not None:
                messages.append(converted)
            if getattr(msg, "role", "") == "user" and getattr(msg, "id", None) in analyses_by_message_id:
                analysis_parts = [
                    f"[{item.analysis_type}] {item.content}".strip()
                    for item in analyses_by_message_id[int(msg.id)]
                    if str(item.content or "").strip()
                ]
                if analysis_parts:
                    messages.append(
                        SystemMessage(
                            content=(
                                "以下是该用户消息所附文件的持久化分析结果，仅作为上下文，"
                                "不要把它误认为用户原话：\n"
                                + "\n".join(analysis_parts)
                            )
                        )
                    )

        # 清理无效工具链后返回历史消息
        result = sanitize_tool_message_chain(messages)
        logger.info(
            "[ChatContext] build_history 完成: raw=%d messages=%d summarized_through=%s",
            len(raw_messages), len(result), summarized_through_id,
        )
        return result
