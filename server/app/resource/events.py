"""
资源生成 SSE 事件系统。

架构：
- AgentEventEmitter: agent 在执行关键节点时 emit 状态消息
- ResourceEventBus: 内存广播器，把事件推给所有订阅的 SSE 连接

SSE 事件分两层：
  agent/done              — 兼容旧前端的粗粒度状态
  agent.snapshot/step/... — 驱动生成页动画卡片的细粒度观测事件
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from types import TracebackType
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.infra.logging import get_logger

logger = get_logger(__name__)


# ======================================================================
# AgentEvent — SSE 推送给前端的数据格式
# ======================================================================

AgentEventType = Literal[
    "agent",
    "agent.snapshot",
    "agent.step",
    "agent.heartbeat",
    "agent.artifact_ready",
    "done",
]
AgentStatus = Literal["running", "finished", "failed", "skipped"]


class AgentEvent(BaseModel):
    """单个 SSE 事件：既兼容旧 agent 事件，也支持卡片动画状态快照。"""

    event_type: AgentEventType = "agent"
    agent_id: str | None = None
    status: AgentStatus | None = None
    message: str | None = None
    progress: int = 0
    run_id: str | None = None
    span_id: str | None = None
    phase: str | None = None
    elapsed_ms: int | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    dependency: str | None = None
    artifact_id: str | None = None
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
        self._latest_snapshots: dict[int, dict[str, Any]] = {}

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
        self._record_latest_snapshot(resource_id, event)
        subs = self._subscribers.get(resource_id, [])
        for q in subs:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("EventBus queue full for resource_id=%s, dropping event", resource_id)
        if event.event_type == "done":
            loop = asyncio.get_event_loop()
            loop.call_later(1800, self._cleanup_snapshot, resource_id)

    def _cleanup_snapshot(self, resource_id: int) -> None:
        self._latest_snapshots.pop(resource_id, None)
        logger.debug("EventBus 清理快照: resource_id=%s", resource_id)

    def get_latest_snapshot(self, resource_id: int) -> dict[str, Any]:
        """返回最近一次事件驱动的任务快照，供 status 接口兜底同步。"""
        snapshot = self._latest_snapshots.get(resource_id)
        if not snapshot:
            return {"agent_snapshots": {}, "current_message": ""}
        return {
            "agent_snapshots": {
                agent_id: dict(agent_snapshot)
                for agent_id, agent_snapshot in snapshot.get("agent_snapshots", {}).items()
            },
            "current_message": snapshot.get("current_message", ""),
        }

    def _record_latest_snapshot(self, resource_id: int, event: AgentEvent) -> None:
        snapshot = self._latest_snapshots.setdefault(
            resource_id,
            {"agent_snapshots": {}, "current_message": ""},
        )
        if event.message:
            snapshot["current_message"] = event.message

        if not event.agent_id:
            return

        agent_snapshot = dict(snapshot["agent_snapshots"].get(event.agent_id, {}))
        event_data = event.model_dump(mode="json", exclude_none=True)
        for key in (
            "event_type",
            "agent_id",
            "status",
            "message",
            "progress",
            "run_id",
            "span_id",
            "phase",
            "elapsed_ms",
            "metrics",
            "dependency",
            "artifact_id",
            "timestamp",
        ):
            if key in event_data:
                agent_snapshot[key] = event_data[key]
        snapshot["agent_snapshots"][event.agent_id] = agent_snapshot


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
        run_id: str | None = None,
        event_sink: EventSink | None = None,
    ) -> None:
        self.resource_id = resource_id
        self.run_id = run_id
        self._event_sink = event_sink

    async def emit(self, event: AgentEvent) -> None:
        """发送任意资源事件，并自动补齐 run_id。"""
        if event.run_id is None:
            event.run_id = self.run_id
        await resource_event_bus.publish(self.resource_id, event)
        if self._event_sink:
            await self._event_sink(event)

    async def emit_agent(
        self,
        agent_id: str,
        status: AgentStatus,
        message: str = "",
        progress: int = 0,
        *,
        phase: str | None = None,
        elapsed_ms: int | None = None,
        metrics: dict[str, Any] | None = None,
        dependency: str | None = None,
        artifact_id: str | None = None,
    ) -> None:
        """发送 agent 状态变更。比如：emit_agent("content", "running", "正在生成渐进式讲解...", progress=25)"""
        event = AgentEvent(
            event_type="agent",
            agent_id=agent_id,
            status=status,
            message=message,
            progress=progress,
            run_id=self.run_id,
            phase=phase,
            elapsed_ms=elapsed_ms,
            metrics=metrics or {},
            dependency=dependency,
            artifact_id=artifact_id,
        )
        await self.emit(event)

    async def emit_agent_snapshot(
        self,
        agent_id: str,
        status: AgentStatus,
        message: str = "",
        progress: int = 0,
        *,
        phase: str | None = None,
        elapsed_ms: int | None = None,
        metrics: dict[str, Any] | None = None,
        dependency: str | None = None,
        artifact_id: str | None = None,
        span_id: str | None = None,
    ) -> None:
        """发送可直接驱动前端 agent 卡片的状态快照。"""
        await self.emit(
            AgentEvent(
                event_type="agent.snapshot",
                agent_id=agent_id,
                status=status,
                message=message,
                progress=progress,
                run_id=self.run_id,
                span_id=span_id,
                phase=phase,
                elapsed_ms=elapsed_ms,
                metrics=metrics or {},
                dependency=dependency,
                artifact_id=artifact_id,
            )
        )

    async def emit_agent_step(
        self,
        agent_id: str,
        phase: str,
        message: str,
        progress: int = 0,
        *,
        elapsed_ms: int | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> None:
        """发送 agent 内部步骤变化，用于卡片步骤和舞台动画。"""
        await self.emit(
            AgentEvent(
                event_type="agent.step",
                agent_id=agent_id,
                status="running",
                message=message,
                progress=progress,
                run_id=self.run_id,
                phase=phase,
                elapsed_ms=elapsed_ms,
                metrics=metrics or {},
            )
        )

    async def emit_agent_heartbeat(
        self,
        agent_id: str,
        phase: str,
        message: str,
        *,
        progress: int = 0,
        elapsed_ms: int | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> None:
        """发送长耗时 agent 的心跳，避免前端动画舞台静止。"""
        await self.emit(
            AgentEvent(
                event_type="agent.heartbeat",
                agent_id=agent_id,
                status="running",
                message=message,
                progress=progress,
                run_id=self.run_id,
                phase=phase,
                elapsed_ms=elapsed_ms,
                metrics=metrics or {},
            )
        )

    async def emit_artifact_ready(
        self,
        agent_id: str,
        message: str,
        *,
        artifact_id: str | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> None:
        """发送资源产物已落库事件，点亮前端资源坞。"""
        await self.emit(
            AgentEvent(
                event_type="agent.artifact_ready",
                agent_id=agent_id,
                status="finished",
                message=message,
                progress=100,
                run_id=self.run_id,
                phase="artifact_saved",
                artifact_id=artifact_id,
                metrics=metrics or {},
            )
        )

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
            run_id=self.run_id,
        )
        await self.emit(event)


class AgentRunTracker:
    """Agent 运行观测器：发送开始快照、周期心跳、步骤变化和结束快照。"""

    def __init__(
        self,
        *,
        emitter: AgentEventEmitter,
        agent_id: str,
        phase: str,
        message: str,
        progress: int = 10,
        heartbeat_interval: float = 3.0,
    ) -> None:
        self.emitter = emitter
        self.agent_id = agent_id
        self.phase = phase
        self.message = message
        self.progress = progress
        self.heartbeat_interval = heartbeat_interval
        self._start_time = 0.0
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._closed = False

    async def __aenter__(self) -> "AgentRunTracker":
        self._start_time = time.perf_counter()
        await self.emitter.emit_agent_snapshot(
            self.agent_id,
            status="running",
            phase=self.phase,
            message=self.message,
            progress=self.progress,
            elapsed_ms=0,
        )
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        return self

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None,
        exc: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        self._closed = True
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

    @property
    def elapsed_ms(self) -> int:
        if not self._start_time:
            return 0
        return int((time.perf_counter() - self._start_time) * 1000)

    async def step(
        self,
        phase: str,
        message: str,
        *,
        progress: int | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> None:
        self.phase = phase
        self.message = message
        if progress is not None:
            self.progress = progress
        await self.emitter.emit_agent_step(
            self.agent_id,
            phase=self.phase,
            message=self.message,
            progress=self.progress,
            elapsed_ms=self.elapsed_ms,
            metrics=metrics,
        )

    async def finish(
        self,
        message: str,
        *,
        success: bool,
        progress: int = 100,
        metrics: dict[str, Any] | None = None,
    ) -> None:
        await self.emitter.emit_agent_snapshot(
            self.agent_id,
            status="finished" if success else "failed",
            phase="finished" if success else "failed",
            message=message,
            progress=progress if success else 0,
            elapsed_ms=self.elapsed_ms,
            metrics=metrics,
        )

    async def _heartbeat_loop(self) -> None:
        try:
            while not self._closed:
                await asyncio.sleep(self.heartbeat_interval)
                await self.emitter.emit_agent_heartbeat(
                    self.agent_id,
                    phase=self.phase,
                    message=self.message,
                    progress=self.progress,
                    elapsed_ms=self.elapsed_ms,
                )
        except asyncio.CancelledError:
            raise
