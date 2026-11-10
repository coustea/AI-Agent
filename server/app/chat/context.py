"""聊天上下文组装：历史消息清洗与动态背景注入。"""

from __future__ import annotations

import asyncio
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from sqlmodel import select

from app.chat.memory import extract_content_text
from app.chat.schemas import AgentInput, AttachmentInput
from app.config import CHAT_HISTORY_LIMIT
from app.evaluation.guidance import get_effective_guidance_strategy
from app.infra.database import session_scope
from app.infra.logging import get_logger
from app.infra.llm import (
    AIMessage,
    HumanMessage,
    Message,
    SystemMessage,
    ToolCall,
    ToolMessage,
    load_prompt,
)
from app.infra.models import ChatMessage, ChatSession

logger = get_logger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "tutor_agent.md"


def build_user_content(text: str, attachments: list[AttachmentInput]) -> list[dict[str, Any]]:
    """根据用户提问文本与附件列表，构建持久化的 ChatMessage.content 结构。"""
    content: list[dict[str, Any]] = []
    if text.strip():
        content.append({"type": "text", "text": text.strip()})
    for item in attachments:
        is_image = item.file_type == "image"
        filename = item.original_name or item.url.rsplit("/", 1)[-1]
        block: dict[str, Any] = {
            "type": "image_url" if is_image else "file",
            "url": item.url,
            "file_type": item.file_type,
            "original_name": filename,
            "mime_type": item.mime_type,
            "size_bytes": item.size_bytes,
        }
        content.append(block)
    return content


def convert_stored_message(message: ChatMessage) -> Message | None:
    """将当前格式的数据库消息转换为模型消息，历史附件只保留路径说明。"""
    text = extract_content_text(message.content)
    if message.role == "user":
        notes = [
            f"[历史上传文件: {part['original_name']} ({part['url']})]"
            for part in message.content if part.get("type") in {"image_url", "file"}
        ]
        return HumanMessage("\n".join([text, *notes]).strip())
    if message.role == "assistant":
        calls = [
            ToolCall(id=call["id"], name=call["name"], args=call["args"],
                     raw_arguments=json.dumps(call["args"], ensure_ascii=False))
            for call in message.tool_calls or []
        ]
        return AIMessage(text, tool_calls=calls) if text or calls else None
    if message.role == "system":
        return SystemMessage(text) if text else None
    if message.role == "tool" and message.tool_call_id:
        return ToolMessage(text, tool_call_id=message.tool_call_id)
    return None


def sanitize_tool_message_chain(messages: list[Message]) -> list[Message]:
    """校验并清理孤立的 tool_calls 与 ToolMessage，确保满足 OpenAI 消息配对约束。"""
    result: list[Message] = []
    index = 0
    while index < len(messages):
        message = messages[index]
        index += 1
        if message.role == "assistant" and message.tool_calls:
            results: dict[str, Message] = {}
            while index < len(messages) and messages[index].role == "tool":
                reply = messages[index]
                results[reply.tool_call_id] = reply
                index += 1
            calls = [call for call in message.tool_calls if call.id in results]
            if calls:
                result.append(AIMessage(message.content, tool_calls=calls))
                result.extend(results[call.id] for call in calls)
            elif message.content:
                result.append(AIMessage(message.content))
        elif message.role != "tool":
            result.append(message)
    return result


def prune_tool_messages(
    messages: list[Message],
    *,
    keep_recent_turns: int = 2,
    max_chars: int = 300,
) -> list[Message]:
    """裁剪早期对话轮次中过长的 ToolMessage 输出，避免撑爆上下文窗口。"""
    turn_indices = [i for i, m in enumerate(messages) if m.role == "user"]
    recent_turn_start = (
        turn_indices[-keep_recent_turns] if len(turn_indices) >= keep_recent_turns else 0
    )

    pruned: list[Message] = []
    for i, m in enumerate(messages):
        if m.role == "tool" and i < recent_turn_start:
            content_str = str(m.content or "")
            if len(content_str) > max_chars:
                pruned.append(
                    ToolMessage(
                        content=f"[Tool output pruned: 原始长 {len(content_str)} 字符]\n{content_str[:max_chars]}...",
                        tool_call_id=m.tool_call_id or "",
                    )
                )
                continue
        pruned.append(m)
    return pruned


async def load_conversation(
    user_id: int,
    session_id: str,
    *,
    exclude_message_id: int | None = None,
) -> tuple[list[Message], str]:
    """使用会话内置滚动摘要及其水位加载历史，保留完整工具链并裁剪长输出。"""
    async with session_scope() as db:
        chat_session = await db.get(ChatSession, session_id)
        if chat_session is None or chat_session.user_id != user_id:
            return [], ""

        summary = chat_session.summary_markdown or ""
        summarized_through_id = chat_session.last_summarized_message_id or 0

        stmt = (
            select(ChatMessage)
            .where(
                ChatMessage.session_id == session_id,
                ChatMessage.id > summarized_through_id,
            )
            .order_by(ChatMessage.id.desc())
            .limit(CHAT_HISTORY_LIMIT)
        )
        raw_messages = list(reversed((await db.exec(stmt)).all()))

    if exclude_message_id is not None:
        raw_messages = [m for m in raw_messages if m.id != exclude_message_id]

    if raw_messages and raw_messages[0].role != "user":
        first_user_idx = next(
            (i for i, m in enumerate(raw_messages) if m.role == "user"),
            len(raw_messages),
        )
        raw_messages = raw_messages[first_user_idx:]

    converted = [m for msg in raw_messages if (m := convert_stored_message(msg)) is not None]
    sanitized = sanitize_tool_message_chain(converted)
    return prune_tool_messages(sanitized), summary


async def _load_guidance_strategy(user_id: int) -> dict[str, Any] | None:
    """读取用户当前生效的个性化辅导策略。"""
    try:
        async with session_scope() as db:
            return await get_effective_guidance_strategy(db, user_id)
    except Exception as exc:
        logger.warning("[ChatContext] 读取辅导策略失败: user_id=%s err=%s", user_id, exc)
        return None


def _format_attachment_manifest(attachments: list[AttachmentInput]) -> str:
    """生成本轮上传附件的路径与类型清单，引导 Agent 调用对应工具。"""
    if not attachments:
        return ""
    lines = [f"[上传附件]\n学生本轮上传了 {len(attachments)} 个文件："]
    has_image = False
    has_doc = False
    for attachment in attachments:
        url = attachment.url
        filename = attachment.original_name
        if attachment.file_type == "image":
            has_image = True
            lines.append(f"- 图片: `{url}` (文件名: `{filename}`)")
        else:
            has_doc = True
            lines.append(f"- 文档: `{url}` (文件名: `{filename}`)")
    if has_image:
        lines.append("请调用 `view_image(path=..., question=...)` 查看图片，并结合学生提问写出你想从图片中获取的具体信息。")
    if has_doc:
        lines.append("请调用 `read_document(path=...)` 读取文档内容。")
    return "\n".join(lines)


async def build_turn_messages(inp: AgentInput) -> list[Message]:
    """根据 AgentInput 并行加载历史、会话摘要与辅导策略，组装完整 Message 列表。"""
    (history, session_summary), strategy = await asyncio.gather(
        load_conversation(
            inp.user_id,
            inp.session_id,
            exclude_message_id=inp.user_message_id or None,
        ),
        _load_guidance_strategy(inp.user_id),
    )
    logger.info(
        "[ChatContext] 上下文装配完成: user_id=%d session=%s 历史=%d 条 摘要=%d 字符 策略=%s 附件=%d video_mode=%s diagram=%s",
        inp.user_id, inp.session_id, len(history), len(session_summary),
        bool(strategy), len(inp.attachments), inp.video_mode, inp.diagram_mode,
    )

    blocks: list[str] = [f"[当前日期]\n{datetime.now().date().isoformat()}"]
    if session_summary:
        blocks.append(f"[会话摘要]\n{session_summary}")
    if inp.attachments:
        blocks.append(_format_attachment_manifest(inp.attachments))
    if inp.video_mode:
        blocks.append(
            "[本轮必须生成视频]\n"
            "学生已在前端勾选视频，本轮必须调用 `generate_teaching_video` 工具产出一个教学视频。\n"
            "视频生成成功后，用 2-3 句话简要说明视频讲了什么，不要再长篇复述内容。"
        )
    elif inp.diagram_mode == "required":
        blocks.append(
            "[本轮必须生成图解]\n"
            "学生已在前端勾选图解，本轮回答必须包含一个 ```mermaid 代码块。\n"
            "图解放在回答开头或紧接结论之后，正文用 2-4 句话简要说明关键点，不要长篇展开。"
        )
    if strategy:
        blocks.append(
            "[辅导策略]\n"
            f"本期结论: {strategy.get('conclusion')}\n"
            f"推荐单次时长: {strategy.get('recommended_session_minutes')} 分钟\n"
            f"辅导风格: {strategy.get('tutoring_style')}\n"
            f"重点关注主题: {'、'.join(strategy.get('focus_topics', [])) or '无'}\n"
            f"策略依据: {strategy.get('reason')}"
        )

    dynamic_context = "\n\n".join(blocks)
    question = inp.effective_question
    human_text = f"{question}\n\n{dynamic_context}" if dynamic_context else question

    return [
        SystemMessage(load_prompt(_PROMPT_PATH)),
        *history,
        HumanMessage(human_text),
    ]
