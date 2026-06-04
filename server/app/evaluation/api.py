"""Learning evaluation HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import get_current_user, get_current_user_flexible
from app.evaluation.schemas import LearningEventCreate, LearningSessionCreate
from app.evaluation.service import bg_apply_profile_update_from_learning_event, evaluation_service
from app.infra.database import get_session
from app.infra.logging import get_logger
from app.infra.models import User
from app.infra.response import HttpResponse

router = APIRouter()
logger = get_logger(__name__)


@router.post("/evaluation/events")
async def record_learning_event(
    payload: LearningEventCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user_flexible),
    session: AsyncSession = Depends(get_session),
):
    event = await evaluation_service.record_event(
        session,
        user_id=current_user.id,
        payload=payload,
    )
    background_tasks.add_task(
        bg_apply_profile_update_from_learning_event,
        current_user.id,
        {
            "event_type": event.event_type,
            "session_id": event.session_id,
            "resource_id": event.resource_id,
            "resource_item_id": event.resource_item_id,
            "path_id": event.path_id,
            "path_node_id": event.path_node_id,
            "node_id": event.node_id,
            "course": event.course,
            "topic": event.topic,
            "score": event.score,
            "feedback": event.feedback,
            "metadata": event.metadata_json or {},
        },
    )
    logger.info("[EvalAPI] 学习事件记录: user_id=%s event_type=%s", current_user.id, payload.event_type)
    return HttpResponse.success(data={"id": event.id})


@router.post("/evaluation/sessions")
async def record_learning_session(
    payload: LearningSessionCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """记录一次学习会话（前端离开学习页面时上报）。"""
    learning_session = await evaluation_service.record_session(
        session,
        user_id=current_user.id,
        payload=payload,
    )
    logger.info(
        "[EvalAPI] 学习会话记录: user_id=%s page=%s duration=%ss",
        current_user.id,
        payload.source_page,
        payload.duration_seconds,
    )
    return HttpResponse.success(data={"id": learning_session.id})


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
    """学习时长统计 — 从 LearningSession 表聚合。"""
    stats = await evaluation_service.get_time_stats(
        session,
        user_id=current_user.id,
        days=days,
    )
    return HttpResponse.success(data=stats)