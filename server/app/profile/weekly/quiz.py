"""答题模块 — 周摘要章节构建。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.models import PathNodeQuestion
from app.profile.weekly.types import SectionResult


async def build_quiz_section(
    db: AsyncSession,
    user_id: int,
    week_start: datetime,
    week_end: datetime,
) -> SectionResult:
    """构建周摘要的「答题情况」章节。

    Queries:
        - ``path_node_questions`` 本周提交的答题记录。

    Returns:
        SectionResult 包含答题统计和薄弱知识点。
    """
    stmt = (
        select(PathNodeQuestion)
        .where(
            PathNodeQuestion.user_id == user_id,
            PathNodeQuestion.submitted_at >= week_start,
            PathNodeQuestion.submitted_at <= week_end,
        )
    )
    questions = (await db.exec(stmt)).all()

    if not questions:
        return SectionResult(
            markdown="本周无答题记录。",
            stats={"quiz_total": 0, "quiz_correct": 0, "accuracy": 0},
            raw_length=0,
        )

    total = len(questions)
    correct = sum(1 for q in questions if q.is_correct)
    accuracy = round(correct / total * 100) if total else 0

    wrong_kps: list[str] = []
    for q in questions:
        if q.is_correct is False and q.knowledge_points:
            wrong_kps.extend(q.knowledge_points)

    wrong_kp_str = "、".join(sorted(set(wrong_kps))) if wrong_kps else "无"

    markdown = (
        f"共 {total} 道，正确 {correct} 道，正确率 {accuracy}%\n\n"
        f"错题涉及知识点：{wrong_kp_str}"
    )

    raw_text = f"{total} {correct} {' '.join(wrong_kps)}"

    return SectionResult(
        markdown=markdown,
        stats={
            "quiz_total": total,
            "quiz_correct": correct,
            "accuracy": accuracy,
        },
        raw_length=len(raw_text),
    )
