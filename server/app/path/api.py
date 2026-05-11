"""Path planning HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import get_current_user
from app.infra.database import get_session
from app.infra.models import User
from app.path.schemas import PathFeedbackRequest, PathRebuildRequest
from app.path.service import path_usecases
from app.shared.response import HttpResponse

router = APIRouter()


class NodeProgressRequest(BaseModel):
    """节点进度更新请求。"""
    node_id: str = Field(..., min_length=1, max_length=50)
    status: str | None = Field(default=None, pattern="^(wait|processing|success)$")
    progress: int | None = Field(default=None, ge=0, le=100)
    resource_id: int | None = Field(default=None, ge=1)


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


@router.post("/path-plan/node-progress")
async def update_node_progress(
    req: NodeProgressRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """更新学习节点进度。"""
    data = await path_usecases.path_service.update_node_progress(
        session,
        current_user.id,
        req.node_id,
        status=req.status,
        progress=req.progress,
        resource_id=req.resource_id,
    )
    if data is None:
        return HttpResponse.error(code=404, message="节点不存在或路径未初始化")
    return HttpResponse.success(data={
        "node_id": data.node_id,
        "status": data.status,
        "progress": data.progress,
        "updated_at": data.updated_at.isoformat(),
    })


@router.get("/path-plan/recommendations")
async def get_node_recommendations(
    top_k: int = Query(default=5, ge=1, le=10),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """获取基于用户画像的节点推荐。"""
    data = await path_usecases.path_service.get_node_recommendations(
        session,
        current_user.id,
        top_k=top_k,
    )
    return HttpResponse.success(data=data)
