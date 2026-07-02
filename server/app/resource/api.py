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
import os
import re
from typing import Any

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import get_current_user, get_current_user_flexible
from app.infra.database import get_session
from app.infra.logging import get_logger
from app.infra.models import User
from app.resource.schemas import AGENT_META, AGENT_DEFAULT_ORDER, ResourceGenerationRequest, SingleResourceRequest, AgentSelection
from app.resource.service import ResourceService
from app.resource.orchestrator import run_multi_agent_generation
from app.infra.response import HttpResponse
from app.resource.event import (
    RESOURCE_TERMINAL_EVENTS,
    ResourceEvents,
    encode_resource_sse,
    get_resource_channel,
)


router = APIRouter()
logger = get_logger(__name__)


@router.post("/resources")
async def create_resource_task(
    req: ResourceGenerationRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """启动独立资源生成后台任务。"""
    logger.info(
        "[ResourceAPI] 收到后台生成请求: user_id=%s selected_agents=%s",
        current_user.id,
        req.enabled_agent_ids(),
    )
    service = ResourceService(session)
    result = await service.create_task(
        user_id=current_user.id,
        request=req,
    )
    resource_id = result["resource_id"]

    # 创建事件频道
    events = ResourceEvents(
        user_id=current_user.id,
        resource_id=resource_id,
    )
    await events.open()

    # 启动后台生成（fire-and-forget，不阻塞 Event Loop）
    asyncio.create_task(
        run_multi_agent_generation(
            user_id=current_user.id,
            resource_id=resource_id,
            selected_agents=req.enabled_agent_ids(),
            request_data={
                "learning_need": req.learning_need,
                "learning_scenario": req.learning_scenario,
                "agent_configs": req.agent_configs.model_dump(mode="json"),
            },
        )
    )

    return HttpResponse.success(data={"resource_id": resource_id, "status": "pending"}, status_code=201)


@router.post("/resources/single")
async def create_single_resource_task(
    req: SingleResourceRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """启动单智能体资源生成后台任务（即调即用）。"""
    logger.info(
        "[ResourceAPI] 收到单智能体生成请求: user_id=%s agent_id=%s",
        current_user.id,
        req.agent_id.value,
    )

    service = ResourceService(session)
    result = await service.create_task(
        user_id=current_user.id,
        request=ResourceGenerationRequest(
            learning_need=req.learning_need,
            selected_agents=[AgentSelection(agent_id=req.agent_id, enabled=True)],
        ),
    )
    resource_id = result["resource_id"]

    # 创建事件频道
    events = ResourceEvents(
        user_id=current_user.id,
        resource_id=resource_id,
    )
    await events.open()

    # 启动后台生成（fire-and-forget，不阻塞 Event Loop）
    asyncio.create_task(
        run_multi_agent_generation(
            user_id=current_user.id,
            resource_id=resource_id,
            selected_agents=[req.agent_id.value],
            request_data={
                "learning_need": req.learning_need,
                "learning_scenario": "self_study",
                "agent_configs": {},
            },
        )
    )

    return HttpResponse.success(data={"resource_id": resource_id, "status": "generating", "agent_id": req.agent_id.value}, status_code=201)


@router.get("/resources/{resource_id}/status")
async def get_generation_status(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """查询后台生成任务的状态。"""
    service = ResourceService(session)
    status_data = await service.get_generation_status(
        user_id=current_user.id,
        resource_id=resource_id,
    )
    if status_data is None:
        return HttpResponse.error(code=404, message="资源不存在或无权限")
    return HttpResponse.success(data=status_data)


@router.get("/resources/{resource_id}/events")
async def get_resource_events(
    resource_id: int,
    after_sequence: int = Query(default=0, ge=0),
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    current_user: User = Depends(get_current_user_flexible),
    session: AsyncSession = Depends(get_session),
):
    """SSE 推送任务事件。"""
    # 验证资源所有权
    service = ResourceService(session)
    resource = await service.get_resource(
        current_user.id,
        resource_id,
    )
    if resource is None:
        return HttpResponse.error(code=404, message="资源不存在或无权限")

    # 获取已存在的频道
    events = await get_resource_channel(current_user.id, resource_id)
    if events is None:
        return HttpResponse.error(code=410, message="事件流已过期或不存在")

    resume_sequence = after_sequence
    if last_event_id and last_event_id.isdigit():
        resume_sequence = max(resume_sequence, int(last_event_id))

    async def event_generator():
        queue: asyncio.Queue | None = None
        try:
            queue, replay = await events.subscribe(after_sequence=resume_sequence)
            # 先发送回放事件
            for event in replay:
                yield encode_resource_sse(event)
                if event.event in RESOURCE_TERMINAL_EVENTS:
                    return
            # 然后监听新事件
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield encode_resource_sse(event)
                    if event.event in RESOURCE_TERMINAL_EVENTS:
                        break
                except asyncio.TimeoutError:
                    # 发送心跳
                    yield ": heartbeat\n\n"
        except Exception as e:
            logger.error("SSE event generator error: %s", e)
        finally:
            if queue is not None:
                await events.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/agents")
async def list_agents():
    """查询可用 Agent 列表。"""
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
    service = ResourceService(session)
    resources = await service.list_resources(
        current_user.id,
        limit,
        offset,
    )
    total = await service.count_resources(current_user.id)
    type_summary = await service.list_resource_type_summary(
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
    service = ResourceService(session)
    bundle = await service.get_resource_bundle(
        current_user.id,
        resource_id,
    )
    if bundle is None:
        return HttpResponse.error(code=404, message="资源不存在")
    return HttpResponse.success(data=bundle.model_dump(mode="json"))


@router.get("/resources/public/{resource_id}/html")
async def get_public_html(
    resource_id: str,
    session: AsyncSession = Depends(get_session),
):
    """公开获取 HTML 幻灯片内容，支持 iframe 直接加载。"""
    if not re.fullmatch(r"[A-Za-z0-9_-]+", resource_id):
        return HttpResponse.error(code=400, message="非法幻灯片 ID")

    # 从数据库查找 PPT item 的 metadata 获取文件路径
    from sqlmodel import select, col
    from app.infra.models import GeneratedResourceItem as ItemModel
    try:
        rid = int(resource_id)
    except ValueError:
        rid = None

    if rid is not None:
        stmt = select(ItemModel).where(
            ItemModel.resource_id == rid,
            ItemModel.agent_type == "ppt",
        )
        item = (await session.exec(stmt)).one_or_none()
        if item and item.metadata_json:
            html_path = item.metadata_json.get("html_file_path")
            if html_path and os.path.exists(html_path):
                return FileResponse(
                    path=html_path,
                    media_type="text/html",
                )

    return HttpResponse.error(code=404, message="HTML 幻灯片不存在")


@router.get("/resources/{resource_id}/html")
async def download_html(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """下载 HTML 幻灯片文件。"""
    service = ResourceService(session)

    # 获取资源项
    items = await service.list_resource_items(current_user.id, resource_id)
    ppt_item = None
    for item in items:
        if item.agent_type == "ppt":
            ppt_item = item
            break

    if not ppt_item:
        return HttpResponse.error(code=404, message="PPT 资源不存在")

    # 从 metadata 获取 HTML 文件路径
    html_path = None
    if ppt_item.metadata_json:
        html_path = ppt_item.metadata_json.get("html_file_path")

    if not html_path or not os.path.exists(html_path):
        return HttpResponse.error(code=404, message="HTML 文件未找到")

    return FileResponse(
        path=html_path,
        filename=f"{ppt_item.title}.html",
        media_type="text/html",
    )
