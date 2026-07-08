"""辅导对话模块 — 周摘要章节构建。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.logging import get_logger
from app.infra.models import ChatSession, ChatSessionSummaryBlock
from app.profile.weekly.types import SectionResult

logger = get_logger(__name__)


async def build_chat_section(
    db: AsyncSession,
    user_id: int,
    week_start: datetime,
    week_end: datetime,
) -> SectionResult:
    """构建周摘要的「辅导对话」章节。

    Queries:
        - ``chat_session_summary_blocks`` 本周的对话摘要。

    Returns:
        SectionResult 包含对话摘要列表和轮次数统计。
    """
    stmt = (
        select(ChatSessionSummaryBlock.summary_markdown)
        .join(ChatSession, ChatSessionSummaryBlock.session_id == ChatSession.id)
        .where(
            ChatSession.user_id == user_id,
            ChatSessionSummaryBlock.created_at >= week_start,
            ChatSessionSummaryBlock.created_at <= week_end,
        )
        .order_by(ChatSessionSummaryBlock.created_at.asc())
    )
    rows = (await db.exec(stmt)).all()

    logger.info("Chat section — user=%d week=%s~%s summaries=%d", user_id, week_start.date(), week_end.date(), len(rows))

    if not rows:
        return SectionResult(
            markdown="本周无辅导对话记录。",
            stats={"dialogue_turns": 0},
            raw_length=0,
        )

    summary_count = len(rows)
    raw_text = "\n\n".join(str(r) for r in rows)
    parts = list(rows)

    markdown_parts: list[str] = []
    for i, summary in enumerate(parts[:5]):
        summary_str = str(summary).strip()
        if summary_str:
            markdown_parts.append(summary_str)

    if summary_count > 5:
        markdown_parts.append(f"... 及其他 {summary_count - 5} 轮对话摘要")

    markdown = (
        f"共 {summary_count} 轮辅导对话\n\n" + "\n\n---\n\n".join(markdown_parts)
        if markdown_parts
        else "本周无辅导对话记录。"
    )

    return SectionResult(
        markdown=markdown,
        stats={"dialogue_turns": summary_count},
        raw_length=len(raw_text),
    )
