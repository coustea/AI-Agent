"""学习评估服务。"""

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
    EvaluationSummaryResponse,
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
    """记忆更新信号类型（遗留类型，仅用于类型检查兼容）。"""
    content: str
    signal_type: str
    dimension: str
    course: str | None = None
    knowledge_point: str | None = None
    confidence: float = 0.5


def derive_memory_signals(event: LearningEventCreate) -> list[MemoryUpdateSignal]:
    """从学习事件派生记忆信号（遗留方法，不再产生有效信号）。"""
    return []


def build_profile_update_payload(event: LearningEventCreate | LearningEvent) -> dict[str, Any] | None:
    """构建画像更新负载（遗留方法，始终返回 None）。"""
    return None


async def bg_apply_profile_update_from_learning_event(user_id: int, event_payload: dict[str, Any]) -> None:
    """后台任务：从学习事件更新用户画像（当前重构版本不执行更新）。"""
    logger.debug(
        "[Evaluation] skip profile update for learning event: user_id=%s event_type=%s",
        user_id,
        event_payload.get("event_type"),
    )


def build_summary_from_events(events: list[LearningEvent]) -> EvaluationSummaryResponse:
    """从学习事件列表构建评估摘要（平均分、薄弱点、推荐等）。"""
    score_values = [event.score for event in events if event.score is not None]
    average_score = round(sum(score_values) / len(score_values), 1) if score_values else None
    completed_resources = sum(1 for event in events if event.event_type == "resource_completed")
    viewed_resources = sum(1 for event in events if event.event_type == "resource_viewed")

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
        recommendations.append(f"下一轮资源生成应重点覆盖「{weak_counter.most_common(1)[0][0]}」。")
    if preferred_counter:
        recommendations.append(f"资源推送可提高「{preferred_counter.most_common(1)[0][0]}」占比。")
    if not recommendations:
        recommendations.append("继续按当前路径推进，并通过阶段测验积累更多评估信号。")

    return EvaluationSummaryResponse(
        event_count=len(events),
        average_score=average_score,
        completed_resources=completed_resources,
        viewed_resources=viewed_resources,
        weak_topics=[item for item, _ in weak_counter.most_common(5)],
        preferred_resources=[item for item, _ in preferred_counter.most_common(5)],
        recommendations=recommendations,
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
        """获取评估摘要 — 从最近学习事件构建。"""
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
            context_breakdown=dict(sorted(context_map.items(), key=lambda item: item[1], reverse=True)),
        )


def _parse_iso_datetime(value: str) -> datetime:
    """解析 ISO8601 格式日期时间字符串。"""
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _to_item(event: LearningEvent) -> LearningEventItem:
    """将 LearningEvent 模型转换为响应项 — 仅返回前端展示所需字段。"""
    return LearningEventItem(
        id=event.id or 0,
        event_type=event.event_type,
        course=event.course,
        topic=event.topic,
        feedback=event.feedback,
        created_at=event.created_at,
    )


def _to_local(value: datetime) -> datetime:
    """将 UTC 时间转换为上海时区。"""
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(SHANGHAI_TZ)


def _local_day_start(day: date) -> datetime:
    """获取指定日期的上海时区零点（转换为 UTC）。"""
    return datetime.combine(day, time.min, tzinfo=SHANGHAI_TZ).astimezone(UTC)


def _get_time_boundaries(now_local: datetime) -> dict[str, datetime]:
    """计算今日/本周/本月的起止时间（上海时区和 UTC）。"""
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
    """构建每日学习时长分布列表。"""
    start_date = end_date - timedelta(days=days - 1)
    return [
        DailyTimeEntry(date=(start_date + timedelta(days=offset)).isoformat(), seconds=daily_map.get(start_date + timedelta(days=offset), 0))
        for offset in range(days)
    ]



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
