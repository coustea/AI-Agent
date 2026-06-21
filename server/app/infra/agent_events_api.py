"""全局 Agent 运行事件订阅接口。"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.auth.security import get_current_user_flexible
from app.infra.agent_events import (
    agent_event_bus,
    build_terminal_event,
    encode_sse_event,
    get_owned_agent_run,
)
from app.infra.models import User
from app.infra.response import HttpResponse

router = APIRouter(prefix="/agent-runs", tags=["agent-runs"])

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


@router.get("/{run_id}/events")
async def stream_agent_run_events(
    run_id: str,
    after_sequence: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user_flexible),
):
    run = await get_owned_agent_run(run_id=run_id, user_id=current_user.id)
    if run is None:
        return HttpResponse.error(code=404, message="Agent 运行不存在或无权限")

    async def event_stream():
        queue, replay = await agent_event_bus.subscribe(run_id, after_sequence)
        try:
            for event in replay:
                yield encode_sse_event(event)
            if run.status in {"completed", "failed"} and not replay:
                yield encode_sse_event(build_terminal_event(run))
                return
            if replay and replay[-1].type in {"run.completed", "run.failed"}:
                return
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
                    continue
                yield encode_sse_event(event)
                if event.type in {"run.completed", "run.failed"}:
                    return
        finally:
            await agent_event_bus.unsubscribe(run_id, queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
