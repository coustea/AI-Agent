"""学习评估服务 — 学习事件采集与时间窗口聚合。

事件来源由各业务模块的 ``events.py`` 调用 ``EvaluationService.record_event`` 埋点。
本模块不关心业务语义，只负责持久化和按时间窗口聚合统计。

聚合策略：纯 SQL，零 LLM 调用。画像评分时由 ``score_profile`` 调用
``aggregate_period_stats`` 拿到结构化数值后注入 prompt。
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.evaluation.event_types import (
    MODULE_CHAT,
    MODULE_PATH,
    MODULE_QUIZ,
    MODULE_RESOURCE,
    MODULE_VISUALIZER,
    PATH_QUIZ_ANSWERED,
    QUIZ_SUBMITTED,
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


async def aggregate_period_stats(
    session: AsyncSession,
    user_id: int,
    start_utc: datetime,
    end_utc: datetime,
) -> dict[str, Any]:
    """聚合指定 UTC 时间窗口内的学习统计 — 纯 SQL，无 LLM 调用。

    返回 JSON 可序列化的统计字典，可直接注入画像评分 prompt。

    Args:
        session: 异步数据库会话。
        user_id: 用户 ID。
        start_utc: 窗口起点（UTC，含）。
        end_utc: 窗口终点（UTC，不含）。

    Returns:
        统计字典，包含按 module 分桶的计数、平均分、薄弱知识点等。
    """
    counts_by_module = await _query_event_counts(session, user_id, start_utc, end_utc)
    score_stats = await _query_score_stats(session, user_id, start_utc, end_utc)
    weak_topics = await _query_weak_topics(session, user_id, start_utc, end_utc)

    total_events = sum(counts_by_module.values())

    return {
        "window_start": start_utc.isoformat(),
        "window_end": end_utc.isoformat(),
        "total_events": total_events,
        "by_module": counts_by_module,
        "chat_dialogues": counts_by_module.get(MODULE_CHAT, 0),
        "resources": counts_by_module.get(MODULE_RESOURCE, 0),
        "path_events": counts_by_module.get(MODULE_PATH, 0),
        "quizzes": counts_by_module.get(MODULE_QUIZ, 0),
        "visualizer_runs": counts_by_module.get(MODULE_VISUALIZER, 0),
        "average_score": score_stats.get("average_score"),
        "quiz_average_score": score_stats.get("quiz_average_score"),
        "path_quiz_average_score": score_stats.get("path_quiz_average_score"),
        "weak_topics": weak_topics,
    }


async def _query_event_counts(
    session: AsyncSession,
    user_id: int,
    start_utc: datetime,
    end_utc: datetime,
) -> dict[str, int]:
    stmt = (
        select(LearningEvent.module, func.count().label("cnt"))
        .where(LearningEvent.user_id == user_id)
        .where(LearningEvent.created_at >= start_utc)
        .where(LearningEvent.created_at < end_utc)
        .group_by(LearningEvent.module)
    )
    result = await session.exec(stmt)
    return {row.module: int(row.cnt) for row in result.all()}


async def _query_score_stats(
    session: AsyncSession,
    user_id: int,
    start_utc: datetime,
    end_utc: datetime,
) -> dict[str, float | None]:
    base_filter = (
        LearningEvent.user_id == user_id,
        LearningEvent.created_at >= start_utc,
        LearningEvent.created_at < end_utc,
        LearningEvent.score.is_not(None),
    )

    overall_avg = await _avg_score(session, base_filter)
    quiz_avg = await _avg_score(
        session,
        base_filter + (LearningEvent.event_type == QUIZ_SUBMITTED,),
    )
    path_quiz_avg = await _avg_score(
        session,
        base_filter + (LearningEvent.event_type == PATH_QUIZ_ANSWERED,),
    )

    return {
        "average_score": overall_avg,
        "quiz_average_score": quiz_avg,
        "path_quiz_average_score": path_quiz_avg,
    }


async def _avg_score(
    session: AsyncSession, filters: tuple[Any, ...]
) -> float | None:
    stmt = select(func.avg(LearningEvent.score)).where(*filters)
    result = await session.exec(stmt)
    value = result.first()
    if value is None:
        return None
    return round(float(value), 1)


async def _query_weak_topics(
    session: AsyncSession,
    user_id: int,
    start_utc: datetime,
    end_utc: datetime,
) -> list[str]:
    stmt = (
        select(LearningEvent.topic)
        .where(LearningEvent.user_id == user_id)
        .where(LearningEvent.created_at >= start_utc)
        .where(LearningEvent.created_at < end_utc)
        .where(LearningEvent.score.is_not(None))
        .where(LearningEvent.score < WEAK_SCORE_THRESHOLD)
        .where(LearningEvent.topic.is_not(None))
        .where(LearningEvent.event_type.in_(tuple(SCORED_EVENT_TYPES)))
        .distinct()
    )
    result = await session.exec(stmt)
    return [topic for topic in result.all() if topic]





def build_summary_from_events(events: list[LearningEvent]) -> EvaluationSummaryResponse:
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

    recommendations = _build_recommendations(average_score, weak_counter, preferred_counter)

    return EvaluationSummaryResponse(
        event_count=len(events),
        average_score=average_score,
        completed_resources=completed_resources,
        viewed_resources=viewed_resources,
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
            "[Evaluation] event recorded user=%s module=%s type=%s event_id=%s",
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
        learning_session = LearningSession(
            user_id=user_id,
            source_page=payload.source_page,
            started_at=started_at,
            ended_at=ended_at,
            duration_seconds=payload.duration_seconds,
            resource_id=payload.resource_id,
            path_id=payload.path_id,
            path_node_id=payload.path_node_id,
            node_id=payload.node_id,
            course=payload.course,
            topic=payload.topic,
            metadata_json=payload.event_metadata or None,
        )
        session.add(learning_session)
        await session.commit()
        await session.refresh(learning_session)
        logger.info(
            "[Evaluation] session recorded user=%s page=%s duration=%ss session_id=%s",
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
        return build_summary_from_events(events)

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
        module=event.module,
        entity_id=event.entity_id,
        event_type=event.event_type,
        course=event.course,
        topic=event.topic,
        score=event.score,
        event_metadata=event.event_metadata,
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
