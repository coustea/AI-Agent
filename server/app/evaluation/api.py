"""学习评估 HTTP 路由。

包含首页仪表盘相关端点（从 dashboard 模块迁移）。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import get_current_user, get_current_user_flexible
from app.evaluation.schemas import LearningEventCreate, LearningSessionCreate
from app.evaluation.service import evaluation_service
from app.infra.database import get_session
from app.infra.logging import get_logger
from app.infra.models import LearningSession, User
from app.infra.response import HttpResponse

router = APIRouter()
logger = get_logger(__name__)


# 记录学习事件（资源浏览/完成/测验/对话/生成/路径节点/可视化运行等）
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
    # 记录学习事件后写审计日志
    logger.info(
        "[EvalAPI] 事件已记录: user_id=%s event_type=%s event_id=%s",
        current_user.id,
        payload.event_type,
        event.id,
    )
    return HttpResponse.success(data={"id": event.id})


# 记录一次学习会话（前端离开学习页面时上报）
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
    # 记录学习会话后写审计日志
    logger.info(
        "[EvalAPI] 学习会话已记录: user_id=%s page=%s duration=%ss",
        current_user.id,
        payload.source_page,
        payload.duration_seconds,
    )
    return HttpResponse.success(data={"id": learning_session.id})


# 获取评估摘要（平均分、薄弱知识点、推荐等）
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


# 获取学习时长统计（今日/本周/本月/连续天数等）
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


# ---------------------------------------------------------------------------
# 仪表盘端点（从 dashboard 模块迁移）
# ---------------------------------------------------------------------------


# 获取学习统计（本周活跃天数）
@router.get("/dashboard/study-stats")
async def get_study_stats(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """获取学习统计 — 本周活跃天数。"""
    # 以本周一 0 点作为统计起点
    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    # 统计本周内出现的学习会话 distinct 天数
    weekly_days = (await session.exec(
        select(func.count(func.distinct(func.date(col(LearningSession.started_at)))))
        .where(LearningSession.user_id == current_user.id, LearningSession.started_at >= week_start)
    )).one() or 0

    return HttpResponse.success(data={"weekly_days": int(weekly_days)})