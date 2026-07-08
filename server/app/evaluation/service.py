"""学习评估服务 — 学习事件采集与时间窗口聚合。

事件来源由各业务模块的 ``events.py`` 调用 ``EvaluationService.record_event`` 埋点。
本模块不关心业务语义，只负责持久化和按时间窗口聚合统计。

聚合策略：纯 SQL，零 LLM 调用。学习者画像评分不在此处触发（画像更新由
``app.profile.service.infer_profile_from_digest`` 基于周概要缓冲驱动）。
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.evaluation.event_types import (
    RESOURCE_COMPLETED,
    RESOURCE_VIEWED,
    SCORED_EVENT_TYPES,
)
from app.evaluation.request import LearningEventCreate, LearningSessionCreate
from app.evaluation.response import (
    DailyTimeEntry,
    EvaluationSummaryResponse,
    LearningEventItem,
    LearningTimeStatsResponse,
)
from app.config import STREAK_MIN_SECONDS
from app.infra.logging import get_logger
from app.infra.models import LearningEvent, LearningSession

logger = get_logger(__name__)

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
WEAK_SCORE_THRESHOLD = 65.0


def build_summary_from_events(
    events: list[LearningEvent], active_minutes: int = 0
) -> EvaluationSummaryResponse:
    """从学习事件列表构建评估摘要（平均分、薄弱点、推荐等）。"""
    score_values = [e.score for e in events if e.score is not None]
    average_score = round(sum(score_values) / len(score_values), 1) if score_values else None

    completed_resources = sum(1 for e in events if e.event_type == RESOURCE_COMPLETED)
    viewed_resources = sum(1 for e in events if e.event_type == RESOURCE_VIEWED)

    weak_counter: Counter[str] = Counter()
    preferred_counter: Counter[str] = Counter()
    for event in events:
        topic = event.topic or event.course
        is_scored_quiz = event.event_type in SCORED_EVENT_TYPES
        if is_scored_quiz and event.score is not None and event.score < WEAK_SCORE_THRESHOLD and topic:
            weak_counter[topic] += 1
        meta = event.event_metadata or {}
        feedback = meta.get("feedback") or ""
        if any(keyword in feedback for keyword in ("太难", "看不懂", "不会", "卡住", "薄弱", "错")) and topic:
            weak_counter[topic] += 1
        for keyword, label in {
            "图解": "图解材料",
            "案例": "案例讲解",
            "代码": "代码实操",
            "视频": "视频讲解",
            "题": "练习题库",
        }.items():
            if keyword in feedback:
                preferred_counter[label] += 1

    recommendations = _build_recommendations(average_score, weak_counter, preferred_counter)

    return EvaluationSummaryResponse(
        event_count=len(events),
        average_score=average_score,
        completed_resources=completed_resources,
        viewed_resources=viewed_resources,
        active_minutes=active_minutes,
        weak_topics=[item for item, _ in weak_counter.most_common(5)],
        preferred_resources=[item for item, _ in preferred_counter.most_common(5)],
        recommendations=recommendations,
        recent_events=[_to_item(e) for e in events[:10]],
    )


def _build_recommendations(
    average_score: float | None,
    weak_counter: Counter[str],
    preferred_counter: Counter[str],
) -> list[str]:
    recommendations: list[str] = []
    if average_score is not None and average_score < 70:
        recommendations.append("优先安排错题复盘和基础讲解资源，降低后续学习坡度。")
    if weak_counter:
        recommendations.append(f"下一轮资源生成应重点覆盖「{weak_counter.most_common(1)[0][0]}」。")
    if preferred_counter:
        recommendations.append(f"资源推送可提高「{preferred_counter.most_common(1)[0][0]}」占比。")
    if not recommendations:
        recommendations.append("继续按当前路径推进，并通过阶段测验积累更多评估信号。")
    return recommendations


class EvaluationService:
    """评估服务 — 学习事件记录、会话记录、摘要生成。"""

    async def record_event(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        payload: LearningEventCreate,
    ) -> LearningEvent:
        event = LearningEvent(
            user_id=user_id,
            module=payload.module,
            entity_id=payload.entity_id,
            event_type=payload.event_type,
            course=payload.course,
            topic=payload.topic,
            score=payload.score,
            event_metadata=payload.event_metadata or None,
        )
        session.add(event)
        await session.commit()
        await session.refresh(event)
        logger.info(
            "[Evaluation] 事件已记录: user=%s module=%s type=%s event_id=%s",
            user_id,
            payload.module,
            payload.event_type,
            event.id,
        )
        return event

    async def record_session(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        payload: LearningSessionCreate,
    ) -> LearningSession:
        started_at = _parse_iso_datetime(payload.started_at)
        ended_at = _parse_iso_datetime(payload.ended_at)

        metadata = payload.event_metadata or {}
        
        resource_id = metadata.get("resource_id")
        if resource_id is not None:
            try:
                resource_id = int(resource_id)
            except (ValueError, TypeError):
                resource_id = None

        path_id = metadata.get("path_id")
        if path_id is not None:
            try:
                path_id = int(path_id)
            except (ValueError, TypeError):
                path_id = None

        path_node_id = metadata.get("path_node_id")
        if path_node_id is not None:
            try:
                path_node_id = int(path_node_id)
            except (ValueError, TypeError):
                path_node_id = None

        node_id = metadata.get("node_id")
        if node_id is not None:
            node_id = str(node_id)

        learning_session = LearningSession(
            user_id=user_id,
            source_page=payload.source_page,
            started_at=started_at,
            ended_at=ended_at,
            duration_seconds=payload.duration_seconds,
            resource_id=resource_id,
            path_id=path_id,
            path_node_id=path_node_id,
            node_id=node_id,
            course=payload.course,
            topic=payload.topic,
            metadata_json=payload.event_metadata or None,
        )
        session.add(learning_session)
        await session.commit()
        await session.refresh(learning_session)
        logger.info(
            "[Evaluation] 学习会话已记录: user=%s page=%s duration=%ss session_id=%s",
            user_id,
            payload.source_page,
            payload.duration_seconds,
            learning_session.id,
        )
        return learning_session

    async def get_summary(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        limit: int = 100,
    ) -> EvaluationSummaryResponse:
        stmt = (
            select(LearningEvent)
            .where(LearningEvent.user_id == user_id)
            .order_by(LearningEvent.created_at.desc())
            .limit(limit)
        )
        result = await session.exec(stmt)
        events = list(result.all())
        active_minutes = await self._get_active_minutes(session, user_id=user_id)
        return build_summary_from_events(events, active_minutes=active_minutes)

    async def _get_active_minutes(self, session: AsyncSession, *, user_id: int) -> int:
        """获取用户总活跃分钟数。"""
        stmt = select(LearningSession.duration_seconds).where(LearningSession.user_id == user_id)
        result = await session.exec(stmt)
        total_seconds = sum(s for s in result.all() if s is not None)
        return int(total_seconds // 60) if total_seconds else 0

    async def get_time_stats(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        days: int = 30,
    ) -> LearningTimeStatsResponse:
        window_days = max(1, min(days, 90))
        now_local = datetime.now(SHANGHAI_TZ)
        bounds = _get_time_boundaries(now_local)
        query_start_utc = min(
            bounds["month_start_utc"],
            _local_day_start(now_local.date() - timedelta(days=window_days - 1)),
        )

        recent_stmt = (
            select(LearningSession)
            .where(LearningSession.user_id == user_id)
            .where(LearningSession.started_at >= query_start_utc)
            .order_by(LearningSession.started_at.asc())
        )
        recent_result = await session.exec(recent_stmt)
        recent_sessions = list(recent_result.all())

        total_stmt = (
            select(LearningSession)
            .where(LearningSession.user_id == user_id)
            .order_by(LearningSession.started_at.asc())
        )
        total_result = await session.exec(total_stmt)
        all_sessions = list(total_result.all())

        today_seconds = 0
        daily_map: dict[date, int] = defaultdict(int)
        context_map: dict[str, int] = defaultdict(int)

        for sess in recent_sessions:
            duration = sess.duration_seconds or 0
            if duration <= 0:
                continue
            created_local = _to_local(sess.started_at)
            if created_local >= bounds["today_start_local"]:
                today_seconds += duration
            event_date = created_local.date()
            if event_date >= (now_local.date() - timedelta(days=window_days - 1)):
                daily_map[event_date] += duration
            context = sess.source_page
            if context:
                context_map[context] += duration

        total_seconds = sum(s.duration_seconds or 0 for s in all_sessions)
        streak_days = _compute_streak_days(all_sessions, now_local.date())

        return LearningTimeStatsResponse(
            today_seconds=today_seconds,
            total_seconds=total_seconds,
            streak_days=streak_days,
            daily_breakdown=_build_daily_breakdown(now_local.date(), window_days, daily_map),
            context_breakdown=dict(
                sorted(context_map.items(), key=lambda item: item[1], reverse=True)
            ),
        )


def _parse_iso_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _to_item(event: LearningEvent) -> LearningEventItem:
    return LearningEventItem(
        id=event.id or 0,
        module=event.module or "mentor",
        entity_id=event.entity_id,
        event_type=event.event_type,
        course=event.course,
        topic=event.topic,
        score=event.score,
        event_metadata=event.event_metadata or {},
        created_at=event.created_at,
    )


def _to_local(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(SHANGHAI_TZ)


def _local_day_start(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=SHANGHAI_TZ).astimezone(UTC)


def _get_time_boundaries(now_local: datetime) -> dict[str, datetime]:
    today_start_local = datetime.combine(now_local.date(), time.min, tzinfo=SHANGHAI_TZ)
    week_start_date = now_local.date() - timedelta(days=now_local.weekday())
    week_start_local = datetime.combine(week_start_date, time.min, tzinfo=SHANGHAI_TZ)
    month_start_date = now_local.date().replace(day=1)
    month_start_local = datetime.combine(month_start_date, time.min, tzinfo=SHANGHAI_TZ)
    return {
        "today_start_local": today_start_local,
        "week_start_local": week_start_local,
        "month_start_local": month_start_local,
        "today_start_utc": today_start_local.astimezone(UTC),
        "week_start_utc": week_start_local.astimezone(UTC),
        "month_start_utc": month_start_local.astimezone(UTC),
    }


def _build_daily_breakdown(
    end_date: date, days: int, daily_map: dict[date, int]
) -> list[DailyTimeEntry]:
    start_date = end_date - timedelta(days=days - 1)
    return [
        DailyTimeEntry(
            date=(start_date + timedelta(days=offset)).isoformat(),
            seconds=daily_map.get(start_date + timedelta(days=offset), 0),
        )
        for offset in range(days)
    ]


def _compute_streak_days(
    sessions: list[LearningSession], today_local: date
) -> int:
    daily_totals: dict[date, int] = defaultdict(int)
    for sess in sessions:
        duration = sess.duration_seconds or 0
        if duration <= 0:
            continue
        daily_totals[_to_local(sess.started_at).date()] += duration

    streak = 0
    cursor = today_local
    while daily_totals.get(cursor, 0) >= STREAK_MIN_SECONDS:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


evaluation_service = EvaluationService()
