"""学习评估服务 — 学习事件采集与时间窗口聚合。

事件来源由各业务模块的 ``events.py`` 调用 ``EvaluationService.record_event`` 埋点。
本模块不关心业务语义，只负责持久化和按时间窗口聚合统计。

聚合策略：纯 SQL，零 LLM 调用。学习者画像评分不在此处触发（画像更新由
``app.profile.service.infer_profile_from_digest`` 基于周概要缓冲驱动）。
"""

# 评估服务：学习事件采集、会话记录与时间窗口聚合（纯 SQL，无 LLM 调用）。
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, date, datetime, time, timedelta, timezone
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
from app.infra.models import LearningEvent, LearningSession, LearningAssessmentReport

logger = get_logger(__name__)

# 上海时区与判定为薄弱知识点的最低分数阈值
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
WEAK_SCORE_THRESHOLD = 65.0


# 从学习事件列表聚合出评估摘要（平均分、薄弱点、推荐、最近事件）
def build_summary_from_events(
    events: list[LearningEvent], active_minutes: int = 0
) -> EvaluationSummaryResponse:
    """从学习事件列表构建评估摘要（平均分、薄弱点、推荐等）。"""
    # 汇总所有带评分事件的分数并计算平均分
    score_values = [e.score for e in events if e.score is not None]
    average_score = round(sum(score_values) / len(score_values), 1) if score_values else None

    # 统计已完成与已浏览的资源数量
    completed_resources = sum(1 for e in events if e.event_type == RESOURCE_COMPLETED)
    viewed_resources = sum(1 for e in events if e.event_type == RESOURCE_VIEWED)

    # 初始化薄弱主题与偏好资源的计数器
    weak_counter: Counter[str] = Counter()
    preferred_counter: Counter[str] = Counter()
    # 遍历事件，统计薄弱主题与用户偏好的资源类型
    for event in events:
        topic = event.topic or event.course
        is_scored_quiz = event.event_type in SCORED_EVENT_TYPES
        # 评分类事件中低于阈值则记为薄弱主题
        if is_scored_quiz and event.score is not None and event.score < WEAK_SCORE_THRESHOLD and topic:
            weak_counter[topic] += 1
        meta = event.event_metadata or {}
        feedback = meta.get("feedback") or ""
        # 反馈文本含困难关键词则同样记为薄弱主题
        if any(keyword in feedback for keyword in ("太难", "看不懂", "不会", "卡住", "薄弱", "错")) and topic:
            weak_counter[topic] += 1
        # 根据反馈文本关键词统计用户偏好的资源类型
        for keyword, label in {
            "图解": "图解材料",
            "案例": "案例讲解",
            "代码": "代码实操",
            "视频": "视频讲解",
            "题": "练习题库",
        }.items():
            if keyword in feedback:
                preferred_counter[label] += 1

    # 根据平均分与统计结果生成个性化推荐
    recommendations = _build_recommendations(average_score, weak_counter, preferred_counter)

    # 组装并返回评估摘要响应
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


# 根据平均分、薄弱点与偏好生成推荐文案
def _build_recommendations(
    average_score: float | None,
    weak_counter: Counter[str],
    preferred_counter: Counter[str],
) -> list[str]:
    recommendations: list[str] = []
    # 平均分偏低时建议错题复盘与基础讲解
    if average_score is not None and average_score < 70:
        recommendations.append("优先安排错题复盘和基础讲解资源，降低后续学习坡度。")
    # 存在薄弱主题时建议重点覆盖
    if weak_counter:
        recommendations.append(f"下一轮资源生成应重点覆盖「{weak_counter.most_common(1)[0][0]}」。")
    # 存在偏好资源类型时建议提高占比
    if preferred_counter:
        recommendations.append(f"资源推送可提高「{preferred_counter.most_common(1)[0][0]}」占比。")
    # 无明确信号时给出通用推进建议
    if not recommendations:
        recommendations.append("继续按当前路径推进，并通过阶段测验积累更多评估信号。")
    return recommendations


class ConcurrencyError(Exception):
    """当用户已有正在生成的报告时抛出该异常。"""
    pass


# 评估服务类：学习事件记录、会话记录、摘要与时间统计
class EvaluationService:
    """评估服务 — 学习事件记录、会话记录、摘要生成。"""

    # 生成学习效果评估报告并只更新当前辅导策略
    async def generate_report(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        range_days: int,
    ) -> LearningAssessmentReport:
        if range_days not in (7, 14, 30):
            raise ValueError("range_days must be 7, 14, or 30")

        # 1. 原子创建 generating 报告并检测并发
        now_utc = datetime.now(timezone.utc)
        window_start = now_utc - timedelta(days=range_days)
        window_end = now_utc

        # 查询是否已有生成中报告
        existing_generating = await session.scalar(
            select(LearningAssessmentReport).where(
                LearningAssessmentReport.user_id == user_id,
                LearningAssessmentReport.status == "generating",
            )
        )
        if existing_generating is not None:
            raise ConcurrencyError("assessment_generation_in_progress")

        report = LearningAssessmentReport(
            user_id=user_id,
            range_days=range_days,
            window_start=window_start,
            window_end=window_end,
            status="generating",
            created_at=now_utc,
            updated_at=now_utc,
        )
        session.add(report)
        
        from sqlalchemy.exc import IntegrityError
        try:
            await session.commit()
            await session.refresh(report)
        except IntegrityError:
            await session.rollback()
            raise ConcurrencyError("assessment_generation_in_progress")

        # 2. 聚合事实快照并保存
        try:
            from app.evaluation.facts import build_assessment_facts
            facts_snapshot = await build_assessment_facts(
                session, user_id=user_id, window_start=window_start, window_end=window_end
            )
            report.facts_snapshot = facts_snapshot
            report.updated_at = datetime.now(timezone.utc)
            await session.commit()
        except Exception as e:
            # 聚合失败，修改报告状态
            report.status = "failed"
            report.failure_code = "facts_aggregation_failed"
            report.updated_at = datetime.now(timezone.utc)
            await session.commit()
            raise e

        # 3. 调用大模型生成报告与辅导策略
        try:
            from app.evaluation import reporting
            report_markdown, guidance_strategy = await reporting.generate(facts_snapshot)

            # 4. 在同一个事务中更新报告并写入用户画像策略字段
            report.status = "ready"
            report.report_markdown = report_markdown
            report.generated_at = datetime.now(timezone.utc)
            report.updated_at = datetime.now(timezone.utc)

            await self._update_guidance_strategy_only(
                session,
                user_id=user_id,
                strategy=guidance_strategy,
                report_id=report.id,
            )
            await session.commit()
            await session.refresh(report)
        except Exception as e:
            await session.rollback()
            report.status = "failed"
            report.failure_code = "llm_generation_failed"
            report.updated_at = datetime.now(timezone.utc)
            await session.commit()
            raise e

        return report

    async def _update_guidance_strategy_only(
        self, session: AsyncSession, *, user_id: int, strategy: dict[str, Any], report_id: int
    ) -> None:
        from app.infra.models import UserProfile
        profile = await session.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
        now = datetime.now(timezone.utc)
        if profile is None:
            profile = UserProfile(
                user_id=user_id,
                overall_score=0,
                scored_at=None,
                guidance_strategy=strategy,
                guidance_updated_at=now,
                last_assessment_report_id=report_id,
                created_at=now,
                updated_at=now,
            )
            session.add(profile)
        else:
            profile.guidance_strategy = strategy
            profile.guidance_updated_at = now
            profile.last_assessment_report_id = report_id
            profile.updated_at = now

    # 记录单条学习事件并落库（带幂等去重）
    async def record_event(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        payload: LearningEventCreate,
    ) -> tuple[LearningEvent, bool]:
        if payload.client_event_id:
            existing = await session.scalar(
                select(LearningEvent).where(
                    LearningEvent.user_id == user_id,
                    LearningEvent.client_event_id == payload.client_event_id,
                )
            )
            if existing is not None:
                return existing, True

        event = LearningEvent(
            user_id=user_id,
            module=payload.module,
            entity_id=payload.entity_id,
            event_type=payload.event_type,
            course=payload.course,
            topic=payload.topic,
            score=payload.score,
            event_metadata=payload.event_metadata or None,
            client_event_id=payload.client_event_id,
            occurred_at=payload.occurred_at or datetime.now(timezone.utc),
        )
        try:
            session.add(event)
            await session.commit()
            await session.refresh(event)
        except Exception as e:
            await session.rollback()
            if payload.client_event_id:
                existing = await session.scalar(
                    select(LearningEvent).where(
                        LearningEvent.user_id == user_id,
                        LearningEvent.client_event_id == payload.client_event_id,
                    )
                )
                if existing is not None:
                    return existing, True
            raise e

        logger.info(
            "[Evaluation] 事件已记录: user=%s module=%s type=%s event_id=%s",
            user_id,
            payload.module,
            payload.event_type,
            event.id,
        )
        return event, False

    # 记录一次学习会话（带幂等去重）
    async def record_session(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        payload: LearningSessionCreate,
    ) -> tuple[LearningSession, bool]:
        if payload.client_session_id:
            existing = await session.scalar(
                select(LearningSession).where(
                    LearningSession.user_id == user_id,
                    LearningSession.client_session_id == payload.client_session_id,
                )
            )
            if existing is not None:
                return existing, True

        started_at = payload.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        ended_at = payload.ended_at
        if ended_at.tzinfo is None:
            ended_at = ended_at.replace(tzinfo=timezone.utc)

        # 读取上报的扩展字段并做类型规整
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
            client_session_id=payload.client_session_id,
        )
        try:
            session.add(learning_session)
            await session.commit()
            await session.refresh(learning_session)
        except Exception as e:
            await session.rollback()
            if payload.client_session_id:
                existing = await session.scalar(
                    select(LearningSession).where(
                        LearningSession.user_id == user_id,
                        LearningSession.client_session_id == payload.client_session_id,
                    )
                )
                if existing is not None:
                    return existing, True
            raise e

        logger.info(
            "[Evaluation] 学习会话已记录: user=%s page=%s duration=%ss session_id=%s",
            user_id,
            payload.source_page,
            payload.duration_seconds,
            learning_session.id,
        )
        return learning_session, False

    # 获取评估摘要：查询最近事件并聚合
    async def get_summary(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        limit: int = 100,
    ) -> EvaluationSummaryResponse:
        # 按时间倒序查询该用户最近的学习事件
        stmt = (
            select(LearningEvent)
            .where(LearningEvent.user_id == user_id)
            .order_by(LearningEvent.created_at.desc())
            .limit(limit)
        )
        result = await session.exec(stmt)
        events = list(result.all())
        # 汇总活跃分钟数后构建摘要返回
        active_minutes = await self._get_active_minutes(session, user_id=user_id)
        return build_summary_from_events(events, active_minutes=active_minutes)

    # 统计用户累计活跃分钟数（所有会话时长秒数换算）
    async def _get_active_minutes(self, session: AsyncSession, *, user_id: int) -> int:
        """获取用户总活跃分钟数。"""
        # 对所有会话时长求和并换算为分钟
        stmt = select(LearningSession.duration_seconds).where(LearningSession.user_id == user_id)
        result = await session.exec(stmt)
        total_seconds = sum(s for s in result.all() if s is not None)
        return int(total_seconds // 60) if total_seconds else 0

    # 获取学习时长统计：今日/累计/连续天数/每日与来源分布
    async def get_time_stats(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        days: int = 30,
    ) -> LearningTimeStatsResponse:
        # 限制统计窗口在 1~90 天并取本地（上海）当前时间
        window_days = max(1, min(days, 90))
        now_local = datetime.now(SHANGHAI_TZ)
        bounds = _get_time_boundaries(now_local)
        # 取月起点与窗口起点中较早者作为查询下界
        query_start_utc = min(
            bounds["month_start_utc"],
            _local_day_start(now_local.date() - timedelta(days=window_days - 1)),
        )

        # 查询窗口内的会话用于每日与来源分布统计
        recent_stmt = (
            select(LearningSession)
            .where(LearningSession.user_id == user_id)
            .where(LearningSession.started_at >= query_start_utc)
            .order_by(LearningSession.started_at.asc())
        )
        recent_result = await session.exec(recent_stmt)
        recent_sessions = list(recent_result.all())

        # 查询全部会话用于累计时长与连续天数统计
        total_stmt = (
            select(LearningSession)
            .where(LearningSession.user_id == user_id)
            .order_by(LearningSession.started_at.asc())
        )
        total_result = await session.exec(total_stmt)
        all_sessions = list(total_result.all())

        # 初始化今日秒数、每日时长映射与来源分布映射
        today_seconds = 0
        daily_map: dict[date, int] = defaultdict(int)
        context_map: dict[str, int] = defaultdict(int)

        # 遍历窗口内会话，按日期与来源累加学习时长
        for sess in recent_sessions:
            duration = sess.duration_seconds or 0
            # 跳过无效时长的会话
            if duration <= 0:
                continue
            created_local = _to_local(sess.started_at)
            # 属于今天则累加今日学习秒数
            if created_local >= bounds["today_start_local"]:
                today_seconds += duration
            event_date = created_local.date()
            # 在统计窗口内则累加该日期的学习秒数
            if event_date >= (now_local.date() - timedelta(days=window_days - 1)):
                daily_map[event_date] += duration
            # 按来源页面归集学习时长
            context = sess.source_page
            if context:
                context_map[context] += duration

        # 汇总累计时长并计算连续学习天数
        total_seconds = sum(s.duration_seconds or 0 for s in all_sessions)
        streak_days = _compute_streak_days(all_sessions, now_local.date())

        # 组装并返回学习时长统计响应
        return LearningTimeStatsResponse(
            today_seconds=today_seconds,
            total_seconds=total_seconds,
            streak_days=streak_days,
            daily_breakdown=_build_daily_breakdown(now_local.date(), window_days, daily_map),
            context_breakdown=dict(
                sorted(context_map.items(), key=lambda item: item[1], reverse=True)
            ),
        )


# 解析 ISO 时间字符串，缺省时区则补为 UTC
def _parse_iso_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


# 将数据库学习事件转换为对外响应项
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


# 将时间转换为上海本地时区（缺时区则按 UTC 处理）
def _to_local(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(SHANGHAI_TZ)


# 取本地某日的 0 点并转换为 UTC
def _local_day_start(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=SHANGHAI_TZ).astimezone(UTC)


# 计算今天/本周/本月起点的本地与 UTC 时间边界
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


# 生成连续 window_days 天的每日时长明细
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


# 从今天往前推算连续学习达到最低时长的天数
def _compute_streak_days(
    sessions: list[LearningSession], today_local: date
) -> int:
    # 按本地日期聚合会话时长
    daily_totals: dict[date, int] = defaultdict(int)
    for sess in sessions:
        duration = sess.duration_seconds or 0
        if duration <= 0:
            continue
        daily_totals[_to_local(sess.started_at).date()] += duration

    # 从今天起逐日回退，累计达到最低时长的连续天数
    streak = 0
    cursor = today_local
    while daily_totals.get(cursor, 0) >= STREAK_MIN_SECONDS:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


# 模块级单例评估服务
evaluation_service = EvaluationService()
