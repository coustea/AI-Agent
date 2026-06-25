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
    "run.started",
    "thinking",
    "tool.running",
    "tool.completed",
    "tool.failed",
    "attachment.running",
    "attachment.completed",
    "attachment.failed",
    "content.delta",
    "content.replace",
    "diagram.ready",
    "run.completed",
    "run.failed",
]

CHAT_TERMINAL_EVENTS: set[ChatEventName] = {"run.completed", "run.failed"}


class ChatEvent(BaseModel):
    """Chat 模块的 SSE 数据结构。"""

    sequence: int = 0
    run_id: str
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

ChannelKey = tuple[int, str, str]  # (user_id, session_id, run_id)


# ===================== 模块私有注册表 =====================

_chat_channels: dict[ChannelKey, "_ChatChannel"] = {}
_chat_lock = asyncio.Lock()


class _ChatChannel:
    """单个 Chat run 的内存频道。"""

    def __init__(
        self,
        *,
        user_id: int,
        session_id: str,
        run_id: str,
        queue_size: int = 256,
        replay_size: int = 256,
        terminal_retention_seconds: float = 1800.0,
    ) -> None:
        self.user_id = user_id
        self.session_id = session_id
        self.run_id = run_id
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
                f"Chat channel closed for run_id={self.run_id}"
            )
        self._sequence += 1
        chat_event = ChatEvent(
            sequence=self._sequence,
            run_id=self.run_id,
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
                    "chat_event_queue_oldest_dropped: run_id=%s",
                    self.run_id,
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
        key = (self.user_id, self.session_id, self.run_id)
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
        run_id: str,
        queue_size: int = 256,
        replay_size: int = 256,
        terminal_retention_seconds: float = 1800.0,
    ) -> None:
        self._user_id = user_id
        self._session_id = session_id
        self._run_id = run_id
        self._queue_size = queue_size
        self._replay_size = replay_size
        self._terminal_retention_seconds = terminal_retention_seconds
        self._channel: _ChatChannel | None = None
        self._key: ChannelKey = (user_id, session_id, run_id)

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
                    run_id=self._run_id,
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
                f"Chat channel not opened for run_id={self._run_id}"
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
                f"Chat channel not found for run_id={self._run_id}"
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
    def run_id(self) -> str:
        return self._run_id

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
    user_id: int, session_id: str, run_id: str
) -> ChatEvents | None:
    """获取已存在的 Chat 频道。"""
    key = (user_id, session_id, run_id)
    async with _chat_lock:
        channel = _chat_channels.get(key)
        if channel is None:
            return None
        events = ChatEvents(
            user_id=user_id,
            session_id=session_id,
            run_id=run_id,
        )
        events._channel = channel
        return events


# ===================== 运行时事件映射 =====================

SSE_EVENT_MAP: dict[str, str] = {
    "message_start": "start",
    "classify_done": "status",
    "file_analysis_start": "status",
    "file_analysis_done": "attachment",
    "agent_status": "agent_status",
    "attachment_status": "attachment_status",
    "answer_token": "token",
    "answer_done": "status",
    "content_replace": "content_replace",
    "diagram_start": "status",
    "diagram_done": "diagram",
    "memory_update_start": "status",
    "memory_update_done": "status",
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
            status = runtime_status(payload.get("status"))
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

        if event_name == "attachment_status":
            status = runtime_status(payload.get("status"))
            if status == "running":
                chat_event = "attachment.running"
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
                data={k: v for k, v in payload.items() if k != "message"},
            )

        return False

    async def publish_many(
        self,
        events: ChatEvents,
        runtime_events: list[dict[str, Any]],
    ) -> bool:
        failed = False
        for event in runtime_events:
            if await self.publish(events, event):
                failed = True
        return failed


# ===================== 工具状态构建 =====================

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
    "duckduckgo_search": ("query",),
    "duckduckgo_instant_answer": ("query",),
    "tavily_search": ("query",),
    "spark_search": ("query",),
    "open_web_page": ("url",),
    "find_in_web_page": ("pattern", "page_id"),
    "extract_web_links": ("page_id",),
    "read_web_pdf": ("url",),
}

# 工具动作描述：工具名 -> "正在{动作}" 格式
_TOOL_ACTIONS: dict[str, str] = {
    "get_learner_profile": "正在了解你的学习情况",
    "get_long_term_memory": "正在回顾学习记录",
    "search_knowledge_base": "正在检索课程知识库",
    "duckduckgo_search": "正在搜索相关资料",
    "duckduckgo_instant_answer": "正在查询即时答案",
    "tavily_search": "正在搜索相关资料",
    "spark_search": "正在搜索相关资料",
    "open_web_page": "正在阅读网页",
    "find_in_web_page": "正在网页中查找内容",
    "extract_web_links": "正在提取网页链接",
    "read_web_pdf": "正在阅读 PDF",
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


