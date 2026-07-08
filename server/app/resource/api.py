"""
Resource HTTP routes.

API 端点：
- POST /resources - 创建后台资源生成任务
- POST /resources/single - 创建单智能体资源生成任务
- GET /resources/{id}/status - 查询任务执行状态
- GET /resources/{id}/events - SSE 推送任务事件
- GET /resources/agents - 查询可用 Agent 列表
- GET /resources/ppt/templates - 查询 PPT 模板列表
- GET /resources - 查询资源列表
- GET /resources/{id} - 查询资源详情
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import get_current_user, get_current_user_flexible
from app.infra.database import get_session
from app.infra.logging import get_logger
from app.infra.models import User
from app.profile.service import ProfileService
from app.resource.schemas import AGENT_META, AGENT_DEFAULT_ORDER, ResourceGenerationRequest, SingleResourceRequest, AgentSelection, AgentConfigs, NodeInput
from app.resource.service import ResourceService
from app.resource.orchestrator import run_multi_agent_generation
from app.resource.workflow.execution import execute_node_agent
from app.infra.response import HttpResponse
from app.resource.event import (
    RESOURCE_TERMINAL_EVENTS,
    ResourceEvents,
    encode_resource_sse,
    get_resource_channel,
)
from app.shared.ppt import PPTGenerator


# PPT/Cartoon 单独调用时走 generate_node（路径规划逻辑），
# 通过 execute_node_agent 统一执行边界，保证消息/保存/校验一致。
_NODE_AGENT_IDS = frozenset({"ppt", "cartoon"})


router = APIRouter()
logger = get_logger(__name__)

# 当前多智能体资源生成页面开放全部资源 Agent。
FRONTEND_RESOURCE_AGENT_IDS = frozenset(
    {"content", "mindmap", "quiz", "code", "reading", "ppt", "cartoon", "video"}
)


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
    profile_service = ProfileService()
    profile_markdown = await profile_service.build_profile_markdown(user_id=current_user.id)
    asyncio.create_task(
        run_multi_agent_generation(
            user_id=current_user.id,
            resource_id=resource_id,
            selected_agents=req.enabled_agent_ids(),
            request_data={
                "learning_need": req.learning_need,
                "learning_scenario": req.learning_scenario,
                "agent_configs": req.agent_configs.model_dump(mode="json"),
                "username": current_user.username,
            },
            profile={"markdown": profile_markdown},
        )
    )

    return HttpResponse.success(data={"resource_id": resource_id, "status": "pending"}, status_code=201)


@router.post("/resources/single")
async def create_single_resource_task(
    req: SingleResourceRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """启动单智能体资源生成后台任务（即调即用）。

    基础 Agent（content/mindmap/code/reading/quiz）走多智能体资源流程
    （run_multi_agent_generation → execute_resource_agent）。

    PPT/Cartoon 走 generate_node 逻辑（execute_node_agent），
    只需要知识点和教程即可生成，通过统一执行边界保证消息/保存/校验一致。
    """
    agent_id_str = req.agent_id.value
    logger.info(
        "[ResourceAPI] 收到单智能体生成请求: user_id=%s agent_id=%s",
        current_user.id,
        agent_id_str,
    )

    service = ResourceService(session)
    request = ResourceGenerationRequest.model_construct(
        learning_need=req.learning_need,
        learning_scenario="self_study",
        selected_agents=[AgentSelection(agent_id=req.agent_id, enabled=True)],
        agent_configs=AgentConfigs(),
    )
    result = await service.create_task(
        user_id=current_user.id,
        request=request,
    )
    resource_id = result["resource_id"]

    # 创建事件频道
    events = ResourceEvents(
        user_id=current_user.id,
        resource_id=resource_id,
    )
    await events.open()

    # ── PPT/Cartoon：走 generate_node 统一执行边界 ──────────────────
    if agent_id_str in _NODE_AGENT_IDS:
        node_input = NodeInput(
            path_id=resource_id,
            node_id=resource_id,
            node_key=str(resource_id),
            path_title=req.learning_need,
            path_goal=req.learning_need,
            node_title=req.learning_need,
            knowledge_points=req.knowledge_points,
            tutorial_title=req.tutorial_title or req.learning_need,
            tutorial_summary=req.learning_need,
            tutorial_markdown=req.tutorial_markdown,
            username=current_user.username,
        )

        asyncio.create_task(
            execute_node_agent(
                user_id=current_user.id,
                resource_id=resource_id,
                agent_id=agent_id_str,
                node_input=node_input,
            )
        )

        return HttpResponse.success(
            data={"resource_id": resource_id, "status": "generating", "agent_id": agent_id_str},
            status_code=201,
        )

    # ── 基础 Agent：走多智能体资源流程 ──────────────────────────────
    profile_service = ProfileService()
    profile_markdown = await profile_service.build_profile_markdown(user_id=current_user.id)
    asyncio.create_task(
        run_multi_agent_generation(
            user_id=current_user.id,
            resource_id=resource_id,
            selected_agents=[req.agent_id.value],
            request_data={
                "learning_need": req.learning_need,
                "learning_scenario": "self_study",
                "agent_configs": {},
                "username": current_user.username,
            },
            profile={"markdown": profile_markdown},
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
            logger.error("SSE 事件生成器错误: %s", e)
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


@router.get("/resources/agents")
async def list_agents():
    """查询当前资源生成前端可选择的 Agent 列表。"""
    agents: list[dict[str, Any]] = []
    for agent_id in AGENT_DEFAULT_ORDER:
        if agent_id not in FRONTEND_RESOURCE_AGENT_IDS:
            continue
        meta = AGENT_META.get(agent_id, {})
        agents.append({
            "id": agent_id,
            "name": meta.get("name", agent_id),
            "icon": meta.get("icon", ""),
            "description": meta.get("description", ""),
            "configurable": True,
        })

    return HttpResponse.success(data=agents)


@router.get("/resources/ppt/templates")
async def list_ppt_templates(
    current_user: User = Depends(get_current_user),
):
    """查询当前 PPT 模块中可用的运行时模板。"""
    return HttpResponse.success(data=PPTGenerator.available_templates())


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


@router.get("/resources/public/{item_id}/html")
async def get_public_item_html(
    item_id: int,
    session: AsyncSession = Depends(get_session),
):
    """公开获取 PPT/Cartoon 的 HTML 内容，支持 iframe 直接加载。"""
    from app.infra.models import GeneratedResourceItem as ItemModel

    item = await session.get(ItemModel, item_id)
    if not item or item.agent_type not in ("ppt", "cartoon"):
        return HttpResponse.error(code=404, message="HTML 资源不存在")

    html_path = None
    if item.metadata_json:
        html_path = item.metadata_json.get("html_file_path")

    if not html_path or not os.path.exists(html_path):
        return HttpResponse.error(code=404, message="HTML 文件未找到")

    return FileResponse(path=html_path, media_type="text/html")


@router.get("/resources/public/{item_id}/video")
async def get_public_item_video(
    item_id: int,
    session: AsyncSession = Depends(get_session),
):
    """公开获取 Video/Cartoon 的 MP4 视频文件。"""
    from app.infra.models import GeneratedResourceItem as ItemModel

    item = await session.get(ItemModel, item_id)
    if not item or item.agent_type not in ("video", "cartoon"):
        return HttpResponse.error(code=404, message="视频资源不存在")

    video_path = None
    if item.metadata_json:
        if item.agent_type == "video":
            video_path = item.metadata_json.get("file_path")
        elif item.agent_type == "cartoon":
            video_path = item.metadata_json.get("video_file_path")

    if not video_path or not os.path.exists(video_path):
        return HttpResponse.error(code=404, message="视频文件未找到")

    return FileResponse(path=video_path, media_type="video/mp4")


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
