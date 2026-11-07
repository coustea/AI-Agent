"""题库模块事件埋点。

在用户提交独立题库答题后记录 ``quiz_submitted`` 事件到 ``learning_events`` 表，
供学习评估按时间窗口聚合统计。
"""

from __future__ import annotations

from sqlmodel.ext.asyncio.session import AsyncSession

from app.evaluation.event_types import MODULE_QUIZ, QUIZ_SUBMITTED
from app.evaluation.schemas import LearningEventCreate
from app.evaluation.service import EvaluationService
from app.infra.logging import get_logger

# 创建模块级日志器
logger = get_logger(__name__)


# 记录一次独立题库答题事件到 learning_events 表
async def record_quiz_submit_event(
    db: AsyncSession,
    user_id: int,
    score: float,
    is_correct: bool,
    attempt_index: int,
    subject: str | None = None,
    question_id: str | None = None,
    question_type: str | None = None,
) -> None:
    """记录一次独立题库单题答题事件。

    Args:
        db: 异步数据库会话。
        user_id: 用户 ID。
        score: 得分百分比（0-100）。
        is_correct: 该题是否回答正确。
        attempt_index: 本次提交中的题目序号。
        subject: 可选的学习科目。
        question_id: 可选题目 ID，仅用于事实关联，不包含题目正文或答案。
        question_type: 可选题型。
    """
    # 构建学习事件载荷（模块、事件类型、科目、得分与元信息）
    payload = LearningEventCreate(
        module=MODULE_QUIZ,
        entity_id=question_id,
        event_type=QUIZ_SUBMITTED,
        course=subject,
        score=score,
        event_metadata={
            "is_correct": is_correct,
            "attempt_index": attempt_index,
            "question_type": question_type,
        },
    )
    # 调用评测服务持久化答题事件
    await EvaluationService().record_event(db, user_id=user_id, payload=payload)
    # 记录事件落库日志
    logger.info(
        "[Quiz] event recorded: user_id=%s question_id=%s score=%s correct=%s attempt=%s",
        user_id,
        question_id,
        score,
        is_correct,
        attempt_index,
    )
