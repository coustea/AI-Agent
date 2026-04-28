from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
from typing import Any

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.evaluation.schemas import (
    EvaluationMetric,
    EvaluationSummary,
    LearningEventCreate,
    LearningEventItem,
)
from app.infra.logging import get_logger
from app.infra.models import LearningEvent
from app.memory import MemoryLayer
from app.memory.memory_types import MEMORY_TYPE_PREFERENCE, MEMORY_TYPE_WEAKNESS

logger = get_logger(__name__)


@dataclass(frozen=True)
class MemoryCandidate:
    content: str
    memory_type: str


def derive_memory_candidates(event: LearningEventCreate) -> list[MemoryCandidate]:
    """Translate high-signal learning events into long-term memory candidates."""
    topic = event.topic or event.course or "当前主题"
    candidates: list[MemoryCandidate] = []

    if event.event_type == "quiz_submitted" and event.score is not None and event.score < 65:
        candidates.append(
            MemoryCandidate(
                content=f"在「{topic}」练习中得分偏低（{event.score:.0f}分），需要加强针对性巩固。",
                memory_type=MEMORY_TYPE_WEAKNESS,
            )
        )

    feedback = (event.feedback or "").strip()
    if event.event_type in {"path_feedback", "resource_feedback"} and feedback:
        if any(keyword in feedback for keyword in ("太难", "看不懂", "不会", "卡住", "薄弱", "错")):
            candidates.append(
                MemoryCandidate(
                    content=f"学习「{topic}」时反馈：{feedback}",
                    memory_type=MEMORY_TYPE_WEAKNESS,
                )
            )
        if any(keyword in feedback for keyword in ("喜欢", "希望", "更想", "图解", "案例", "代码", "视频")):
            candidates.append(
                MemoryCandidate(
                    content=f"学习资源偏好反馈：{feedback}",
                    memory_type=MEMORY_TYPE_PREFERENCE,
                )
            )

    return candidates[:2]


def build_summary_from_events(events: list[LearningEvent]) -> EvaluationSummary:
    score_values = [event.score for event in events if event.score is not None]
    average_score = round(sum(score_values) / len(score_values), 1) if score_values else None
    completed_resources = sum(1 for event in events if event.event_type == "resource_completed")
    viewed_resources = sum(1 for event in events if event.event_type == "resource_viewed")
    active_seconds = sum(event.duration_seconds or 0 for event in events)

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

    metrics = [
        EvaluationMetric(label="平均测验分", value="暂无" if average_score is None else f"{average_score:.1f}"),
        EvaluationMetric(label="完成资源", value=str(completed_resources)),
        EvaluationMetric(label="活跃学习", value=f"{active_seconds // 60} 分钟"),
    ]

    return EvaluationSummary(
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
    ) -> LearningEvent:
        event = LearningEvent(
            user_id=user_id,
            session_id=payload.session_id,
            resource_id=payload.resource_id,
            event_type=payload.event_type,
            course=payload.course,
            topic=payload.topic,
            score=payload.score,
            duration_seconds=payload.duration_seconds,
            feedback=payload.feedback,
            metadata_json=payload.metadata or None,
        )
        session.add(event)
        await session.commit()
        await session.refresh(event)
        logger.info("[Evaluation] 学习事件已记录: user=%s type=%s event_id=%s", user_id, payload.event_type, event.id)
        await self._persist_memory_candidates(user_id=user_id, event=event, payload=payload)
        return event

    async def get_summary(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        limit: int = 100,
    ) -> EvaluationSummary:
        stmt = (
            select(LearningEvent)
            .where(LearningEvent.user_id == user_id)
            .order_by(LearningEvent.created_at.desc())
            .limit(limit)
        )
        result = await session.exec(stmt)
        return build_summary_from_events(list(result.all()))

    async def _persist_memory_candidates(
        self,
        *,
        user_id: int,
        event: LearningEvent,
        payload: LearningEventCreate,
    ) -> None:
        memory_layer = MemoryLayer(module_name="mentor")
        for candidate in derive_memory_candidates(payload):
            try:
                await memory_layer.upsert_long_term_fact(
                    user_id=user_id,
                    content_markdown=candidate.content,
                    memory_type=candidate.memory_type,
                    session_id=event.session_id,
                )
            except Exception:
                logger.exception("[Evaluation] 学习事件写入长期记忆失败: event_id=%s", event.id)


def _to_item(event: LearningEvent) -> LearningEventItem:
    return LearningEventItem(
        id=event.id or 0,
        event_type=event.event_type,
        course=event.course,
        topic=event.topic,
        score=event.score,
        duration_seconds=event.duration_seconds,
        feedback=event.feedback,
        created_at=event.created_at,
    )


evaluation_service = EvaluationService()
