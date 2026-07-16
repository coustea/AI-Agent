"""学习评估服务 — 学习事件采集与报告生成。

事件来源由各业务模块的 ``events.py`` 调用 ``EvaluationService.record_event`` 埋点。
本模块负责幂等持久化、报告状态机和当前辅导策略定向写入。

自动触发机制：
- 当用户累计 15 条新学习事件时，自动触发报告生成
- 距离上次报告至少 5 天
"""

# 评估服务：学习事件采集、会话记录、报告状态机与策略定向写入。
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from langchain_core.messages import HumanMessage
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.evaluation.request import LearningEventCreate, LearningSessionCreate
from app.infra.logging import get_logger
from app.infra.models import LearningEvent, LearningSession, LearningAssessmentReport
from app.infra.prompts import prompts

logger = get_logger(__name__)

# 自动触发阈值配置
AUTO_REPORT_MIN_EVENTS = 15  # 最少新事件数
AUTO_REPORT_MIN_DAYS = 5     # 距上次报告最少天数
AUTO_REPORT_DEFAULT_RANGE = 7  # 自动触发时默认 7 天范围


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
        if range_days not in (3, 7, 14):
            raise ValueError("range_days must be 3, 7, or 14")

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

        # 3. 使用 LLM 生成结论和辅导策略
        guidance_strategy = await self._derive_strategy_with_llm(facts_snapshot)

        # 4. 更新报告状态并写入策略
        report.status = "ready"
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

        return report

    async def _derive_strategy_with_llm(self, facts: dict[str, Any]) -> dict[str, Any]:
        """使用 LLM 从 facts_snapshot 生成结论和辅导策略。

        Args:
            facts: AssessmentFacts 快照字典

        Returns:
            GuidanceStrategy 字典，包含 conclusion 和 action_plan
        """
        from app.infra.llm import get_llm
        from pydantic import BaseModel
        from typing import Literal

        # 提取薄弱主题作为备用（LLM 失败时使用）
        practice = facts.get("practice", {}).get("by_topic", [])
        weak_topics = [
            t["topic"]
            for t in practice
            if t.get("submitted", 0) >= 3 and t.get("accuracy", 1) < 0.6
        ][:4]

        # 定义输出结构
        class ActionPlanItem(BaseModel):
            topic: str
            action_type: Literal["review", "practice", "quiz"]
            description: str
            link: str

        class GuidanceStrategyOutput(BaseModel):
            conclusion: str  # 本期结论文案
            focus_topics: list[str]
            recommended_session_minutes: int
            tutoring_style: str
            action_plan: list[ActionPlanItem]

        try:
            llm = get_llm()
            prompt = prompts.get("evaluation").render(
                "strategy",
                facts_json=json.dumps(facts, ensure_ascii=False, indent=2),
            )
            result = await llm.ainvoke_json(
                GuidanceStrategyOutput,
                [HumanMessage(content=prompt)],
            )

            return {
                "version": 1,
                "conclusion": result.conclusion,
                "focus_topics": result.focus_topics,
                "recommended_session_minutes": result.recommended_session_minutes,
                "tutoring_style": result.tutoring_style,
                "action_plan": [item.model_dump() for item in result.action_plan],
                "reason": "基于学习数据 LLM 生成",
            }
        except Exception as e:
            logger.warning("[Evaluation] LLM 策略生成失败，使用规则推导: %s", e)
            # 降级：规则推导
            return self._derive_strategy_from_facts_simple(facts, weak_topics)

    def _derive_strategy_from_facts_simple(
        self, facts: dict[str, Any], weak_topics: list[str]
    ) -> dict[str, Any]:
        """规则推导辅导策略（LLM 失败时的降级方案）。

        Args:
            facts: AssessmentFacts 快照字典
            weak_topics: 薄弱主题列表

        Returns:
            GuidanceStrategy 字典
        """
        practice = facts.get("practice", {})
        accuracy = practice.get("accuracy", 0)
        submitted = practice.get("submitted", 0)

        # 生成结论文案
        if submitted < 5:
            conclusion = "练习数据较少，建议继续学习积累更多学习事实后再进行评估。"
        elif accuracy < 0.6:
            conclusion = f"练习正确率偏低（{int(accuracy * 100)}%），{'、'.join(weak_topics[:3])} 需要优先巩固。"
        elif accuracy < 0.8:
            conclusion = f"练习正确率中等（{int(accuracy * 100)}%），{'、'.join(weak_topics[:2])} 有提升空间。"
        else:
            conclusion = f"练习正确率良好（{int(accuracy * 100)}%），继续保持并拓展新知识。"

        # 生成行动计划
        action_plan = []
        for topic in weak_topics[:4]:
            action_plan.append({
                "topic": topic,
                "action_type": "practice",
                "description": f"完成 {topic} 相关练习",
                "link": f"/quiz?topic={topic}",
            })

        return {
            "version": 1,
            "conclusion": conclusion,
            "focus_topics": weak_topics,
            "recommended_session_minutes": 25,
            "tutoring_style": "分步骤讲解 + 错题练习",
            "action_plan": action_plan,
            "reason": "基于练习正确率规则推导",
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

        # 检测是否达到阈值，触发自动报告生成（异步执行，不阻塞当前请求）
        try:
            await self._check_and_trigger_auto_report(session, user_id)
        except Exception as e:
            # 自动触发失败不影响事件记录本身
            logger.warning("[Evaluation] 自动报告检测失败: user=%s error=%s", user_id, e)

        return event, False

    async def _check_and_trigger_auto_report(
        self, session: AsyncSession, user_id: int
    ) -> None:
        """检测学习事件阈值，触发画像更新和报告生成。

        条件：
        1. 距离上次报告 >= AUTO_REPORT_MIN_DAYS 天
        2. 或累计新事件数 >= AUTO_REPORT_MIN_EVENTS 条
        3. 且当前没有生成中的报告

        触发链路：
        学习事件达到阈值 → 更新画像分数 → 生成学习评估报告
        """
        from app.infra.database import session_scope
        from app.profile.service import get_profile_service

        # 获取最近一份报告
        latest_report = await session.scalar(
            select(LearningAssessmentReport)
            .where(LearningAssessmentReport.user_id == user_id)
            .order_by(LearningAssessmentReport.created_at.desc())
            .limit(1)
        )

        now = datetime.now(timezone.utc)

        # 检查时间间隔
        if latest_report:
            days_since_last = (now - latest_report.created_at).days
            if days_since_last < AUTO_REPORT_MIN_DAYS:
                logger.debug(
                    "[Evaluation] 自动报告跳过: user=%s 距上次 %d 天 < %d 天",
                    user_id, days_since_last, AUTO_REPORT_MIN_DAYS
                )
                return

            # 统计上次报告后新增的事件数
            new_events_result = await session.exec(
                select(LearningEvent.id)
                .where(
                    LearningEvent.user_id == user_id,
                    LearningEvent.created_at > latest_report.created_at,
                )
            )
            new_events_list = list(new_events_result.all())
            new_events_count = len(new_events_list)

            if new_events_count < AUTO_REPORT_MIN_EVENTS:
                logger.debug(
                    "[Evaluation] 自动报告跳过: user=%s 新事件 %d < %d",
                    user_id, new_events_count, AUTO_REPORT_MIN_EVENTS
                )
                return

        # 检查是否有正在生成的报告
        generating_report = await session.scalar(
            select(LearningAssessmentReport).where(
                LearningAssessmentReport.user_id == user_id,
                LearningAssessmentReport.status == "generating",
            )
        )
        if generating_report:
            logger.debug("[Evaluation] 自动报告跳过: user=%s 已有生成中报告", user_id)
            return

        # 满足条件，在新的 session 中执行：画像更新 → 报告生成
        logger.info(
            "[Evaluation] 触发自动评估链路: user=%s range_days=%d",
            user_id, AUTO_REPORT_DEFAULT_RANGE
        )

        # 使用新的 session scope 避免当前事务冲突
        async with session_scope() as new_session:
            try:
                # Step 1: 更新画像分数
                profile_service = get_profile_service()
                score_result = await profile_service.score_profile(user_id=user_id)
                logger.info(
                    "[Evaluation] 画像评分更新完成: user=%s overall_score=%s",
                    user_id, score_result.get("overall_score")
                )

                # Step 2: 生成学习评估报告
                await self.generate_report(
                    new_session,
                    user_id=user_id,
                    range_days=AUTO_REPORT_DEFAULT_RANGE,
                )
                logger.info("[Evaluation] 自动报告生成成功: user=%s", user_id)
            except ConcurrencyError:
                logger.debug("[Evaluation] 自动报告并发冲突: user=%s", user_id)
            except Exception as e:
                logger.error("[Evaluation] 自动评估链路失败: user=%s error=%s", user_id, e)

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
