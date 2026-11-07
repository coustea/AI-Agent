"""学习者画像即时装配器 (Just-In-Time Learner Context Loader).

原则：
1. 去中心化实时加载，不再依赖后台预计算 8 维度画像宽表；
2. 单一事实源：User 静态基线档案 + LearningEvent 真实答题/行为流 + WrongQuestion 错题本；
3. 针对不同消费场景（Chat / Resource / Path / Summary）动态装配最精炼、最高信噪比的学情上下文。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.logging import get_logger
from app.infra.models import (
    LearningEvent,
    LearningSession,
    User,
    UserProfile,
    WrongQuestion,
)

logger = get_logger(__name__)


class ProfileScope(str, Enum):
    CHAT = "chat"
    RESOURCE = "resource"
    PATH = "path"
    SUMMARY = "summary"


@dataclass
class LearnerContext:
    user_id: int
    base_info: dict[str, Any]
    weak_topics: list[str] = field(default_factory=list)
    recent_accuracy: float | None = None
    total_practice_count: int = 0
    topic_performance: dict[str, Any] = field(default_factory=dict)
    guidance_strategy: dict[str, Any] | None = None

    def to_prompt_text(self, scope: ProfileScope | str = ProfileScope.SUMMARY) -> str:
        """根据具体的消费场景输出最精炼的结构化提示词文本，避免长篇大论挤占 Prompt 窗口。"""
        if isinstance(scope, str):
            try:
                scope = ProfileScope(scope)
            except ValueError:
                scope = ProfileScope.SUMMARY

        lines: list[str] = []

        # 1. 基础学员身份
        school = self.base_info.get("school")
        major = self.base_info.get("major")
        grade = self.base_info.get("grade")
        identity_parts = [p for p in [school, major, grade] if p]
        identity_str = " · ".join(identity_parts) if identity_parts else "高校学生"

        level = self.base_info.get("foundational_level") or "初学/入门"
        style = self.base_info.get("learning_style") or "理论与实践并重"
        depth = self.base_info.get("content_depth") or "循序渐进"
        goal = self.base_info.get("global_learning_goal")

        if scope == ProfileScope.CHAT:
            lines.append(f"【学员背景】{identity_str}（基础水平：{level}，偏好风格：{style}）")
            if goal:
                lines.append(f"【学习目标】{goal}")
            if self.weak_topics:
                lines.append(f"【近期薄弱知识点】{'、'.join(self.weak_topics[:5])}")
            if self.recent_accuracy is not None:
                lines.append(f"【近期测验正确率】{self.recent_accuracy:.0%}")
            if self.guidance_strategy:
                conclusion = self.guidance_strategy.get("conclusion")
                style_rec = self.guidance_strategy.get("tutoring_style")
                if conclusion:
                    lines.append(f"【自适应导学建议】{conclusion}（推荐交互风格：{style_rec or '循循善诱'}）")

        elif scope == ProfileScope.RESOURCE:
            lines.append(f"【目标学习者】{identity_str}（基础水准：{level}，内容深度：{depth}，认知风格：{style}）")
            if self.topic_performance:
                topic = self.topic_performance.get("topic", "")
                acc = self.topic_performance.get("accuracy")
                cnt = self.topic_performance.get("question_count", 0)
                wrongs = self.topic_performance.get("wrong_count", 0)
                if cnt > 0 and acc is not None:
                    lines.append(f"【当前主题学情】针对主题「{topic}」，该学员已练习 {cnt} 题，历史正确率 {acc:.0%}，错题 {wrongs} 道。")
                    if acc < 0.6:
                        lines.append("【教学侧重点】该主题掌握较薄弱，请着重直观原理解释、对比图解与基础示例，避免突兀的高难度抽象推导。")
                    else:
                        lines.append("【教学侧重点】该主题基础扎实，可适度拔高，引入工程边界场景与深度变体思考。")
            if self.weak_topics:
                lines.append(f"【关联薄弱项】{'、'.join(self.weak_topics[:4])}")

        elif scope == ProfileScope.PATH:
            lines.append(f"【学员档案】{identity_str}")
            if goal:
                lines.append(f"【总规划目标】{goal}")
            daily_time = self.base_info.get("daily_study_time")
            if daily_time:
                lines.append(f"【预期每日学习时长】{daily_time}")
            lines.append(f"【起点水准】{level}（深度偏好：{depth}）")
            all_weak = list(dict.fromkeys(self.weak_topics + (self.base_info.get("weak_points") or [])))
            if all_weak:
                lines.append(f"【重点攻克薄弱项】{'、'.join(all_weak[:8])}")

        else:  # SUMMARY
            lines.append(f"# 学习者实时学情档案")
            lines.append(f"- 学员背景：{identity_str}")
            lines.append(f"- 基础水平：{level} | 认知偏好：{style} | 期望深度：{depth}")
            if goal:
                lines.append(f"- 学习目标：{goal}")
            if self.weak_topics:
                lines.append(f"- 薄弱知识点：{'、'.join(self.weak_topics)}")
            if self.recent_accuracy is not None:
                lines.append(f"- 近期测验综合表现：练习题量 {self.total_practice_count}，正确率 {self.recent_accuracy:.0%}")

        return "\n".join(lines)


async def load_learner_context(
    session: AsyncSession,
    *,
    user_id: int,
    scope: ProfileScope = ProfileScope.SUMMARY,
    topic: str | None = None,
    range_days: int = 30,
) -> LearnerContext:
    """即时从单一事实源装配学习者上下文。

    执行耗时通常 < 5ms，完全取代后台多轮 LLM 画像推断批处理。
    """
    # 1. 查询静态基线（User）
    user = (await session.exec(select(User).where(User.id == user_id))).first()
    base_info: dict[str, Any] = {}
    if user:
        base_info = {
            "school": user.school or "",
            "school_level": user.school_level or "",
            "major": user.major or "",
            "grade": user.grade or "",
            "daily_study_time": user.daily_study_time or "",
            "global_learning_goal": user.global_learning_goal or "",
            "programming_languages": user.programming_languages or [],
            "courses": user.courses or [],
            "foundational_level": user.foundational_level or "",
            "learning_style": user.learning_style or "",
            "content_depth": user.content_depth or "",
            "weak_points": user.weak_points or [],
        }

    # 2. 从错题本与近期测验事件提取薄弱知识点
    weak_topics: list[str] = list(base_info.get("weak_points") or [])

    # 错题本中未归档的主题（真实错题往往最具即时针对性）
    try:
        wrong_stmt = (
            select(WrongQuestion.subject)
            .where(
                WrongQuestion.user_id == user_id,
                WrongQuestion.is_archived == False,  # noqa: E712
            )
            .group_by(WrongQuestion.subject)
            .order_by(func.count(WrongQuestion.id).desc())
            .limit(6)
        )
        wrong_subjects = list((await session.exec(wrong_stmt)).all())
        for subj in wrong_subjects:
            if subj and subj not in weak_topics:
                weak_topics.append(subj)
    except Exception as e:
        logger.warning("[JIT LearnerContext] 查询错题失败: %s", e)

    # 3. 统计近期测验事件表现
    since = datetime.now(timezone.utc) - timedelta(days=range_days)
    recent_accuracy: float | None = None
    total_practice = 0

    try:
        quiz_events_stmt = (
            select(LearningEvent)
            .where(
                LearningEvent.user_id == user_id,
                LearningEvent.module == "quiz",
                LearningEvent.occurred_at >= since,
            )
            .order_by(col(LearningEvent.occurred_at).desc())
            .limit(100)
        )
        quiz_events = list((await session.exec(quiz_events_stmt)).all())
        if quiz_events:
            total_practice = len(quiz_events)
            # score 为 0~100 或 metadata 中 is_correct
            correct_count = sum(
                1 for e in quiz_events
                if (e.score is not None and e.score >= 60)
                or (e.event_metadata and e.event_metadata.get("is_correct") is True)
            )
            recent_accuracy = correct_count / total_practice if total_practice > 0 else None
    except Exception as e:
        logger.warning("[JIT LearnerContext] 统计测验表现失败: %s", e)

    # 4. 若指定了具体主题，计算该主题专项学情
    topic_perf: dict[str, Any] = {}
    if topic:
        try:
            topic_events_stmt = (
                select(LearningEvent)
                .where(
                    LearningEvent.user_id == user_id,
                    LearningEvent.occurred_at >= since,
                    (LearningEvent.topic == topic) | (LearningEvent.course == topic),
                )
            )
            t_events = list((await session.exec(topic_events_stmt)).all())
            q_events = [e for e in t_events if e.module == "quiz"]
            if q_events:
                q_correct = sum(
                    1 for e in q_events
                    if (e.score is not None and e.score >= 60)
                    or (e.event_metadata and e.event_metadata.get("is_correct") is True)
                )
                topic_perf = {
                    "topic": topic,
                    "question_count": len(q_events),
                    "correct_count": q_correct,
                    "wrong_count": len(q_events) - q_correct,
                    "accuracy": q_correct / len(q_events) if q_events else None,
                }
        except Exception as e:
            logger.warning("[JIT LearnerContext] 查询专项主题失败: %s", e)

    # 5. 读取宏观导学策略（来自正式评估报告沉淀）
    guidance_strategy: dict[str, Any] | None = None
    try:
        profile_row = (
            await session.exec(select(UserProfile).where(UserProfile.user_id == user_id))
        ).first()
        if profile_row and profile_row.guidance_strategy:
            guidance_strategy = profile_row.guidance_strategy
    except Exception as e:
        logger.warning("[JIT LearnerContext] 查询导学策略失败: %s", e)

    return LearnerContext(
        user_id=user_id,
        base_info=base_info,
        weak_topics=weak_topics,
        recent_accuracy=recent_accuracy,
        total_practice_count=total_practice,
        topic_performance=topic_perf,
        guidance_strategy=guidance_strategy,
    )
