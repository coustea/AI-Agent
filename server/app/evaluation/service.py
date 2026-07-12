"""学习评估服务 — 学习事件采集与报告生成。

事件来源由各业务模块的 ``events.py`` 调用 ``EvaluationService.record_event`` 埋点。
本模块负责幂等持久化、报告状态机和当前辅导策略定向写入；不会触发画像评分。
"""

# 评估服务：学习事件采集、会话记录、报告状态机与策略定向写入。
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.evaluation.request import LearningEventCreate, LearningSessionCreate
from app.infra.logging import get_logger
from app.infra.models import LearningEvent, LearningSession, LearningAssessmentReport

logger = get_logger(__name__)


class ConcurrencyError(Exception):
    """当用户已有正在生成的报告时抛出该异常。"""
    pass


# 评估服务类：学习事件记录、会话记录与学习评估报告生成
class EvaluationService:
    """评估服务 — 学习事件记录、会话记录与报告生成。"""

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

        # 3. 从 facts_snapshot 直接推导辅导策略（不调用 LLM）
        guidance_strategy = self._derive_strategy_from_facts(facts_snapshot)

        # 4. 更新报告状态并写入策略
        report.status = "ready"
        report.generated_at = datetime.now(timezone.utc)
        report.updated_at = datetime.now(timezone.utc)
        # report_markdown 不再生成，保持 None

        await self._update_guidance_strategy_only(
            session,
            user_id=user_id,
            strategy=guidance_strategy,
            report_id=report.id,
        )
        await session.commit()
        await session.refresh(report)

        return report

    def _derive_strategy_from_facts(self, facts: dict[str, Any]) -> dict[str, Any]:
        """从 facts_snapshot 直接提取辅导策略，无需调用 LLM。

        规则：
        - 重点主题：练习次数 >= 3 且正确率 < 60% 的主题，最多取 4 个
        - 其他字段使用默认值

        Args:
            facts: AssessmentFacts 快照字典

        Returns:
            GuidanceStrategy 字典
        """
        practice = facts.get("practice", {}).get("by_topic", [])

        # 提取薄弱主题：练习次数 >= 3 且正确率 < 60%
        weak_topics = [
            t["topic"]
            for t in practice
            if t.get("submitted", 0) >= 3 and t.get("accuracy", 1) < 0.6
        ][:4]

        return {
            "version": 1,
            "focus_topics": weak_topics,
            "preferred_resource_types": [],
            "recommended_session_minutes": 25,
            "weekly_goal": "",
            "tutoring_style": "",
            "reason": "基于练习正确率自动推导" if weak_topics else "暂无足够练习数据",
        }

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

# 模块级单例评估服务
evaluation_service = EvaluationService()
