"""Learning evaluation service."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.evaluation.request import LearningEventCreate, LearningSessionCreate
from app.evaluation.response import (
    DailyTimeEntry,
    EvaluationMetric,
    EvaluationSummaryResponse,
    HourlyDistributionEntry,
    LearningEventItem,
    LearningTimeStatsResponse,
)
from app.infra.logging import get_logger
from app.infra.models import LearningEvent, LearningSession
from app.config import STREAK_MIN_SECONDS

logger = get_logger(__name__)

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")  # 前端时区：上海（UTC+8）


@dataclass(frozen=True)
class MemoryUpdateSignal:
    """Legacy signal type — kept for type-checking compatibility only."""
    content: str
    signal_type: str
    dimension: str
    course: str | None = None
    knowledge_point: str | None = None
    confidence: float = 0.5


def derive_memory_signals(event: LearningEventCreate) -> list[MemoryUpdateSignal]:
    """Legacy helper — no longer produces actionable signals."""
    return []


def build_profile_update_payload(event: LearningEventCreate | LearningEvent) -> dict[str, Any] | None:
    """Legacy helper — always returns None (no profile update)."""
    return None


async def bg_apply_profile_update_from_learning_event(user_id: int, event_payload: dict[str, Any]) -> None:
    """Profile V2 does not update from generic learning events in this refactor."""
    logger.debug(
        "[Evaluation] skip profile update for learning event: user_id=%s event_type=%s",
        user_id,
        event_payload.get("event_type"),
    )


def build_summary_from_events(events: list[LearningEvent], active_minutes: int = 0) -> EvaluationSummaryResponse:
    """从学习事件列表构建评估摘要（平均分、薄弱点、推荐等）。"""
    score_values = [event.score for event in events if event.score is not None]  # 提取所有有分数的事件
    average_score = round(sum(score_values) / len(score_values), 1) if score_values else None  # 计算平均分
    completed_resources = sum(1 for event in events if event.event_type == "resource_completed")  # 已完成资源数
    viewed_resources = sum(1 for event in events if event.event_type == "resource_viewed")  # 已浏览资源数

    weak_counter: Counter[str] = Counter()  # 薄弱知识点计数器
    preferred_counter: Counter[str] = Counter()  # 资源偏好计数器
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

    recommendations: list[str] = []  # 优化建议列表
    if average_score is not None and average_score < 70:
        recommendations.append("优先安排错题复盘和基础讲解资源，降低后续学习坡度。")  # 低分建议
    if weak_counter:
        recommendations.append(f"下一轮资源生成应重点覆盖「{weak_counter.most_common(1)[0][0]}」。")  # 薄弱点建议
    if preferred_counter:
        recommendations.append(f"资源推送可提高「{preferred_counter.most_common(1)[0][0]}」占比。")  # 偏好建议
    if not recommendations:
        recommendations.append("继续按当前路径推进，并通过阶段测验积累更多评估信号。")  # 默认建议

    metrics = [  # 构建评估指标卡片列表
        EvaluationMetric(label="平均测验分", value="暂无" if average_score is None else f"{average_score:.1f}"),
        EvaluationMetric(label="完成资源", value=str(completed_resources)),
        EvaluationMetric(label="活跃学习", value=f"{active_minutes} 分钟"),
    ]

    return EvaluationSummaryResponse(
        event_count=len(events),
        average_score=average_score,
        completed_resources=completed_resources,
        viewed_resources=viewed_resources,
        active_minutes=active_minutes,
        weak_topics=[item for item, _ in weak_counter.most_common(5)],
        preferred_resources=[item for item, _ in preferred_counter.most_common(5)],
        recommendations=recommendations,
        metrics=metrics,
        recent_events=[_to_item(event) for event in events[:10]],
    )


class EvaluationService:
    """评估服务 — 学习事件记录、会话记录、摘要生成。"""

    async def record_event(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        payload: LearningEventCreate,
    ) -> LearningEvent:
        """记录一条学习事件（资源浏览/完成/测验提交/反馈等）。"""
        event = LearningEvent(  # 构建学习事件模型
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
            feedback=payload.feedback,
            metadata_json=payload.metadata or None,
        )
        session.add(event)
        await session.commit()
        await session.refresh(event)
        logger.info(
            "[Evaluation] event recorded user=%s type=%s event_id=%s",
            user_id,
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
        """记录一次学习会话（前端离开页面时上报实际活跃时长）。"""
        started_at = _parse_iso_datetime(payload.started_at)  # 解析开始时间
        ended_at = _parse_iso_datetime(payload.ended_at)  # 解析结束时间
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
            metadata_json=payload.metadata or None,
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

        active_minutes = await self._get_active_minutes(session, user_id=user_id)
        return build_summary_from_events(events, active_minutes=active_minutes)

    async def _get_active_minutes(self, session: AsyncSession, *, user_id: int) -> int:
        stmt = select(LearningSession).where(LearningSession.user_id == user_id)
        result = await session.exec(stmt)
        total_seconds = sum(s.duration_seconds or 0 for s in result.all())
        return total_seconds // 60

    async def get_time_stats(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        days: int = 30,
    ) -> LearningTimeStatsResponse:
        """获取学习时长统计 — 今日/本周/本月/连续天数/每日分布/小时分布。"""
        window_days = max(1, min(days, 90))  # 限制查询窗口在 1-90 天
        now_local = datetime.now(SHANGHAI_TZ)  # 当前上海时间
        bounds = _get_time_boundaries(now_local)  # 计算今日/本周/本月的起止时间
        query_start_utc = min(bounds["month_start_utc"], _local_day_start(now_local.date() - timedelta(days=window_days - 1)))  # 查询起始时间（取月份起点和窗口起点的较早者）

        stmt = (  # 查询指定窗口内的学习会话
            select(LearningSession)
            .where(LearningSession.user_id == user_id)
            .where(LearningSession.started_at >= query_start_utc)
            .order_by(LearningSession.started_at.asc())
        )
        result = await session.exec(stmt)
        recent_sessions = list(result.all())

        total_stmt = (
            select(LearningSession)
            .where(LearningSession.user_id == user_id)
            .order_by(LearningSession.started_at.asc())
        )
        total_result = await session.exec(total_stmt)
        all_sessions = list(total_result.all())

        today_seconds = 0
        week_seconds = 0
        month_seconds = 0
        daily_map: dict[date, int] = defaultdict(int)
        hourly_map: dict[int, int] = defaultdict(int)
        context_map: dict[str, int] = defaultdict(int)

        for sess in recent_sessions:
            duration = sess.duration_seconds or 0
            if duration <= 0:
                continue

            created_local = _to_local(sess.started_at)
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

            context = sess.source_page
            if context:
                context_map[context] += duration

        total_seconds = sum(s.duration_seconds or 0 for s in all_sessions)
        streak_days = _compute_streak_days(all_sessions, now_local.date())

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


def _parse_iso_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


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


def _compute_streak_days(sessions: list[LearningSession], today_local: date) -> int:
    """计算连续学习天数 — 从今天向前回溯，每天至少 STREAK_MIN_SECONDS 秒。"""
    daily_totals: dict[date, int] = defaultdict(int)  # 按日期汇总学习时长
    for sess in sessions:
        duration = sess.duration_seconds or 0
        if duration <= 0:
            continue
        daily_totals[_to_local(sess.started_at).date()] += duration  # 转换为上海时区后按日汇总

    streak = 0  # 连续天数计数器
    cursor = today_local  # 从今天开始向前回溯
    while daily_totals.get(cursor, 0) >= STREAK_MIN_SECONDS:  # 当天学习时长 >= 5 分钟
        streak += 1
        cursor -= timedelta(days=1)
    return streak


evaluation_service = EvaluationService()
