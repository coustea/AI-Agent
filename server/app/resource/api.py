"""
Resource HTTP routes.

API 端点：
- POST /generate - 生成资源包（SSE 流式）
- GET /agents - 查询可用 Agent 列表
- GET /resources - 查询资源列表
- GET /resources/{id} - 查询资源详情
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import get_current_user
from app.infra.database import get_session
from app.infra.logging import get_logger
from app.infra.models import User
from app.resource.schemas import ResourceGenerationRequest
from app.resource.service import ResourceUsecases, ResourceStreamService, get_stream_service
from app.shared.response import HttpResponse

router = APIRouter()
logger = get_logger(__name__)


@router.post("/generate")
async def generate_resources(
    req: ResourceGenerationRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """生成资源包（SSE 流式）。

    请求体：ResourceGenerationRequest
    - learning_need: 用户自然语言学习需求
    - selected_agents: list[AgentSelection]
    - agent_configs: AgentConfigs
    - output_options: OutputOptions
    """
    logger.info(
        "[ResourceAPI] 收到生成请求: user_id=%s selected_agents=%s",
        current_user.id,
        req.enabled_agent_ids(),
    )

    stream_service = await get_stream_service(session)
    return StreamingResponse(
        stream_service.stream_bundle(
            user_id=current_user.id,
            request=req,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/agents")
async def list_agents():
    """查询可用 Agent 列表。

    返回 6 个活跃 Agent：content, mindmap, diagram, quiz, reading, code
    """
    logger.info("[ResourceAPI] 查询可用 Agent 列表")
    from app.resource.registry import ensure_initialized, get_enabled_agent_ids, get_agent_entry
    ensure_initialized()

    agent_ids = get_enabled_agent_ids()
    agents: list[dict[str, Any]] = []

    for agent_id in agent_ids:
        entry = get_agent_entry(agent_id)
        if entry:
            agents.append({
                "id": agent_id,
                "name": entry.agent_class.__name__,
                "role": entry.role,
                "description": entry.description,
                "dependencies": entry.dependencies,
                "execution_layer": entry.execution_layer,
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


@router.get("/resources/{resource_id}/files/{filename}")
async def get_resource_file(
    resource_id: int,
    filename: str,
    token: str = Query(default="", description="资源文件访问 token"),
):
    """旧文件下载接口已废弃。"""
    raise HTTPException(status_code=410, detail="资源已改为数据库存储，请使用资源详情接口读取 content")


@router.get("/resources/{resource_id}")
async def get_resource(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """查询资源详情。

    返回 ResourceBundle 结构：
    - id: 资源包 ID
    - task_id: 任务 ID
    - title: 资源包标题
    - learning_need: 学习需求
    - resources: 资源列表
    - study_path: 学习路径
    - review_result: 审查结果
    - status: 状态
    - created_at: 创建时间
    - updated_at: 更新时间
    """
    logger.info("[ResourceAPI] 查询资源详情: user_id=%s resource_id=%s", current_user.id, resource_id)

    usecases = ResourceUsecases(session)
    resource = await usecases.get_resource(current_user.id, resource_id)
    if resource is None:
        logger.warning("[ResourceAPI] 资源不存在或无权限: user_id=%s resource_id=%s", current_user.id, resource_id)
        return HttpResponse.error(code=404, message="资源不存在")

    db_items = await usecases.list_resource_items(current_user.id, resource_id)
    resources: list[dict[str, Any]] = [
        {
            "id": item.id,
            "type": item.resource_type,
            "title": item.title,
            "format": item.format,
            "content": item.content_json if item.content_json is not None else item.content_text,
            "summary": item.summary or "",
            "metadata": item.metadata_json or {},
            "status": item.status,
            "error_message": item.error_message,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }
        for item in db_items
    ]

    bundle = {
        "id": str(resource.id),
        "task_id": str(resource.id),
        "title": "个性化学习资源包",
        "learning_need": resource.learning_need or "",
        "selected_agents": resource.selected_agents or [],
        "resources": resources,
        "study_path": [],
        "review_result": None,
        "status": resource.status,
        "created_at": resource.created_at.isoformat() if resource.created_at else None,
        "updated_at": resource.updated_at.isoformat() if resource.updated_at else None,
        "metadata": {
            "source": "database",
        },
    }
    return HttpResponse.success(data=bundle)
