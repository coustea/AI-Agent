"""路径学习模块 — 周摘要章节构建。"""

# 聚合本周路径节点的接触与完成情况，生成章节统计
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import or_ as sa_or
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.logging import get_logger
from app.infra.models import PathNode
from app.profile.weekly.types import SectionResult

logger = get_logger(__name__)


# 构建周摘要的「路径学习」章节
async def build_path_section(
    db: AsyncSession,
    user_id: int,
    week_start: datetime,
    week_end: datetime,
) -> SectionResult:
    """构建周摘要的「路径学习」章节。

    Queries:
        - ``path_nodes`` 本周活跃的路径节点。

    Returns:
        SectionResult 包含节点列表和完成统计。
    """
    stmt = (
        select(PathNode)
        .where(
            PathNode.user_id == user_id,
            sa_or(
                PathNode.started_at.is_not(None),
                PathNode.completed_at.is_not(None),
            ),
            sa_or(
                PathNode.started_at.between(week_start, week_end),
                PathNode.completed_at.between(week_start, week_end),
            ),
        )
    )
    nodes = (await db.exec(stmt)).all()

    logger.info("Path section — user=%d week=%s~%s nodes=%d", user_id, week_start.date(), week_end.date(), len(nodes))

    if not nodes:
        return SectionResult(
            markdown="本周无路径学习记录。",
            stats={"nodes_touched": 0, "nodes_completed": 0},
            raw_length=0,
        )

    # 统计已完成的节点
    completed = [n for n in nodes if n.status == "completed"]

    lines: list[str] = []
    raw_parts: list[str] = []
    for n in nodes:
        diff = n.difficulty or "未指定"
        attempt = n.attempt_count or 0
        line = (
            f"- 节点「{n.title}」— 状态：{n.status}，"
            f"难度：{diff}，尝试次数：{attempt}"
        )
        lines.append(line)
        raw_parts.append(str(n.title or ""))

    raw_text = " ".join(raw_parts)
    markdown = (
        f"接触 {len(nodes)} 个节点，完成 {len(completed)} 个\n\n"
        + "\n".join(lines)
    )

    # courses_active：去重后的节点标题集合
    course_titles = sorted({str(n.title) for n in nodes if n.title})

    return SectionResult(
        markdown=markdown,
        stats={
            "nodes_touched": len(nodes),
            "nodes_completed": len(completed),
            "course_titles": course_titles,
        },
        raw_length=len(raw_text),
    )
