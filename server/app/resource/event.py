"""Resource 模块独立实时事件流。

提供 Resource 专属的事件类型、内存频道、订阅管理和 SSE 编码。
与 Chat、Path 模块完全隔离，不共享任何实现。
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
    "plan.running",
    "plan.completed",
    "agent.pending",
    "agent.running",
    "agent.completed",
    "agent.failed",
    "artifact.ready",
    "generation.completed",
    "generation.failed",
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


class ResourceEventNotOpenError(RuntimeError):
    """在 open() 之前调用 send() 时抛出。"""

    pass


class ResourceEventClosedError(RuntimeError):
    """终态事件后继续发送消息时抛出。"""

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
    """Resource 模块的实时事件流管理器。"""

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
        self._user_id = user_id
        self._resource_id = resource_id
        self._run_id = run_id
        self._queue_size = queue_size
        self._replay_size = replay_size
        self._terminal_retention_seconds = terminal_retention_seconds
        self._channel: _ResourceChannel | None = None
        self._key: ChannelKey = (user_id, resource_id, run_id)

    async def open(self) -> None:
        async with _resource_lock:
            if self._key in _resource_channels:
                self._channel = _resource_channels[self._key]
            else:
                self._channel = _ResourceChannel(
                    user_id=self._user_id,
                    resource_id=self._resource_id,
                    run_id=self._run_id,
                    queue_size=self._queue_size,
                    replay_size=self._replay_size,
                    terminal_retention_seconds=self._terminal_retention_seconds,
                )
                _resource_channels[self._key] = self._channel

    async def send(
        self,
        *,
        event: ResourceEventName,
        message: str,
        data: dict[str, Any] | None = None,
        agent_id: str | None = None,
        progress: int | None = None,
    ) -> ResourceEvent:
        if self._channel is None:
            raise ResourceEventNotOpenError(
                f"Resource channel not opened for run_id={self._run_id}"
            )
        return await self._channel.send(event, message, data, agent_id, progress)

    async def subscribe(
        self, after_sequence: int = 0
    ) -> tuple[asyncio.Queue[ResourceEvent], list[ResourceEvent]]:
        if self._channel is None:
            async with _resource_lock:
                self._channel = _resource_channels.get(self._key)
        if self._channel is None:
            raise ResourceEventNotOpenError(
                f"Resource channel not found for run_id={self._run_id}"
            )
        return await self._channel.subscribe(after_sequence)

    async def unsubscribe(self, queue: asyncio.Queue[ResourceEvent]) -> None:
        if self._channel is None:
            return
        await self._channel.unsubscribe(queue)

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
        return self._channel is not None and self._channel._is_terminal

    # ===================== Agent helper methods =====================

    async def send_agent_status(
        self,
        agent_id: str,
        status: str,
        message: str,
        progress: int | None = None,
    ) -> ResourceEvent:
        """Helper method for agents to send status updates."""
        event_map = {
            "running": "agent.running",
            "completed": "agent.completed",
            "failed": "agent.failed",
            "pending": "agent.pending",
        }
        event = event_map.get(status, "agent.running")
        return await self.send(event=event, message=message, agent_id=agent_id, progress=progress)

    async def send_agent_step(
        self,
        agent_id: str,
        phase: str,
        message: str,
        progress: int | None = None,
    ) -> ResourceEvent:
        """Helper method for agents to send step updates."""
        return await self.send(
            event="agent.running",
            message=message,
            agent_id=agent_id,
            progress=progress,
            data={"phase": phase},
        )

    async def send_artifact_ready(
        self,
        agent_id: str,
        message: str,
        artifact_id: str | None = None,
    ) -> ResourceEvent:
        """Helper method for agents to signal artifact is ready."""
        return await self.send(
            event="artifact.ready",
            message=message,
            agent_id=agent_id,
            data={"artifact_id": artifact_id} if artifact_id else {},
        )


class ResourceAgentTracker:
    """Context manager for tracking agent runs with automatic status updates."""

    def __init__(
        self,
        events: ResourceEvents,
        agent_id: str,
        phase: str,
        message: str,
        progress: int | None = None,
    ):
        self._events = events
        self._agent_id = agent_id
        self._phase = phase
        self._message = message
        self._progress = progress

    async def __aenter__(self) -> "ResourceAgentTracker":
        await self._events.send_agent_step(
            self._agent_id,
            phase=self._phase,
            message=self._message,
            progress=self._progress,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, _exc_tb) -> None:
        if exc_type is not None:
            await self._events.send_agent_status(
                self._agent_id,
                status="failed",
                message=str(exc_val)[:200] if exc_val else "Agent failed",
                progress=None,
            )

    async def finish(
        self,
        message: str,
        success: bool = True,
        metrics: dict[str, Any] | None = None,
    ) -> None:
        """Mark agent as finished with final status."""
        await self._events.send_agent_status(
            self._agent_id,
            status="completed" if success else "failed",
            message=message,
            progress=100 if success else None,
        )


# ===================== SSE 编码 =====================


def encode_resource_sse(event: ResourceEvent) -> str:
    return f"id: {event.sequence}\nevent: resource.event\ndata: {event.model_dump_json()}\n\n"


# ===================== 辅助函数 =====================


async def get_resource_channel(
    user_id: int, resource_id: int, run_id: str
) -> ResourceEvents | None:
    key = (user_id, resource_id, run_id)
    async with _resource_lock:
        channel = _resource_channels.get(key)
        if channel is None:
            return None
        events = ResourceEvents(
            user_id=user_id,
            resource_id=resource_id,
            run_id=run_id,
        )
        events._channel = channel
        return events


# ===================== ResourceAgentTracker =====================


class ResourceAgentTracker:
    """Resource Agent 的阶段观测器。"""

    def __init__(
        self,
        *,
        events: ResourceEvents,
        agent_id: str,
        phase: str,
        message: str,
        progress: int = 10,
    ) -> None:
        self.events = events
        self.agent_id = agent_id
        self.phase = phase
        self.message = message
        self.progress = progress
        self._start_time = 0.0

    async def __aenter__(self) -> "ResourceAgentTracker":
        self._start_time = time.perf_counter()
        await self.events.send(
            event="agent.running",
            message=self.message,
            agent_id=self.agent_id,
            progress=self.progress,
            data={"phase": self.phase},
        )
        return self

    async def __aexit__(self, *args) -> None:
        return None

    @property
    def elapsed_ms(self) -> int:
        return int((time.perf_counter() - self._start_time) * 1000) if self._start_time else 0

    async def step(self, phase: str, message: str, *, progress: int | None = None) -> None:
        self.phase = phase
        self.message = message
        if progress is not None:
            self.progress = progress
        await self.events.send(
            event="agent.running",
            message=message,
            agent_id=self.agent_id,
            progress=self.progress,
            data={"phase": phase, "elapsed_ms": self.elapsed_ms},
        )

    async def finish(self, message: str, *, success: bool, progress: int = 100) -> None:
        await self.events.send(
            event="agent.completed" if success else "agent.failed",
            message=message,
            agent_id=self.agent_id,
            progress=progress if success else 0,
            data={"phase": "finished" if success else "failed", "elapsed_ms": self.elapsed_ms},
        )
