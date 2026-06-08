"""题库查询 API。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, distinct
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.database import get_session
from app.infra.models import QuizQuestion, ProgrammingProblem
from app.infra.response import HttpResponse

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
# 编程题 API
# ---------------------------------------------------------------------------


@router.get("/programming-problems")
async def list_programming_problems(
    query: str | None = Query(default=None, max_length=200),
    difficulty: str | None = Query(default=None),
    category: str | None = Query(default=None),
    tag: list[str] | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """编程题列表查询，支持筛选和分页。"""
    base = select(ProgrammingProblem)

    if query:
        base = base.where(
            ProgrammingProblem.title.ilike(f"%{query}%")
            | ProgrammingProblem.description.ilike(f"%{query}%")
        )
    if difficulty:
        base = base.where(ProgrammingProblem.difficulty == difficulty)
    if category:
        base = base.where(ProgrammingProblem.category == category)
    if tag:
        base = base.where(ProgrammingProblem.tags.contains(tag))

    total = (await session.exec(
        select(func.count()).select_from(base.subquery())
    )).scalar() or 0

    items = (await session.exec(
        base.order_by(ProgrammingProblem.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )).scalars().all()

    all_difficulties = sorted({
        d for d in (await session.exec(
            select(distinct(ProgrammingProblem.difficulty))
        )).scalars().all() if d
    })
    all_categories = sorted({
        c for c in (await session.exec(
            select(distinct(ProgrammingProblem.category))
        )).scalars().all() if c
    })
    all_tags = sorted({
        t for row in (await session.exec(
            select(distinct(ProgrammingProblem.tags))
        )).scalars().all() if row for t in (row or [])
    })

    return HttpResponse.success(data={
        "items": [
            {
                "id": p.problem_slug,
                "title": p.title,
                "difficulty": p.difficulty,
                "category": p.category,
                "tags": p.tags or [],
            }
            for p in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "difficulties": all_difficulties,
        "categories": all_categories,
        "tags": all_tags,
    })


@router.get("/programming-problems/{problem_slug}")
async def get_programming_problem(
    problem_slug: str,
    session: AsyncSession = Depends(get_session),
):
    """获取编程题详情。"""
    result = await session.exec(
        select(ProgrammingProblem).where(
            ProgrammingProblem.problem_slug == problem_slug
        )
    )
    problem = result.scalars().first()

    if not problem:
        return HttpResponse.error(code=404, message="编程题不存在")

    return HttpResponse.success(data={
        "id": problem.problem_slug,
        "title": problem.title,
        "difficulty": problem.difficulty,
        "category": problem.category,
        "description": problem.description,
        "input_format": problem.input_format,
        "output_format": problem.output_format,
        "examples": problem.examples or [],
        "hints": problem.hints or [],
        "code_snippets": problem.code_snippets or {},
        "test_cases": problem.test_cases or [],
        "tags": problem.tags or [],
    })