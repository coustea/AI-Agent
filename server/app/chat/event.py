"""Chat 模块独立实时事件流。

提供 Chat 专属的事件类型、内存频道、订阅管理和 SSE 编码。
与 Resource、Path 模块完全隔离，不共享任何实现。
"""

from __future__ import annotations

import asyncio
import time
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
        self._cleanup_task: asyncio.Task | None = None

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
        self._subscribers = [q for q in self._subscribers if q is not queue]

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