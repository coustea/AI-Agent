"""题库查询 API。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, distinct
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import get_current_user
from app.infra.database import get_session
from app.infra.models import QuizQuestion, WrongQuestion, User
from app.infra.response import HttpResponse
from app.quiz.schemas import (
    QuizReviewRequest, 
    QuizReviewResponse,
    ObjectiveSubmitRequest,
    ObjectiveSubmitResponse,
    WrongQuestionRead,
    WrongQuestionListResponse,
)
from app.quiz.service import quiz_review_service

router = APIRouter()  # 题库模块路由，挂载在 /api/v1/ai/quiz-bank/ 下


@router.get("/quiz-bank/questions")  # GET 题库题目列表查询，支持筛选和分页
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


@router.post("/quiz-bank/review-subjective")  # POST AI 审查主观题答案（分析题、简答题）
async def review_quiz_answer(
    request: QuizReviewRequest,
) -> QuizReviewResponse:
    """AI 审查主观题答案（分析题、简答题）。"""
    result = await quiz_review_service.review(
        question_type=request.question_type,
        question_content=request.question_content,
        standard_answer=request.standard_answer,
        user_answer=request.user_answer,
        knowledge_points=request.knowledge_points,
    )
    return QuizReviewResponse(**result)


@router.post("/quiz-bank/submit-objective")
async def submit_objective_results(
    request: ObjectiveSubmitRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> HttpResponse:
    """客观题判卷结果提交与错题本自动收录。"""
    user_id = current_user.id
    wrong_saved_count = 0

    for result in request.results:
        if result.is_correct:
            continue

        # 尝试从数据库中查询已有错题
        existing = (await session.exec(
            select(WrongQuestion).where(
                WrongQuestion.user_id == user_id,
                WrongQuestion.question_id == result.question_id,
            )
        )).scalars().first()

        if existing:
            existing.wrong_count += 1
            existing.user_answer = result.user_answer
            existing.is_archived = False
            existing.updated_at = func.now()
            wrong_saved_count += 1
            continue

        # 尝试从题库获取原始题目
        quiz = (await session.exec(
            select(QuizQuestion).where(QuizQuestion.question_id == result.question_id)
        )).scalars().first()

        if quiz:
            wrong = WrongQuestion(
                user_id=user_id,
                question_id=quiz.question_id,
                subject=quiz.subject,
                question_type=quiz.question_type,
                content=quiz.content,
                options_json=quiz.options_json,
                standard_answer=quiz.answer,
                analysis=quiz.analysis,
                user_answer=result.user_answer,
                wrong_count=1,
            )
            session.add(wrong)
            wrong_saved_count += 1
        elif result.content:
            # 题库中不存在（可能是动态生成的），但前端传了题目快照
            wrong = WrongQuestion(
                user_id=user_id,
                question_id=result.question_id,
                subject=result.subject or "未知科目",
                question_type=result.question_type or "客观题",
                content=result.content,
                options_json=result.options,
                standard_answer=result.answer,
                analysis=result.analysis,
                user_answer=result.user_answer,
                wrong_count=1,
            )
            session.add(wrong)
            wrong_saved_count += 1
    
    await session.commit()

    return HttpResponse.success(data=ObjectiveSubmitResponse(
        processed_count=len(request.results),
        wrong_saved_count=wrong_saved_count
    ).model_dump())


# ---------------------------------------------------------------------------
# 错题本 API
# ---------------------------------------------------------------------------


@router.get("/wrong-questions")
async def list_wrong_questions(
    subject: str | None = Query(default=None),
    question_type: str | None = Query(default=None),
    is_archived: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> WrongQuestionListResponse:
    """获取当前用户的错题列表（支持科目/类型筛选、分页、归档过滤）。"""
    user_id = current_user.id

    # 构建基础查询条件
    base = select(WrongQuestion).where(
        WrongQuestion.user_id == user_id,
        WrongQuestion.is_archived == is_archived,
    )

    # 可选的科目和题目类型筛选
    if subject:
        base = base.where(WrongQuestion.subject == subject)
    if question_type:
        base = base.where(WrongQuestion.question_type == question_type)

    # 统计符合条件的总数
    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await session.exec(count_stmt)).scalar() or 0

    # 分页查询
    items_raw = (await session.exec(
        base.order_by(WrongQuestion.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )).scalars().all()

    items = [_to_read(item) for item in items_raw]

    # 聚合可用的科目和类型选项（用于前端筛选下拉框）
    subjects_stmt = select(func.distinct(WrongQuestion.subject)).where(
        WrongQuestion.user_id == user_id,
        WrongQuestion.is_archived == is_archived,
    )
    subjects = sorted([s for s in (await session.exec(subjects_stmt)).scalars().all() if s])

    types_stmt = select(func.distinct(WrongQuestion.question_type)).where(
        WrongQuestion.user_id == user_id,
        WrongQuestion.is_archived == is_archived,
    )
    types = sorted([t for t in (await session.exec(types_stmt)).scalars().all() if t])

    return WrongQuestionListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        subjects=subjects,
        types=types,
    )


@router.delete("/wrong-questions/{wrong_id}")
async def remove_wrong_question(
    wrong_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> HttpResponse:
    """物理删除错题记录。"""
    user_id = current_user.id

    wrong = (await session.exec(
        select(WrongQuestion).where(
            WrongQuestion.id == wrong_id,
            WrongQuestion.user_id == user_id,
        )
    )).scalars().first()

    if not wrong:
        return HttpResponse.error(code=404, message="错题记录不存在")

    await session.delete(wrong)
    await session.commit()

    return HttpResponse.success(message="已移除")


@router.post("/wrong-questions/{wrong_id}/archive")
async def archive_wrong_question(
    wrong_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> HttpResponse:
    """归档错题（答对后移入归档，不再出现在活跃错题列表中）。"""
    user_id = current_user.id

    wrong = (await session.exec(
        select(WrongQuestion).where(
            WrongQuestion.id == wrong_id,
            WrongQuestion.user_id == user_id,
        )
    )).scalars().first()

    if not wrong:
        return HttpResponse.error(code=404, message="错题记录不存在")

    wrong.is_archived = True
    await session.commit()

    return HttpResponse.success(message="已归档")


@router.post("/wrong-questions/{wrong_id}/unarchive")
async def unarchive_wrong_question(
    wrong_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> HttpResponse:
    """取消归档（将错题恢复到活跃错题列表中）。"""
    user_id = current_user.id

    wrong = (await session.exec(
        select(WrongQuestion).where(
            WrongQuestion.id == wrong_id,
            WrongQuestion.user_id == user_id,
        )
    )).scalars().first()

    if not wrong:
        return HttpResponse.error(code=404, message="错题记录不存在")

    wrong.is_archived = False
    await session.commit()

    return HttpResponse.success(message="已恢复")


@router.get("/wrong-questions/random")
async def get_random_wrong_question(
    subject: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> HttpResponse:
    """随机获取一道未归档的错题用于重练。"""
    user_id = current_user.id

    base = select(WrongQuestion).where(
        WrongQuestion.user_id == user_id,
        WrongQuestion.is_archived == False,
    )

    if subject:
        base = base.where(WrongQuestion.subject == subject)

    # 查询所有符合条件的错题
    items = (await session.exec(base)).scalars().all()
    if not items:
        return HttpResponse.success(data=None)

    # 随机选择一道
    import random
    item = random.choice(items)

    return HttpResponse.success(data=_to_read(item))


def _to_read(item: WrongQuestion) -> WrongQuestionRead:
    """将 ORM 对象转换为 API 响应 DTO。"""
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