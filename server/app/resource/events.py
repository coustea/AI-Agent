"""
SSE 事件发射器。

统一的事件结构，支持 workflow/agent/resource/review/bundle/error/done 事件类型。
每个事件包含 event_id / task_id / event_type / stage / status / message / timestamp。
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.infra.logging import get_logger

logger = get_logger(__name__)
DEFAULT_QUEUE_SIZE = 200


class ResourceGenerateEvent(BaseModel):
    """资源生成 SSE 标准事件。"""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    task_id: str
    event_type: str
    stage: str
    agent: str | None = None
    status: str
    message: str
    progress: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AgentEventEmitter:
    """SSE 事件发射器。"""

    def __init__(self, task_id: str | None = None):
        self._queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue(maxsize=DEFAULT_QUEUE_SIZE)
        self._task_id = task_id or ""

    def bind_task(self, task_id: str) -> None:
        """绑定任务 ID，后续便捷方法可省略 task_id。"""
        self._task_id = task_id

    def _resolve_task_id(self, task_id: str | None = None) -> str:
        return task_id or self._task_id or "unknown"

    async def emit_event(
        self,
        *,
        task_id: str | None = None,
        event_type: str,
        stage: str,
        status: str,
        message: str,
        agent: str | None = None,
        progress: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """发送标准事件。

        Args:
            task_id: 任务 ID
            event_type: 事件类型 (workflow/agent/resource/review/bundle/error/done)
            stage: 阶段 (created/planning/generating/reviewing/assembling/completed/failed)
            status: 状态 (pending/running/success/failed/skipped)
            message: 消息
            agent: Agent 名称
            progress: 进度 0-100
            payload: 负载数据
        """
        event = ResourceGenerateEvent(
            task_id=self._resolve_task_id(task_id),
            event_type=event_type,
            stage=stage,
            agent=agent,
            status=status,
            message=message,
            progress=progress,
            payload=payload or {},
        ).model_dump()
        if self._queue.full():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        await self._queue.put(event)

    # =========================================================================
    # 便捷方法
    # =========================================================================

    async def emit_workflow(
        self,
        stage: str,
        status: str,
        message: str,
        payload: dict[str, Any] | None = None,
        progress: int | None = None,
        task_id: str | None = None,
    ) -> None:
        """发送 workflow 事件。"""
        await self.emit_event(
            task_id=task_id,
            event_type="workflow",
            stage=stage,
            status=status,
            message=message,
            agent="coordinator",
            payload=payload,
            progress=progress,
        )

    async def emit_agent(
        self,
        agent: str,
        status: str,
        message: str,
        payload: dict[str, Any] | None = None,
        progress: int | None = None,
        task_id: str | None = None,
    ) -> None:
        """发送 agent 事件。"""
        await self.emit_event(
            task_id=task_id,
            event_type="agent",
            stage="generating",
            status=status,
            message=message,
            agent=agent,
            payload=payload,
            progress=progress,
        )

    async def emit_resource(
        self,
        agent: str,
        resource: Any,
        message: str | None = None,
        progress: int | None = None,
        payload: dict[str, Any] | None = None,
        task_id: str | None = None,
    ) -> None:
        """发送 resource 事件。"""
        resource_payload = resource.model_dump() if hasattr(resource, "model_dump") else resource
        event_payload = {"resource": resource_payload}
        if payload:
            event_payload.update(payload)
        await self.emit_event(
            task_id=task_id,
            event_type="resource",
            stage="generating",
            status="success",
            message=message or f"{agent} 资源生成完成",
            agent=agent,
            payload=event_payload,
            progress=progress,
        )

    async def emit_review(
        self,
        review_result: Any,
        status: str = "success",
        progress: int | None = None,
        task_id: str | None = None,
    ) -> None:
        """发送 review 事件。"""
        review_payload = review_result.model_dump() if hasattr(review_result, "model_dump") else review_result
        await self.emit_event(
            task_id=task_id,
            event_type="review",
            stage="reviewing",
            status=status,
            message="资源审查完成",
            agent="reviewer",
            payload={"review_result": review_payload},
            progress=progress,
        )

    async def emit_bundle(
        self,
        bundle: Any,
        status: str = "success",
        progress: int = 100,
        task_id: str | None = None,
    ) -> None:
        """发送 bundle 事件。"""
        bundle_payload = bundle.model_dump() if hasattr(bundle, "model_dump") else bundle
        await self.emit_event(
            task_id=task_id,
            event_type="bundle",
            stage="assembling",
            status=status,
            message="资源包组装完成",
            agent="assembler",
            payload={"bundle": bundle_payload},
            progress=progress,
        )

    async def emit_error(
        self,
        message: str,
        stage: str = "failed",
        agent: str | None = None,
        payload: dict[str, Any] | None = None,
        task_id: str | None = None,
    ) -> None:
        """发送 error 事件。"""
        await self.emit_event(
            task_id=task_id,
            event_type="error",
            stage=stage,
            status="failed",
            message=message,
            agent=agent,
            payload=payload,
        )

    async def emit_done(
        self,
        bundle: Any | None = None,
        message: str = "资源生成完成",
        task_id: str | None = None,
    ) -> None:
        """发送 done 事件。"""
        bundle_payload = bundle.model_dump() if hasattr(bundle, "model_dump") else bundle
        payload = {"bundle": bundle_payload} if bundle_payload else {}
        await self.emit_event(
            task_id=task_id,
            event_type="done",
            stage="completed",
            status="success",
            message=message,
            payload=payload,
            progress=100,
        )

    # =========================================================================
    # 兼容旧接口
    # =========================================================================

    async def emit_agent_status(self, agent: str, status: str, message: str, **meta: Any) -> None:
        """兼容旧接口：发送 Agent 状态事件。"""
        task_id = str(meta.pop("task_id", self._resolve_task_id()))
        await self.emit_agent(task_id=task_id, agent=agent, status=status, message=message, payload=meta)

    async def emit_agent_action(
        self,
        agent: str,
        action: str,
        detail: str = "",
        current_step: int = 0,
        total_steps: int = 0,
        step_label: str = "",
        **meta: Any,
    ) -> None:
        """兼容旧接口：发送 Agent 动作事件。"""
        task_id = str(meta.pop("task_id", self._resolve_task_id()))
        payload = {
            "action": action,
            "current_step": current_step,
            "total_steps": total_steps,
            "step_label": step_label,
            **meta,
        }
        await self.emit_agent(
            task_id=task_id,
            agent=agent,
            status="running",
            message=detail or action,
            payload=payload,
        )

    async def emit_artifact_ready(self, agent: str, artifact: dict[str, Any]) -> None:
        """兼容旧接口：发送产物就绪事件。"""
        await self.emit_event(
            task_id=self._resolve_task_id(),
            event_type="resource",
            stage="generating",
            status="success",
            message=f"{agent} 产物就绪",
            agent=agent,
            payload={"artifact": artifact},
        )

    # =========================================================================
    # 流控制
    # =========================================================================

    async def close(self) -> None:
        """关闭事件流。"""
        await self._queue.put(None)

    async def stream(self) -> AsyncGenerator[str, None]:
        """生成 SSE 事件流。"""
        while True:
            event = await self._queue.get()
            if event is None:
                break
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            if event.get("event_type") == "done":
                break
