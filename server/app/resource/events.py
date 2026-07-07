"""资源生成模块事件埋点。

在资源生成完成（或失败）后记录 ``resource_generated`` 事件到 ``learning_events`` 表，
供画像评分按时间窗口聚合统计。
"""

from __future__ import annotations

from typing import Sequence

from sqlmodel.ext.asyncio.session import AsyncSession

from app.evaluation.event_types import MODULE_RESOURCE, RESOURCE_GENERATED
from app.evaluation.request import LearningEventCreate
from app.evaluation.service import EvaluationService
from app.infra.logging import get_logger

logger = get_logger(__name__)


async def record_resource_generated_event(
    db: AsyncSession,
    user_id: int,
    resource_id: int,
    status: str,
    course: str | None = None,
    topic: str | None = None,
    agent_types: Sequence[str] | None = None,
) -> None:
    """记录一次资源生成事件。

    Args:
        db: 异步数据库会话。
        user_id: 用户 ID。
        resource_id: 资源 ID。
        status: 生成状态（completed / partial_completed / failed）。
        course: 可选的学习课程/科目。
        topic: 可选的学习主题。
        agent_types: 成功生成的智能体类型列表。
    """
    payload = LearningEventCreate(
        module=MODULE_RESOURCE,
        entity_id=str(resource_id),
        event_type=RESOURCE_GENERATED,
        course=course,
        topic=topic,
        event_metadata={
            "resource_id": resource_id,
            "status": status,
            "agent_types": list(agent_types) if agent_types else [],
        },
    )
    await EvaluationService().record_event(db, user_id=user_id, payload=payload)
    logger.info(
        "[Resource] event recorded: user_id=%s resource_id=%s status=%s",
        user_id,
        resource_id,
        status,
    )
