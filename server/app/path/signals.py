"""学习效果摘要与资源策略兜底逻辑。"""

from __future__ import annotations

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.logging import get_logger
from app.infra.models import CoursePath, LearningEvent
from app.path.schemas import LearningSignalSnapshot

logger = get_logger(__name__)

FALLBACK_POLICY_BY_DIFFICULTY: dict[str, list[str]] = {
    "beginner": ["content", "quiz"],
    "intermediate": ["content", "quiz", "mindmap"],
    "advanced": ["content", "code"],
}


def get_resource_policy_fallback(difficulty: str | None = None) -> list[str]:
    """Return default agent list when node has no resource_policy."""
    key = difficulty if difficulty in FALLBACK_POLICY_BY_DIFFICULTY else "intermediate"
    return list(FALLBACK_POLICY_BY_DIFFICULTY[key])


async def build_learning_signal_snapshot(
    session: AsyncSession,
    user_id: int,
    path: CoursePath,
) -> LearningSignalSnapshot:
    """Aggregate learning events into a summary for path adjustment."""
    stmt = (
        select(LearningEvent)
        .where(
            LearningEvent.user_id == user_id,
            LearningEvent.created_at >= path.created_at,
        )
        .order_by(LearningEvent.created_at.desc())
        .limit(50)
    )
    events = list((await session.exec(stmt)).all())

    if not events:
        return LearningSignalSnapshot()

    score_values = [e.score for e in events if e.score is not None]
    average_score = round(sum(score_values) / len(score_values), 1) if score_values else None

    weak_topics: list[str] = []
    for e in events:
        if e.event_type == "quiz_submitted" and e.score is not None and e.score < 65:
            topic = e.topic or e.course or ""
            if topic and topic not in weak_topics:
                weak_topics.append(topic)

    preferred_resources: list[str] = []
    negative_feedback: list[str] = []
    for e in events:
        if e.event_type in ("path_feedback", "resource_feedback") and e.feedback:
            fb = e.feedback
            if any(kw in fb for kw in ("喜欢", "希望", "更想", "图解", "案例", "代码", "视频")):
                if fb not in preferred_resources:
                    preferred_resources.append(fb)
            if any(kw in fb for kw in ("太难", "看不懂", "不会", "卡住", "薄弱", "偏难", "跟不上")):
                if fb not in negative_feedback:
                    negative_feedback.append(fb)

    completed_resource_count = sum(1 for e in events if e.event_type == "resource_completed")
    viewed_resource_count = sum(1 for e in events if e.event_type == "resource_viewed")
    active_minutes = sum(e.duration_seconds or 0 for e in events if e.event_type == "learning_heartbeat") // 60

    recommendations: list[str] = []
    if weak_topics:
        recommendations.append(f"薄弱知识点需要巩固: {', '.join(weak_topics[:3])}")
    if average_score is not None and average_score < 70:
        recommendations.append("整体测验分数偏低，建议降低后续节点难度或增加练习")

    return LearningSignalSnapshot(
        average_score=average_score,
        weak_topics=weak_topics[:5],
        preferred_resources=preferred_resources[:3],
        negative_feedback=negative_feedback[:3],
        completed_resource_count=completed_resource_count,
        viewed_resource_count=viewed_resource_count,
        active_minutes=active_minutes,
        recommendations=recommendations,
    )
