"""错题本 API — 提供错题的增删查改、归档和随机重练功能。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, delete
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.database import get_session
from app.infra.models import WrongQuestion, QuizQuestion, User
from app.infra.response import HttpResponse
from app.auth.security import get_current_user
from app.quiz.wrong_schemas import (
    WrongQuestionCreate,
    WrongQuestionRead,
    WrongQuestionListResponse,
)

router = APIRouter()


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


@router.post("/wrong-questions")
async def add_wrong_question(
    request: WrongQuestionCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> HttpResponse:
    """添加错题（若已存在则更新错误次数，不存在则从题库快照创建）。"""
    user_id = current_user.id

    # 查找是否已存在相同的错题记录
    existing = (await session.exec(
        select(WrongQuestion).where(
            WrongQuestion.user_id == user_id,
            WrongQuestion.question_id == request.question_id,
        )
    )).scalars().first()

    if existing:
        # 已存在：递增错误次数，更新用户答案，取消归档
        existing.wrong_count += 1
        existing.user_answer = request.user_answer
        existing.is_archived = False
        existing.updated_at = func.now()
        await session.commit()
        await session.refresh(existing)
        return HttpResponse.success(data={"id": existing.id, "action": "updated"})

    # 不存在：从题库获取题目快照，创建新的错题记录
    quiz = (await session.exec(
        select(QuizQuestion).where(QuizQuestion.question_id == request.question_id)
    )).scalars().first()

    if not quiz:
        return HttpResponse.error(code=404, message="题目不存在")

    # 从题库快照创建错题记录，保留题目原始内容
    wrong = WrongQuestion(
        user_id=user_id,
        question_id=quiz.question_id,
        subject=quiz.subject,
        question_type=quiz.question_type,
        content=quiz.content,
        options_json=quiz.options_json,
        standard_answer=quiz.answer,
        analysis=quiz.analysis,
        user_answer=request.user_answer,
        wrong_count=1,
    )
    session.add(wrong)
    await session.commit()
    await session.refresh(wrong)

    return HttpResponse.success(data={"id": wrong.id, "action": "created"})


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
