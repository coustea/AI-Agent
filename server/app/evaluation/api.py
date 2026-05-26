"""Learning evaluation HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import get_current_user, get_current_user_flexible
from app.evaluation.schemas import LearningEventCreate
from app.evaluation.service import evaluation_service
from app.infra.database import get_session
from app.infra.models import User
from app.infra.response import HttpResponse

router = APIRouter()


@router.post("/evaluation/events")
async def record_learning_event(
    payload: LearningEventCreate,
    current_user: User = Depends(get_current_user_flexible),
    session: AsyncSession = Depends(get_session),
):
    event = await evaluation_service.record_event(
        session,
        user_id=current_user.id,
        payload=payload,
    )
    return HttpResponse.success(data={"id": event.id if event else None})


@router.get("/evaluation/summary")
async def get_evaluation_summary(
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    summary = await evaluation_service.get_summary(
        session,
        user_id=current_user.id,
        limit=limit,
    )
    return HttpResponse.success(data=summary)


@router.get("/evaluation/time-stats")
async def get_learning_time_stats(
    days: int = Query(default=30, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    stats = await evaluation_service.get_time_stats(
        session,
        user_id=current_user.id,
        days=days,
    )
    return HttpResponse.success(data=stats)

