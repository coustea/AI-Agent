"""题库查询 API。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, distinct
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.database import get_session
from app.infra.models import QuizQuestion
from app.infra.response import HttpResponse
from app.quiz.schemas import QuizReviewRequest, QuizReviewResponse
from app.quiz.service import quiz_review_service

router = APIRouter()


@router.get("/quiz-bank/questions")
async def list_quiz_questions(
    query: str | None = Query(default=None, max_length=200),
    subject: str | None = Query(default=None),
    subjects: list[str] | None = Query(default=None),
    difficulty: str | None = Query(default=None),
    type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """题库题目列表查询，支持筛选和分页。"""
    base = select(QuizQuestion)

    if query:
        base = base.where(QuizQuestion.content.ilike(f"%{query}%"))
    if subject:
        base = base.where(QuizQuestion.subject == subject)
    if subjects:
        base = base.where(QuizQuestion.subject.in_(subjects))
    if difficulty:
        base = base.where(QuizQuestion.difficulty == difficulty)
    if type:
        base = base.where(QuizQuestion.question_type == type)

    # 总数
    total = (await session.exec(
        select(func.count()).select_from(base.subquery())
    )).scalar() or 0

    # 分页
    items = (await session.exec(
        base.order_by(QuizQuestion.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )).scalars().all()

    # 聚合选项
    all_subjects = sorted({
        s for s in (await session.exec(
            select(distinct(QuizQuestion.subject))
        )).scalars().all() if s
    })
    all_difficulties = sorted({
        d for d in (await session.exec(
            select(distinct(QuizQuestion.difficulty))
        )).scalars().all() if d
    })
    all_types = sorted({
        t for t in (await session.exec(
            select(distinct(QuizQuestion.question_type))
        )).scalars().all() if t
    })

    return HttpResponse.success(data={
        "items": [
            {
                "id": q.question_id,
                "subject": q.subject,
                "subject_en": q.subject_en,
                "type": q.question_type,
                "difficulty": q.difficulty,
                "bloom_level": q.bloom_level,
                "content": q.content,
                "options": q.options_json,
                "answer": q.answer,
                "analysis": q.analysis,
                "knowledge_points": q.knowledge_points or [],
                "tags": q.tags or [],
                "language": q.language,
                "split": q.split,
            }
            for q in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "subjects": all_subjects,
        "difficulties": all_difficulties,
        "types": all_types,
    })


# ---------------------------------------------------------------------------
# AI 答案审查 API
# ---------------------------------------------------------------------------


@router.post("/quiz-review")
async def review_quiz_answer(
    request: QuizReviewRequest,
) -> QuizReviewResponse:
    """AI 审查主观题答案（填空题、简答题）。"""
    result = await quiz_review_service.review(
        question_type=request.question_type,
        question_content=request.question_content,
        standard_answer=request.standard_answer,
        user_answer=request.user_answer,
        knowledge_points=request.knowledge_points,
    )
    return QuizReviewResponse(**result)