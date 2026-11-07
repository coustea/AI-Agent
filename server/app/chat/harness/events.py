"""Chat 运行事件流 — 事件模型、状态归约、持久化发布与 SSE 编码。

数据库是断点续传的唯一事实源：``text.delta`` 只做进程内实时推送，
其余事件落 ``chat_run_events``，刷新页面后按 ``sequence`` 重放即可恢复。
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlmodel import func, select

from app.infra.database import session_scope
from app.infra.logging import get_logger
from app.infra.models import ChatRun, ChatRunEvent

logger = get_logger(__name__)

RunStatus = Literal["queued", "running", "completed", "failed", "cancelled", "interrupted"]

RunEventName = Literal[
    "run.started",
    "turn.started",
    "text.delta",
    "text.completed",
    "activity.updated",
    "artifact.created",
    "run.completed",
    "run.failed",
    "run.cancelled",
    "run.interrupted",
]

TERMINAL_EVENTS: frozenset[str] = frozenset(
    {"run.completed", "run.failed", "run.cancelled", "run.interrupted"}
)

# 逐 token 的增量事件不落库，避免一次对话写入数百行
_LIVE_ONLY_EVENTS: frozenset[str] = frozenset({"text.delta"})

ActivityStatus = Literal["running", "completed", "failed", "cancelled"]


class ChatActivity(BaseModel):
    """一条可公开的执行活动（工具调用、附件分析、工作流阶段）。"""

    activity_id: str
    kind: str = "tool"
    title: str = ""
    status: ActivityStatus = "running"
    detail: dict[str, Any] = Field(default_factory=dict)


class RunArtifact(BaseModel):
    """一次运行产出的可下载产物（视频 / PPT）。"""

    id: str
    kind: str
    title: str = ""
    url: str = ""
    preview_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunState(BaseModel):
    """前端渲染一次运行所需的完整快照。"""

    run_id: str
    sequence: int = 0
    status: RunStatus = "queued"
    content: str = ""
    error: str = ""
    activities: list[ChatActivity] = Field(default_factory=list)
    artifacts: list[RunArtifact] = Field(default_factory=list)


class RunEvent(BaseModel):
    """一次运行的单个 SSE 事件。"""

    run_id: str
    sequence: int
    event: RunEventName
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


def reduce_state(state: RunState, event: RunEvent) -> RunState:
    """按事件推进运行快照；乱序或重复事件直接忽略。"""
    if event.run_id != state.run_id or event.sequence <= state.sequence:
        return state
    next_state = state.model_copy(update={"sequence": event.sequence})
    data = event.data
    if event.event == "run.started":
        next_state.status = "running"
    elif event.event == "turn.started":
        next_state.content = ""
    elif event.event == "text.delta":
        next_state.content += str(data.get("delta") or "")
    elif event.event == "text.completed":
        next_state.content = str(data.get("content") or "")
    elif event.event == "activity.updated":
        activity = ChatActivity(**data)
        kept = [a for a in state.activities if a.activity_id != activity.activity_id]
        next_state.activities = [*kept, activity]
    elif event.event == "artifact.created":
        artifact = RunArtifact(**data)
        kept = [a for a in state.artifacts if a.id != artifact.id]
        next_state.artifacts = [*kept, artifact]
    elif event.event in TERMINAL_EVENTS:
        next_state.status = str(event.event).removeprefix("run.")  # type: ignore[assignment]
        next_state.error = str(data.get("error") or "")
    return next_state


def encode_chat_sse(event: RunEvent) -> str:
    """把运行事件编码为 SSE 帧（前端监听 ``chat.event``）。"""
    return f"id: {event.sequence}\nevent: chat.event\ndata: {event.model_dump_json()}\n\n"


class _RunHub:
    """同一进程内按 run_id 分发的低延迟队列；不缓存、不负责重放。"""

    def __init__(self) -> None:
        """初始化订阅队列映射与并发锁。"""
        self._queues: dict[str, set[asyncio.Queue[RunEvent]]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, run_id: str) -> asyncio.Queue[RunEvent]:
        """为指定运行注册一个监听队列。"""
        queue: asyncio.Queue[RunEvent] = asyncio.Queue(maxsize=256)
        async with self._lock:
            self._queues.setdefault(run_id, set()).add(queue)
        return queue

    async def unsubscribe(self, run_id: str, queue: asyncio.Queue[RunEvent]) -> None:
        """移除指定运行的监听队列。"""
        async with self._lock:
            queues = self._queues.get(run_id)
            if queues is None:
                return
            queues.discard(queue)
            if not queues:
                self._queues.pop(run_id, None)

    async def publish(self, event: RunEvent) -> None:
        """向指定运行的所有在线监听队列广播事件。"""
        async with self._lock:
            queues = list(self._queues.get(event.run_id, set()))
        for queue in queues:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("chat_run_event_backpressure: run_id=%s", event.run_id)

    async def has_subscribers(self, run_id: str) -> bool:
        """判断指定运行当前是否还有在线订阅者。"""
        async with self._lock:
            return bool(self._queues.get(run_id))


_hub = _RunHub()


class ChatRunEvents:
    """单次运行的事件发布器 — 落库后广播给在线订阅者。"""

    def __init__(self, run_id: str) -> None:
        """绑定运行 ID 并初始化序列号水位。"""
        self.run_id = run_id
        self._sequence = 0
        self._ready = False
        self._cancelled = False

    async def open(self) -> None:
        """从数据库恢复序列号水位，保证重连后序号连续。"""
        if self._ready:
            return
        async with session_scope() as db:
            result = await db.execute(
                select(func.max(ChatRunEvent.sequence)).where(ChatRunEvent.run_id == self.run_id)
            )
            self._sequence = int(result.scalar_one_or_none() or 0)
        self._ready = True

    async def emit(
        self,
        event: RunEventName,
        data: Mapping[str, Any] | None = None,
        *,
        persist: bool | None = None,
    ) -> RunEvent:
        """分配序号、按需落库，并广播给在线订阅者。"""
        if not self._ready:
            await self.open()
        self._sequence += 1
        payload = dict(data or {})
        run_event = RunEvent(
            run_id=self.run_id,
            sequence=self._sequence,
            event=event,
            data=payload,
        )
        should_persist = event not in _LIVE_ONLY_EVENTS if persist is None else persist
        if should_persist:
            async with session_scope() as db:
                db.add(
                    ChatRunEvent(
                        run_id=self.run_id,
                        sequence=run_event.sequence,
                        event=event,
                        data=payload,
                    )
                )
                await db.commit()
        await _hub.publish(run_event)
        if event in TERMINAL_EVENTS:
            await self._apply_terminal(run_event)
        return run_event

    async def _apply_terminal(self, event: RunEvent) -> None:
        """把终态写回运行行，作为刷新后的权威状态。"""
        async with session_scope() as db:
            run = await db.get(ChatRun, self.run_id)
            if run is None:
                return
            run.status = str(event.event).removeprefix("run.")
            run.error = str(event.data.get("error") or "")
            content = event.data.get("content")
            if isinstance(content, str):
                run.content = content
            run.finished_at = func.now()
            db.add(run)
            await db.commit()

    @property
    def cancelled(self) -> bool:
        """运行是否已被请求取消。"""
        return self._cancelled

    def request_cancel(self) -> None:
        """标记取消请求，循环在下一个检查点退出。"""
        self._cancelled = True

    async def subscribe(
        self, after_sequence: int = 0
    ) -> tuple[asyncio.Queue[RunEvent], list[RunEvent]]:
        """订阅运行事件，返回实时队列与 ``after_sequence`` 之后的回放。"""
        queue = await _hub.subscribe(self.run_id)
        replay = await self.replay(after_sequence)
        return queue, replay

    async def unsubscribe(self, queue: asyncio.Queue[RunEvent]) -> None:
        """取消订阅。"""
        await _hub.unsubscribe(self.run_id, queue)

    async def replay(self, after_sequence: int = 0) -> list[RunEvent]:
        """从数据库读取 ``after_sequence`` 之后的事件用于补发。"""
        async with session_scope() as db:
            result = await db.execute(
                select(ChatRunEvent)
                .where(
                    ChatRunEvent.run_id == self.run_id,
                    ChatRunEvent.sequence > after_sequence,
                )
                .order_by(ChatRunEvent.sequence.asc())
            )
            rows = list(result.scalars().all())
        return [
            RunEvent(
                run_id=row.run_id,
                sequence=row.sequence,
                event=row.event,  # type: ignore[arg-type]
                data=row.data or {},
                timestamp=row.created_at.timestamp() if row.created_at else time.time(),
            )
            for row in rows
        ]


async def load_run_state(run_id: str) -> RunState | None:
    """从数据库重建运行快照；运行不存在时返回 None。"""
    async with session_scope() as db:
        run = await db.get(ChatRun, run_id)
        if run is None:
            return None
        result = await db.execute(
            select(ChatRunEvent)
            .where(ChatRunEvent.run_id == run_id)
            .order_by(ChatRunEvent.sequence.asc())
        )
        rows = list(result.scalars().all())

    state = RunState(
        run_id=run.id,
        status=run.status,  # type: ignore[arg-type]
        content=run.content,
        error=run.error,
        artifacts=[RunArtifact(**item) for item in (run.artifacts or [])],
    )
    for row in rows:
        state = reduce_state(
            state,
            RunEvent(
                run_id=row.run_id,
                sequence=row.sequence,
                event=row.event,  # type: ignore[arg-type]
                data=row.data or {},
            ),
        )
    # 运行行里的最终文本比事件回放更权威（text.delta 不落库）
    state.content = run.content or state.content
    return state


async def has_active_run(user_id: int, session_id: str) -> bool:
    """同一会话是否已有未结束的运行，用于拒绝并发请求。"""
    async with session_scope() as db:
        result = await db.execute(
            select(func.count())
            .select_from(ChatRun)
            .where(
                ChatRun.user_id == user_id,
                ChatRun.session_id == session_id,
                ChatRun.status.in_(["queued", "running"]),
            )
        )
        return int(result.scalar_one() or 0) > 0


async def mark_interrupted_runs() -> int:
    """进程启动时把遗留的进行中运行标记为中断，返回处理条数。"""
    async with session_scope() as db:
        result = await db.execute(
            select(ChatRun).where(ChatRun.status.in_(["queued", "running"]))
        )
        runs = list(result.scalars().all())
        for run in runs:
            run.status = "interrupted"
            run.error = "服务重启，运行已中断"
            db.add(run)
        if runs:
            await db.commit()
    return len(runs)


__all__ = [
    "ChatActivity",
    "ChatRunEvents",
    "RunArtifact",
    "RunEvent",
    "RunEventName",
    "RunState",
    "RunStatus",
    "TERMINAL_EVENTS",
    "encode_chat_sse",
    "has_active_run",
    "load_run_state",
    "mark_interrupted_runs",
    "reduce_state",
]
