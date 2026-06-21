"""聊天服务层 — 对话流编排、记忆管理、文件上传。

核心函数：
  build_messages()  — 从数据库构建 LangChain 消息列表（含工具调用链）
  chat()            — 总编排：build_messages → TutorAgent.chat() → 转发 SSE 事件 → 持久化

ChatUseCases 保留会话管理、文件上传等辅助功能，对话核心逻辑委托给 TutorAgent。
"""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage, ToolMessage

from app.chat.agent import TutorAgent
from app.chat.events import build_attachment_status_payload, build_persisted_tool_activity
from app.chat.memory.service import get_chat_memory_service as _get_chat_memory_service
from app.chat.safety import ContentSafetyFilter, SafetyResult, safety_filter
from app.chat.schemas import (
    TutorAgentInput,
    UploadResponse,
)
from app.chat.storage.file_store import LocalFileStore
from app.chat.storage.message_item import ChatMessageItem
from app.config import CHAT_DIR, MAX_UPLOAD_FILES_PER_REQUEST, IMAGE_EXTENSIONS, CHAT_HISTORY_LIMIT
from app.infra.logging import get_logger
from app.infra.models import ChatMessage
from app.infra.agent_events import AgentEventEmitter

logger = get_logger(__name__)


# -----------------------------------------------------------------------
# 核心函数：build_messages / chat helpers / chat
# -----------------------------------------------------------------------


async def _create_turn(
    uc: ChatUseCases,
    *,
    user_id: int,
    session_id: str,
    user_input: str,
    attachments: list[str],
    enable_web_search: bool,
    need_teaching_diagram: bool,
) -> tuple[int, int, int | None, str]:
    """Create turn, persist user message, and generate title if first message.

    Returns (turn_id, turn_index, user_message_id, user_content).
    """
    svc = uc._memory_service
    current_message = (user_input or "").strip()
    merged_attachments = list(dict.fromkeys(attachments or []))

    user_content = current_message
    if merged_attachments:
        image_urls, file_urls = [], []
        for url in merged_attachments:
            ext = url.rsplit(".", 1)[-1].lower().split("?")[0] if "." in url else ""
            if ext in IMAGE_EXTENSIONS:
                image_urls.append(url)
            else:
                file_urls.append(url)
        if image_urls:
            user_content += f" [Attached Images: {', '.join(image_urls)}]"
        if file_urls:
            user_content += f" [Attached Files: {', '.join(file_urls)}]"

    turn_row = await svc.create_turn(
        user_id=user_id, session_id=session_id,
        route="default", execution_mode="default",
        has_attachments=bool(merged_attachments),
        used_web_search=enable_web_search,
        used_teaching_diagram=need_teaching_diagram,
        status="running",
    )
    turn_id = turn_row.id
    turn_index = int(getattr(turn_row, "turn_index", 0) or 0)

    await svc.append_turn_event(
        user_id=user_id, session_id=session_id, turn_id=turn_id,
        event_type="turn.started", payload={"status": "running"},
    )

    user_attachment_records = [
        {"url": url, "type": "image" if url.rsplit(".", 1)[-1].lower().split("?")[0] in IMAGE_EXTENSIONS else "document", "name": url.split("/")[-1]}
        for url in merged_attachments
    ] if merged_attachments else None

    user_message = await uc.save_message(
        user_id=user_id, session_id=session_id,
        role="user", content=user_content,
        attachments=user_attachment_records,
        turn_id=turn_id, message_kind="user_input",
    )
    user_message_id = getattr(user_message, "id", None)

    await svc.append_turn_event(
        user_id=user_id, session_id=session_id, turn_id=turn_id,
        event_type="user.message", payload={"content": user_content},
    )

    if await uc.count_messages(user_id, session_id) <= 1:
        uc._spawn_background(
            svc.generate_session_title(user_id=user_id, session_id=session_id, first_message=current_message),
            label="generate_title",
        )

    return turn_id, turn_index, user_message_id, user_content


async def _persist_assistant_reply(
    uc: ChatUseCases,
    *,
    user_id: int,
    session_id: str,
    turn_id: int,
    full_answer: str,
    sources: list[dict[str, Any]],
    diagram_result: dict[str, Any] | None,
    attachment_analyses: list[dict[str, Any]],
    enable_web_search: bool,
    need_teaching_diagram: bool,
) -> None:
    """Safety-filter, save assistant message, finalize turn transcript and status."""
    svc = uc._memory_service

    if full_answer:
        safety_result = await safety_filter.check(full_answer)
        if safety_result.has_violation:
            full_answer = safety_result.sanitized_text

    if full_answer:
        await uc.save_message(
            user_id=user_id, session_id=session_id,
            role="assistant", content=full_answer,
            knowledge_sources=sources if sources else None,
            teaching_diagram=diagram_result,
            attachment_analyses=attachment_analyses if attachment_analyses else None,
            turn_id=turn_id, message_kind="assistant_answer",
        )

    await svc.append_turn_event(
        user_id=user_id, session_id=session_id, turn_id=turn_id,
        event_type="answer.completed", payload={"answer": full_answer},
    )
    await svc.finalize_turn_transcript(
        user_id=user_id, session_id=session_id, turn_id=turn_id,
        status="completed", final_answer=full_answer,
    )
    await svc.update_turn(
        user_id=user_id, session_id=session_id, turn_id=turn_id,
        status="completed", route="answer", execution_mode="answer",
        used_web_search=enable_web_search, used_teaching_diagram=need_teaching_diagram,
        error_message=None,
    )


async def _run_compression_check(
    svc: Any,
    *,
    user_id: int,
    session_id: str,
    turn_id: int,
    user_message: str,
    assistant_reply: str,
) -> AsyncIterator[dict[str, Any]]:
    """Check context compression, yield SSE status events, and send final compression_payload via send().

    Usage: ``async for event in _run_compression_check(...): yield event``
    After iteration, access ``compression_payload`` attribute on the generator.
    """
    compression_payload: dict[str, Any] = {"compressed": False}

    yield {
        "event": "status",
        "data": {
            "stage": "compression_checking",
            "message": "正在检查是否需要整理上下文...",
        },
    }
    try:
        counters = await svc.update_post_turn_counters(
            user_id=user_id,
            session_id=session_id,
            turn_id=turn_id,
            user_message=user_message,
            assistant_reply=assistant_reply,
        )
        compression_payload["counters"] = counters

        if await svc.should_compress_session(user_id=user_id, session_id=session_id):
            yield {
                "event": "status",
                "data": {
                    "stage": "compression_running",
                    "message": "正在整理较早的对话上下文...",
                },
            }
            summary_block = await svc.compress_session(
                user_id=user_id,
                session_id=session_id,
                reason="post_turn_visible",
            )
        else:
            summary_block = None

        if summary_block is not None:
            compression_payload.update(
                {
                    "compressed": True,
                    "summary_block_id": getattr(summary_block, "id", None),
                    "summarized_message_count": int(getattr(summary_block, "summarized_message_count", 0) or 0),
                }
            )
            compression_message = "上下文整理完成，后续回答会继续使用摘要记忆。"
        else:
            compression_message = "当前上下文仍然轻量，无需整理。"
    except Exception as exc:
        logger.error("[chat] visible compression failed user=%s session=%s err=%s", user_id, session_id, exc)
        compression_payload.update({"compressed": False, "error": str(exc)})
        compression_message = "上下文整理暂时失败，本轮回答已保存。"

    yield {
        "event": "status",
        "data": {
            "stage": "compression_done",
            "message": compression_message,
            **compression_payload,
        },
    }

    _run_compression_check.compression_payload = compression_payload


def _normalize_tool_calls(tool_calls: list[dict] | None) -> list[dict]:
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


async def build_messages(user_id: int, session_id: str) -> list[AnyMessage]:
    """从数据库构建 LangChain 消息列表。

    流程：
    1. 查询 ChatMessage（按时间升序，最近 HISTORY_LIMIT 条）
    2. 查询 ChatToolInvocation（关联到这些消息的工具调用）
    3. 将消息转为 LangChain 类型：HumanMessage / AIMessage(tool_calls) / ToolMessage(tool_call_id)

    注：会话压缩摘要由 TutorAgent 在系统提示词中注入，此处不再重复添加。
    """
    svc = _get_chat_memory_service()

    # 查询历史消息
    raw_messages = await svc.list_messages(user_id=user_id, session_id=session_id, limit=CHAT_HISTORY_LIMIT)
    if raw_messages and getattr(raw_messages[0], "role", "") != "user":
        first_user_index = next(
            (index for index, item in enumerate(raw_messages) if getattr(item, "role", "") == "user"),
            len(raw_messages),
        )
        raw_messages = raw_messages[first_user_index:]

    attachment_analyses = await svc.list_attachment_analyses(
        user_id=user_id,
        session_id=session_id,
        limit=max(CHAT_HISTORY_LIMIT * 2, 50),
    )
    analyses_by_turn: dict[int, list[Any]] = {}
    for analysis in attachment_analyses:
        turn_id = getattr(analysis, "turn_id", None)
        if turn_id is not None:
            analyses_by_turn.setdefault(turn_id, []).append(analysis)

    # 查询工具调用记录，按 tool_call_id 建索引
    tool_invocations = await svc.list_tool_invocations(user_id=user_id, session_id=session_id, limit=50)
    invocations_by_id: dict[str, Any] = {}
    for inv in tool_invocations:
        tc_id = getattr(inv, "tool_call_id", None)
        if tc_id:
            invocations_by_id[tc_id] = inv

    # 转换为 LangChain 消息
    messages: list[AnyMessage] = []
    for msg in raw_messages:
        role = getattr(msg, "role", "")
        content = (getattr(msg, "content", "") or "").strip()
        tool_calls = getattr(msg, "tool_calls", None)
        tool_call_id = getattr(msg, "tool_call_id", None)

        if role == "user" and content:
            analyses = analyses_by_turn.get(getattr(msg, "turn_id", None), [])
            analysis_context = "\n\n".join(
                f"[{getattr(item, 'analysis_type', 'attachment')}] {getattr(item, 'summary_text', '')}"
                for item in reversed(analyses)
                if str(getattr(item, "summary_text", "") or "").strip()
            )
            if analysis_context:
                content = f"{content}\n\n[历史附件分析结果]\n{analysis_context}"
            messages.append(HumanMessage(content=content))
        elif role in {"assistant", "ai"} and (content or tool_calls):
            # 如果有 tool_calls，构建 AIMessage(tool_calls=[...])
            normalized_tc = _normalize_tool_calls(tool_calls)
            if normalized_tc:
                messages.append(AIMessage(content=content, tool_calls=normalized_tc))
            elif content:
                messages.append(AIMessage(content=content))
        elif role == "system" and content:
            messages.append(SystemMessage(content=content))
        elif role == "tool" and tool_call_id:
            # ToolMessage 必须关联 tool_call_id
            tc_id_str = str(tool_call_id)
            messages.append(ToolMessage(content=content or "", tool_call_id=tc_id_str))

    return messages


# SSE 事件类型 → 前端 SSE event 名称映射
_SSE_EVENT_MAP: dict[str, str] = {
    "message_start": "start",
    "classify_done": "status",
    "file_analysis_start": "status",
    "file_analysis_done": "attachment",
    "agent_status": "agent_status",
    "answer_token": "token",
    "answer_done": "status",
    "diagram_start": "status",
    "diagram_done": "diagram",
    "memory_update_start": "status",
    "memory_update_done": "status",
    "final": "done",
    "error": "error",
}


async def chat(
    *,
    user_id: int,
    session_id: str,
    user_input: str,
    attachments: list[str] | None = None,
    enable_web_search: bool = False,
    need_teaching_diagram: bool = False,
) -> AsyncIterator[dict[str, Any]]:
    uc = get_chat_usecases()
    effective_session = session_id or uc.default_session_id(user_id)
    merged_attachments = list(dict.fromkeys(attachments or []))
    current_message = (user_input or "").strip()

    if not current_message:
        yield {"event": "error", "data": "请输入您的问题。"}
        yield {"event": "done", "data": {"session_id": effective_session, "error": True}}
        return

    logger.info(
        "[chat] 开始对话: user_id=%s session_id=%s msg_len=%d attachments=%d",
        user_id, effective_session, len(current_message), len(merged_attachments),
    )

    yield {
        "event": "status",
        "data": {
            "stage": "preparing_context",
            "message": "正在分析附件并准备本轮对话..." if merged_attachments else "正在准备本轮对话...",
        },
    }

    # ── 1. 创建 turn + 持久化用户消息 ──
    turn_id, turn_index, user_message_id, user_content = await _create_turn(
        uc,
        user_id=user_id,
        session_id=effective_session,
        user_input=user_input,
        attachments=merged_attachments,
        enable_web_search=enable_web_search,
        need_teaching_diagram=need_teaching_diagram,
    )

    # ── 2. 构建上下文 ──
    svc = uc._memory_service
    history_messages = await build_messages(user_id, effective_session)
    session_summary = await svc.get_session_summary_context(user_id=user_id, session_id=effective_session)

    # ── 3. 调用 TutorAgent ──
    agent_input = TutorAgentInput(
        user_id=user_id,
        session_id=effective_session,
        turn_id=turn_id,
        user_message_id=user_message_id,
        question=current_message,
        attachments=merged_attachments,
        history_messages=history_messages,
        session_summary=session_summary,
        enable_web_search=enable_web_search,
        need_teaching_diagram=need_teaching_diagram,
    )

    agent = TutorAgent()
    full_answer = ""
    tool_invocations: list[dict[str, Any]] = []
    diagram_result: dict[str, Any] | None = None
    sources: list[dict[str, Any]] = []
    attachment_analyses: list[dict[str, Any]] = []
    has_error = False

    try:
        async for event in agent.chat(agent_input):
            sse_event = _SSE_EVENT_MAP.get(event.type, "status")
            sse_data = event.payload

            if event.type == "answer_token":
                yield {"event": "token", "data": sse_data.get("token", "")}
                continue

            if event.type == "final":
                full_answer = sse_data.get("final_answer", "")
                diagram_result = sse_data.get("diagram_result")
                tool_invocations = sse_data.get("tool_invocations", [])
                sources = sse_data.get("sources", [])
                attachment_analyses = sse_data.get("attachment_analyses", [])

                if diagram_result is not None:
                    yield {"event": "diagram", "data": diagram_result}

                yield {
                    "event": "status",
                    "data": {
                        "stage": "answer_done",
                        "message": "回答已生成，正在保存本轮学习记录...",
                    },
                }
                continue

            if event.type == "error":
                has_error = True
                yield {"event": "error", "data": sse_data.get("error", "未知错误")}
                yield {"event": "done", "data": {"session_id": effective_session, "error": True}}
                return

            yield {"event": sse_event, "data": sse_data}

    except Exception as exc:
        logger.exception("[chat] TutorAgent 执行失败")
        has_error = True
        if turn_id is not None:
            await svc.append_turn_event(
                user_id=user_id, session_id=effective_session, turn_id=turn_id,
                event_type="turn.failed", payload={"error": str(exc)},
            )
            await svc.update_turn(
                user_id=user_id, session_id=effective_session, turn_id=turn_id,
                status="failed", route="default", execution_mode="default",
                used_web_search=enable_web_search, used_teaching_diagram=need_teaching_diagram,
                error_message=str(exc),
            )
        yield {"event": "error", "data": f"服务器出错: {exc}"}
        yield {"event": "done", "data": {"session_id": effective_session, "error": True}}
        return

    # ── 4. 持久化助手回复 ──
    compression_payload: dict[str, Any] = {"compressed": False}

    if turn_id is not None:
        yield {"event": "status", "data": {"stage": "persisting_turn", "message": "正在保存本轮学习记录..."}}
        await _persist_assistant_reply(
            uc,
            user_id=user_id,
            session_id=effective_session,
            turn_id=turn_id,
            full_answer=full_answer,
            sources=sources,
            diagram_result=diagram_result,
            attachment_analyses=attachment_analyses,
            enable_web_search=enable_web_search,
            need_teaching_diagram=need_teaching_diagram,
        )

    # ── 5. 可见压缩检查 ──
    if not has_error and full_answer and turn_id is not None:
        async for sse_event in _run_compression_check(
            svc,
            user_id=user_id,
            session_id=effective_session,
            turn_id=turn_id,
            user_message=current_message,
            assistant_reply=full_answer,
        ):
            yield sse_event
        compression_payload = getattr(_run_compression_check, "compression_payload", {"compressed": False})

    if not has_error:
        yield {
            "event": "done",
            "data": {
                "session_id": effective_session,
                "full_response": full_answer,
                "knowledge_sources": sources,
                "teaching_diagram": diagram_result,
                "tool_calls": [
                    {"id": inv.get("tool_name", ""), "name": inv.get("tool_name", ""), "args": inv.get("payload", {})}
                    for inv in tool_invocations
                ],
                "attachment_analyses": attachment_analyses,
                "context_compression": compression_payload,
            },
        }

    # ── 6. 后台任务 ──
    if full_answer and turn_id is not None:
        async def _post_turn():
            await agent.run_background_memory_jobs(
                user_id=user_id,
                session_id=effective_session,
                turn_id=turn_id,
                user_message=current_message,
                assistant_reply=full_answer,
                turn_index=turn_index,
            )

        uc._spawn_background(_post_turn(), label="post_turn")


def _runtime_status(value: Any) -> str:
    status = str(value or "running")
    return {
        "done": "completed",
        "finished": "completed",
        "error": "failed",
    }.get(status, status if status in {"pending", "running", "completed", "failed", "skipped"} else "running")


async def _publish_chat_runtime_event(
    emitter: AgentEventEmitter,
    event: dict[str, Any],
) -> bool:
    """把辅导内部事件映射成唯一的 AgentEvent；返回是否失败。"""
    event_name = str(event.get("event") or "status")
    data = event.get("data")
    payload = data if isinstance(data, dict) else {}

    if event_name == "token":
        await emitter.content_delta(str(data or ""))
        return False
    if event_name == "agent_status":
        await emitter.tool_status(
            status=_runtime_status(payload.get("status")),
            activity_id=str(payload.get("activity_id") or "") or None,
            agent_id=str(payload.get("tool_name") or "") or None,
            title=str(payload.get("title") or "工具调用"),
            summary=str(payload.get("summary") or payload.get("message") or ""),
            detail=payload.get("detail") if isinstance(payload.get("detail"), dict) else {},
            elapsed_ms=(payload.get("detail") or {}).get("duration_ms") if isinstance(payload.get("detail"), dict) else None,
        )
        return False
    if event_name == "attachment":
        await emitter.agent_status(
            status=_runtime_status(payload.get("status")),
            activity_id=str(payload.get("activity_id") or "") or None,
            agent_id="attachment_analyzer",
            title=str(payload.get("title") or "附件分析"),
            summary=str(payload.get("summary") or payload.get("message") or ""),
            detail=payload.get("detail") if isinstance(payload.get("detail"), dict) else {},
        )
        return False
    if event_name == "diagram" and payload:
        await emitter.artifact_ready(
            activity_id="teaching-diagram",
            agent_id="diagram_generator",
            title="教学图解已生成",
            detail=payload,
        )
        return False
    if event_name == "error":
        return True
    if event_name == "status":
        await emitter.agent_status(
            activity_id=str(payload.get("stage") or "chat-workflow"),
            agent_id="tutor",
            title=str(payload.get("message") or "正在处理"),
            summary=str(payload.get("message") or ""),
            detail={key: value for key, value in payload.items() if key != "message"},
        )
    return False


async def run_chat_agent(
    *,
    run_id: str,
    user_id: int,
    session_id: str,
    user_input: str,
    attachments: list[str],
    enable_web_search: bool,
    need_teaching_diagram: bool,
) -> None:
    """后台执行一次辅导，并通过全局事件流主动推送运行状态。"""
    emitter = AgentEventEmitter(run_id=run_id, module="chat", business_id=session_id)
    await emitter.started(title="智能辅导已开始")
    failed = False
    try:
        async for event in chat(
            user_id=user_id,
            session_id=session_id,
            user_input=user_input,
            attachments=attachments or None,
            enable_web_search=enable_web_search,
            need_teaching_diagram=need_teaching_diagram,
        ):
            failed = await _publish_chat_runtime_event(emitter, event) or failed
        if failed:
            await emitter.failed(title="回答失败", summary="智能辅导暂时无法完成本次回答")
        else:
            await emitter.completed(title="回答完成")
    except Exception:
        logger.exception("chat_agent_run_failed: run_id=%s", run_id)
        await emitter.failed(title="回答失败", summary="智能辅导暂时无法完成本次回答")





class ChatUseCases:
    """聊天服务核心类 — 编排完整的对话生命周期。

    职责：
    1. 请求解析和会话管理（创建/归档/查询）
    2. 附件上传、存储和分析
    3. 流式对话（SSE 事件流）
    4. 安全过滤（敏感词检测）
    5. 消息持久化（消息、工具调用、turn 事件）
    6. 后台任务（记忆管线、画像更新）

    通过 get_chat_usecases() 获取单例，避免重复初始化。
    """

    def __init__(self) -> None:
        # 记忆服务：管理会话、消息、turn 事件的持久化
        self._memory_service = get_chat_memory_service()
        # 本地文件存储：用户上传文件的磁盘读写
        self.file_store: LocalFileStore = LocalFileStore()
        # 后台任务集合：防止未等待的协程被 GC 回收
        self._background_tasks: set[asyncio.Task] = set()
        # 已上传文件的 URL→数据库 ID 映射
        self._uploaded_file_ids_by_url: dict[str, int] = {}

    def default_session_id(self, user_id: int) -> str:
        """生成默认会话 ID — 格式: user-{user_id}-default-mentor。"""
        return f"user-{user_id}-default-mentor"

    async def list_sessions(self, user_id: int, limit: int = 20) -> list[dict[str, Any]]:
        """列出用户的最近 N 个会话，按更新时间倒序。"""
        sessions = await self._memory_service.list_sessions(user_id=user_id, limit=limit)
        return [{"id": item.id, "title": item.title, "updated_at": item.updated_at} for item in sessions]

    async def create_session(self, user_id: int, title: str = "新对话") -> dict[str, Any]:
        """创建新会话，默认标题为"新对话"，后续由后台任务自动生成标题。"""
        session = await self._memory_service.create_session(user_id=user_id, title=title)
        return {"id": session.id, "title": session.title}

    async def archive_session(self, user_id: int, session_id: str) -> bool:
        """归档会话（软删除），不物理删除消息数据。"""
        return await self._memory_service.archive_session(user_id=user_id, session_id=session_id)

    async def update_session_title(self, user_id: int, session_id: str, title: str) -> bool:
        """更新会话标题。"""
        return await self._memory_service.update_session_title(user_id=user_id, session_id=session_id, title=title)

    async def get_history(
        self,
        *,
        user_id: int,
        session_id: str | None = None,
        limit: int = 50,
    ) -> list[ChatMessageItem]:
        """获取会话历史消息，组装为 ChatMessageItem 列表。

        流程：
        1. 若未指定 session_id，自动取用户最近的会话
        2. 查询消息列表和附件分析结果
        3. 按 message_id 分组附件分析
        4. 查询附件绑定关系（新旧两种存储格式兼容）
        5. 组装 ChatMessageItem 返回
        """
        if not session_id:
            sessions = await self._memory_service.list_sessions(user_id=user_id, limit=1)
            if not sessions:
                return []
            session_id = sessions[0].id

        # 查询原始消息列表
        raw_messages = await self._memory_service.list_messages(user_id=user_id, session_id=session_id, limit=limit)
        # 查询附件分析结果（图片描述/文档摘要）
        attachment_analyses = await self._memory_service.list_attachment_analyses(
            user_id=user_id,
            session_id=session_id,
            limit=max(limit, 20),
        )
        tool_invocations = await self._memory_service.list_tool_invocations(
            user_id=user_id,
            session_id=session_id,
            limit=max(limit * 2, 50),
        )
        activities_by_turn: dict[int, list[tuple[int, Any, dict[str, Any]]]] = {}
        for invocation in tool_invocations:
            turn_id = getattr(invocation, "turn_id", None)
            if turn_id is None:
                continue
            activities_by_turn.setdefault(turn_id, []).append(
                (1, getattr(invocation, "created_at", None), build_persisted_tool_activity(invocation))
            )
        # 按 message_id 分组附件分析结果，供后续组装使用
        analyses_by_message_id: dict[int, list[dict[str, Any]]] = {}
        for analysis in attachment_analyses:
            message_id = getattr(analysis, "message_id", None)
            if not message_id:
                continue
            analyses_by_message_id.setdefault(message_id, []).append(
                {
                    "id": getattr(analysis, "id", None),
                    "file_id": getattr(analysis, "file_id", None),
                    "file_name": getattr(analysis, "file_name", None),
                    "file_url": getattr(analysis, "file_url", None),
                    "analysis_type": getattr(analysis, "analysis_type", ""),
                    "summary_text": getattr(analysis, "summary_text", ""),
                    "structured_json": getattr(analysis, "structured_json", None),
                }
            )
            turn_id = getattr(analysis, "turn_id", None)
            if turn_id is not None:
                structured = getattr(analysis, "structured_json", None) or {}
                urls = structured.get("file_urls", []) if isinstance(structured, dict) else []
                file_names = [str(url).split("/")[-1] for url in urls]
                if not file_names and getattr(analysis, "file_name", None):
                    file_names = [str(analysis.file_name)]
                activities_by_turn.setdefault(turn_id, []).append((
                    0,
                    getattr(analysis, "created_at", None),
                    build_attachment_status_payload(
                        activity_id=f"attachment-{turn_id}-{getattr(analysis, 'analysis_type', 'document')}",
                        status="done",
                        file_names=file_names,
                        analysis_type=str(getattr(analysis, "analysis_type", "document")),
                        summary=str(getattr(analysis, "summary_text", "") or ""),
                    ),
                ))
        # 查询附件绑定关系：新版本用 message_attachments 表，旧版本用 message.attachments 字段
        attachment_records_by_message_id = await self._memory_service.list_message_attachments(
            user_id=user_id,
            session_id=session_id,
            message_ids=[item.id for item in raw_messages if getattr(item, "id", None) is not None],
        )
        # 组装 ChatMessageItem 列表
        result: list[ChatMessageItem] = []
        for message in raw_messages:
            parsed_attachments = None
            # 优先使用新版本的附件绑定关系
            bound_attachments = attachment_records_by_message_id.get(message.id, []) if isinstance(attachment_records_by_message_id, dict) else []
            if bound_attachments:
                parsed_attachments = [
                    {"url": item.get("url", ""), "type": item.get("type", ""), "name": item.get("name", "")}
                    for item in bound_attachments
                ]
            elif message.attachments:
                # 兼容旧版本：附件信息直接存储在 message.attachments 字段（JSON 字符串或列表）
                try:
                    raw = message.attachments if isinstance(message.attachments, list) else json.loads(message.attachments)
                    parsed_attachments = [
                        {"url": item.get("url", ""), "type": item.get("type", ""), "name": item.get("name", "")}
                        for item in raw
                    ]
                except Exception:
                    parsed_attachments = None
            # 组装 ChatMessageItem
            result.append(
                ChatMessageItem(
                    id=message.id,
                    role=message.role,
                    content=message.content,
                    attachments=parsed_attachments,
                    tool_calls=message.tool_calls if isinstance(message.tool_calls, list) else None,
                    tool_call_id=getattr(message, "tool_call_id", None),
                    knowledge_sources=message.knowledge_sources if isinstance(message.knowledge_sources, list) else None,
                    attachment_analyses=analyses_by_message_id.get(message.id, []),  # 关联的附件分析结果
                    agent_activities=[
                        activity for _, _, activity in sorted(
                            activities_by_turn.get(getattr(message, "turn_id", None), []),
                            key=lambda item: (item[0], item[1].isoformat() if item[1] is not None else ""),
                        )
                    ] if getattr(message, "message_kind", None) == "assistant_answer" else None,
                    teaching_diagram=message.teaching_diagram if isinstance(message.teaching_diagram, dict) else None,
                    turn_id=getattr(message, "turn_id", None),
                    message_kind=getattr(message, "message_kind", None),
                    created_at=message.created_at,
                )
            )
        return result

    async def save_message(
        self,
        *,
        user_id: int,
        session_id: str,
        role: str,
        content: str,
        attachments: list[dict[str, Any]] | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        tool_call_id: str | None = None,
        knowledge_sources: list[dict[str, Any]] | None = None,
        attachment_analyses: list[dict[str, Any]] | None = None,
        teaching_diagram: dict[str, Any] | None = None,
        usage_metadata: dict[str, Any] | None = None,
        turn_id: int | None = None,
        message_kind: str | None = None,
    ) -> Any:
        """保存单条消息到数据库。

        由 chat() 在流式结束后调用，持久化用户消息和助手回复。
        turn_id 将消息关联到具体的对话轮次，便于后续记忆管线处理。
        """
        return await self._memory_service.save_message(
            user_id=user_id,
            session_id=session_id,
            role=role,
            content=content,
            attachments=attachments,
            tool_calls=tool_calls,
            tool_call_id=tool_call_id,
            knowledge_sources=knowledge_sources,
            attachment_analyses=attachment_analyses,
            teaching_diagram=teaching_diagram,
            usage_metadata=usage_metadata,
            turn_id=turn_id,
            message_kind=message_kind,
        )

    async def count_messages(self, user_id: int, session_id: str) -> int:
        """统计会话中的消息总数。"""
        return await self._memory_service.count_messages(user_id=user_id, session_id=session_id)

    async def clear_history(self, user_id: int, session_id: str) -> int:
        """清空会话历史：删除短期消息并重置计数器。

        返回删除的消息数量。注意：只删除短期消息，长期记忆保留。
        """
        deleted_count = await self._memory_service.delete_short_term_messages(user_id=user_id, session_id=session_id)
        await self._memory_service.reset_session_counters(user_id=user_id, session_id=session_id)
        return deleted_count

    async def save_upload(
        self,
        *,
        filename: str,
        content: bytes,
        user_id: int,
        session_id: str,
    ) -> dict[str, Any]:
        """保存用户上传的文件：磁盘存储 + 数据库记录。

        流程：
        1. 校验文件名非空
        2. 检查单次上传文件数是否超限
        3. 调用 LocalFileStore 写入磁盘
        4. 在数据库中保存文件记录
        5. 维护 URL→数据库 ID 映射，供附件分析器引用
        """
        if not filename:
            raise ValueError("文件名不能为空")
        # 检查文件数上限
        existing = self.file_store.list_files(user_id=user_id, session_id=session_id)
        if len(existing) >= MAX_UPLOAD_FILES_PER_REQUEST:
            raise ValueError(f"单次上传最多 {MAX_UPLOAD_FILES_PER_REQUEST} 个文件")
        # 写入磁盘
        payload = await self.file_store.save_upload(
            filename=filename,
            content=content,
            user_id=user_id,
            session_id=session_id,
        )
        # 保存文件记录到数据库，返回带 ID 的记录
        file_record = await self._memory_service.save_uploaded_file(user_id=user_id, session_id=session_id, payload=payload)
        # 维护 URL→文件 ID 映射，附件分析器需要用这个 ID 引用文件
        self._uploaded_file_ids_by_url[str(payload.get("url") or "")] = file_record.id
        return payload

    def resolve_uploaded_file(
        self,
        *,
        current_user_id: int,
        owner_id: int,
        session_id: str,
        filename: str,
    ) -> Path:
        """解析上传文件路径，带权限校验。

        只有文件所有者才能访问，防止越权读取。
        实际路径解析委托给 LocalFileStore.resolve_user_file。
        """
        if current_user_id != owner_id:
            raise PermissionError("无权访问此文件")
        return self.file_store.resolve_user_file(
            current_user_id=current_user_id,
            owner_id=owner_id,
            session_id=session_id,
            filename=filename,
        )

    def _spawn_background(self, coro, *, label: str = "") -> None:
        """安全地启动后台协程任务。

        关键设计：
        1. 任务加入 _background_tasks 集合，防止被 GC 回收
        2. 完成回调自动从集合移除，避免内存泄漏
        3. 异常被 catch 并记录日志，不会影响主流程
        4. 若当前不在事件循环中（极端情况），记录警告而非崩溃
        """
        async def _run() -> None:
            try:
                await coro
            except Exception as exc:
                logger.error("[ChatUseCases] 后台任务失败 label=%s err=%s", label, exc)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            # 确保任务被引用，不会被垃圾回收
            task = asyncio.ensure_future(_run())
            self._background_tasks.add(task)
            # 完成后自动从集合移除
            task.add_done_callback(self._background_tasks.discard)
        else:
            logger.warning("[ChatUseCases] 无法在非事件循环中启动后台任务 label=%s", label)


# ── 单例管理 ──
# 两个独立单例：主对话和数字人对话，避免共享状态（如 _uploaded_file_ids_by_url）
_chat_usecases: ChatUseCases | None = None
_avatar_chat_usecases: ChatUseCases | None = None


def get_chat_usecases() -> ChatUseCases:
    """获取主对话的 ChatUseCases 单例。

    懒加载模式：首次调用时创建实例，后续复用。
    """
    global _chat_usecases
    if _chat_usecases is None:
        _chat_usecases = ChatUseCases()
    return _chat_usecases


def get_chat_memory_service():
    """获取记忆服务实例，委托给 memory 模块的工厂函数。"""
    return _get_chat_memory_service()


def get_avatar_chat_usecases() -> ChatUseCases:
    """获取数字人对话的 ChatUseCases 单例。

    与主对话单例独立，避免上传文件映射等状态互相干扰。
    """
    global _avatar_chat_usecases
    if _avatar_chat_usecases is None:
        _avatar_chat_usecases = ChatUseCases()
    return _avatar_chat_usecases
