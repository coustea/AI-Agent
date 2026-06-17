from __future__ import annotations

import asyncio
from typing import Literal

from pydantic import BaseModel, Field

from app.infra.logging import get_logger

logger = get_logger(__name__)

# 路径事件类型：generating（生成中）、step（进度步进）、done（完成）
PathEventType = Literal["path.generating", "path.step", "path.done"]
# 路径状态：generating（生成中）、active（激活）、failed（失败）
PathStatus = Literal["generating", "active", "failed"]


class PathEvent(BaseModel):
    """单个路径事件 — 通过 SSE 推送给前端的进度通知。"""

    event_type: PathEventType = "path.step"
    path_id: int
    status: PathStatus = "generating"
    message: str | None = None
    progress: int = 0
    success: bool | None = None
    timestamp: float = Field(default_factory=lambda: __import__("time").time())


class PathEventBus:
    """路径事件总线 — 基于 asyncio.Queue 的发布/订阅模式。

    每个 path_id 可以有多个订阅者（SSE 连接），事件通过队列广播。
    队列满时丢弃事件并记录警告。
    """

    def __init__(self) -> None:
        # 订阅者映射：path_id → [Queue, Queue, ...]
        self._subscribers: dict[int, list[asyncio.Queue[PathEvent]]] = {}

    def subscribe(self, path_id: int) -> asyncio.Queue[PathEvent]:
        """订阅指定路径的事件流，返回一个异步队列。"""
        q: asyncio.Queue[PathEvent] = asyncio.Queue(maxsize=256)
        if path_id not in self._subscribers:
            self._subscribers[path_id] = []
        self._subscribers[path_id].append(q)
        return q

    def unsubscribe(self, path_id: int, queue: asyncio.Queue[PathEvent]) -> None:
        """取消订阅，从订阅者列表中移除指定队列。"""
        if path_id in self._subscribers:
            subs = self._subscribers[path_id]
            subs[:] = [q for q in subs if q is not queue]
            if not subs:
                del self._subscribers[path_id]

    async def publish(self, path_id: int, event: PathEvent) -> None:
        """向指定路径的所有订阅者广播事件。"""
        subs = self._subscribers.get(path_id, [])
        for q in subs:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("PathEventBus queue full for path_id=%s, dropping event", path_id)


# 全局单例事件总线
path_event_bus = PathEventBus()
