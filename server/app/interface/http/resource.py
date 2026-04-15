"""Resource HTTP routes."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.bootstrap.container import AppContainer
from app.core.response import HttpResponse
from app.interface.http.dependencies import get_app_container, get_current_user, get_session
from app.models.user import User
from app.shared.dto.resource import ResourceGenerateRequest

router = APIRouter()


@router.post("/generate")
async def generate_resources(
    req: ResourceGenerateRequest,
    current_user: User = Depends(get_current_user),
    container: AppContainer = Depends(get_app_container),
):
    task_dict = req.learning_task.model_dump()
    return StreamingResponse(
        container.resource_usecases.stream_bundle(
            user_id=current_user.id,
            task=task_dict,
            selected_resources=req.selected_resources,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/agents")
async def list_agents(container: AppContainer = Depends(get_app_container)):
    return HttpResponse.success(data=container.resource_usecases.list_agents())


@router.get("/resources")
async def list_resources(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    container: AppContainer = Depends(get_app_container),
):
    resources = await container.resource_usecases.list_resources(session, current_user.id, limit)
    items = [
        {
            "id": value.id,
            "course": value.course,
            "gap": value.gap,
            "need": value.need,
            "has_mindmap": value.mindmap_result is not None,
            "has_content": value.content_result is not None,
            "has_code": value.code_result is not None,
            "has_quiz": value.quiz_result is not None,
            "has_reading": value.reading_result is not None,
            "has_ppt": value.ppt_result is not None,
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
    container: AppContainer = Depends(get_app_container),
):
    resource = await container.resource_usecases.get_resource(session, current_user.id, resource_id)
    if resource is None:
        return HttpResponse.error(code=404, message="资源不存在")

    data = {
        "id": resource.id,
        "course": resource.course,
        "gap": resource.gap,
        "need": resource.need,
        "extra": resource.extra,
        "results": {},
        "created_at": resource.created_at,
    }
    for key in ("mindmap", "content", "code", "quiz", "reading", "ppt"):
        raw = getattr(resource, f"{key}_result")
        if raw:
            try:
                data["results"][key] = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                data["results"][key] = raw
    return HttpResponse.success(data=data)
