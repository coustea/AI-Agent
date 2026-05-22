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

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import get_current_user
from app.infra.database import get_session
from app.infra.logging import get_logger
from app.infra.models import User
from app.resource.schemas import ResourceGenerationRequest
from app.resource.service import ResourceUsecases, ResourceStreamService, get_stream_service
from app.utils.response import HttpResponse

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

    返回活跃 Agent：content, mindmap, knowledge_graph, quiz, reading, code
    """
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


@router.get("/resources/{resource_id}/files/{filename}")
async def get_resource_file(
    resource_id: int,
    filename: str,
    token: str = Query(default="", description="资源文件访问 token"),
):
    """旧文件下载接口已废弃。"""
    return HttpResponse.error(code=410, message="资源已改为数据库存储，请使用资源详情接口读取 content")


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
    bundle = await usecases.get_resource_bundle(current_user.id, resource_id)
    if bundle is None:
        logger.warning("[ResourceAPI] 资源不存在或无权限: user_id=%s resource_id=%s", current_user.id, resource_id)
        return HttpResponse.error(code=404, message="资源不存在")
    return HttpResponse.success(data=bundle.model_dump(mode="json"))
