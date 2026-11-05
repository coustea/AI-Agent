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
from app.infra.models import QuizQuestion, QuizAnswerHistory, School, User, WrongQuestion
from app.response import HttpResponse
from app.quiz.schemas import (
    ObjectiveQuestionResult,
    ObjectiveSubmitRequest,
    ObjectiveSubmitResponse,
    QuizAnswerHistoryItem,
    QuizAnswerHistoryResponse,
    QuizReviewBatchRequest,
    QuizReviewBatchResponse,
    QuizReviewRequest,
    QuizReviewResponse,
    WrongQuestionListResponse,
    WrongQuestionRead,
)
from app.quiz.service import quiz_bank_service, quiz_review_service

# 创建模块级日志器
logger = get_logger(__name__)

# 创建题库相关路由实例
router = APIRouter()

# 408 四门科目
SUBJECTS_408 = ["数据结构与算法", "计算机组成原理", "计算机网络", "操作系统"]


# ---------------------------------------------------------------------------
# 学校 API
# ---------------------------------------------------------------------------


# 学校列表查询接口（支持按层次筛选与分页）
@router.get("/schools")
async def list_schools(
    tier: str | None = Query(default=None, description="院校层次：985/211/双一流/普通本科"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    """获取学校列表。"""
    # 构建学校查询语句与计数语句
    stmt = select(School)
    count_stmt = select(func.count()).select_from(School)

    # 按院校层次过滤
    if tier:
        stmt = stmt.where(School.tier == tier)
        count_stmt = count_stmt.where(School.tier == tier)

    # 执行计数查询，获取学校总数
    total = (await session.exec(count_stmt)).scalar() or 0
    # 分页查询学校列表并按 id 排序
    items = (await session.exec(
        stmt.order_by(School.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )).scalars().all()

    # 返回学校列表及分页元信息
    return HttpResponse.success(data={
        "items": [{"name": s.name, "level": s.level, "tier": s.tier} for s in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


# ---------------------------------------------------------------------------
# 题库 API
# ---------------------------------------------------------------------------


# 408 题库统计接口（按科目统计题量与题型分布）
@router.get("/quiz/stats")
async def get_quiz_stats(session: AsyncSession = Depends(get_session)):
    """获取 408 题库统计。"""
    # 按科目聚合统计结果
    stats = {}
    for subject in SUBJECTS_408:
        # 统计该科目的题目总数
        total = (await session.exec(
            select(func.count()).select_from(QuizQuestion).where(
                QuizQuestion.subject == subject
            )
        )).scalar() or 0

        # 按题型分组统计数量
        type_rows = (await session.exec(
            select(QuizQuestion.question_type, func.count().label("c"))
            .where(QuizQuestion.subject == subject)
            .group_by(QuizQuestion.question_type)
        )).all()
        # 转换为题型-数量字典
        types = {t: c for t, c in type_rows}

        # 记录该科目的统计结果
        stats[subject] = {"total": total, "types": types}

    # 返回各科目统计及总体题量
    return HttpResponse.success(data={
        "subjects": SUBJECTS_408,
        "total": sum(s["total"] for s in stats.values()),
        "stats": stats,
    })


# 题目列表查询接口（委托题库服务执行筛选与分页）
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
    # 调用题库服务查询题目
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
    # 返回题目列表分页结果
    return HttpResponse.success(data=result.model_dump())


# ---------------------------------------------------------------------------
# 答题 API
# ---------------------------------------------------------------------------


# AI 主观题答案审查接口
@router.post("/quiz/review")
async def review_answer(request: QuizReviewRequest) -> QuizReviewResponse:
    """AI 审查主观题答案。"""
    logger.info("[QuizAPI] AI审查主观题: question_type=%s", request.question_type)
    # 调用 AI 审查服务评判用户答案
    result = await quiz_review_service.review(
        question_type=request.question_type,
        question_content=request.question_content,
        standard_answer=request.standard_answer,
        user_answer=request.user_answer,
        knowledge_points=request.knowledge_points,
    )
    logger.info("[QuizAPI] AI审查完成: question_type=%s score=%s is_correct=%s", request.question_type, result.get("score"), result.get("is_correct"))
    # 返回结构化审查结果
    return QuizReviewResponse(**result)


# 批量 AI 主观题答案审查接口（交卷等多题场景）
@router.post("/quiz/review/batch")
async def review_answers_batch(request: QuizReviewBatchRequest) -> HttpResponse:
    """批量审查主观题答案。

    服务端使用并发池限制 LLM 调用；填空题精确匹配会规则短路，不走模型。
    返回顺序与请求 items 一致。
    """
    logger.info("[QuizAPI] 批量审查: item_count=%s", len(request.items))
    results = await quiz_review_service.review_batch(
        [item.model_dump() for item in request.items]
    )
    payload = QuizReviewBatchResponse(
        results=[
            {
                "question_id": item["question_id"],
                "score": item["score"],
                "is_correct": item["is_correct"],
                "feedback": item["feedback"],
                "improvement_hints": item["improvement_hints"],
            }
            for item in results
        ]
    )
    return HttpResponse.success(data=payload.model_dump())


# 答题历史查询接口：获取用户做过的所有题目（支持分页和筛选）
@router.get("/quiz/history")
async def get_quiz_history(
    subject: str | None = Query(default=None, description="科目筛选"),
    is_correct: bool | None = Query(default=None, description="对错筛选"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> HttpResponse:
    """获取用户答题历史。返回每道做过的题的最新状态，支持分页和筛选。"""
    from sqlalchemy import func as sa_func

    user_id = current_user.id

    # 基础条件
    base_filters = [QuizAnswerHistory.user_id == user_id]
    if subject:
        base_filters.append(QuizAnswerHistory.subject == subject)

    # 子查询：先确定每个 question_id 的最新一条记录，再按最新状态筛选。
    latest_subq = (
        select(
            QuizAnswerHistory.question_id,
            sa_func.max(QuizAnswerHistory.id).label("max_id"),
        )
        .where(*base_filters)
        .group_by(QuizAnswerHistory.question_id)
        .subquery()
    )

    latest_stmt = select(QuizAnswerHistory).join(
        latest_subq,
        QuizAnswerHistory.id == latest_subq.c.max_id,
    )
    if is_correct is not None:
        latest_stmt = latest_stmt.where(QuizAnswerHistory.is_correct == is_correct)

    # 总数统计（按最新状态筛选后的题目数量）
    total = (await session.exec(
        select(sa_func.count()).select_from(latest_stmt.subquery())
    )).scalar() or 0

    # 联表获取最新记录的详细信息，分页
    stmt = (
        latest_stmt
        .order_by(QuizAnswerHistory.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await session.exec(stmt)).scalars().all()

    # 统计每个 question_id 的总做题次数（不受最新正确状态筛选影响）
    count_stmt = (
        select(
            QuizAnswerHistory.question_id,
            sa_func.count().label("cnt"),
        )
        .where(*base_filters)
        .group_by(QuizAnswerHistory.question_id)
    )
    count_rows = (await session.exec(count_stmt)).all()
    attempt_counts = {qid: cnt for qid, cnt in count_rows}

    items = [
        QuizAnswerHistoryItem(
            question_id=r.question_id,
            subject=r.subject,
            question_type=r.question_type,
            score=r.score,
            is_correct=r.is_correct,
            attempts=attempt_counts.get(r.question_id, 1),
            last_answer=r.user_answer,
            created_at=r.created_at,
        )
        for r in rows
    ]

    return HttpResponse.success(data=QuizAnswerHistoryResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    ).model_dump())


# 客观题提交接口：自动判卷并收录错题本
@router.post("/quiz/submit")
async def submit_quiz(
    request: ObjectiveSubmitRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> HttpResponse:
    """提交客观题结果，自动收录错题。"""
    logger.info("[QuizAPI] 提交客观题: user_id=%s question_count=%s", current_user.id, len(request.results))
    # 获取当前用户 ID 并初始化错题计数
    user_id = current_user.id
    wrong_count = 0
    submitted_results: list[tuple[ObjectiveQuestionResult, int, bool]] = []

    # 遍历每道题目的判卷结果
    for r in request.results:
        score = r.score if r.score is not None else (100 if r.is_correct else 0)
        is_correct = score >= 60 if r.score is not None else r.is_correct
        submitted_results.append((r, score, is_correct))

        # 保存答题历史（所有题目，无论对错）
        session.add(QuizAnswerHistory(
            user_id=user_id,
            question_id=r.question_id,
            subject=r.subject,
            question_type=r.question_type,
            user_answer=r.user_answer,
            score=score,
            is_correct=is_correct,
        ))

        # 答对的题目直接跳过，不收录错题本
        if is_correct:
            continue

        # 查询该题是否已存在于错题本
        existing = (await session.exec(
            select(WrongQuestion).where(
                WrongQuestion.user_id == user_id,
                WrongQuestion.question_id == r.question_id,
            )
        )).scalars().first()

        # 已存在则累加错误次数并更新用户答案、取消归档
        if existing:
            existing.wrong_count += 1
            existing.user_answer = r.user_answer
            existing.is_archived = False
            wrong_count += 1
            continue

        # 从题库中查找原题信息
        quiz = (await session.exec(
            select(QuizQuestion).where(QuizQuestion.question_id == r.question_id)
        )).scalars().first()

        # 题库中存在原题：写入完整错题记录
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
        # 题库中无原题：使用前端传回的快照创建错题
        elif r.content:
            # 前端可能传中文标签，需转换为英文键以保持一致
            from app.quiz.service import QuizBankService
            raw_type = r.question_type or "客观题"
            normalized_type = QuizBankService._TYPE_LABEL_TO_KEY.get(raw_type, raw_type)
            session.add(WrongQuestion(
                user_id=user_id,
                question_id=r.question_id,
                subject=r.subject or "未知",
                question_type=normalized_type,
                content=r.content,
                options_json=r.options,
                standard_answer=r.answer,
                analysis=r.analysis,
                user_answer=r.user_answer,
                wrong_count=1,
            ))
            wrong_count += 1

    # 提交数据库，保存错题记录
    await session.commit()

    # 记录逐题答题事实用于学习评估聚合，失败不影响主流程
    total = len(request.results)
    try:
        for index, (result, score, is_correct) in enumerate(submitted_results, start=1):
            await record_quiz_submit_event(
                db=session,
                user_id=user_id,
                score=score,
                is_correct=is_correct,
                attempt_index=index,
                subject=result.subject,
                question_id=result.question_id,
                question_type=result.question_type,
            )
    except Exception:
        logger.exception("记录 quiz_submitted 事件失败: user_id=%s", user_id)

    # 返回处理结果
    logger.info("[QuizAPI] 提交完成: user_id=%s total=%s wrong_saved=%s", user_id, total, wrong_count)
    return HttpResponse.success(data=ObjectiveSubmitResponse(
        processed_count=total,
        wrong_saved_count=wrong_count,
    ).model_dump())


# ---------------------------------------------------------------------------
# 错题本 API
# ---------------------------------------------------------------------------


# 错题列表查询接口（支持科目、题型、归档状态筛选）
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
    # 获取当前用户 ID
    user_id = current_user.id

    # 基础查询：当前用户且匹配归档状态
    stmt = select(WrongQuestion).where(
        WrongQuestion.user_id == user_id,
        WrongQuestion.is_archived == archived,
    )

    # 按科目筛选
    if subject:
        stmt = stmt.where(WrongQuestion.subject == subject)
    # 按题型筛选（兼容中英文标签）
    if type:
        # 前端传中文标签，需兼容英文键和中文标签两种存储格式
        from app.quiz.service import QuizBankService
        db_type = QuizBankService._TYPE_LABEL_TO_KEY.get(type, type)
        stmt = stmt.where(
            (WrongQuestion.question_type == type) | (WrongQuestion.question_type == db_type)
        )

    # 统计符合筛选条件的错题总数
    total = (await session.exec(
        select(func.count()).select_from(stmt.subquery())
    )).scalar() or 0

    # 分页查询错题列表，按更新时间倒序
    items = (await session.exec(
        stmt.order_by(WrongQuestion.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )).scalars().all()

    # 返回错题列表分页响应
    return WrongQuestionListResponse(
        items=[_to_wrong_read(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        subjects=[],
        types=[],
    )


# 随机抽题接口：从未归档错题中随机返回一道
@router.get("/wrong/random")
async def get_wrong_random(
    subject: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> HttpResponse:
    """随机获取一道错题。"""
    # 获取当前用户 ID
    user_id = current_user.id

    # 查询当前用户未归档的错题
    stmt = select(WrongQuestion).where(
        WrongQuestion.user_id == user_id,
        WrongQuestion.is_archived == False,
    )
    # 可选按科目过滤
    if subject:
        stmt = stmt.where(WrongQuestion.subject == subject)

    # 取回全部候选错题
    items = (await session.exec(stmt)).scalars().all()
    # 无可练习错题时返回空
    if not items:
        return HttpResponse.success(data=None)

    # 随机返回一道错题
    return HttpResponse.success(data=_to_wrong_read(random.choice(items)))


# 错题归档接口：将指定错题标记为已归档
@router.post("/wrong/{wrong_id}/archive")
async def archive_wrong(
    wrong_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> HttpResponse:
    """归档错题。"""
    # 查询归属当前用户的错题
    wrong = (await session.exec(
        select(WrongQuestion).where(
            WrongQuestion.id == wrong_id,
            WrongQuestion.user_id == current_user.id,
        )
    )).scalars().first()

    # 错题不存在时返回 404
    if not wrong:
        return HttpResponse.error(code=404, message="错题不存在")

    # 标记归档并保存
    wrong.is_archived = True
    await session.commit()
    # 返回归档成功
    return HttpResponse.success(message="已归档")


# 错题删除接口：从错题本中移除指定错题
@router.delete("/wrong/{wrong_id}")
async def delete_wrong(
    wrong_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> HttpResponse:
    """删除错题。"""
    # 查询归属当前用户的错题
    wrong = (await session.exec(
        select(WrongQuestion).where(
            WrongQuestion.id == wrong_id,
            WrongQuestion.user_id == current_user.id,
        )
    )).scalars().first()

    # 错题不存在时返回 404
    if not wrong:
        return HttpResponse.error(code=404, message="错题不存在")

    # 删除错题并保存
    await session.delete(wrong)
    await session.commit()
    # 返回删除成功
    return HttpResponse.success(message="已删除")


# 将错题 ORM 对象转换为对外响应 DTO
def _to_wrong_read(item: WrongQuestion) -> WrongQuestionRead:
    """转换 ORM 为响应 DTO。"""
    # 逐个字段映射构建响应对象
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
