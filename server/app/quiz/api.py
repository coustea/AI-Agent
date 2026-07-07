"""题库 API。"""

from __future__ import annotations

import random

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import get_current_user
from app.infra.logging import get_logger
from app.infra.database import get_session
from app.quiz.events import record_quiz_submit_event
from app.infra.models import QuizQuestion, School, User, WrongQuestion
from app.infra.response import HttpResponse
from app.quiz.schemas import (
    ObjectiveSubmitRequest,
    ObjectiveSubmitResponse,
    QuizReviewRequest,
    QuizReviewResponse,
    WrongQuestionListResponse,
    WrongQuestionRead,
)
from app.quiz.service import quiz_bank_service, quiz_review_service

logger = get_logger(__name__)

router = APIRouter()

# 408 四门科目
SUBJECTS_408 = ["数据结构与算法", "计算机组成原理", "计算机网络", "操作系统"]


# ---------------------------------------------------------------------------
# 学校 API
# ---------------------------------------------------------------------------


@router.get("/schools")
async def list_schools(
    tier: str | None = Query(default=None, description="院校层次：985/211/双一流/普通本科"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    """获取学校列表。"""
    stmt = select(School)
    count_stmt = select(func.count()).select_from(School)

    if tier:
        stmt = stmt.where(School.tier == tier)
        count_stmt = count_stmt.where(School.tier == tier)

    total = (await session.exec(count_stmt)).scalar() or 0
    items = (await session.exec(
        stmt.order_by(School.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )).scalars().all()

    return HttpResponse.success(data={
        "items": [{"name": s.name, "level": s.level, "tier": s.tier} for s in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


# ---------------------------------------------------------------------------
# 题库 API
# ---------------------------------------------------------------------------


@router.get("/quiz/stats")
async def get_quiz_stats(session: AsyncSession = Depends(get_session)):
    """获取 408 题库统计。"""
    stats = {}
    for subject in SUBJECTS_408:
        total = (await session.exec(
            select(func.count()).select_from(QuizQuestion).where(
                QuizQuestion.subject == subject
            )
        )).scalar() or 0

        type_rows = (await session.exec(
            select(QuizQuestion.question_type, func.count().label("c"))
            .where(QuizQuestion.subject == subject)
            .group_by(QuizQuestion.question_type)
        )).all()
        types = {t: c for t, c in type_rows}

        stats[subject] = {"total": total, "types": types}

    return HttpResponse.success(data={
        "subjects": SUBJECTS_408,
        "total": sum(s["total"] for s in stats.values()),
        "stats": stats,
    })


@router.get("/quiz")
async def list_quiz(
    query: str | None = Query(default=None, description="搜索关键词"),
    subject: str | None = Query(default=None, description="科目"),
    subjects: list[str] | None = Query(default=None, description="科目列表"),
    type: str | None = Query(default=None, description="题型"),
    difficulty: str | None = Query(default=None, description="难度"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """获取题目列表。"""
    result = await quiz_bank_service.list_questions(
        session=session,
        query=query,
        subject=subject,
        subjects=subjects,
        difficulty=difficulty,
        question_type=type,
        page=page,
        page_size=page_size,
    )
    return HttpResponse.success(data=result.model_dump())


# ---------------------------------------------------------------------------
# 答题 API
# ---------------------------------------------------------------------------


@router.post("/quiz/review")
async def review_answer(request: QuizReviewRequest) -> QuizReviewResponse:
    """AI 审查主观题答案。"""
    result = await quiz_review_service.review(
        question_type=request.question_type,
        question_content=request.question_content,
        standard_answer=request.standard_answer,
        user_answer=request.user_answer,
        knowledge_points=request.knowledge_points,
    )
    return QuizReviewResponse(**result)


@router.post("/quiz/submit")
async def submit_quiz(
    request: ObjectiveSubmitRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> HttpResponse:
    """提交客观题结果，自动收录错题。"""
    user_id = current_user.id
    wrong_count = 0

    for r in request.results:
        if r.is_correct:
            continue

        existing = (await session.exec(
            select(WrongQuestion).where(
                WrongQuestion.user_id == user_id,
                WrongQuestion.question_id == r.question_id,
            )
        )).scalars().first()

        if existing:
            existing.wrong_count += 1
            existing.user_answer = r.user_answer
            existing.is_archived = False
            wrong_count += 1
            continue

        quiz = (await session.exec(
            select(QuizQuestion).where(QuizQuestion.question_id == r.question_id)
        )).scalars().first()

        if quiz:
            session.add(WrongQuestion(
                user_id=user_id,
                question_id=quiz.question_id,
                subject=quiz.subject,
                question_type=quiz.question_type,
                content=quiz.content,
                options_json=quiz.options_json,
                standard_answer=quiz.answer,
                analysis=quiz.analysis,
                user_answer=r.user_answer,
                wrong_count=1,
            ))
            wrong_count += 1
        elif r.content:
            session.add(WrongQuestion(
                user_id=user_id,
                question_id=r.question_id,
                subject=r.subject or "未知",
                question_type=r.question_type or "客观题",
                content=r.content,
                options_json=r.options,
                standard_answer=r.answer,
                analysis=r.analysis,
                user_answer=r.user_answer,
                wrong_count=1,
            ))
            wrong_count += 1

    await session.commit()

    total = len(request.results)
    correct_count = sum(1 for r in request.results if r.is_correct)
    score = (correct_count / total * 100) if total > 0 else 0
    subject = request.results[0].subject if request.results else None
    try:
        await record_quiz_submit_event(
            db=session,
            user_id=user_id,
            total_count=total,
            correct_count=correct_count,
            score=score,
            subject=subject,
        )
    except Exception:
        logger.exception("Failed to record quiz_submitted event: user_id=%s", user_id)

    return HttpResponse.success(data=ObjectiveSubmitResponse(
        processed_count=total,
        wrong_saved_count=wrong_count,
    ).model_dump())


# ---------------------------------------------------------------------------
# 错题本 API
# ---------------------------------------------------------------------------


@router.get("/wrong")
async def list_wrong(
    subject: str | None = Query(default=None),
    type: str | None = Query(default=None),
    archived: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> WrongQuestionListResponse:
    """获取错题列表。"""
    user_id = current_user.id

    stmt = select(WrongQuestion).where(
        WrongQuestion.user_id == user_id,
        WrongQuestion.is_archived == archived,
    )

    if subject:
        stmt = stmt.where(WrongQuestion.subject == subject)
    if type:
        stmt = stmt.where(WrongQuestion.question_type == type)

    total = (await session.exec(
        select(func.count()).select_from(stmt.subquery())
    )).scalar() or 0

    items = (await session.exec(
        stmt.order_by(WrongQuestion.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )).scalars().all()

    return WrongQuestionListResponse(
        items=[_to_wrong_read(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        subjects=[],
        types=[],
    )


@router.get("/wrong/random")
async def get_wrong_random(
    subject: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> HttpResponse:
    """随机获取一道错题。"""
    user_id = current_user.id

    stmt = select(WrongQuestion).where(
        WrongQuestion.user_id == user_id,
        WrongQuestion.is_archived == False,
    )
    if subject:
        stmt = stmt.where(WrongQuestion.subject == subject)

    items = (await session.exec(stmt)).scalars().all()
    if not items:
        return HttpResponse.success(data=None)

    return HttpResponse.success(data=_to_wrong_read(random.choice(items)))


@router.post("/wrong/{wrong_id}/archive")
async def archive_wrong(
    wrong_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> HttpResponse:
    """归档错题。"""
    wrong = (await session.exec(
        select(WrongQuestion).where(
            WrongQuestion.id == wrong_id,
            WrongQuestion.user_id == current_user.id,
        )
    )).scalars().first()

    if not wrong:
        return HttpResponse.error(code=404, message="错题不存在")

    wrong.is_archived = True
    await session.commit()
    return HttpResponse.success(message="已归档")


@router.delete("/wrong/{wrong_id}")
async def delete_wrong(
    wrong_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> HttpResponse:
    """删除错题。"""
    wrong = (await session.exec(
        select(WrongQuestion).where(
            WrongQuestion.id == wrong_id,
            WrongQuestion.user_id == current_user.id,
        )
    )).scalars().first()

    if not wrong:
        return HttpResponse.error(code=404, message="错题不存在")

    await session.delete(wrong)
    await session.commit()
    return HttpResponse.success(message="已删除")


def _to_wrong_read(item: WrongQuestion) -> WrongQuestionRead:
    """转换 ORM 为响应 DTO。"""
    return WrongQuestionRead(
        id=item.id,
        question_id=item.question_id,
        subject=item.subject,
        question_type=item.question_type,
        content=item.content,
        options=item.options_json,
        standard_answer=item.standard_answer,
        analysis=item.analysis,
        user_answer=item.user_answer,
        wrong_count=item.wrong_count,
        note=item.note,
        is_archived=item.is_archived,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )
