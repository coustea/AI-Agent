"""资源生成模块 — 周摘要章节构建。"""

# 聚合本周生成的资源及其项目，生成章节统计
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.logging import get_logger
from app.infra.models import GeneratedResource, GeneratedResourceItem
from app.profile.weekly.types import SectionResult

logger = get_logger(__name__)


# 构建周摘要的「资源生成」章节
async def build_resource_section(
    db: AsyncSession,
    user_id: int,
    week_start: datetime,
    week_end: datetime,
) -> SectionResult:
    """构建周摘要的「资源生成」章节。

    Queries:
        - ``generated_resources`` 本周生成的资源。
        - ``generated_resource_items`` 对应的资源项目。

    Returns:
        SectionResult 包含资源列表和生成统计。
    """
    res_stmt = (
        select(GeneratedResource)
        .where(
            GeneratedResource.user_id == user_id,
            GeneratedResource.created_at >= week_start,
            GeneratedResource.created_at <= week_end,
        )
        .order_by(GeneratedResource.created_at.asc())
    )
    resources = (await db.exec(res_stmt)).all()

    logger.info("Resource section — user=%d week=%s~%s resources=%d", user_id, week_start.date(), week_end.date(), len(resources))

    if not resources:
        return SectionResult(
            markdown="本周无资源生成记录。",
            stats={"resources_generated": 0, "resources_completed": 0},
            raw_length=0,
        )

    # 查询资源对应的资源项目（含 agent 类型）
    res_ids = [r.id for r in resources]
    item_stmt = (
        select(GeneratedResourceItem.resource_id, GeneratedResourceItem.agent_type)
        .where(GeneratedResourceItem.resource_id.in_(res_ids))
    )
    items = (await db.exec(item_stmt)).all()

    # 按资源 ID 归并 agent 类型
    type_by_res: dict[int, list[str]] = {}
    for item in items:
        rid, atype = item[0], item[1]
        if rid not in type_by_res:
            type_by_res[rid] = []
        type_by_res[rid].append(atype)

    # 统计已完成资源数量
    completed = sum(1 for r in resources if r.status == "completed")

    lines: list[str] = []
    raw_parts: list[str] = []

    for r in resources:
        need = r.learning_need or "未指定"
        status = r.status or "unknown"
        agent_types = type_by_res.get(r.id, [])
        type_str = f"，类型：{', '.join(agent_types)}" if agent_types else ""
        line = f"- 学习需求：{need}（状态：{status}{type_str}）"
        lines.append(line)
        raw_parts.append(str(r.learning_need or ""))

    raw_text = " ".join(raw_parts)
    markdown = f"共生成 {len(resources)} 个资源（{completed} 个已完成）\n\n" + "\n".join(lines)

    return SectionResult(
        markdown=markdown,
        stats={
            "resources_generated": len(resources),
            "resources_completed": completed,
        },
        raw_length=len(raw_text),
    )
