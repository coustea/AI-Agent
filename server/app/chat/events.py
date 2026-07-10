"""chat 模块事件埋点 — chat_dialogue。

在每轮 SSE 对话成功完成后记录事件。``summary_md`` 取该 session 最新一条
``ChatSessionSummaryBlock.summary_markdown``（可能是上一轮压缩的），
保证不依赖异步压缩任务的时序。
"""

from __future__ import annotations

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.evaluation.event_types import CHAT_DIALOGUE, MODULE_CHAT
from app.evaluation.request import LearningEventCreate
from app.evaluation.service import EvaluationService
from app.infra.logging import get_logger
from app.infra.models import ChatSessionSummaryBlock

logger = get_logger(__name__)


# 记录一次辅导对话事件，用于学习行为埋点统计
async def record_dialogue_event(
    db: AsyncSession,
    user_id: int,
    session_id: str,
    summary_md: str | None = None,
    turn_count: int = 1,
) -> None:
    """记录一次辅导对话事件。

    Args:
        db: 异步数据库会话。
        user_id: 用户 ID。
        session_id: 会话 ID（UUID 字符串）。
        summary_md: 可选的会话压缩摘要；为 None 时尝试从最新 ChatSessionSummaryBlock 取。
        turn_count: 本轮对话包含的消息数（默认 1）。
    """
    # 未传入摘要时，从最近一次会话压缩摘要块中获取
    if summary_md is None:
        summary_md = await _fetch_latest_summary(db, session_id)

    # 构造对话事件负载并提交到评估服务
    payload = LearningEventCreate(
        module=MODULE_CHAT,
        entity_id=session_id,
        event_type=CHAT_DIALOGUE,
        event_metadata={
            "summary_md": summary_md or "",
            "summary_length": len(summary_md or ""),
            "turn_count": turn_count,
        },
    )
    await EvaluationService().record_event(db, user_id=user_id, payload=payload)
    logger.info(
        "[Chat] 对话事件已记录: user_id=%s session=%s summary_len=%s",
        user_id,
        session_id,
        len(summary_md or ""),
    )


# 查询指定会话的最新压缩摘要，无则返回空字符串
async def _fetch_latest_summary(db: AsyncSession, session_id: str) -> str:
    """从 chat_session_summary_blocks 取最新一条 summary_markdown，无则空字符串。"""
    stmt = (
        select(ChatSessionSummaryBlock.summary_markdown)
        .where(ChatSessionSummaryBlock.session_id == session_id)
        .order_by(ChatSessionSummaryBlock.created_at.desc())
        .limit(1)
    )
    # 执行查询并返回最新摘要（可能为空）
    result = await db.exec(stmt)
    row = result.first()
    return row or ""
