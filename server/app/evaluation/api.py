"""Learning evaluation HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import get_current_user
from app.evaluation.schemas import LearningEventCreate
from app.evaluation.service import evaluation_service
from app.infra.database import get_session
from app.infra.models import User
from app.shared.response import HttpResponse

router = APIRouter()


@router.post("/evaluation/events")
async def record_learning_event(
    payload: LearningEventCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    event = await evaluation_service.record_event(
        session,
        user_id=current_user.id,
        payload=payload,
    )
    return HttpResponse.success(data={"id": event.id})


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

