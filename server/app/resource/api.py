"""Resource HTTP routes."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import get_current_user
from app.infra.database import get_session
from app.infra.logging import get_logger
from app.infra.models import User
from app.resource.schemas import ResourceGenerateRequest
from app.resource.service import resource_usecases
from app.shared.response import HttpResponse

router = APIRouter()
logger = get_logger(__name__)


@router.post("/generate")
async def generate_resources(
    req: ResourceGenerateRequest,
    current_user: User = Depends(get_current_user),
):
    task_dict = req.learning_task.model_dump()
    logger.info(
        "[ResourceAPI] 收到生成请求: user_id=%s course=%r selected_resources=%s",
        current_user.id,
        task_dict.get("course", ""),
        req.selected_resources,
    )
    return StreamingResponse(
        resource_usecases.stream_bundle(
            user_id=current_user.id,
            task=task_dict,
            selected_resources=req.selected_resources,
        ),
        # 这里直接返回 text/event-stream，让前端一边接收一边更新工作看板。
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/agents")
async def list_agents():
    logger.info("[ResourceAPI] 查询可用 Agent 列表")
    return HttpResponse.success(data=resource_usecases.list_agents())


@router.get("/resources")
async def list_resources(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    logger.info("[ResourceAPI] 查询资源列表: user_id=%s limit=%s", current_user.id, limit)
    resources = await resource_usecases.list_resources(session, current_user.id, limit)

    items = [
        {
            "id": value.id,
            "course": value.course,
            "gap": value.gap,
            "need": value.need,
            "status": value.status,
            "has_mindmap": value.mindmap_result is not None,
            "has_content": value.content_result is not None,
            "has_code": value.code_result is not None,
            "has_quiz": value.quiz_result is not None,
            "has_reading": value.reading_result is not None,
            "has_image": value.image_result is not None,
            "has_ppt": value.ppt_result is not None,
            "has_video": value.video_result is not None,
            "created_at": value.created_at,
        }
        for value in resources
    ]
    return HttpResponse.success(data=items)


@router.get("/resources/{resource_id}")
async def get_resource(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    logger.info("[ResourceAPI] 查询资源详情: user_id=%s resource_id=%s", current_user.id, resource_id)
    resource = await resource_usecases.get_resource(session, current_user.id, resource_id)
    if resource is None:
        logger.warning("[ResourceAPI] 资源不存在或无权限: user_id=%s resource_id=%s", current_user.id, resource_id)
        return HttpResponse.error(code=404, message="资源不存在")

    data = {
        "id": resource.id,
        "course": resource.course,
        "gap": resource.gap,
        "need": resource.need,
        "status": resource.status,
        "request_extra": resource.request_extra,
        "plan_result": resource.plan_result,
        "results": {},
        "created_at": resource.created_at,
    }
    for key in ("mindmap", "content", "code", "quiz", "reading", "image", "ppt", "video"):
        raw = getattr(resource, f"{key}_result")
        if raw:
            try:
                data["results"][key] = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                # 新架构里仍允许个别资源先以纯文本落库，详情页不因为单个解析失败而中断。
                data["results"][key] = raw
    return HttpResponse.success(data=data)
