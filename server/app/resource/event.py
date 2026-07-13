"""资源任务事件：持久化状态为事实源，进程内队列只负责即时推送。"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.infra.database import session_scope
from app.infra.models import GeneratedResourceRunEvent
from app.infra.logging import get_logger
from app.resource.service import ResourceService

logger = get_logger(__name__)

ResourceEventName = Literal[
    "generation.started",
    "generation.completed",
    "generation.failed",
    "agent.status",
]
RESOURCE_TERMINAL_EVENTS: set[ResourceEventName] = {"generation.completed", "generation.failed"}


class ResourceEvent(BaseModel):
    sequence: int
    resource_id: int
    event: ResourceEventName
    agent_id: str | None = None
    message: str
    progress: int | None = Field(default=None, ge=0, le=100)
    data: dict[str, Any] = Field(default_factory=dict)
    # Unix epoch milliseconds. This is the same unit used by the status
    # snapshot so a replayed event and a live SSE event render identically.
    timestamp: int


def _to_event(row: GeneratedResourceRunEvent) -> ResourceEvent:
    return ResourceEvent(
        sequence=int(row.id or 0),
        resource_id=row.resource_id,
        event=row.event,
        agent_id=row.agent_id,
        message=row.message,
        progress=row.progress,
        data={
            "status": row.status,
            "phase": row.phase,
            **(row.data_json or {}),
        },
        timestamp=int((row.created_at or datetime.now(timezone.utc)).timestamp() * 1000),
    )


class _LiveSubscribers:
    """同一 API 进程内的低延迟 fan-out；不缓存、不负责重放。"""

    def __init__(self) -> None:
        self._queues: dict[int, set[asyncio.Queue[ResourceEvent]]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, resource_id: int) -> asyncio.Queue[ResourceEvent]:
        queue: asyncio.Queue[ResourceEvent] = asyncio.Queue(maxsize=128)
        async with self._lock:
            self._queues.setdefault(resource_id, set()).add(queue)
        return queue

    async def unsubscribe(self, resource_id: int, queue: asyncio.Queue[ResourceEvent]) -> None:
        async with self._lock:
            queues = self._queues.get(resource_id)
            if queues is None:
                return
            queues.discard(queue)
            if not queues:
                self._queues.pop(resource_id, None)

    async def publish(self, event: ResourceEvent) -> None:
        async with self._lock:
            queues = list(self._queues.get(event.resource_id, set()))
        for queue in queues:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("resource_event_subscriber_backpressure: resource_id=%s", event.resource_id)


_subscribers = _LiveSubscribers()


class ResourceEvents:
    """资源事件发布器。

    send() 先以数据库事务提交 Agent 快照和事件，再通知当前 SSE 订阅者。
    因此刷新页面不会依赖这个对象是否仍在内存中。
    """

    def __init__(self, *, user_id: int, resource_id: int) -> None:
        self._user_id = user_id
        self._resource_id = resource_id

    async def send(
        self,
        agent_id: str,
        status: Literal["pending", "running", "completed", "failed", "interrupted"],
        message: str,
        progress: int | None = None,
        *,
        data: dict[str, Any] | None = None,
    ) -> ResourceEvent:
        phase = str((data or {}).get("phase") or "working")
        async with session_scope() as session:
            service = ResourceService(session)
            if agent_id == "global":
                resource_status = {
                    "running": "generating",
                    "completed": "completed",
                    "failed": "failed",
                }.get(status, "generating")
                row = await service.publish_generation_status(
                    resource_id=self._resource_id,
                    status=resource_status,
                    message=message,
                    data=data,
                )
            else:
                row = await service.publish_agent_status(
                    resource_id=self._resource_id,
                    agent_id=agent_id,
                    status=status,
                    message=message,
                    phase=phase,
                    progress=progress,
                    data=data,
                )
        event = _to_event(row)
        await _subscribers.publish(event)
        return event

    async def publish_committed(self, row: GeneratedResourceRunEvent) -> ResourceEvent:
        """广播已经由同一业务事务提交的事件，绝不二次落库。"""
        event = _to_event(row)
        await _subscribers.publish(event)
        return event

    async def subscribe(self) -> asyncio.Queue[ResourceEvent]:
        return await _subscribers.subscribe(self._resource_id)

    async def unsubscribe(self, queue: asyncio.Queue[ResourceEvent]) -> None:
        await _subscribers.unsubscribe(self._resource_id, queue)


def encode_resource_sse(event: ResourceEvent) -> str:
    return f"id: {event.sequence}\nevent: resource.event\ndata: {event.model_dump_json()}\n\n"


__all__ = [
    "RESOURCE_TERMINAL_EVENTS",
    "ResourceEvent",
    "ResourceEvents",
    "encode_resource_sse",
    "_to_event",
]
