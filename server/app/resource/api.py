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
import json
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import get_current_user
from app.infra.database import get_session, session_scope
from app.infra.logging import get_logger
from app.infra.models import User
from app.resource.schemas import ResourceGenerationRequest, SingleResourceRequest, AgentSelection
from app.resource.service import ResourceUsecases, bg_gen_task, bg_single_gen_task
from app.memory.service import MemoryService
from app.infra.response import HttpResponse

router = APIRouter()
logger = get_logger(__name__)


@router.post("/resources")
async def gen_task(
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
    usecases = ResourceUsecases(session)
    result = await usecases.start_resource_task(
        user_id=current_user.id,
        request=req,
        source="standalone",
    )
    resource_id = result["resource_id"]

    memory_service = MemoryService(module="mentor")
    profile_record = await memory_service.get_profile(user_id=current_user.id)
    profile_dict = profile_record.model_dump(exclude_none=True) if profile_record else {}

    background_tasks.add_task(
        bg_gen_task,
        user_id=current_user.id,
        request=req,
        profile=profile_dict,
        resource_id=resource_id,
    )

    return HttpResponse.success(data={"resource_id": resource_id, "status": "pending"}, status_code=201)


@router.post("/resources/single")
async def gen_single(
    req: SingleResourceRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """启动单智能体资源生成后台任务（路径规划 / 即调即用）。"""
    logger.info(
        "[ResourceAPI] 收到单智能体生成请求: user_id=%s agent_id=%s",
        current_user.id,
        req.agent_id.value,
    )

    memory_service = MemoryService(module="mentor")
    profile_record = await memory_service.get_profile(user_id=current_user.id)
    profile_dict = profile_record.model_dump(exclude_none=True) if profile_record else {}

    usecases = ResourceUsecases(session)
    result = await usecases.start_resource_task(
        user_id=current_user.id,
        request=ResourceGenerationRequest(
            learning_need=req.learning_need,
            selected_agents=[AgentSelection(agent_id=req.agent_id, enabled=True)],
        ),
        source="single_agent",
    )
    resource_id = result["resource_id"]

    background_tasks.add_task(
        bg_single_gen_task,
        user_id=current_user.id,
        resource_id=resource_id,
        agent_id=req.agent_id.value,
        learning_need=req.learning_need,
        profile=profile_dict,
    )

    return HttpResponse.success(data={"resource_id": resource_id, "status": "generating", "agent_id": req.agent_id.value}, status_code=201)


@router.get("/resources/{resource_id}/status")
async def get_generation_status(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """查询后台生成任务的状态。"""
    usecases = ResourceUsecases(session)
    status_data = await usecases.get_generation_status(user_id=current_user.id, resource_id=resource_id)
    if status_data is None:
        return HttpResponse.error(code=404, message="资源不存在或无权限")

    return HttpResponse.success(data=status_data)


@router.get("/resources/{resource_id}/events")
async def stream_generation_events(
    resource_id: int,
    current_user: User = Depends(get_current_user),
):
    """以 SSE 推送资源任务快照，让前端动画和阶段产物接近实时更新。"""
    return StreamingResponse(
        _stream_generation_snapshots(current_user.id, resource_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _stream_generation_snapshots(
    user_id: int,
    resource_id: int,
) -> AsyncGenerator[str, None]:
    previous_payload = ""
    while True:
        async with session_scope() as session:
            usecases = ResourceUsecases(session)
            status_data = await usecases.get_generation_status(user_id=user_id, resource_id=resource_id)

        if status_data is None:
            payload = {"message": "资源不存在或无权限"}
            yield f"event: error\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
            return

        payload_text = json.dumps(status_data, ensure_ascii=False)
        if payload_text != previous_payload:
            yield f"event: snapshot\ndata: {payload_text}\n\n"
            previous_payload = payload_text

        if status_data.get("status") in {"completed", "partial_completed", "failed"}:
            yield f"event: done\ndata: {payload_text}\n\n"
            return

        await asyncio.sleep(1)


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
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """查询资源列表。"""
    usecases = ResourceUsecases(session)
    resources = await usecases.list_resources(current_user.id, limit)
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
    return HttpResponse.success(data=items)



@router.get("/resources/{resource_id}")
async def get_resource(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """查询资源详情。"""
    usecases = ResourceUsecases(session)
    bundle = await usecases.get_resource_bundle(current_user.id, resource_id)
    if bundle is None:
        return HttpResponse.error(code=404, message="资源不存在")
    return HttpResponse.success(data=bundle.model_dump(mode="json"))
