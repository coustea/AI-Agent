"""学习评估 HTTP 路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import get_current_user, get_current_user_flexible
from app.evaluation.schemas import LearningEventCreate, LearningSessionCreate
from app.evaluation.service import evaluation_service
from app.infra.database import get_session
from app.infra.logging import get_logger
from app.infra.models import User
from app.infra.response import HttpResponse

router = APIRouter()
logger = get_logger(__name__)


@router.post("/evaluation/events")
async def record_learning_event(
    payload: LearningEventCreate,
    current_user: User = Depends(get_current_user_flexible),
    session: AsyncSession = Depends(get_session),
):
    """记录学习事件 — 资源浏览/完成/测验/对话/资源生成/路径节点/可视化运行等。"""
    event = await evaluation_service.record_event(
        session,
        user_id=current_user.id,
        payload=payload,
    )
    logger.info(
        "[EvalAPI] event recorded: user_id=%s event_type=%s event_id=%s",
        current_user.id,
        payload.event_type,
        event.id,
    )
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
        "[EvalAPI] session recorded: user_id=%s page=%s duration=%ss",
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
    """获取评估摘要 — 平均分、薄弱知识点、推荐等。"""
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
    """获取学习时长统计 — 今日/本周/本月/连续天数等。"""
    stats = await evaluation_service.get_time_stats(
        session,
        user_id=current_user.id,
        days=days,
    )
    return HttpResponse.success(data=stats)