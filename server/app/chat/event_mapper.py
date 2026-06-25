"""ChatRuntimeEventMapper — 统一运行时事件→SSE 事件转换。"""

from __future__ import annotations

from typing import Any

from app.chat.emitter import ChatEventName, ChatEvents
from app.infra.logging import get_logger

logger = get_logger(__name__)


SSE_EVENT_MAP: dict[str, str] = {
    "message_start": "start",
    "classify_done": "status",
    "file_analysis_start": "status",
    "file_analysis_done": "attachment",
    "agent_status": "agent_status",
    "attachment_status": "attachment_status",
    "answer_token": "token",
    "answer_done": "status",
    "content_replace": "content_replace",
    "diagram_start": "status",
    "diagram_done": "status",  # 改为 status，避免重复发送 diagram.ready
    "memory_update_start": "status",
    "memory_update_done": "status",
    "final": "done",
    "error": "error",
}


def runtime_status(value: Any) -> str:
    status = str(value or "running")
    return {
        "done": "completed",
        "finished": "completed",
        "error": "failed",
    }.get(status, status if status in {"pending", "running", "completed", "failed", "skipped"} else "running")


class EventPublishResult:
    def __init__(self, *, failed: bool = False, terminal: bool = False):
        self.failed = failed
        self.terminal = terminal


class ChatRuntimeEventMapper:
    """统一转换器：内部字典事件 → ChatEvent → SSE。"""

    async def publish(
        self,
        events: ChatEvents,
        event: dict[str, Any],
    ) -> EventPublishResult:
        event_name = str(event.get("event") or "status")
        data = event.get("data")
        payload = data if isinstance(data, dict) else {}

        if event_name == "token":
            await events.send(event="content.delta", message="", data={"delta": str(data or "")})
            return EventPublishResult()

        if event_name == "content_replace":
            await events.send(
                event="content.replace",
                message="",
                data={"content": payload.get("content", ""), "delta": ""},
            )
            return EventPublishResult()

        if event_name == "agent_status":
            status = runtime_status(payload.get("status"))
            if status == "running":
                chat_event: ChatEventName = "tool.running"
            elif status == "failed":
                chat_event = "tool.failed"
            else:
                chat_event = "tool.completed"
            await events.send(
                event=chat_event,
                message=str(payload.get("message") or payload.get("title") or ""),
                data={
                    "activity_id": payload.get("activity_id"),
                    "tool_name": payload.get("tool_name"),
                    "detail": payload.get("detail"),
                },
            )
            return EventPublishResult()

        if event_name == "attachment_status":
            status = runtime_status(payload.get("status"))
            if status == "running":
                chat_event = "attachment.running"
            elif status == "failed":
                chat_event = "attachment.failed"
            else:
                chat_event = "attachment.completed"
            await events.send(
                event=chat_event,
                message=str(payload.get("message") or payload.get("title") or ""),
                data={
                    "activity_id": payload.get("activity_id"),
                    "detail": payload.get("detail"),
                },
            )
            return EventPublishResult()

        if event_name == "diagram" and payload:
            await events.send(
                event="diagram.ready",
                message="教学图解已生成",
                data=payload,
            )
            return EventPublishResult()

        if event_name == "error":
            return EventPublishResult(failed=True)

        if event_name == "status":
            await events.send(
                event="thinking",
                message=str(payload.get("message") or "正在处理"),
                data={k: v for k, v in payload.items() if k != "message"},
            )

        return EventPublishResult()

    async def publish_many(
        self,
        events: ChatEvents,
        runtime_events: list[dict[str, Any]],
    ) -> bool:
        failed = False
        for event in runtime_events:
            result = await self.publish(events, event)
            if result.failed:
                failed = True
        return failed
