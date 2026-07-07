"""题库模块事件埋点。

在用户提交独立题库答题后记录 ``quiz_submitted`` 事件到 ``learning_events`` 表，
供画像评分按时间窗口聚合统计。
"""

from __future__ import annotations

from sqlmodel.ext.asyncio.session import AsyncSession

from app.evaluation.event_types import MODULE_QUIZ, QUIZ_SUBMITTED
from app.evaluation.request import LearningEventCreate
from app.evaluation.service import EvaluationService
from app.infra.logging import get_logger

logger = get_logger(__name__)


async def record_quiz_submit_event(
    db: AsyncSession,
    user_id: int,
    total_count: int,
    correct_count: int,
    score: float,
    subject: str | None = None,
) -> None:
    """记录一次独立题库答题事件。

    Args:
        db: 异步数据库会话。
        user_id: 用户 ID。
        total_count: 总题数。
        correct_count: 正确题数。
        score: 得分百分比（0-100）。
        subject: 可选的学习科目。
    """
    payload = LearningEventCreate(
        module=MODULE_QUIZ,
        event_type=QUIZ_SUBMITTED,
        course=subject,
        score=score,
        event_metadata={
            "total_count": total_count,
            "correct_count": correct_count,
        },
    )
    await EvaluationService().record_event(db, user_id=user_id, payload=payload)
    logger.info(
        "[Quiz] event recorded: user_id=%s score=%s total=%s correct=%s",
        user_id,
        score,
        total_count,
        correct_count,
    )
