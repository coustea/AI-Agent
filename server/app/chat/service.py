"""聊天服务层 — 对话流编排、记忆管理、文件上传。

核心函数：
  build_messages()  — 从数据库构建 LangChain 消息列表（含工具调用链）
  chat()            — 总编排：build_messages → TutorAgent.chat() → 转发 SSE 事件 → 持久化

ChatUseCases 保留会话管理、文件上传等辅助功能，对话核心逻辑委托给 TutorAgent。
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage, ToolMessage

from app.chat.agent import TutorAgent
from app.chat.event import ChatEvents, ChatEventName
from app.chat.events import build_attachment_status_payload, build_persisted_tool_activity_from_message
from app.chat.memory.service import get_chat_memory_service as _get_chat_memory_service
from app.chat.safety import SafetyResult, safety_filter
from app.chat.schemas import TutorAgentInput
from app.chat.storage.file_store import LocalFileStore
from app.chat.storage.message_item import ChatMessageItem
from app.config import CHAT_DIR, MAX_UPLOAD_FILES_PER_REQUEST, CHAT_HISTORY_LIMIT
from app.infra.logging import get_logger

logger = get_logger(__name__)


# -----------------------------------------------------------------------
# 核心函数：build_messages / chat helpers / chat
# -----------------------------------------------------------------------


IMAGE_EXTENSIONS = frozenset(["jpg", "jpeg", "png", "gif", "webp", "bmp"])


def _build_user_content(text: str, attachments: list[str]) -> list[dict[str, Any]]:
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
    """执行一次辅导对话，流式返回 SSE 事件。

    简化流程（不再创建 turn）：
    1. 保存用户消息
    2. 构建上下文
    3. 调用 TutorAgent
    4. 保存助手回复
    5. 后台记忆任务
    """
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

    # ── 1. 持久化用户消息 ──
    svc = uc._memory_service
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

    await uc.save_message(
        user_id=user_id,
        session_id=effective_session,
        role="user",
        content=user_content,
    )

    # 如果是第一条消息，后台生成标题
    if await uc.count_messages(user_id, effective_session) <= 1:
        uc._spawn_background(
            svc.generate_session_title(
                user_id=user_id,
                session_id=effective_session,
                first_message=current_message,
            ),
            label="generate_title",
        )

    # ── 2. 构建上下文 ──
    history_messages = await build_messages(user_id, effective_session)
    session_summary = await svc.get_session_summary_context(user_id=user_id, session_id=effective_session)

    # ── 3. 调用 TutorAgent ──
    agent_input = TutorAgentInput(
        user_id=user_id,
        session_id=effective_session,
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
                        "message": "回答已生成，正在保存...",
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
        yield {"event": "error", "data": f"服务器出错: {exc}"}
        yield {"event": "done", "data": {"session_id": effective_session, "error": True}}
        return

    # ── 4. 持久化助手回复 ──
    if not has_error and full_answer:
        # 安全过滤
        safety_result = await safety_filter.check(full_answer)
        if safety_result.has_violation:
            full_answer = safety_result.sanitized_text

        await uc.save_message(
            user_id=user_id,
            session_id=effective_session,
            role="assistant",
            content=full_answer,
            attachment_analyses=attachment_analyses if attachment_analyses else None,
        )

    # ── 5. 返回最终结果 ──
    if not has_error:
        yield {
            "event": "done",
            "data": {
                "session_id": effective_session,
                "full_response": full_answer,
                "tool_calls": [
                    {"id": inv.get("tool_name", ""), "name": inv.get("tool_name", ""), "args": inv.get("payload", {})}
                    for inv in tool_invocations
                ],
                "attachment_analyses": attachment_analyses,
            },
        }

    # ── 6. 后台记忆任务 ──
    if full_answer:
        uc._spawn_background(
            agent.run_background_memory_jobs(
                user_id=user_id,
                session_id=effective_session,
                user_message=current_message,
                assistant_reply=full_answer,
            ),
            label="post_turn",
        )


def _runtime_status(value: Any) -> str:
    status = str(value or "running")
    return {
        "done": "completed",
        "finished": "completed",
        "error": "failed",
    }.get(status, status if status in {"pending", "running", "completed", "failed", "skipped"} else "running")


async def _publish_chat_runtime_event(
    events: ChatEvents,
    event: dict[str, Any],
) -> bool:
    """把辅导内部事件映射成 ChatEvent 并发送；返回是否失败。"""
    event_name = str(event.get("event") or "status")
    data = event.get("data")
    payload = data if isinstance(data, dict) else {}

    if event_name == "token":
        await events.send(event="content.delta", message="", data={"delta": str(data or "")})
        return False
    if event_name == "agent_status":
        status = _runtime_status(payload.get("status"))
        # 映射到 tool.running/tool.completed/tool.failed
        if status == "running":
            chat_event: ChatEventName = "tool.running"
        elif status == "failed":
            chat_event = "tool.failed"
        else:
            chat_event = "tool.completed"
        await events.send(
            event=chat_event,
            message=str(payload.get("message") or payload.get("title") or ""),
            data={
                "activity_id": payload.get("activity_id"),
                "tool_name": payload.get("tool_name"),
                "detail": payload.get("detail"),
            },
        )
        return False
    if event_name == "attachment":
        status = _runtime_status(payload.get("status"))
        if status == "running":
            chat_event: ChatEventName = "attachment.running"
        elif status == "failed":
            chat_event = "attachment.failed"
        else:
            chat_event = "attachment.completed"
        await events.send(
            event=chat_event,
            message=str(payload.get("message") or payload.get("title") or ""),
            data={
                "activity_id": payload.get("activity_id"),
                "detail": payload.get("detail"),
            },
        )
        return False
    if event_name == "diagram" and payload:
        await events.send(
            event="diagram.ready",
            message="教学图解已生成",
            data=payload,
        )
        return False
    if event_name == "error":
        return True
    if event_name == "status":
        await events.send(
            event="thinking",
            message=str(payload.get("message") or "正在处理"),
            data={key: value for key, value in payload.items() if key != "message"},
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
    """后台执行一次辅导，并通过 ChatEvents 推送运行状态。

    频道已在 router 中通过 ChatEvents.open() 注册。
    """
    events = ChatEvents(user_id=user_id, session_id=session_id, run_id=run_id)
    # 频道已由 router 打开，直接获取
    await events.send(event="run.started", message="智能辅导已开始", data={})
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
            failed = await _publish_chat_runtime_event(events, event) or failed
        if failed:
            await events.send(event="run.failed", message="回答失败", data={"error": "智能辅导暂时无法完成本次回答"})
        else:
            await events.send(event="run.completed", message="回答完成", data={})
    except Exception as e:
        logger.exception("chat_agent_run_failed: run_id=%s", run_id)
        await events.send(event="run.failed", message="回答失败", data={"error": str(e)})





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
        # 从消息表中提取工具调用记录（替代 ChatToolInvocation 表查询）
        # 按 turn_id 分组工具调用活动，同时获取工具执行结果
        activities_by_turn: dict[int, list[tuple[int, Any, dict[str, Any]]]] = {}

        # 先构建 tool_call_id -> result 的映射（从 tool 角色消息获取结果）
        tool_results: dict[str, str] = {}
        for msg in raw_messages:
            if getattr(msg, "role", "") == "tool":
                tc_id = getattr(msg, "tool_call_id", None)
                content = getattr(msg, "content", "") or ""
                if tc_id and content:
                    tool_results[str(tc_id)] = content

        # 从 assistant 消息的 tool_calls 字段构建活动
        for msg in raw_messages:
            turn_id = getattr(msg, "turn_id", None)
            if turn_id is None:
                continue
            tool_calls = getattr(msg, "tool_calls", None)
            if not tool_calls or not isinstance(tool_calls, list):
                continue
            for tc in tool_calls:
                if not isinstance(tc, dict):
                    continue
                tc_id = str(tc.get("id", "") or "")
                # 获取对应的工具执行结果
                result = tool_results.get(tc_id, "")
                activities_by_turn.setdefault(turn_id, []).append(
                    (1, getattr(msg, "created_at", None), build_persisted_tool_activity_from_message(tc, result))
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
                    attachment_analyses=analyses_by_message_id.get(message.id, []),
                    agent_activities=[
                        activity for _, _, activity in sorted(
                            activities_by_turn.get(getattr(message, "turn_id", None), []),
                            key=lambda item: (item[0], item[1].isoformat() if item[1] is not None else ""),
                        )
                    ] if message.role == "assistant" else None,
                    turn_id=getattr(message, "turn_id", None),
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
        tool_calls: list[dict[str, Any]] | None = None,
        tool_call_id: str | None = None,
        attachment_analyses: list[dict[str, Any]] | None = None,
        usage_metadata: dict[str, Any] | None = None,
        turn_id: int | None = None,
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
            tool_calls=tool_calls,
            tool_call_id=tool_call_id,
            attachment_analyses=attachment_analyses,
            usage_metadata=usage_metadata,
            turn_id=turn_id,
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
