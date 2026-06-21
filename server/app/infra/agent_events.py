"""统一 Agent 运行事件、生命周期持久化与进程内广播。"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from types import TracebackType
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlmodel import select

from app.infra.database import session_scope
from app.infra.logging import get_logger
from app.infra.models import AgentRun

logger = get_logger(__name__)

AgentModule = Literal["chat", "resource", "path"]
AgentEventType = Literal[
    "run.started",
    "agent.status",
    "tool.status",
    "artifact.ready",
    "content.delta",
    "run.completed",
    "run.failed",
]
AgentRunStatus = Literal["pending", "running", "completed", "failed", "skipped"]


class AgentEvent(BaseModel):
    """唯一对外暴露的 Agent SSE 数据类型。"""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    sequence: int = 0
    module: AgentModule
    business_id: str
    type: AgentEventType
    status: AgentRunStatus
    activity_id: str | None = None
    agent_id: str | None = None
    title: str = ""
    summary: str = ""
    progress: int | None = Field(default=None, ge=0, le=100)
    detail: dict[str, Any] = Field(default_factory=dict)
    elapsed_ms: int | None = Field(default=None, ge=0)
    timestamp: float = Field(default_factory=time.time)


class AgentEventBus:
    """按 run_id 隔离、支持有限回放的进程内事件总线。"""

    def __init__(
        self,
        *,
        queue_size: int = 256,
        replay_size: int = 256,
        terminal_retention_seconds: float = 1800.0,
    ) -> None:
        self._queue_size = queue_size
        self._replay_size = replay_size
        self._terminal_retention_seconds = terminal_retention_seconds
        self._buffers: dict[str, deque[AgentEvent]] = {}
        self._subscribers: dict[str, list[asyncio.Queue[AgentEvent]]] = {}
        self._sequences: dict[str, int] = {}
        self._terminal_runs: set[str] = set()
        self._lock = asyncio.Lock()

    async def publish(self, event: AgentEvent) -> AgentEvent:
        async with self._lock:
            if event.run_id in self._terminal_runs:
                logger.warning("agent_event_after_terminal_dropped: run_id=%s type=%s", event.run_id, event.type)
                return event
            sequence = self._sequences.get(event.run_id, 0) + 1
            self._sequences[event.run_id] = sequence
            event.sequence = sequence
            buffer = self._buffers.setdefault(event.run_id, deque(maxlen=self._replay_size))
            buffer.append(event)
            subscribers = list(self._subscribers.get(event.run_id, []))
            if event.type in {"run.completed", "run.failed"}:
                self._terminal_runs.add(event.run_id)
                asyncio.get_running_loop().call_later(
                    self._terminal_retention_seconds,
                    lambda: asyncio.create_task(self._cleanup_run(event.run_id)),
                )

        for queue in subscribers:
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                logger.warning("agent_event_queue_oldest_dropped: run_id=%s", event.run_id)
            queue.put_nowait(event)
        return event

    async def subscribe(
        self,
        run_id: str,
        after_sequence: int = 0,
    ) -> tuple[asyncio.Queue[AgentEvent], list[AgentEvent]]:
        queue: asyncio.Queue[AgentEvent] = asyncio.Queue(maxsize=self._queue_size)
        async with self._lock:
            self._subscribers.setdefault(run_id, []).append(queue)
            replay = [event for event in self._buffers.get(run_id, ()) if event.sequence > after_sequence]
        return queue, replay

    async def unsubscribe(self, run_id: str, queue: asyncio.Queue[AgentEvent]) -> None:
        async with self._lock:
            subscribers = self._subscribers.get(run_id)
            if not subscribers:
                return
            self._subscribers[run_id] = [item for item in subscribers if item is not queue]
            if not self._subscribers[run_id]:
                self._subscribers.pop(run_id, None)

    async def close_run(self, run_id: str) -> None:
        async with self._lock:
            self._terminal_runs.add(run_id)

    async def _cleanup_run(self, run_id: str) -> None:
        async with self._lock:
            if self._subscribers.get(run_id):
                return
            self._buffers.pop(run_id, None)
            self._sequences.pop(run_id, None)
            self._terminal_runs.discard(run_id)


agent_event_bus = AgentEventBus()


async def create_agent_run(*, user_id: int, module: AgentModule, business_id: str) -> AgentRun:
    run = AgentRun(
        run_id=str(uuid4()),
        user_id=user_id,
        module=module,
        business_id=str(business_id),
    )
    async with session_scope() as session:
        session.add(run)
        await session.flush()
        await session.refresh(run)
    return run


async def get_owned_agent_run(*, run_id: str, user_id: int) -> AgentRun | None:
    async with session_scope() as session:
        result = await session.exec(
            select(AgentRun).where(AgentRun.run_id == run_id, AgentRun.user_id == user_id)
        )
        return result.first()


async def mark_agent_run_started(run_id: str) -> None:
    async with session_scope() as session:
        result = await session.exec(select(AgentRun).where(AgentRun.run_id == run_id))
        run = result.first()
        if run is not None and run.status == "pending":
            run.status = "running"
            run.updated_at = _utc_now()
            session.add(run)


async def mark_agent_run_terminal(
    run_id: str,
    status: Literal["completed", "failed"],
    error: str = "",
) -> None:
    async with session_scope() as session:
        result = await session.exec(select(AgentRun).where(AgentRun.run_id == run_id))
        run = result.first()
        if run is None or run.status in {"completed", "failed"}:
            return
        run.status = status
        run.error_message = error[:2000] if status == "failed" and error else None
        run.completed_at = _utc_now()
        run.updated_at = run.completed_at
        session.add(run)


async def _persist_agent_run_sequence(run_id: str, sequence: int) -> None:
    async with session_scope() as session:
        result = await session.exec(select(AgentRun).where(AgentRun.run_id == run_id))
        run = result.first()
        if run is not None and sequence > run.sequence:
            run.sequence = sequence
            run.updated_at = _utc_now()
            session.add(run)


def _utc_now():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)


class AgentEventEmitter:
    """业务模块向统一事件流发布消息的窄接口。"""

    def __init__(self, *, run_id: str, module: AgentModule, business_id: str) -> None:
        self.run_id = run_id
        self.module = module
        self.business_id = str(business_id)

    async def _publish(self, event_type: AgentEventType, status: AgentRunStatus, **kwargs: Any) -> AgentEvent:
        event = AgentEvent(
            run_id=self.run_id,
            module=self.module,
            business_id=self.business_id,
            type=event_type,
            status=status,
            **kwargs,
        )
        return await agent_event_bus.publish(event)

    async def started(self, *, title: str = "Agent 运行已开始", summary: str = "", **kwargs: Any) -> AgentEvent:
        await mark_agent_run_started(self.run_id)
        return await self._publish("run.started", "running", title=title, summary=summary, **kwargs)

    async def agent_status(self, *, status: AgentRunStatus = "running", **kwargs: Any) -> AgentEvent:
        return await self._publish("agent.status", status, **kwargs)

    async def tool_status(self, *, status: AgentRunStatus = "running", **kwargs: Any) -> AgentEvent:
        return await self._publish("tool.status", status, **kwargs)

    async def artifact_ready(self, *, status: AgentRunStatus = "completed", **kwargs: Any) -> AgentEvent:
        return await self._publish("artifact.ready", status, **kwargs)

    async def content_delta(self, text: str, **kwargs: Any) -> AgentEvent:
        detail = dict(kwargs.pop("detail", {}))
        detail["delta"] = text
        return await self._publish("content.delta", "running", detail=detail, **kwargs)

    async def completed(self, *, title: str = "Agent 运行完成", summary: str = "", **kwargs: Any) -> AgentEvent:
        await mark_agent_run_terminal(self.run_id, "completed")
        event = await self._publish("run.completed", "completed", title=title, summary=summary, **kwargs)
        await _persist_agent_run_sequence(self.run_id, event.sequence)
        return event

    async def failed(self, *, title: str = "Agent 运行失败", summary: str = "", **kwargs: Any) -> AgentEvent:
        await mark_agent_run_terminal(self.run_id, "failed", summary)
        event = await self._publish("run.failed", "failed", title=title, summary=summary, **kwargs)
        await _persist_agent_run_sequence(self.run_id, event.sequence)
        return event

    async def emit_agent(
        self,
        agent_id: str,
        status: str,
        message: str = "",
        progress: int = 0,
        *,
        phase: str | None = None,
        elapsed_ms: int | None = None,
        metrics: dict[str, Any] | None = None,
        dependency: str | None = None,
        artifact_id: str | None = None,
    ) -> AgentEvent:
        """资源 Agent 的统一状态发布入口。"""
        normalized = {
            "finished": "completed",
            "done": "completed",
        }.get(status, status)
        if normalized not in {"pending", "running", "completed", "failed", "skipped"}:
            normalized = "running"
        detail = {
            key: value
            for key, value in {
                "phase": phase,
                "metrics": metrics or {},
                "dependency": dependency,
                "artifact_id": artifact_id,
            }.items()
            if value is not None and value != ""
        }
        return await self.agent_status(
            status=normalized,
            activity_id=f"agent:{agent_id}",
            agent_id=agent_id,
            title=message or agent_id,
            summary=message,
            progress=progress,
            detail=detail,
            elapsed_ms=elapsed_ms,
        )

    async def emit_agent_snapshot(self, agent_id: str, status: str, message: str = "", progress: int = 0, **kwargs: Any) -> AgentEvent:
        return await self.emit_agent(agent_id, status, message, progress, **kwargs)

    async def emit_agent_step(self, agent_id: str, phase: str, message: str, progress: int = 0, **kwargs: Any) -> AgentEvent:
        return await self.emit_agent(agent_id, "running", message, progress, phase=phase, **kwargs)

    async def emit_artifact_ready(
        self,
        agent_id: str,
        message: str,
        *,
        artifact_id: str | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> AgentEvent:
        return await self.artifact_ready(
            activity_id=f"artifact:{agent_id}",
            agent_id=agent_id,
            title=message or "资源已生成",
            summary=message,
            progress=100,
            detail={"artifact_id": artifact_id, "metrics": metrics or {}},
        )


class AgentRunTracker:
    """资源 Agent 的阶段观测器；所有数据仍发布为全局 AgentEvent。"""

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

    async def __aenter__(self) -> "AgentRunTracker":
        self._start_time = time.perf_counter()
        await self.emitter.emit_agent_snapshot(
            self.agent_id,
            "running",
            self.message,
            self.progress,
            phase=self.phase,
            elapsed_ms=0,
        )
        return self

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        return None

    @property
    def elapsed_ms(self) -> int:
        return int((time.perf_counter() - self._start_time) * 1000) if self._start_time else 0

    async def step(self, phase: str, message: str, *, progress: int | None = None, metrics: dict[str, Any] | None = None) -> None:
        self.phase = phase
        self.message = message
        if progress is not None:
            self.progress = progress
        await self.emitter.emit_agent_step(
            self.agent_id,
            phase,
            message,
            self.progress,
            elapsed_ms=self.elapsed_ms,
            metrics=metrics,
        )

    async def finish(self, message: str, *, success: bool, progress: int = 100, metrics: dict[str, Any] | None = None) -> None:
        await self.emitter.emit_agent_snapshot(
            self.agent_id,
            "completed" if success else "failed",
            message,
            progress if success else 0,
            phase="finished" if success else "failed",
            elapsed_ms=self.elapsed_ms,
            metrics=metrics,
        )


def build_terminal_event(run: AgentRun) -> AgentEvent:
    failed = run.status == "failed"
    return AgentEvent(
        run_id=run.run_id,
        sequence=run.sequence,
        module=run.module,  # type: ignore[arg-type]
        business_id=run.business_id,
        type="run.failed" if failed else "run.completed",
        status="failed" if failed else "completed",
        title="Agent 运行失败" if failed else "Agent 运行完成",
        summary=run.error_message or "",
        timestamp=(run.completed_at or run.updated_at).timestamp(),
    )


def encode_sse_event(event: AgentEvent) -> str:
    return f"event: agent.event\ndata: {event.model_dump_json()}\n\n"
