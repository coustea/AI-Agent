"""
Resource HTTP routes.

API 端点：
- POST /resources - 创建后台资源生成任务
- POST /resources/single - 创建单智能体资源生成任务
- GET /resources/{id}/status - 查询任务执行状态
- GET /resources/{id}/events - SSE 推送任务事件
- GET /agents - 查询可用 Agent 列表
- GET /resources - 查询资源列表
- GET /resources/{id} - 查询资源详情
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import get_current_user
from app.infra.database import get_session
from app.infra.logging import get_logger
from app.infra.models import User
from app.resource.constants import STANDALONE_RESOURCE_SOURCES
from app.resource.events import resource_event_bus
from app.resource.schemas import ResourceGenerationRequest, SingleResourceRequest, AgentSelection
from app.resource.service import ResourceService
from app.resource.orchestrator import run_multi_agent_generation
from app.profile.service import get_profile_service
from app.infra.response import HttpResponse

router = APIRouter()
logger = get_logger(__name__)


@router.post("/resources")
async def create_resource_task(
    req: ResourceGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """启动独立资源生成后台任务。"""
    logger.info(
        "[ResourceAPI] 收到后台生成请求: user_id=%s selected_agents=%s",
        current_user.id,
        req.enabled_agent_ids(),
    )
    usecases = ResourceService(session)
    result = await usecases.start_resource_task(
        user_id=current_user.id,
        request=req,
        source="standalone",
    )
    resource_id = result["resource_id"]

    profile_builder = get_profile_service()
    profile_record = await profile_builder.get_profile(user_id=current_user.id)
    profile_dict = profile_record.model_dump(exclude_none=True) if profile_record else {}

    background_tasks.add_task(
        run_multi_agent_generation,
        user_id=current_user.id,
        request=req,
        profile=profile_dict,
        resource_id=resource_id,
    )

    return HttpResponse.success(data={"resource_id": resource_id, "status": "pending"}, status_code=201)


@router.post("/resources/single")
async def create_single_resource_task(
    req: SingleResourceRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """启动单智能体资源生成后台任务（即调即用）。"""
    logger.info(
        "[ResourceAPI] 收到单智能体生成请求: user_id=%s agent_id=%s",
        current_user.id,
        req.agent_id.value,
    )

    profile_builder = get_profile_service()
    profile_record = await profile_builder.get_profile(user_id=current_user.id)
    profile_dict = profile_record.model_dump(exclude_none=True) if profile_record else {}

    usecases = ResourceService(session)
    result = await usecases.start_resource_task(
        user_id=current_user.id,
        request=ResourceGenerationRequest(
            learning_need=req.learning_need,
            selected_agents=[AgentSelection(agent_id=req.agent_id, enabled=True)],
        ),
        source="single_agent",
    )
    resource_id = result["resource_id"]

    # Single agent mode: run via multi-agent pipeline with only one agent selected
    background_tasks.add_task(
        run_multi_agent_generation,
        user_id=current_user.id,
        request=ResourceGenerationRequest(
            learning_need=req.learning_need,
            selected_agents=[AgentSelection(agent_id=req.agent_id, enabled=True)],
        ),
        profile=profile_dict,
        resource_id=resource_id,
    )

    return HttpResponse.success(data={"resource_id": resource_id, "status": "generating", "agent_id": req.agent_id.value}, status_code=201)


@router.get("/resources/{resource_id}/status")
async def get_generation_status(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """查询后台生成任务的状态。"""
    usecases = ResourceService(session)
    status_data = await usecases.get_generation_status(
        user_id=current_user.id,
        resource_id=resource_id,
        allowed_sources=STANDALONE_RESOURCE_SOURCES,
    )
    if status_data is None:
        return HttpResponse.error(code=404, message="资源不存在或无权限")

    return HttpResponse.success(data=status_data)


@router.get("/resources/{resource_id}/events")
async def stream_resource_events(
    resource_id: int,
    token: str = Query(default="", description="JWT token for SSE auth"),
):
    """SSE 端点：订阅资源生成事件，实时推送 agent 状态变更。"""
    if not token:
        return HttpResponse.error(code=401, message="缺少认证 token")

    from app.auth.security import decode_token
    try:
        decode_token(token)
    except Exception:
        return HttpResponse.error(code=401, message="认证失败")

    async def event_stream():
        # 先回填当前已有的快照状态，避免 SSE 连接晚于事件导致前端空白
        from app.resource.events import AgentEvent
        snapshot = resource_event_bus.get_latest_snapshot(resource_id)
        for agent_id, agent_snapshot in snapshot.get("agent_snapshots", {}).items():
            snapshot_event = AgentEvent(
                event_type="agent.snapshot",
                agent_id=agent_id,
                **{k: v for k, v in agent_snapshot.items() if k in AgentEvent.model_fields},
            )
            yield f"event: {snapshot_event.event_type}\ndata: {snapshot_event.model_dump_json()}\n\n"
        if snapshot.get("current_message") and not snapshot.get("agent_snapshots"):
            snapshot_event = AgentEvent(
                event_type="agent",
                message=snapshot["current_message"],
            )
            yield f"event: agent\ndata: {snapshot_event.model_dump_json()}\n\n"

        # 然后订阅实时事件
        queue = resource_event_bus.subscribe(resource_id)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    yield f": heartbeat\n\n"
                    continue
                data = event.model_dump_json()
                yield f"event: {event.event_type}\ndata: {data}\n\n"
                if event.event_type == "done":
                    break
        finally:
            resource_event_bus.unsubscribe(resource_id, queue)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/agents")
async def list_agents():
    """查询可用 Agent 列表。"""
    from app.resource.schemas import AGENT_META, AGENT_DEFAULT_ORDER

    agents: list[dict[str, Any]] = []
    for agent_id in AGENT_DEFAULT_ORDER:
        meta = AGENT_META.get(agent_id, {})
        agents.append({
            "id": agent_id,
            "name": meta.get("name", agent_id),
            "icon": meta.get("icon", ""),
            "description": meta.get("description", ""),
            "configurable": True,
        })

    return HttpResponse.success(data=agents)


@router.get("/resources")
async def list_resources(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """查询资源列表。"""
    usecases = ResourceService(session)
    resources = await usecases.list_resources(
        current_user.id,
        limit,
        offset,
        sources=STANDALONE_RESOURCE_SOURCES,
    )
    total = await usecases.count_resources(current_user.id, sources=STANDALONE_RESOURCE_SOURCES)
    type_summary = await usecases.list_resource_type_summary(
        user_id=current_user.id,
        resource_ids=[value.id for value in resources if value.id is not None],
    )

    items: list[dict[str, Any]] = []
    for value in resources:
        items.append(
            {
                "id": value.id,
                "learning_need": value.learning_need or "",
                "status": value.status,
                "resource_types": type_summary.get(value.id or 0, []),
                "created_at": value.created_at,
                "updated_at": value.updated_at,
            }
        )
    return HttpResponse.success(data={"items": items, "total": total})



@router.get("/resources/{resource_id}")
async def get_resource(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """查询资源详情。"""
    usecases = ResourceService(session)
    bundle = await usecases.get_resource_bundle(
        current_user.id,
        resource_id,
        allowed_sources=STANDALONE_RESOURCE_SOURCES,
    )
    if bundle is None:
        return HttpResponse.error(code=404, message="资源不存在")
    return HttpResponse.success(data=bundle.model_dump(mode="json"))


@router.get("/video/audio/{filename:path}")
async def get_video_audio(filename: str):
    """Serve generated video audio files."""
    from app.config import WORKPLACE_DIR
    from fastapi.responses import FileResponse
    
    # Simple directory traversal checks
    if ".." in filename or "/" in filename or "\\" in filename:
        return HttpResponse.error(code=400, message="Illegal filename")
        
    file_path = WORKPLACE_DIR / "video_audio" / filename
    if not file_path.exists():
        return HttpResponse.error(code=404, message="Audio file not found")
        
    return FileResponse(path=str(file_path), media_type="audio/mpeg")


