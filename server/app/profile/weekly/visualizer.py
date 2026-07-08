"""算法可视化模块 — 周摘要章节构建。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.logging import get_logger
from app.infra.models import LearningEvent
from app.profile.weekly.types import SectionResult

logger = get_logger(__name__)


async def build_visualizer_section(
    db: AsyncSession,
    user_id: int,
    week_start: datetime,
    week_end: datetime,
) -> SectionResult:
    """构建周摘要的「算法可视化」章节。

    Queries:
        - ``learning_events`` 中 module = ``visualizer`` 本周的事件记录。

    Returns:
        SectionResult 包含可视化运行统计和详情列表。
    """
    stmt = (
        select(LearningEvent)
        .where(
            LearningEvent.user_id == user_id,
            LearningEvent.module == "visualizer",
            LearningEvent.created_at >= week_start,
            LearningEvent.created_at <= week_end,
        )
        .order_by(LearningEvent.created_at.asc())
    )
    events = (await db.exec(stmt)).all()

    logger.info("Visualizer section — user=%d week=%s~%s events=%d", user_id, week_start.date(), week_end.date(), len(events))

    if not events:
        return SectionResult(
            markdown="本周无算法可视化记录。",
            stats={"visualizer_runs": 0, "visualizer_failures": 0},
            raw_length=0,
        )

    lines: list[str] = []
    failures = 0
    raw_parts: list[str] = []

    for ev in events:
        meta = ev.event_metadata or {}
        language = meta.get("language", "未知")
        success = meta.get("success", True)
        error_msg = meta.get("error_message", "")

        if not success:
            failures += 1
            status = f"失败：{error_msg}" if error_msg else "失败"
        else:
            status = "成功"

        line = f"- {ev.topic or '算法'}（{language}）— {status}"
        lines.append(line)
        raw_parts.append(str(ev.topic or ""))

    raw_text = " ".join(raw_parts)
    markdown = (
        f"运行 {len(events)} 次算法可视化（失败 {failures} 次）\n\n"
        + "\n".join(lines)
    )

    return SectionResult(
        markdown=markdown,
        stats={
            "visualizer_runs": len(events),
            "visualizer_failures": failures,
        },
        raw_length=len(raw_text),
    )
