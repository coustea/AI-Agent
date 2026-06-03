"""
资源生成 SSE 事件系统。

架构：
- AgentEventEmitter: agent 在执行关键节点时 emit 状态消息
- ResourceEventBus: 内存广播器，把事件推给所有订阅的 SSE 连接

SSE 只发两种事件：
  agent  — { agent_id, status, message }  （status: running / finished / failed / skipped）
  done   — { success, message }
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Literal

from pydantic import BaseModel, Field

from app.infra.logging import get_logger

logger = get_logger(__name__)


# ======================================================================
# AgentEvent — SSE 推送给前端的唯一数据格式
# ======================================================================

class AgentEvent(BaseModel):
    """单个 SSE 事件：agent 状态变更 或 生成完成。"""

    event_type: Literal["agent", "done"] = "agent"
    agent_id: str | None = None
    status: Literal["running", "finished", "failed", "skipped"] | None = None
    message: str | None = None
    # done 事件专用
    success: bool | None = None
    timestamp: float = Field(default_factory=lambda: __import__("time").time())


# ======================================================================
# ResourceEventBus — 内存广播器（进程级单例）
# ======================================================================

class ResourceEventBus:
    """进程级事件广播器。

    后台任务 publish 事件，SSE endpoint subscribe 拿到 asyncio.Queue，
    事件通过 Queue 直接推给前端，不再轮询 DB。
    """

    def __init__(self) -> None:
        self._subscribers: dict[int, list[asyncio.Queue[AgentEvent]]] = {}

    def subscribe(self, resource_id: int) -> asyncio.Queue[AgentEvent]:
        """SSE endpoint 调用，拿到一个 Queue，事件会自动灌入。"""
        q: asyncio.Queue[AgentEvent] = asyncio.Queue(maxsize=256)
        if resource_id not in self._subscribers:
            self._subscribers[resource_id] = []
        self._subscribers[resource_id].append(q)
        return q

    def unsubscribe(self, resource_id: int, queue: asyncio.Queue[AgentEvent]) -> None:
        """SSE 连接断开时调用，清理 Queue。"""
        if resource_id in self._subscribers:
            subs = self._subscribers[resource_id]
            subs[:] = [q for q in subs if q is not queue]
            if not subs:
                del self._subscribers[resource_id]

    async def publish(self, resource_id: int, event: AgentEvent) -> None:
        """后台任务调用，事件广播给所有订阅者。"""
        subs = self._subscribers.get(resource_id, [])
        for q in subs:
            try:
                await q.put(event)
            except asyncio.QueueFull:
                logger.warning("EventBus queue full for resource_id=%s, dropping event", resource_id)


# 进程级单例
resource_event_bus = ResourceEventBus()


# ======================================================================
# AgentEventEmitter — agent 在关键节点 emit 状态
# ======================================================================

EventSink = Callable[[AgentEvent], Awaitable[None]]


class AgentEventEmitter:
    """Agent 的事件发射器。

    调用方在 agent 执行的关键节点调用 emit_agent 或 emit_done，
    事件通过 EventBus 直接推给 SSE。
    """

    def __init__(
        self,
        resource_id: int = 0,
        event_sink: EventSink | None = None,
    ) -> None:
        self.resource_id = resource_id
        self._event_sink = event_sink

    async def emit_agent(
        self,
        agent_id: str,
        status: Literal["running", "finished", "failed", "skipped"],
        message: str = "",
    ) -> None:
        """发送 agent 状态变更。比如：emit_agent("content", "running", "正在生成渐进式讲解...")"""
        event = AgentEvent(
            event_type="agent",
            agent_id=agent_id,
            status=status,
            message=message,
        )
        await resource_event_bus.publish(self.resource_id, event)
        if self._event_sink:
            await self._event_sink(event)

    async def emit_done(
        self,
        success: bool = True,
        message: str = "资源生成完成",
    ) -> None:
        """发送生成完成信号。"""
        event = AgentEvent(
            event_type="done",
            success=success,
            message=message,
        )
        await resource_event_bus.publish(self.resource_id, event)
        if self._event_sink:
            await self._event_sink(event)