"""错题本 API — 添加、查询、归档错题记录。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func, insert as sa_insert
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import get_current_user
from app.infra.database import get_session
from app.infra.models import User, WrongQuestion, QuizQuestion
from app.infra.response import HttpResponse

router = APIRouter()


class AddWrongQuestionRequest(BaseModel):
    question_id: str
    user_answer: str | None = None


@router.post("/wrong-questions")
async def add_wrong_question(
    request: AddWrongQuestionRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """添加错题记录。若已存在则累加 wrong_count。"""
    quiz = (await session.exec(
        select(QuizQuestion).where(QuizQuestion.question_id == request.question_id)
    )).scalars().first()

    if not quiz:
        return HttpResponse.error(code=404, message="题目不存在")

    stmt = sa_insert(WrongQuestion).values(
        user_id=current_user.id,
        question_id=request.question_id,
        subject=quiz.subject,
        question_type=quiz.question_type,
        content=quiz.content,
        options_json=quiz.options_json,
        standard_answer=quiz.answer,
        analysis=quiz.analysis,
        user_answer=request.user_answer,
        wrong_count=1,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["user_id", "question_id"],
        set_={
            "wrong_count": WrongQuestion.wrong_count + 1,
            "user_answer": request.user_answer,
            "updated_at": func.now(),
        },
    )
    await session.exec(stmt)  # type: ignore[arg-type]
    await session.commit()
    return HttpResponse.success(message="已记录错题")


@router.get("/wrong-questions")
async def list_wrong_questions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """查询当前用户的错题列表。"""
    base = select(WrongQuestion).where(
        WrongQuestion.user_id == current_user.id,
        WrongQuestion.is_archived == False,  # noqa: E712
    )

    total = (await session.exec(
        select(func.count()).select_from(base.subquery())
    )).scalar() or 0

    items = (await session.exec(
        base.order_by(WrongQuestion.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )).scalars().all()

    return HttpResponse.success(data={
        "items": [
            {
                "id": w.id,
                "question_id": w.question_id,
                "subject": w.subject,
                "question_type": w.question_type,
                "content": w.content,
                "options_json": w.options_json,
                "standard_answer": w.standard_answer,
                "analysis": w.analysis,
                "user_answer": w.user_answer,
                "wrong_count": w.wrong_count,
                "note": w.note,
                "created_at": w.created_at.isoformat() if w.created_at else None,
                "updated_at": w.updated_at.isoformat() if w.updated_at else None,
            }
            for w in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.put("/wrong-questions/{wrong_id}/archive")
async def archive_wrong_question(
    wrong_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """归档（移除）错题记录。"""
    wq = (await session.exec(
        select(WrongQuestion).where(
            WrongQuestion.id == wrong_id,
            WrongQuestion.user_id == current_user.id,
        )
    )).scalars().first()

    if not wq:
        return HttpResponse.error(code=404, message="错题记录不存在")

    wq.is_archived = True  # type: ignore[assignment]
    session.add(wq)
    await session.commit()
    return HttpResponse.success(message="已归档")
