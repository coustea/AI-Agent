"""Path 模块独立实时事件流。

提供 Path 专属的事件类型、内存频道、订阅管理和 SSE 编码。
与 Chat、Resource 模块完全隔离，不共享任何实现。
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.infra.logging import get_logger

logger = get_logger(__name__)

PathEventName = Literal[
    "planning.started",
    "profile.loaded",
    "search.running",
    "search.completed",
    "structure.running",
    "node.ready",
    "planning.completed",
    "planning.failed",
]

PATH_TERMINAL_EVENTS: set[PathEventName] = {"planning.completed", "planning.failed"}


class PathEvent(BaseModel):
    sequence: int = 0
    run_id: str
    path_id: int
    event: PathEventName
    stage: str = ""
    message: str
    progress: int | None = Field(default=None, ge=0, le=100)
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


class PathEventNotOpenError(RuntimeError):
    pass


class PathEventClosedError(RuntimeError):
    pass


ChannelKey = tuple[int, int, str]

_path_channels: dict[ChannelKey, "_PathChannel"] = {}
_path_lock = asyncio.Lock()


class _PathChannel:
    def __init__(
        self,
        *,
        user_id: int,
        path_id: int,
        run_id: str,
        queue_size: int = 256,
        replay_size: int = 256,
        terminal_retention_seconds: float = 1800.0,
    ) -> None:
        self.user_id = user_id
        self.path_id = path_id
        self.run_id = run_id
        self.queue_size = queue_size
        self.replay_size = replay_size
        self.terminal_retention_seconds = terminal_retention_seconds
        self._buffer: deque[PathEvent] = deque(maxlen=replay_size)
        self._subscribers: list[asyncio.Queue[PathEvent]] = []
        self._sequence = 0
        self._is_terminal = False

    async def send(
        self,
        event: PathEventName,
        message: str,
        data: dict[str, Any] | None,
        stage: str = "",
        progress: int | None = None,
    ) -> PathEvent:
        if self._is_terminal:
            raise PathEventClosedError(f"Path channel closed for run_id={self.run_id}")
        self._sequence += 1
        path_event = PathEvent(
            sequence=self._sequence,
            run_id=self.run_id,
            path_id=self.path_id,
            event=event,
            stage=stage,
            message=message,
            progress=progress,
            data=data or {},
        )
        self._buffer.append(path_event)
        for queue in list(self._subscribers):
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            queue.put_nowait(path_event)
        if event in PATH_TERMINAL_EVENTS:
            self._is_terminal = True
            asyncio.get_running_loop().call_later(
                self.terminal_retention_seconds,
                lambda: asyncio.create_task(self._cleanup()),
            )
        return path_event

    async def subscribe(
        self, after_sequence: int
    ) -> tuple[asyncio.Queue[PathEvent], list[PathEvent]]:
        queue: asyncio.Queue[PathEvent] = asyncio.Queue(maxsize=self.queue_size)
        self._subscribers.append(queue)
        replay = [e for e in self._buffer if e.sequence > after_sequence]
        return queue, replay

    async def unsubscribe(self, queue: asyncio.Queue[PathEvent]) -> None:
        self._subscribers = [q for q in self._subscribers if q is not queue]

    async def _cleanup(self) -> None:
        if self._subscribers:
            return
        key = (self.user_id, self.path_id, self.run_id)
        async with _path_lock:
            _path_channels.pop(key, None)


class PathEvents:
    def __init__(
        self,
        *,
        user_id: int,
        path_id: int,
        run_id: str,
        queue_size: int = 256,
        replay_size: int = 256,
        terminal_retention_seconds: float = 1800.0,
    ) -> None:
        self._user_id = user_id
        self._path_id = path_id
        self._run_id = run_id
        self._queue_size = queue_size
        self._replay_size = replay_size
        self._terminal_retention_seconds = terminal_retention_seconds
        self._channel: _PathChannel | None = None
        self._key: ChannelKey = (user_id, path_id, run_id)

    async def open(self) -> None:
        async with _path_lock:
            if self._key in _path_channels:
                self._channel = _path_channels[self._key]
            else:
                self._channel = _PathChannel(
                    user_id=self._user_id,
                    path_id=self._path_id,
                    run_id=self._run_id,
                    queue_size=self._queue_size,
                    replay_size=self._replay_size,
                    terminal_retention_seconds=self._terminal_retention_seconds,
                )
                _path_channels[self._key] = self._channel

    async def send(
        self,
        *,
        event: PathEventName,
        message: str,
        data: dict[str, Any] | None = None,
        stage: str = "",
        progress: int | None = None,
    ) -> PathEvent:
        if self._channel is None:
            raise PathEventNotOpenError(f"Path channel not opened for run_id={self._run_id}")
        return await self._channel.send(event, message, data, stage, progress)

    async def subscribe(
        self, after_sequence: int = 0
    ) -> tuple[asyncio.Queue[PathEvent], list[PathEvent]]:
        if self._channel is None:
            async with _path_lock:
                self._channel = _path_channels.get(self._key)
        if self._channel is None:
            raise PathEventNotOpenError(f"Path channel not found for run_id={self._run_id}")
        return await self._channel.subscribe(after_sequence)

    async def unsubscribe(self, queue: asyncio.Queue[PathEvent]) -> None:
        if self._channel is None:
            return
        await self._channel.unsubscribe(queue)

    @property
    def run_id(self) -> str:
        return self._run_id

    @property
    def path_id(self) -> int:
        return self._path_id

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def is_terminal(self) -> bool:
        return self._channel is not None and self._channel._is_terminal


def encode_path_sse(event: PathEvent) -> str:
    return f"id: {event.sequence}\nevent: path.event\ndata: {event.model_dump_json()}\n\n"


async def get_path_channel(user_id: int, path_id: int, run_id: str) -> PathEvents | None:
    key = (user_id, path_id, run_id)
    async with _path_lock:
        channel = _path_channels.get(key)
        if channel is None:
            return None
        events = PathEvents(user_id=user_id, path_id=path_id, run_id=run_id)
        events._channel = channel
        return events