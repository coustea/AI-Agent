from __future__ import annotations

import asyncio
from typing import Literal

from pydantic import BaseModel, Field

from app.infra.logging import get_logger

logger = get_logger(__name__)

PathEventType = Literal["path.generating", "path.step", "path.done"]
PathStatus = Literal["generating", "active", "failed"]

class PathEvent(BaseModel):
    event_type: PathEventType = "path.step"
    path_id: int
    status: PathStatus = "generating"
    message: str | None = None
    progress: int = 0
    success: bool | None = None
    timestamp: float = Field(default_factory=lambda: __import__("time").time())


class PathEventBus:
    def __init__(self) -> None:
        self._subscribers: dict[int, list[asyncio.Queue[PathEvent]]] = {}

    def subscribe(self, path_id: int) -> asyncio.Queue[PathEvent]:
        q: asyncio.Queue[PathEvent] = asyncio.Queue(maxsize=256)
        if path_id not in self._subscribers:
            self._subscribers[path_id] = []
        self._subscribers[path_id].append(q)
        return q

    def unsubscribe(self, path_id: int, queue: asyncio.Queue[PathEvent]) -> None:
        if path_id in self._subscribers:
            subs = self._subscribers[path_id]
            subs[:] = [q for q in subs if q is not queue]
            if not subs:
                del self._subscribers[path_id]

    async def publish(self, path_id: int, event: PathEvent) -> None:
        subs = self._subscribers.get(path_id, [])
        for q in subs:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("PathEventBus queue full for path_id=%s, dropping event", path_id)


# Singleton
path_event_bus = PathEventBus()
