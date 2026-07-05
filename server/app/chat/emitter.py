"""Chat 模块独立实时事件流。

提供 Chat 专属的事件类型、内存频道、订阅管理和 SSE 编码。
与 Resource、Path 模块完全隔离，不共享任何实现。
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Mapping
from collections import deque
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.infra.logging import get_logger

logger = get_logger(__name__)

# ===================== 事件类型定义 =====================

ChatEventName = Literal[
    "message.started",
    "activity.running",
    "activity.completed",
    "activity.failed",
    "content.delta",
    "content.replace",
    "diagram.ready",
    "message.completed",
    "message.failed",
]

CHAT_TERMINAL_EVENTS: set[ChatEventName] = {"message.completed", "message.failed"}


class ChatEvent(BaseModel):
    """Chat 模块的 SSE 数据结构。"""

    sequence: int = 0
    user_message_id: int
    session_id: str
    event: ChatEventName
    message: str
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


# ===================== 异常定义 =====================


class ChatEventNotOpenError(RuntimeError):
    """在 open() 之前调用 send() 时抛出。"""

    pass


class ChatEventClosedError(RuntimeError):
    """终态事件后继续发送消息时抛出。"""

    pass


# ===================== 频道键 =====================

ChannelKey = tuple[int, str, int]  # (user_id, session_id, user_message_id)


# ===================== 模块私有注册表 =====================

_chat_channels: dict[ChannelKey, "_ChatChannel"] = {}
_chat_lock = asyncio.Lock()


class _ChatChannel:
    """单条 UserMessage 的内存事件频道。"""

    def __init__(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message_id: int,
        queue_size: int = 256,
        replay_size: int = 256,
        terminal_retention_seconds: float = 1800.0,
    ) -> None:
        self.user_id = user_id
        self.session_id = session_id
        self.user_message_id = user_message_id
        self.queue_size = queue_size
        self.replay_size = replay_size
        self.terminal_retention_seconds = terminal_retention_seconds
        self._buffer: deque[ChatEvent] = deque(maxlen=replay_size)
        self._subscribers: list[asyncio.Queue[ChatEvent]] = []
        self._sequence = 0
        self._is_terminal = False
        self._cleanup_task: asyncio.TimerHandle | None = None

    async def send(
        self, event: ChatEventName, message: str, data: dict[str, Any] | None
    ) -> ChatEvent:
        if self._is_terminal:
            raise ChatEventClosedError(
                f"Chat channel closed for user_message_id={self.user_message_id}"
            )
        self._sequence += 1
        chat_event = ChatEvent(
            sequence=self._sequence,
            user_message_id=self.user_message_id,
            session_id=self.session_id,
            event=event,
            message=message,
            data=data or {},
        )
        self._buffer.append(chat_event)

        # 广播给所有订阅者
        for queue in list(self._subscribers):
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                logger.warning(
                    "chat_event_queue_oldest_dropped: user_message_id=%s",
                    self.user_message_id,
                )
            queue.put_nowait(chat_event)

        # 终态处理
        if event in CHAT_TERMINAL_EVENTS:
            self._is_terminal = True
            self._cleanup_task = asyncio.get_running_loop().call_later(
                self.terminal_retention_seconds,
                lambda: asyncio.create_task(self._cleanup()),
            )

        return chat_event

    async def subscribe(
        self, after_sequence: int
    ) -> tuple[asyncio.Queue[ChatEvent], list[ChatEvent]]:
        queue: asyncio.Queue[ChatEvent] = asyncio.Queue(maxsize=self.queue_size)
        self._subscribers.append(queue)
        replay = [e for e in self._buffer if e.sequence > after_sequence]
        return queue, replay

    async def unsubscribe(self, queue: asyncio.Queue[ChatEvent]) -> None:
        """取消订阅，终态且无订阅者时清理频道。"""
        self._subscribers = [q for q in self._subscribers if q is not queue]
        if self._is_terminal and not self._subscribers:
            await self._cleanup()

    async def _cleanup(self) -> None:
        """终态保留期结束后清理频道。"""
        if self._subscribers:
            # 还有订阅者，不清理
            return
        key = (self.user_id, self.session_id, self.user_message_id)
        async with _chat_lock:
            _chat_channels.pop(key, None)


# ===================== 公开 API =====================


class ChatEvents:
    """Chat 模块的实时事件流管理器。

    业务代码创建实例后调用 open() 注册频道，
    然后通过 send() 发布事件，前端通过 SSE 订阅。
    """

    def __init__(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message_id: int,
        queue_size: int = 256,
        replay_size: int = 256,
        terminal_retention_seconds: float = 1800.0,
    ) -> None:
        self._user_id = user_id
        self._session_id = session_id
        self._user_message_id = user_message_id
        self._queue_size = queue_size
        self._replay_size = replay_size
        self._terminal_retention_seconds = terminal_retention_seconds
        self._channel: _ChatChannel | None = None
        self._key: ChannelKey = (user_id, session_id, user_message_id)

    async def open(self) -> None:
        """注册频道，必须在调度后台任务之前调用。"""
        async with _chat_lock:
            if self._key in _chat_channels:
                # 频道已存在，可能是重连场景
                self._channel = _chat_channels[self._key]
            else:
                self._channel = _ChatChannel(
                    user_id=self._user_id,
                    session_id=self._session_id,
                    user_message_id=self._user_message_id,
                    queue_size=self._queue_size,
                    replay_size=self._replay_size,
                    terminal_retention_seconds=self._terminal_retention_seconds,
                )
                _chat_channels[self._key] = self._channel

    async def send(
        self,
        *,
        event: ChatEventName,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> ChatEvent:
        """发送事件到频道。

        Raises:
            ChatEventNotOpenError: 未调用 open()
            ChatEventClosedError: 终态后继续发送
        """
        if self._channel is None:
            raise ChatEventNotOpenError(
                f"Chat channel not opened for user_message_id={self._user_message_id}"
            )
        return await self._channel.send(event, message, data)

    async def subscribe(
        self, after_sequence: int = 0
    ) -> tuple[asyncio.Queue[ChatEvent], list[ChatEvent]]:
        """订阅频道，返回队列和回放事件列表。"""
        if self._channel is None:
            async with _chat_lock:
                self._channel = _chat_channels.get(self._key)
        if self._channel is None:
            raise ChatEventNotOpenError(
                f"Chat channel not found for user_message_id={self._user_message_id}"
            )
        return await self._channel.subscribe(after_sequence)

    async def unsubscribe(self, queue: asyncio.Queue[ChatEvent]) -> None:
        """取消订阅。"""
        if self._channel is None:
            return
        await self._channel.unsubscribe(queue)

    async def close(self) -> None:
        """手动关闭频道（通常由终态事件自动触发）。"""
        if self._channel is None:
            return
        self._channel._is_terminal = True
        await self._channel._cleanup()

    @property
    def user_message_id(self) -> int:
        return self._user_message_id

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def is_terminal(self) -> bool:
        return self._channel is not None and self._channel._is_terminal


# ===================== SSE 编码 =====================


def encode_chat_sse(event: ChatEvent) -> str:
    """将 ChatEvent 编码为 SSE 格式。

    输出格式：
    id: <sequence>
    event: chat.event
    data: <ChatEvent JSON>

    """
    return f"id: {event.sequence}\nevent: chat.event\ndata: {event.model_dump_json()}\n\n"


# ===================== 辅助函数 =====================


async def get_chat_channel(
    user_id: int, session_id: str, user_message_id: int
) -> ChatEvents | None:
    """获取已存在的 Chat 频道。"""
    key = (user_id, session_id, user_message_id)
    async with _chat_lock:
        channel = _chat_channels.get(key)
        if channel is None:
            return None
        events = ChatEvents(
            user_id=user_id,
            session_id=session_id,
            user_message_id=user_message_id,
        )
        events._channel = channel
        return events


async def has_active_chat_channel(user_id: int, session_id: str) -> bool:
    """同一会话只允许处理一条用户消息。"""
    async with _chat_lock:
        return any(
            key_user_id == user_id
            and key_session_id == session_id
            and not channel._is_terminal
            for (key_user_id, key_session_id, _), channel in _chat_channels.items()
        )


# ===================== 运行时事件映射（简化后）=====================

SSE_EVENT_MAP: dict[str, str] = {
    "message_start": "start",
    "agent_status": "agent_status",
    "answer_token": "token",
    "answer_done": "status",
    "content_replace": "content_replace",
    "diagram": "diagram",
    "final": "done",
    "error": "error",
}


def runtime_status(value: Any) -> str:
    status = str(value or "running")
    return {
        "done": "completed",
        "finished": "completed",
        "error": "failed",
    }.get(status, status if status in {"pending", "running", "completed", "failed", "skipped"} else "running")


class ChatRuntimeEventMapper:
    """统一转换器：内部字典事件 → ChatEvent → SSE。"""

    def _activity_event_name(self, status: Any) -> ChatEventName:
        normalized = runtime_status(status)
        if normalized == "failed":
            return "activity.failed"
        if normalized in {"completed", "skipped"}:
            return "activity.completed"
        return "activity.running"

    def _activity_data(self, payload: Mapping[str, Any], *, kind: str) -> dict[str, Any]:
        stage = str(payload.get("stage") or "").strip()
        title = str(payload.get("title") or payload.get("message") or "").strip()
        message = str(payload.get("message") or title).strip()
        activity_id = str(payload.get("activity_id") or "").strip()
        if not activity_id:
            activity_id = f"{kind}:{stage or title or 'running'}"
        return {
            "activity_id": activity_id,
            "kind": payload.get("kind") or kind,
            "stage": stage,
            "status": payload.get("status") or "running",
            "tool_name": payload.get("tool_name"),
            "title": title or "正在处理",
            "summary": payload.get("summary") or "",
            "message": message or title or "正在处理",
            "detail": payload.get("detail") if isinstance(payload.get("detail"), Mapping) else {},
        }

    async def publish(
        self,
        events: ChatEvents,
        event: dict[str, Any],
    ) -> bool:
        """发布事件，返回是否失败。"""
        event_name = str(event.get("event") or "status")
        data = event.get("data")
        payload = data if isinstance(data, dict) else {}

        if event_name == "token":
            await events.send(event="content.delta", message="", data={"delta": str(data or "")})
            return False

        if event_name == "content_replace":
            await events.send(
                event="content.replace",
                message="",
                data={"content": payload.get("content", ""), "delta": ""},
            )
            return False

        if event_name == "agent_status":
            # agent_status 包含所有工具调用状态（包括附件分析）
            kind = payload.get("kind", "tool")
            activity = self._activity_data(payload, kind=kind)
            await events.send(
                event=self._activity_event_name(payload.get("status")),
                message=activity["message"],
                data=activity,
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
            if str(payload.get("stage") or "") == "answer_done":
                return False
            activity = build_workflow_activity_payload(
                stage=str(payload.get("stage") or "processing"),
                title=str(payload.get("title") or payload.get("message") or "正在处理"),
                message=str(payload.get("message") or payload.get("title") or "正在处理"),
                summary=str(payload.get("summary") or ""),
                status=str(payload.get("status") or "running"),
            )
            await events.send(
                event=self._activity_event_name(activity["status"]),
                message=activity["message"],
                data=activity,
            )

        return False


# ===================== 工具状态构建 =====================

def build_workflow_activity_payload(
    *,
    stage: str,
    title: str,
    message: str | None = None,
    summary: str = "",
    status: str = "running",
    activity_id: str | None = None,
) -> dict[str, Any]:
    """构建回答前流程状态，前端只展示后端发送的真实步骤。"""
    safe_stage = str(stage or "processing").strip()
    safe_title = str(title or "正在处理").strip()
    safe_message = str(message or safe_title).strip()
    return {
        "activity_id": activity_id or f"workflow:{safe_stage}",
        "kind": "workflow",
        "stage": safe_stage,
        "status": status,
        "title": safe_title,
        "summary": _preview(summary, limit=120),
        "message": safe_message,
        "detail": {},
    }

def _preview(value: Any, *, limit: int = 50) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _result_preview(value: Any, *, limit: int = 500) -> str:
    if isinstance(value, Mapping):
        value = value.get("text") or value.get("message") or value
    return _preview(value, limit=limit)


# 工具参数提取配置：工具名 -> 要显示的参数键列表
_TOOL_CONTEXT_KEYS: dict[str, tuple[str, ...]] = {
    "get_learner_profile": ("dimension", "course_name"),
    "get_long_term_memory": ("category",),
    "search_knowledge_base": ("query", "course_name"),
    "research": ("query", "objective"),
}

# 工具动作描述：工具名 -> "正在{动作}" 格式
_TOOL_ACTIONS: dict[str, str] = {
    "get_learner_profile": "正在了解你的学习情况",
    "get_long_term_memory": "正在回顾学习记录",
    "search_knowledge_base": "正在检索课程知识库",
    "research": "正在研究资料",
}

def _tool_context(tool_name: str, arguments: Mapping[str, Any]) -> str:
    """从工具参数中提取关键信息用于展示。"""
    for key in _TOOL_CONTEXT_KEYS.get(tool_name, ()):
        value = _preview(arguments.get(key))
        if value:
            return f"「{value}」"
    return ""


def build_agent_status_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """构建单条、无敏感参数的前端工具状态。"""
    status = str(event.get("status") or "running")
    tool_name = str(event.get("tool_name") or "").strip()
    raw_arguments = event.get("arguments")
    arguments = raw_arguments if isinstance(raw_arguments, Mapping) else {}
    context = _tool_context(tool_name, arguments)
    output = _result_preview(event.get("result"))
    error = _preview(event.get("error"), limit=200)
    action = _TOOL_ACTIONS.get(tool_name, "正在调用工具")
    title = action.removeprefix("正在")

    if status == "done":
        message = f"{title}已完成"
    elif status == "failed":
        message = f"{title}未完成"
    else:
        message = f"{action}{context}..."

    return {
        "activity_id": str(event.get("activity_id") or "").strip(),
        "kind": "tool",
        "stage": "tool_running",
        "status": status,
        "tool_name": tool_name,
        "title": title,
        "summary": context.strip("「」"),
        "message": message,
        "detail": {
            "tool_name": tool_name,
            "input": context.strip("「」"),
            "output": output,
            "error": error,
            "duration_ms": event.get("duration_ms"),
        },
    }


def build_research_status_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """把共享 ResearchAgent 的内部动作转换为 Chat 活动事件。"""
    status = str(event.get("status") or "running")
    tool_name = str(event.get("tool_name") or "").strip()
    raw_arguments = event.get("arguments")
    arguments = raw_arguments if isinstance(raw_arguments, Mapping) else {}
    query = _preview(arguments.get("query"), limit=80)
    action = str(event.get("action") or "核验研究资料").strip()
    error = _preview(event.get("error"), limit=200)

    if status == "done":
        message = f"{action}已完成"
    elif status == "failed":
        message = f"{action}未完成"
    else:
        message = f"正在{action}{f'「{query}」' if query else ''}..."

    return {
        "activity_id": f"research:{event.get('activity_id') or tool_name}",
        "kind": "agent",
        "stage": "research",
        "status": status,
        "tool_name": tool_name,
        "title": action,
        "summary": query,
        "message": message,
        "detail": {
            "agent": "research",
            "action": action,
            "error": error,
            "duration_ms": event.get("duration_ms"),
        },
    }


def build_attachment_status_payload(
    *,
    activity_id: str,
    status: str,
    file_names: list[str],
    analysis_type: str,
    summary: str = "",
    error: str = "",
) -> dict[str, Any]:
    """构建附件分析活动，供实时事件和历史记录复用。"""
    label = "图片分析" if analysis_type == "image" else "文档分析"
    names = "、".join(name for name in file_names if name) or "附件"
    if status == "running":
        message = f"正在进行{label}：{_preview(names)}..."
    elif status == "failed":
        message = f"{label}未完成"
    else:
        message = f"{label}已完成"
    return {
        "activity_id": activity_id,
        "kind": "attachment",
        "stage": "attachment_analysis",
        "status": status,
        "title": label,
        "summary": _preview(names),
        "message": message,
        "detail": {
            "analysis_type": analysis_type,
            "files": file_names,
            "output": _preview(summary, limit=1000),
            "error": _preview(error, limit=200),
            "duration_ms": None,
        },
    }
