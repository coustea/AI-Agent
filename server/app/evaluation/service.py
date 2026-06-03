"""Learning evaluation service."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.evaluation.request import LearningEventCreate
from app.evaluation.response import (
    DailyTimeEntry,
    EvaluationMetric,
    EvaluationSummaryResponse,
    HourlyDistributionEntry,
    LearningEventItem,
    LearningTimeStatsResponse,
)
from app.infra.logging import get_logger
from app.infra.models import LearningEvent

logger = get_logger(__name__)

HEARTBEAT_EVENT = "learning_heartbeat"
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
MAX_HEARTBEAT_SECONDS = 120
MAX_NON_HEARTBEAT_SECONDS = 30
STREAK_MIN_SECONDS = 300


@dataclass(frozen=True)
class MemoryUpdateSignal:
    content: str
    signal_type: str
    course: str | None = None
    knowledge_point: str | None = None
    confidence: float = 0.5


def derive_memory_signals(event: LearningEventCreate) -> list[MemoryUpdateSignal]:
    """Extract profile update signals from learning events."""
    topic = event.topic or event.course or "当前主题"
    signals: list[MemoryUpdateSignal] = []

    if event.event_type == "quiz_submitted" and event.score is not None and event.score < 65:
        signals.append(
            MemoryUpdateSignal(
                content=f"在“{topic}”练习中得分偏低（{event.score:.0f}分），需要加强针对性巩固。",
                signal_type="quiz_result",
                course=event.course,
                knowledge_point=event.topic,
                confidence=0.7,
            )
        )

    feedback = (event.feedback or "").strip()
    if event.event_type in {"path_feedback", "resource_feedback"} and feedback:
        if any(keyword in feedback for keyword in ("太难", "看不懂", "不会", "卡住", "薄弱", "错")):
            signals.append(
                MemoryUpdateSignal(
                    content=f"学习“{topic}”时用户反馈：{feedback}",
                    signal_type="self_report_weakness",
                    course=event.course,
                    knowledge_point=event.topic,
                    confidence=0.65,
                )
            )
        if any(keyword in feedback for keyword in ("喜欢", "希望", "更想", "图解", "案例", "代码", "视频")):
            signals.append(
                MemoryUpdateSignal(
                    content=f"学习资源偏好反馈：{feedback}",
                    signal_type="preference",
                    course=event.course,
                    knowledge_point=event.topic,
                    confidence=0.6,
                )
            )

    return signals[:2]


def build_summary_from_events(events: list[LearningEvent]) -> EvaluationSummaryResponse:
    score_values = [event.score for event in events if event.score is not None]
    average_score = round(sum(score_values) / len(score_values), 1) if score_values else None
    completed_resources = sum(1 for event in events if event.event_type == "resource_completed")
    viewed_resources = sum(1 for event in events if event.event_type == "resource_viewed")
    active_seconds = sum(
        _normalized_duration_for_summary(event)
        for event in events
        if event.event_type == HEARTBEAT_EVENT
    )

    weak_counter: Counter[str] = Counter()
    preferred_counter: Counter[str] = Counter()
    for event in events:
        topic = event.topic or event.course
        if event.event_type == "quiz_submitted" and event.score is not None and event.score < 65 and topic:
            weak_counter[topic] += 1
        feedback = event.feedback or ""
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

    recommendations: list[str] = []
    if average_score is not None and average_score < 70:
        recommendations.append("优先安排错题复盘和基础讲解资源，降低后续学习坡度。")
    if weak_counter:
        recommendations.append(f"下一轮资源生成应重点覆盖“{weak_counter.most_common(1)[0][0]}”。")
    if preferred_counter:
        recommendations.append(f"资源推送可提高“{preferred_counter.most_common(1)[0][0]}”占比。")
    if not recommendations:
        recommendations.append("继续按当前路径推进，并通过阶段测验积累更多评估信号。")

    metrics = [
        EvaluationMetric(label="平均测验分", value="暂无" if average_score is None else f"{average_score:.1f}"),
        EvaluationMetric(label="完成资源", value=str(completed_resources)),
        EvaluationMetric(label="活跃学习", value=f"{active_seconds // 60} 分钟"),
    ]

    return EvaluationSummaryResponse(
        event_count=len(events),
        average_score=average_score,
        completed_resources=completed_resources,
        viewed_resources=viewed_resources,
        active_minutes=active_seconds // 60,
        weak_topics=[item for item, _ in weak_counter.most_common(5)],
        preferred_resources=[item for item, _ in preferred_counter.most_common(5)],
        recommendations=recommendations,
        metrics=metrics,
        recent_events=[_to_item(event) for event in events[:10]],
    )


class EvaluationService:
    async def record_event(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        payload: LearningEventCreate,
    ) -> LearningEvent | None:
        normalized_duration = _normalize_duration(payload)
        if payload.event_type == HEARTBEAT_EVENT and normalized_duration is None:
            logger.info("[Evaluation] Ignore invalid heartbeat user=%s", user_id)
            return None

        event = LearningEvent(
            user_id=user_id,
            session_id=payload.session_id,
            resource_id=payload.resource_id,
            resource_item_id=payload.resource_item_id,
            path_id=payload.path_id,
            path_node_id=payload.path_node_id,
            node_id=payload.node_id,
            event_type=payload.event_type,
            course=payload.course,
            topic=payload.topic,
            score=payload.score,
            duration_seconds=normalized_duration,
            feedback=payload.feedback,
            metadata_json=payload.metadata or None,
        )
        session.add(event)
        await session.commit()
        await session.refresh(event)
        logger.info(
            "[Evaluation] event recorded user=%s type=%s event_id=%s duration=%s",
            user_id,
            payload.event_type,
            event.id,
            normalized_duration,
        )
        return event

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
        return build_summary_from_events(list(result.all()))

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
        query_start_utc = min(bounds["month_start_utc"], _local_day_start(now_local.date() - timedelta(days=window_days - 1)))

        stmt = (
            select(LearningEvent)
            .where(LearningEvent.user_id == user_id)
            .where(LearningEvent.event_type == HEARTBEAT_EVENT)
            .where(LearningEvent.created_at >= query_start_utc)
            .order_by(LearningEvent.created_at.asc())
        )
        result = await session.exec(stmt)
        recent_events = list(result.all())

        total_stmt = (
            select(LearningEvent)
            .where(LearningEvent.user_id == user_id)
            .where(LearningEvent.event_type == HEARTBEAT_EVENT)
            .order_by(LearningEvent.created_at.asc())
        )
        total_result = await session.exec(total_stmt)
        all_heartbeat_events = list(total_result.all())

        today_seconds = 0
        week_seconds = 0
        month_seconds = 0
        daily_map: dict[date, int] = defaultdict(int)
        hourly_map: dict[int, int] = defaultdict(int)
        context_map: dict[str, int] = defaultdict(int)

        for event in recent_events:
            duration = _normalized_duration_for_summary(event)
            if duration <= 0:
                continue

            created_local = _to_local(event.created_at)
            if created_local >= bounds["today_start_local"]:
                today_seconds += duration
            if created_local >= bounds["week_start_local"]:
                week_seconds += duration
            if created_local >= bounds["month_start_local"]:
                month_seconds += duration

            event_date = created_local.date()
            if event_date >= (now_local.date() - timedelta(days=window_days - 1)):
                daily_map[event_date] += duration
            hourly_map[created_local.hour] += duration

            context = ""
            if isinstance(event.metadata_json, dict):
                raw_context = event.metadata_json.get("context")
                context = str(raw_context).strip() if raw_context is not None else ""
            if context:
                context_map[context] += duration

        total_seconds = sum(_normalized_duration_for_summary(event) for event in all_heartbeat_events)
        streak_days = _compute_streak_days(all_heartbeat_events, now_local.date())

        return LearningTimeStatsResponse(
            today_seconds=today_seconds,
            week_seconds=week_seconds,
            month_seconds=month_seconds,
            total_seconds=total_seconds,
            streak_days=streak_days,
            daily_breakdown=_build_daily_breakdown(now_local.date(), window_days, daily_map),
            hourly_distribution=_build_hourly_distribution(hourly_map),
            context_breakdown=dict(sorted(context_map.items(), key=lambda item: item[1], reverse=True)),
        )


def _normalize_duration(payload: LearningEventCreate) -> int | None:
    raw = payload.duration_seconds
    if payload.event_type == HEARTBEAT_EVENT:
        if raw is None or raw <= 0:
            return None
        return min(raw, MAX_HEARTBEAT_SECONDS)

    if raw is None:
        return None
    if raw <= 0:
        return None
    return min(raw, MAX_NON_HEARTBEAT_SECONDS)


def _normalized_duration_for_summary(event: LearningEvent) -> int:
    raw = int(event.duration_seconds or 0)
    if raw <= 0:
        return 0
    cap = MAX_HEARTBEAT_SECONDS if event.event_type == HEARTBEAT_EVENT else MAX_NON_HEARTBEAT_SECONDS
    return min(raw, cap)


def _to_item(event: LearningEvent) -> LearningEventItem:
    return LearningEventItem(
        id=event.id or 0,
        event_type=event.event_type,
        resource_id=event.resource_id,
        resource_item_id=event.resource_item_id,
        path_id=event.path_id,
        path_node_id=event.path_node_id,
        node_id=event.node_id,
        course=event.course,
        topic=event.topic,
        score=event.score,
        duration_seconds=event.duration_seconds,
        feedback=event.feedback,
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


def _build_daily_breakdown(end_date: date, days: int, daily_map: dict[date, int]) -> list[DailyTimeEntry]:
    start_date = end_date - timedelta(days=days - 1)
    return [
        DailyTimeEntry(date=(start_date + timedelta(days=offset)).isoformat(), seconds=daily_map.get(start_date + timedelta(days=offset), 0))
        for offset in range(days)
    ]


def _build_hourly_distribution(hourly_map: dict[int, int]) -> list[HourlyDistributionEntry]:
    return [HourlyDistributionEntry(hour=hour, seconds=hourly_map.get(hour, 0)) for hour in range(24)]


def _compute_streak_days(events: list[LearningEvent], today_local: date) -> int:
    daily_totals: dict[date, int] = defaultdict(int)
    for event in events:
        if event.event_type != HEARTBEAT_EVENT:
            continue
        duration = _normalized_duration_for_summary(event)
        if duration <= 0:
            continue
        daily_totals[_to_local(event.created_at).date()] += duration

    streak = 0
    cursor = today_local
    while daily_totals.get(cursor, 0) >= STREAK_MIN_SECONDS:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


evaluation_service = EvaluationService()
