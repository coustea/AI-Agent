"""
SSE 事件发射器 — 资源生成过程中的实时事件推送。

ResourceGenerateEvent: 事件数据模型
AgentEventEmitter: 事件发射器，支持 SSE 格式输出
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any, AsyncGenerator

from pydantic import BaseModel, Field

from app.infra.logging import get_logger

logger = get_logger(__name__)


class ResourceGenerateEvent(BaseModel):
    """资源生成事件。"""
    event_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    task_id: str = ""
    event_type: str = "workflow"  # workflow | planning | agent_step | agent | resource | review | bundle | error | done | layer
    stage: str = ""
    agent: str | None = None
    status: str = "pending"  # pending | running | success | failed | skipped
    message: str = ""
    progress: int = 0
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%S"))


EventSink = Callable[[ResourceGenerateEvent], Awaitable[None]]


class AgentEventEmitter:
    """
    Agent 事件发射器。

    收集生成过程中的事件，支持 SSE 格式流式输出。
    """

    def __init__(
        self,
        resource_id: int = 0,
        task_id: str | None = None,
        event_sink: EventSink | None = None,
    ):
        self.resource_id = resource_id
        self.task_id = task_id or (str(resource_id) if resource_id else "")
        self._event_sink = event_sink
        self._queue: asyncio.Queue[ResourceGenerateEvent | None] = asyncio.Queue()
        self._finished = False

    def bind_task(self, task_id: str) -> None:
        """绑定任务 ID。"""
        self.task_id = task_id

    def _make_event(
        self,
        event_type: str,
        stage: str = "",
        agent: str | None = None,
        status: str = "running",
        message: str = "",
        progress: int = 0,
        payload: dict[str, Any] | None = None,
        task_id: str | None = None,
    ) -> ResourceGenerateEvent:
        """创建事件对象。"""
        return ResourceGenerateEvent(
            task_id=task_id or self.task_id or str(self.resource_id),
            event_type=event_type,
            stage=stage,
            agent=agent,
            status=status,
            message=message,
            progress=progress,
            payload=payload or {},
        )

    def _enqueue(self, event: ResourceGenerateEvent) -> None:
        """将事件放入队列。"""
        self._queue.put_nowait(event)

    async def _publish(self, event: ResourceGenerateEvent) -> None:
        """发布事件，并等待数据库快照已反映这一真实状态。"""
        self._enqueue(event)
        if self._event_sink:
            await self._event_sink(event)

    # ------------------------------------------------------------------
    # 事件发送方法
    # ------------------------------------------------------------------

    async def emit_workflow(
        self,
        stage: str,
        message: str = "",
        progress: int = 0,
        status: str = "running",
        payload: dict[str, Any] | None = None,
        task_id: str | None = None,
        agent: str | None = "coordinator",
    ) -> None:
        """发送工作流事件。"""
        await self._publish(self._make_event(
            event_type="workflow",
            stage=stage,
            agent=agent,
            status=status,
            message=message,
            progress=progress,
            payload=payload,
            task_id=task_id,
        ))

    
    async def emit_agent_action(
        self,
        agent_name: str,
        action: str,
        detail: str = "",
        *,
        current_step: int = 0,
        total_steps: int = 0,
        step_label: str = "",
        current_action: str = "",
        layer: int = 0,
        layer_name: str = "",
        agent_role: str = "",
        resource_type: str = "",
        progress: int = 0,
    ) -> None:
        """发送 Agent 动作事件。"""
        event = self._make_event(
            event_type="agent_step",
            stage=f"layer_{layer}",
            agent=agent_name,
            message=detail or current_action or action,
            progress=progress,
            payload={
                "action": action,
                "detail": detail,
                "current_step": current_step,
                "total_steps": total_steps,
                "step_label": step_label,
                "current_action": current_action,
                "layer": layer,
                "layer_name": layer_name,
                "agent_role": agent_role,
                "resource_type": resource_type,
            },
        )
        await self._publish(event)

    async def emit_agent(
        self,
        agent_name: str = "",
        status: str = "running",
        message: str = "",
        progress: int = 0,
        *,
        payload: dict[str, Any] | None = None,
        task_id: str | None = None,
        stage: str = "",
        agent: str | None = None,
    ) -> None:
        """发送 Agent 状态事件。"""
        resolved_agent = agent_name or agent or ""
        await self._publish(self._make_event(
            event_type="agent",
            stage=stage,
            agent=resolved_agent,
            status=status,
            message=message,
            progress=progress,
            payload=payload,
            task_id=task_id,
        ))

    async def emit_resource(
        self,
        agent_id: str = "",
        title: str = "",
        file_type: str = "",
        content: Any = None,
        summary: str = "",
        summary_data: dict | None = None,
        metadata: dict | None = None,
        resource: Any = None,
        task_id: str | None = None,
        progress: int = 0,
        agent: str | None = None,
    ) -> None:
        """发送资源生成完成事件。"""
        resolved_agent_id = agent_id or agent or ""
        resource_payload = resource.model_dump(mode="json") if hasattr(resource, "model_dump") else resource
        if resource_payload is None:
            resource_payload = {
                "id": f"{self.resource_id}-{resolved_agent_id}" if self.resource_id else resolved_agent_id,
                "type": resolved_agent_id,
                "title": title,
                "format": file_type,
                "content": content,
                "summary": summary,
                "summary_data": summary_data or {},
                "metadata": metadata or {},
            }
        await self._publish(self._make_event(
            event_type="resource",
            agent=resolved_agent_id,
            status="success",
            message=f"资源生成完成: {title or resolved_agent_id}",
            progress=progress,
            task_id=task_id,
            payload={
                "resource": resource_payload,
                "agent_id": resolved_agent_id,
                "title": title,
                "file_type": file_type,
                "summary": summary,
                "summary_data": summary_data or {},
                "metadata": metadata or {},
            },
        ))

    async def emit_review(
        self,
        message: str = "",
        progress: int = 0,
        payload: dict | None = None,
    ) -> None:
        """发送审核事件。"""
        await self._publish(self._make_event(
            event_type="review",
            stage="reviewing",
            message=message,
            progress=progress,
            payload=payload or {},
        ))

    async def emit_bundle(
        self,
        bundle: Any = None,
        progress: int = 0,
    ) -> None:
        """发送组装事件。"""
        bundle_payload = bundle.model_dump(mode="json") if hasattr(bundle, "model_dump") else bundle
        item_count = 0
        if isinstance(bundle_payload, list):
            item_count = len(bundle_payload)
        elif isinstance(bundle_payload, dict) and isinstance(bundle_payload.get("resources"), list):
            item_count = len(bundle_payload["resources"])
        await self._publish(self._make_event(
            event_type="bundle",
            stage="assembling",
            agent="assembler",
            status="success",
            message="资源组装完成",
            progress=progress,
            payload={"bundle": bundle_payload, "item_count": item_count},
        ))

    async def emit_error(self, message: str) -> None:
        """发送错误事件。"""
        await self._publish(self._make_event(
            event_type="error",
            status="failed",
            message=message,
        ))

    async def emit_done(
        self,
        progress: int = 100,
        bundle: Any = None,
        task_id: str | None = None,
        message: str = "资源生成完成",
    ) -> None:
        """发送完成事件。"""
        bundle_payload = bundle.model_dump(mode="json") if hasattr(bundle, "model_dump") else bundle
        await self._publish(self._make_event(
            event_type="done",
            stage="completed",
            status="success",
            message=message,
            progress=progress,
            payload={"bundle": bundle_payload} if bundle_payload else {},
            task_id=task_id,
        ))
        # 发送结束信号
        self._queue.put_nowait(None)
        self._finished = True

    async def close(self) -> None:
        """关闭事件流。"""
        self._queue.put_nowait(None)
        self._finished = True

    # ------------------------------------------------------------------
    # SSE 流式输出
    # ------------------------------------------------------------------

    async def stream(self) -> AsyncGenerator[str, None]:
        """以 SSE 格式流式输出事件。"""
        while True:
            event = await self._queue.get()
            if event is None:
                yield "event: close\ndata: {}\n\n"
                break
            yield self._format_sse(event)

    def _format_sse(self, event: ResourceGenerateEvent) -> str:
        """将事件格式化为 SSE 字符串。"""
        data = json.dumps(event.model_dump(mode="json"), ensure_ascii=False)
        return f"event: {event.event_type}\ndata: {data}\n\n"
