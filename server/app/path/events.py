"""路径模块学习事件埋点。

提供路径节点启动、完成和测验答题三个事件埋点函数，记录到 ``learning_events`` 表，
供画像评分按时间窗口聚合统计。

依赖关系：本文件仅被 ``service.py`` 和 ``workflows.py`` 调用，
不依赖 ``path/event.py``（SSE 事件流）。
"""

from __future__ import annotations

from typing import Any

from sqlmodel.ext.asyncio.session import AsyncSession

from app.evaluation.event_types import (
    MODULE_PATH,
    PATH_NODE_COMPLETED,
    PATH_NODE_STARTED,
    PATH_QUIZ_ANSWERED,
)
from app.evaluation.request import LearningEventCreate
from app.evaluation.service import EvaluationService
from app.infra.logging import get_logger

logger = get_logger(__name__)


# 记录路径节点启动事件到 learning_events 表
async def record_node_started_event(
    db: AsyncSession,
    user_id: int,
    path_id: int,
    path_node_id: int,
    node_id: int,
    course: str,
    topic: str,
) -> None:
    """记录一次路径节点启动事件。

    Args:
        db: 异步数据库会话。
        user_id: 用户 ID。
        path_id: 路径 ID。
        path_node_id: 路径节点内部 ID。
        node_id: 节点序号。
        course: 课程/路径标题。
        topic: 节点标题。
    """
    payload = LearningEventCreate(
        module=MODULE_PATH,
        entity_id=str(path_id),
        event_type=PATH_NODE_STARTED,
        course=course,
        topic=topic,
        event_metadata={
            "path_node_id": path_node_id,
            "node_id": node_id,
        },
    )
    await EvaluationService().record_event(db, user_id=user_id, payload=payload)
    logger.info(
        "[Path] node_started: user_id=%s path_id=%s node_id=%s topic=%s",
        user_id,
        path_id,
        node_id,
        topic,
    )


# 记录路径节点完成事件（含得分和薄弱知识点）
async def record_node_completed_event(
    db: AsyncSession,
    user_id: int,
    path_id: int,
    path_node_id: int,
    node_id: int,
    course: str,
    topic: str,
    score: float,
    weak_knowledge_points: list[str] | None = None,
) -> None:
    """记录一次路径节点完成事件。

    Args:
        db: 异步数据库会话。
        user_id: 用户 ID。
        path_id: 路径 ID。
        path_node_id: 路径节点内部 ID。
        node_id: 节点序号。
        course: 课程/路径标题。
        topic: 节点标题。
        score: 测验得分百分比（0-100）。
        weak_knowledge_points: 薄弱知识点列表。
    """
    meta: dict[str, Any] = {
        "path_node_id": path_node_id,
        "node_id": node_id,
    }
    if weak_knowledge_points:
        meta["weak_knowledge_points"] = weak_knowledge_points
    payload = LearningEventCreate(
        module=MODULE_PATH,
        entity_id=str(path_id),
        event_type=PATH_NODE_COMPLETED,
        course=course,
        topic=topic,
        score=score,
        event_metadata=meta,
    )
    await EvaluationService().record_event(db, user_id=user_id, payload=payload)
    logger.info(
        "[Path] node_completed: user_id=%s path_id=%s node_id=%s score=%s",
        user_id,
        path_id,
        node_id,
        score,
    )


# 记录节点测验答题事件到评估系统
async def record_path_quiz_answered_event(
    db: AsyncSession,
    user_id: int,
    path_id: int,
    path_node_id: int,
    node_id: int,
    course: str,
    topic: str,
    score: float,
    outcome: str = "completed",
    weak_knowledge_points: list[str] | None = None,
) -> None:
    """记录一次路径节点答题事件。

    区分于独立题库 ``quiz_submitted``。

    Args:
        db: 异步数据库会话。
        user_id: 用户 ID。
        path_id: 路径 ID。
        path_node_id: 路径节点内部 ID。
        node_id: 节点序号。
        course: 课程/路径标题。
        topic: 节点标题。
        score: 得分百分比（0-100）。
        outcome: 答题结果（completed / failed）。
        weak_knowledge_points: 薄弱知识点列表。
    """
    payload = LearningEventCreate(
        module=MODULE_PATH,
        entity_id=str(path_id),
        event_type=PATH_QUIZ_ANSWERED,
        course=course,
        topic=topic,
        score=score,
        event_metadata={
            "path_node_id": path_node_id,
            "node_id": node_id,
            "weak_knowledge_points": weak_knowledge_points or [],
            "outcome": outcome,
        },
    )
    await EvaluationService().record_event(db, user_id=user_id, payload=payload)
    logger.info(
        "[Path] quiz_answered: user_id=%s path_id=%s node_id=%s score=%s outcome=%s",
        user_id,
        path_id,
        node_id,
        score,
        outcome,
    )
