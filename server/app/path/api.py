"""Path planning HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import get_current_user
from app.infra.database import get_session
from app.infra.models import User
from app.path.schemas import PathFeedbackRequest, PathRebuildRequest
from app.path.service import path_usecases
from app.shared.response import HttpResponse

router = APIRouter()


@router.get("/path-plan")
async def get_path_plan(
    resource_id: int | None = Query(default=None, ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        data = await path_usecases.get_path_plan(
            session,
            current_user.id,
            resource_id=resource_id,
        )
    except LookupError:
        return HttpResponse.error(code=404, message="路径规划资源不存在")
    return HttpResponse.success(data=data)


@router.post("/path-plan/rebuild")
async def rebuild_path_plan(
    req: PathRebuildRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        data = await path_usecases.rebuild_path_plan(
            session,
            current_user.id,
            resource_id=req.resource_id,
        )
    except LookupError:
        return HttpResponse.error(code=404, message="路径规划资源不存在")
    return HttpResponse.success(data=data)


@router.post("/path-plan/feedback")
async def feedback_path_plan(
    req: PathFeedbackRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        data = await path_usecases.apply_feedback(
            session,
            current_user.id,
            feedback=req.feedback,
            weak_points=req.weak_points,
            resource_id=req.resource_id,
        )
    except LookupError:
        return HttpResponse.error(code=404, message="路径规划资源不存在")
    return HttpResponse.success(data=data)
