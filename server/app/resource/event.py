"""Resource 模块独立实时事件流。

提供 Resource 专属的事件类型、内存频道、订阅管理和 SSE 编码。
与 Chat、Path 模块完全隔离，不共享任何实现。

设计原则：
- ResourceEvents 是无状态代理，通过 channel key 获取/创建频道
- 频道在首次 send/subscribe 时自动创建，无需显式 open()
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

ResourceEventName = Literal[
    "generation.started",
    "generation.completed",
    "generation.failed",
    "agent.pending",
    "agent.running",
    "agent.completed",
    "agent.failed",
]

RESOURCE_TERMINAL_EVENTS: set[ResourceEventName] = {"generation.completed", "generation.failed"}


class ResourceEvent(BaseModel):
    """Resource 模块的 SSE 数据结构。"""

    sequence: int = 0
    run_id: str
    resource_id: int
    event: ResourceEventName
    agent_id: str | None = None
    message: str
    progress: int | None = Field(default=None, ge=0, le=100)
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


# ===================== 异常定义 =====================


class ResourceEventClosedError(RuntimeError):
    """终态事件后继续发送消息时抛出。"""

    pass


class ResourceEventExpiredError(RuntimeError):
    """频道已过期或不存在时抛出。"""

    pass


# ===================== 频道键 =====================

ChannelKey = tuple[int, int, str]  # (user_id, resource_id, run_id)


# ===================== 模块私有注册表 =====================

_resource_channels: dict[ChannelKey, "_ResourceChannel"] = {}
_resource_lock = asyncio.Lock()


class _ResourceChannel:
    """单个 Resource run 的内存频道。"""

    def __init__(
        self,
        *,
        user_id: int,
        resource_id: int,
        run_id: str,
        queue_size: int = 256,
        replay_size: int = 256,
        terminal_retention_seconds: float = 1800.0,
    ) -> None:
        self.user_id = user_id
        self.resource_id = resource_id
        self.run_id = run_id
        self.queue_size = queue_size
        self.replay_size = replay_size
        self.terminal_retention_seconds = terminal_retention_seconds
        self._buffer: deque[ResourceEvent] = deque(maxlen=replay_size)
        self._subscribers: list[asyncio.Queue[ResourceEvent]] = []
        self._sequence = 0
        self._is_terminal = False

    async def send(
        self,
        event: ResourceEventName,
        message: str,
        data: dict[str, Any] | None,
        agent_id: str | None = None,
        progress: int | None = None,
    ) -> ResourceEvent:
        if self._is_terminal:
            raise ResourceEventClosedError(
                f"Resource channel closed for run_id={self.run_id}"
            )
        self._sequence += 1
        resource_event = ResourceEvent(
            sequence=self._sequence,
            run_id=self.run_id,
            resource_id=self.resource_id,
            event=event,
            agent_id=agent_id,
            message=message,
            progress=progress,
            data=data or {},
        )
        self._buffer.append(resource_event)

        for queue in list(self._subscribers):
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                logger.warning(
                    "resource_event_queue_oldest_dropped: run_id=%s",
                    self.run_id,
                )
            queue.put_nowait(resource_event)

        if event in RESOURCE_TERMINAL_EVENTS:
            self._is_terminal = True
            asyncio.get_running_loop().call_later(
                self.terminal_retention_seconds,
                lambda: asyncio.create_task(self._cleanup()),
            )

        return resource_event

    async def subscribe(
        self, after_sequence: int
    ) -> tuple[asyncio.Queue[ResourceEvent], list[ResourceEvent]]:
        queue: asyncio.Queue[ResourceEvent] = asyncio.Queue(maxsize=self.queue_size)
        self._subscribers.append(queue)
        replay = [e for e in self._buffer if e.sequence > after_sequence]
        return queue, replay

    async def unsubscribe(self, queue: asyncio.Queue[ResourceEvent]) -> None:
        self._subscribers = [q for q in self._subscribers if q is not queue]

    async def _cleanup(self) -> None:
        if self._subscribers:
            return
        key = (self.user_id, self.resource_id, self.run_id)
        async with _resource_lock:
            _resource_channels.pop(key, None)


# ===================== 公开 API =====================


class ResourceEvents:
    """Resource 模块的实时事件流管理器。

    无状态代理模式：实例本身不持有频道，通过 channel key 从 registry 获取。
    """

    def __init__(
        self,
        *,
        user_id: int,
        resource_id: int,
        run_id: str,
        auto_create: bool = True,
    ) -> None:
        self._user_id = user_id
        self._resource_id = resource_id
        self._run_id = run_id
        self._auto_create = auto_create
        self._key: ChannelKey = (user_id, resource_id, run_id)

    async def _get_or_create_channel(self) -> _ResourceChannel:
        """获取或创建频道。根据 auto_create 决定是否自动创建。"""
        async with _resource_lock:
            channel = _resource_channels.get(self._key)
            if channel is not None:
                return channel
            if not self._auto_create:
                raise ResourceEventExpiredError(
                    f"Resource channel not found for run_id={self._run_id}"
                )
            channel = _ResourceChannel(
                user_id=self._user_id,
                resource_id=self._resource_id,
                run_id=self._run_id,
            )
            _resource_channels[self._key] = channel
            return channel

    async def _get_channel(self) -> _ResourceChannel | None:
        """仅获取频道，不创建。用于检查频道是否存在。"""
        async with _resource_lock:
            return _resource_channels.get(self._key)

    async def send(
        self,
        agent_id: str,
        status: Literal["pending", "running", "completed", "failed"],
        message: str,
        progress: int | None = None,
    ) -> ResourceEvent:
        """发送智能体状态与消息给前端。"""
        if agent_id == "global":
            event_map = {
                "running": "generation.started",
                "completed": "generation.completed",
                "failed": "generation.failed",
            }
            event = event_map.get(status, "generation.started")
        else:
            event_map = {
                "pending": "agent.pending",
                "running": "agent.running",
                "completed": "agent.completed",
                "failed": "agent.failed",
            }
            event = event_map.get(status, "agent.running")

        channel = await self._get_or_create_channel()
        return await channel.send(
            event=event,
            message=message,
            agent_id=agent_id if agent_id != "global" else None,
            progress=progress,
            data={},
        )

    async def subscribe(
        self, after_sequence: int = 0
    ) -> tuple[asyncio.Queue[ResourceEvent], list[ResourceEvent]]:
        """订阅频道。频道必须已存在，否则抛出 ResourceEventExpiredError。"""
        async with _resource_lock:
            channel = _resource_channels.get(self._key)
            if channel is None:
                raise ResourceEventExpiredError(
                    f"Resource channel not found for run_id={self._run_id}"
                )
            return await channel.subscribe(after_sequence)

    async def unsubscribe(self, queue: asyncio.Queue[ResourceEvent]) -> None:
        channel = await self._get_channel()
        if channel is not None:
            await channel.unsubscribe(queue)

    @property
    def run_id(self) -> str:
        return self._run_id

    @property
    def resource_id(self) -> int:
        return self._resource_id

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def is_terminal(self) -> bool:
        channel = _resource_channels.get(self._key)
        return channel is not None and channel._is_terminal


# ===================== SSE 编码 =====================


def encode_resource_sse(event: ResourceEvent) -> str:
    return f"id: {event.sequence}\nevent: resource.event\ndata: {event.model_dump_json()}\n\n"


# ===================== 辅助函数 =====================


async def get_resource_channel(
    user_id: int, resource_id: int, run_id: str
) -> ResourceEvents | None:
    """获取已存在的频道（不创建新频道）。用于 SSE 订阅端点。"""
    key = (user_id, resource_id, run_id)
    async with _resource_lock:
        channel = _resource_channels.get(key)
        if channel is None:
            return None
        events = ResourceEvents(
            user_id=user_id,
            resource_id=resource_id,
            run_id=run_id,
            auto_create=False,
        )
        return events