"""
Resource HTTP routes.

API 端点：
- POST /generate/task - 创建后台资源生成任务（独立入口）
- GET /generate/task/{id}/status - 查询数据库中的真实执行快照
- GET /agents - 查询可用 Agent 列表
- GET /resources - 查询资源列表
- GET /resources/{id} - 查询资源详情
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import get_current_user
from app.infra.database import get_session
from app.infra.logging import get_logger
from app.infra.models import User
from app.resource.schemas import ResourceGenerationRequest
from app.resource.service import ResourceUsecases, bg_gen_task
from app.memory.service import MemoryService
from app.infra.response import HttpResponse

router = APIRouter()
logger = get_logger(__name__)


@router.post("/generate/task")
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

    return HttpResponse.success(data={"resource_id": resource_id, "status": "pending"})


@router.get("/generate/task/{resource_id}/status")
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


@router.get("/agents")
async def list_agents():
    """查询可用 Agent 列表。"""
    logger.info("[ResourceAPI] 查询可用 Agent 列表")
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
    logger.info("[ResourceAPI] 查询资源列表: user_id=%s limit=%s", current_user.id, limit)

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
    logger.info("[ResourceAPI] 查询资源详情: user_id=%s resource_id=%s", current_user.id, resource_id)

    usecases = ResourceUsecases(session)
    bundle = await usecases.get_resource_bundle(current_user.id, resource_id)
    if bundle is None:
        logger.warning("[ResourceAPI] 资源不存在或无权限: user_id=%s resource_id=%s", current_user.id, resource_id)
        return HttpResponse.error(code=404, message="资源不存在")
    return HttpResponse.success(data=bundle.model_dump(mode="json"))
