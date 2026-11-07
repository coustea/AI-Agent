"""算法可视化模块事件埋点。

在用户运行可视化后异步记录 ``visualizer_run`` 事件到 ``learning_events`` 表，
供学习评估按时间窗口聚合统计。
"""

from __future__ import annotations

from sqlmodel.ext.asyncio.session import AsyncSession

from app.evaluation.event_types import MODULE_VISUALIZER, VISUALIZER_RUN
from app.evaluation.schemas import LearningEventCreate
from app.evaluation.service import EvaluationService
from app.infra.logging import get_logger

logger = get_logger(__name__)


# 记录一次算法可视化运行事件到 learning_events 表，供学习评估聚合
async def record_visualizer_run_event(
    db: AsyncSession,
    user_id: int,
    template_key: str,
    success: bool,
    error_message: str | None = None,
) -> None:
    """记录一次算法可视化运行事件。

    Args:
        db: 异步数据库会话。
        user_id: 用户 ID。
        template_key: 算法模板 key（如 ``bubble_sort``）。
        success: 是否运行成功。
        error_message: 失败时的错误信息（成功时为 None）。
    """
    # 构造学习事件负载（含成功与否、错误信息）
    payload = LearningEventCreate(
        module=MODULE_VISUALIZER,
        entity_id=template_key,
        event_type=VISUALIZER_RUN,
        topic=template_key,
        event_metadata={
            "success": success,
            "error_message": error_message,
        },
    )
    # 写入学习事件表
    await EvaluationService().record_event(db, user_id=user_id, payload=payload)
    logger.info(
        "[Visualizer] event recorded: user_id=%s template=%s success=%s",
        user_id,
        template_key,
        success,
    )
