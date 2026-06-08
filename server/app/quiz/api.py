from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import get_current_user
from app.infra.database import get_session
from app.infra.models import User
from app.infra.response import HttpResponse
from app.quiz.service import quiz_bank_service

router = APIRouter()


@router.get("/quiz-bank/questions")
async def list_quiz_bank_questions(
    query: str | None = Query(default=None),
    subject: str | None = Query(default=None),
    subjects: list[str] | None = Query(default=None),
    difficulty: str | None = Query(default=None),
    question_type: str | None = Query(default=None, alias="type"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    _ = current_user
    result = await quiz_bank_service.list_questions(
        session,
        query=query,
        subject=subject,
        subjects=subjects,
        difficulty=difficulty,
        question_type=question_type,
        page=page,
        page_size=page_size,
    )
    return HttpResponse.success(data=result.model_dump(mode="json"))
