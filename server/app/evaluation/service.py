"""学习评估服务 — 学习事件采集、评估生成与辅导策略更新。

事件来源由各业务模块的 ``events.py`` 调用 ``EvaluationService.record_event`` 埋点。
本模块负责幂等持久化、评估状态机和辅导策略定向写入。

触发机制：
- 非 chat 模块累计 5 条新学习事件时，触发画像评分 + 学习评估
- chat 模块累计 10 条对话事件时，触发画像评分 + 学习评估
- 用户手动请求生成评估

LLM 输出两部分：
- assessment：学习评估文案（一段话）
- guidance_strategy：辅导策略（结构化），同步写入 UserProfile
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Literal

from app.evaluation.request import LearningEventCreate, LearningSessionCreate
from app.infra.logging import get_logger
from app.infra.models import LearningEvent, LearningSession, LearningAssessment
from app.infra.prompts import prompts

logger = get_logger(__name__)

# 触发阈值配置
EVENT_THRESHOLD_DEFAULT = 5   # 非 chat 模块
EVENT_THRESHOLD_CHAT = 10     # chat 模块
DEFAULT_RANGE_DAYS = 7        # 自动触发时默认 7 天范围


class ConcurrencyError(Exception):
    """当用户已有正在生成的评估时抛出该异常。"""
    pass


# ── LLM 输出结构定义 ──────────────────────────────────────────────────────────

class ActionPlanItem(BaseModel):
    topic: str
    action_type: Literal["review", "practice", "quiz"]
    description: str
    link: str


class GuidanceStrategyOutput(BaseModel):
    version: int = 1
    conclusion: str = Field(description="本期结论文案，一句话概括当前学习状态和方向")
    focus_topics: list[str]
    recommended_session_minutes: int
    tutoring_style: str
    action_plan: list[ActionPlanItem]
    reason: str = Field(description="策略推导依据，简述为何选择此策略")


class AssessmentOutput(BaseModel):
    assessment: str = Field(description="学习评估文案，一段话描述近期学习情况")
    guidance_strategy: GuidanceStrategyOutput


class EvaluationService:
    """评估服务 — 学习事件记录、会话记录与学习评估生成。"""

    # 生成学习评估并更新辅导策略
    async def generate_assessment(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        trigger_source: str,
        range_days: int,
    ) -> LearningAssessment:
        if range_days not in (3, 7, 14):
            raise ValueError("range_days must be 3, 7, or 14")
        if trigger_source not in ("profile_update", "manual"):
            raise ValueError("trigger_source must be profile_update or manual")

        # 1. 原子创建 generating 评估并检测并发
        now_utc = datetime.now(timezone.utc)
        window_start = now_utc - timedelta(days=range_days)
        window_end = now_utc

        # 查询是否已有生成中评估
        existing_generating = await session.scalar(
            select(LearningAssessment).where(
                LearningAssessment.user_id == user_id,
                LearningAssessment.status == "generating",
            )
        )
        if existing_generating is not None:
            raise ConcurrencyError("assessment_generation_in_progress")

        assessment = LearningAssessment(
            user_id=user_id,
            trigger_source=trigger_source,
            range_days=range_days,
            window_start=window_start,
            window_end=window_end,
            status="generating",
            created_at=now_utc,
            updated_at=now_utc,
        )
        session.add(assessment)

        from sqlalchemy.exc import IntegrityError
        try:
            await session.commit()
            await session.refresh(assessment)
        except IntegrityError:
            await session.rollback()
            raise ConcurrencyError("assessment_generation_in_progress")

        # 2. 聚合事实快照（不持久化，仅用于 LLM 推理）
        try:
            from app.evaluation.facts import build_assessment_facts
            facts_snapshot = await build_assessment_facts(
                session, user_id=user_id, window_start=window_start, window_end=window_end
            )
            assessment.updated_at = datetime.now(timezone.utc)
            await session.commit()
        except Exception as e:
            assessment.status = "failed"
            assessment.failure_code = "facts_aggregation_failed"
            assessment.updated_at = datetime.now(timezone.utc)
            await session.commit()
            raise e

        # 3. 使用 LLM 生成评估文案和辅导策略
        assessment_text, guidance_strategy = await self._derive_assessment_with_llm(facts_snapshot)

        # 4. 更新评估状态并写入策略到 UserProfile
        assessment.status = "ready"
        assessment.assessment = assessment_text
        assessment.generated_at = datetime.now(timezone.utc)
        assessment.updated_at = datetime.now(timezone.utc)

        await self._update_guidance_strategy(
            session,
            user_id=user_id,
            strategy=guidance_strategy,
            assessment_id=assessment.id,
        )
        await session.commit()
        await session.refresh(assessment)

        return assessment

    async def _derive_assessment_with_llm(
        self, facts: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        """使用 LLM 从 facts 生成评估文案和辅导策略。

        Returns:
            (assessment_text, guidance_strategy_dict)
        """
        # 提取薄弱主题作为备用（LLM 失败时使用）
        practice = facts.get("practice", {}).get("by_topic", [])
        weak_topics = [
            t["topic"]
            for t in practice
            if t.get("submitted", 0) >= 3 and t.get("accuracy", 1) < 0.6
        ][:4]

        try:
            from app.infra.llm import get_llm
            llm = get_llm()
            prompt = prompts.get("evaluation").render(
                "assessment",
                facts_json=json.dumps(facts, ensure_ascii=False, indent=2),
            )
            result = await llm.ainvoke_json(
                AssessmentOutput,
                [HumanMessage(content=prompt)],
            )

            guidance_dict = {
                "version": result.guidance_strategy.version,
                "conclusion": result.guidance_strategy.conclusion,
                "focus_topics": result.guidance_strategy.focus_topics,
                "recommended_session_minutes": result.guidance_strategy.recommended_session_minutes,
                "tutoring_style": result.guidance_strategy.tutoring_style,
                "action_plan": [item.model_dump() for item in result.guidance_strategy.action_plan],
                "reason": result.guidance_strategy.reason,
            }

            return result.assessment, guidance_dict
        except Exception as e:
            logger.warning("[Evaluation] LLM 评估生成失败，使用规则推导: %s", e)
            return self._derive_assessment_from_facts_simple(facts, weak_topics)

    def _derive_assessment_from_facts_simple(
        self, facts: dict[str, Any], weak_topics: list[str]
    ) -> tuple[str, dict[str, Any]]:
        """规则推导评估文案和辅导策略（LLM 失败时的降级方案）。"""
        practice = facts.get("practice", {})
        accuracy = practice.get("accuracy", 0)
        submitted = practice.get("submitted", 0)
        activity = facts.get("activity", {})
        active_days = activity.get("active_days", 0)
        total_minutes = activity.get("total_minutes", 0)

        # 生成评估文案
        if submitted < 5:
            assessment_text = (
                f"近7天活跃{active_days}天，累计学习{total_minutes}分钟，"
                "练习数据较少，建议继续学习积累更多学习事实后再进行评估。"
            )
        elif accuracy < 0.6:
            weak_str = "、".join(weak_topics[:3]) if weak_topics else "部分知识点"
            assessment_text = (
                f"近7天活跃{active_days}天，累计学习{total_minutes}分钟，"
                f"练习正确率偏低（{int(accuracy * 100)}%），{weak_str}需要优先巩固。"
            )
        elif accuracy < 0.8:
            weak_str = "、".join(weak_topics[:2]) if weak_topics else "部分知识点"
            assessment_text = (
                f"近7天活跃{active_days}天，累计学习{total_minutes}分钟，"
                f"练习正确率中等（{int(accuracy * 100)}%），{weak_str}有提升空间。"
            )
        else:
            assessment_text = (
                f"近7天活跃{active_days}天，累计学习{total_minutes}分钟，"
                f"练习正确率良好（{int(accuracy * 100)}%），继续保持并拓展新知识。"
            )

        # 生成行动计划
        action_plan = []
        for topic in weak_topics[:4]:
            action_plan.append({
                "topic": topic,
                "action_type": "practice",
                "description": f"完成 {topic} 相关练习",
                "link": f"/quiz?topic={topic}",
            })

        guidance_strategy = {
            "version": 1,
            "conclusion": assessment_text,
            "focus_topics": weak_topics,
            "recommended_session_minutes": 25,
            "tutoring_style": "分步骤讲解 + 错题练习",
            "action_plan": action_plan,
            "reason": "基于练习正确率规则推导",
        }

        return assessment_text, guidance_strategy

    async def _update_guidance_strategy(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        strategy: dict[str, Any],
        assessment_id: int,
    ) -> None:
        """将辅导策略写入 UserProfile。"""
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
                last_assessment_id=assessment_id,
                created_at=now,
                updated_at=now,
            )
            session.add(profile)
        else:
            profile.guidance_strategy = strategy
            profile.guidance_updated_at = now
            profile.last_assessment_id = assessment_id
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

        # 检测是否达到阈值，触发画像评分 + 学习评估
        try:
            await self._check_and_trigger_assessment(session, user_id)
        except Exception as e:
            logger.warning("[Evaluation] 自动评估检测失败: user=%s error=%s", user_id, e)

        return event, False

    async def _check_and_trigger_assessment(
        self, session: AsyncSession, user_id: int
    ) -> None:
        """检测学习事件阈值，触发画像评分和学习评估。

        条件：
        - 非 chat 模块累计 >= EVENT_THRESHOLD_DEFAULT 条新事件
        - chat 模块累计 >= EVENT_THRESHOLD_CHAT 条新事件
        - 且当前没有生成中的评估
        """
        from app.infra.database import session_scope
        from app.profile.service import get_profile_service

        # 获取最近一份评估
        latest_assessment = await session.scalar(
            select(LearningAssessment)
            .where(LearningAssessment.user_id == user_id)
            .order_by(LearningAssessment.created_at.desc())
            .limit(1)
        )

        # 统计上次评估后新增的事件数（按模块分开计数）
        if latest_assessment:
            new_events_stmt = select(LearningEvent).where(
                LearningEvent.user_id == user_id,
                LearningEvent.created_at > latest_assessment.created_at,
            )
        else:
            new_events_stmt = select(LearningEvent).where(
                LearningEvent.user_id == user_id,
            )

        new_events = list((await session.exec(new_events_stmt)).all())
        chat_count = sum(1 for e in new_events if e.module == "chat")
        other_count = sum(1 for e in new_events if e.module != "chat")

        # 判断是否达到阈值
        triggered = (other_count >= EVENT_THRESHOLD_DEFAULT) or \
                    (chat_count >= EVENT_THRESHOLD_CHAT)
        if not triggered:
            logger.debug(
                "[Evaluation] 自动评估跳过: user=%s chat=%d/%d other=%d/%d",
                user_id, chat_count, EVENT_THRESHOLD_CHAT, other_count, EVENT_THRESHOLD_DEFAULT,
            )
            return

        # 检查是否有正在生成的评估
        generating = await session.scalar(
            select(LearningAssessment).where(
                LearningAssessment.user_id == user_id,
                LearningAssessment.status == "generating",
            )
        )
        if generating:
            logger.debug("[Evaluation] 自动评估跳过: user=%s 已有生成中评估", user_id)
            return

        # 满足条件，在新的 session 中执行：画像评分 → 学习评估生成
        logger.info(
            "[Evaluation] 触发自动评估链路: user=%s trigger=profile_update range_days=%d",
            user_id, DEFAULT_RANGE_DAYS,
        )

        async with session_scope() as new_session:
            try:
                # Step 1: 更新画像评分
                profile_service = get_profile_service()
                score_result = await profile_service.score_profile(user_id=user_id)
                logger.info(
                    "[Evaluation] 画像评分更新完成: user=%s overall_score=%s",
                    user_id, score_result.get("overall_score"),
                )

                # Step 2: 生成学习评估
                await self.generate_assessment(
                    new_session,
                    user_id=user_id,
                    trigger_source="profile_update",
                    range_days=DEFAULT_RANGE_DAYS,
                )
                logger.info("[Evaluation] 自动评估生成成功: user=%s", user_id)
            except ConcurrencyError:
                logger.debug("[Evaluation] 自动评估并发冲突: user=%s", user_id)
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
