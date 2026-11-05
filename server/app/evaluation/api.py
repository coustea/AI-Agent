"""学习评估 HTTP 路由。"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import get_current_user, get_current_user_flexible
from app.evaluation.schemas import LearningEventCreate, LearningSessionCreate
from app.evaluation.service import evaluation_service
from app.infra.database import get_session
from app.infra.logging import get_logger
from app.infra.models import User, LearningAssessment, UserDailyActivity
from app.response import HttpResponse

router = APIRouter()
logger = get_logger(__name__)


# 记录学习事件（资源浏览/完成/测验/对话/生成/路径节点/可视化运行等）
@router.post("/evaluation/events")
async def record_learning_event(
    payload: LearningEventCreate,
    current_user: User = Depends(get_current_user_flexible),
    session: AsyncSession = Depends(get_session),
):
    """记录学习事件 — 资源浏览/完成/测验/对话/资源生成/路径节点/可视化运行等。"""
    event, deduplicated = await evaluation_service.record_event(
        session,
        user_id=current_user.id,
        payload=payload,
    )
    logger.info(
        "[EvalAPI] 事件已记录: user_id=%s event_type=%s event_id=%s deduplicated=%s",
        current_user.id,
        payload.event_type,
        event.id,
        deduplicated,
    )
    return HttpResponse.success(data={"id": event.id, "deduplicated": deduplicated})


# 记录一次学习会话（前端离开学习页面时上报）
@router.post("/evaluation/sessions")
async def record_learning_session(
    payload: LearningSessionCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """记录一次学习会话（前端离开学习页面时上报）。"""
    learning_session, deduplicated = await evaluation_service.record_session(
        session,
        user_id=current_user.id,
        payload=payload,
    )
    logger.info(
        "[EvalAPI] 学习会话已记录: user_id=%s page=%s duration=%ss deduplicated=%s",
        current_user.id,
        payload.source_page,
        payload.duration_seconds,
        deduplicated,
    )
    return HttpResponse.success(data={"id": learning_session.id, "deduplicated": deduplicated})


class AssessmentGenerateRequest(BaseModel):
    """评估生成请求 — range_days 固定为 7，前端不再提供选择。"""
    range_days: int = Field(default=7, description="评估天数，固定为 7")


# 1. POST /api/v1/ai/evaluation/assessments -> 生成学习评估
@router.post("/evaluation/assessments")
async def generate_assessment(
    payload: AssessmentGenerateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """手动触发生成学习评估；已有生成中评估返回 409。

    立即返回 generating 状态的评估记录，后台异步执行 LLM 生成。
    前端通过 GET /latest 或 GET /{id} 轮询生成结果。
    """
    # 检查是否已有生成中的评估
    existing = await session.scalar(
        select(LearningAssessment).where(
            LearningAssessment.user_id == current_user.id,
            LearningAssessment.status == "generating",
        )
    )
    if existing is not None:
        logger.info("[EvalAPI] 评估生成冲突(已有进行中): user_id=%s", current_user.id)
        return HttpResponse.error(code=409, message="assessment_generation_in_progress")

    logger.info("[EvalAPI] 触发评估生成: user_id=%s range_days=%d", current_user.id, payload.range_days)

    # 创建 generating 记录并立即返回
    now_utc = datetime.now(timezone.utc)
    window_start = now_utc - timedelta(days=payload.range_days)
    assessment = LearningAssessment(
        user_id=current_user.id,
        trigger_source="manual",
        range_days=payload.range_days,
        window_start=window_start,
        window_end=now_utc,
        status="generating",
        created_at=now_utc,
        updated_at=now_utc,
    )
    session.add(assessment)
    await session.commit()
    await session.refresh(assessment)

    assessment_id = assessment.id
    user_id = current_user.id
    range_days = payload.range_days

    # 后台异步执行 LLM 生成
    import asyncio
    asyncio.create_task(_run_assessment_generation(user_id, assessment_id, range_days))

    return HttpResponse.success(data=assessment.model_dump(mode="json"))


async def _run_assessment_generation(user_id: int, assessment_id: int, range_days: int) -> None:
    """后台执行评估生成：聚合事实 → LLM 推理 → 更新状态。"""
    from app.infra.database import session_scope

    try:
        async with session_scope() as bg_session:
            # 重新加载评估记录
            assessment = await bg_session.get(LearningAssessment, assessment_id)
            if assessment is None or assessment.status != "generating":
                return

            # 聚合事实
            from app.evaluation.facts import build_assessment_facts
            facts_snapshot = await build_assessment_facts(
                bg_session, user_id=user_id,
                window_start=assessment.window_start,
                window_end=assessment.window_end,
            )

            # LLM 生成评估文案和辅导策略
            assessment_text, guidance_strategy = await evaluation_service._derive_assessment_with_llm(facts_snapshot)

            # 更新评估状态
            assessment.status = "ready"
            assessment.assessment = assessment_text
            assessment.generated_at = datetime.now(timezone.utc)
            assessment.updated_at = datetime.now(timezone.utc)

            # 写入辅导策略到 UserProfile
            await evaluation_service._update_guidance_strategy(
                bg_session,
                user_id=user_id,
                strategy=guidance_strategy,
                assessment_id=assessment_id,
            )
            await bg_session.commit()

            logger.info(
                "[EvalAPI] 后台评估生成完成: user_id=%s assessment_id=%s range_days=%d",
                user_id, assessment_id, range_days,
            )
    except Exception as e:
        logger.error("[EvalAPI] 后台评估生成失败: user_id=%s assessment_id=%s error=%s", user_id, assessment_id, e)
        try:
            async with session_scope() as bg_session:
                assessment = await bg_session.get(LearningAssessment, assessment_id)
                if assessment and assessment.status == "generating":
                    assessment.status = "failed"
                    assessment.failure_code = "generation_failed"
                    assessment.updated_at = datetime.now(timezone.utc)
                    await bg_session.commit()
        except Exception:
            logger.error("[EvalAPI] 标记评估失败也失败: assessment_id=%s", assessment_id)


# 2. GET /api/v1/ai/evaluation/assessments/latest -> 获取最新 ready 评估
@router.get("/evaluation/assessments/latest")
async def get_latest_assessment(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """获取最新的一条 ready 评估；无评估则返回 null/None。"""
    logger.info("[EvalAPI] 查询最新评估: user_id=%s", current_user.id)
    assessment = (await session.exec(
        select(LearningAssessment)
        .where(
            LearningAssessment.user_id == current_user.id,
            LearningAssessment.status == "ready"
        )
        .order_by(col(LearningAssessment.generated_at).desc())
        .limit(1)
    )).first()

    if assessment is None:
        return HttpResponse.success(data=None)
    return HttpResponse.success(data=assessment.model_dump(mode="json"))


# 3. GET /api/v1/ai/evaluation/assessments -> 获取历史评估分页列表
@router.get("/evaluation/assessments")
async def get_assessments_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """历史分页列表。不回传 assessment 正文以减小带宽。"""
    total = (await session.exec(
        select(func.count())
        .select_from(LearningAssessment)
        .where(LearningAssessment.user_id == current_user.id)
    )).one() or 0

    offset = (page - 1) * page_size
    stmt = (
        select(LearningAssessment)
        .where(LearningAssessment.user_id == current_user.id)
        .order_by(col(LearningAssessment.created_at).desc())
        .offset(offset)
        .limit(page_size)
    )
    assessments = (await session.exec(stmt)).all()

    items = []
    for a in assessments:
        d = a.model_dump(mode="json")
        d.pop("assessment", None)  # 列表不返回评估正文
        items.append(d)

    return HttpResponse.success(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    })


# 4. GET /api/v1/ai/evaluation/assessments/{assessment_id} -> 获取单次评估详情
@router.get("/evaluation/assessments/{assessment_id}")
async def get_assessment_detail(
    assessment_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """获取单次评估详情。如果非本人拥有，返回 404，不泄露存在性。"""
    logger.info("[EvalAPI] 查询评估详情: user_id=%s assessment_id=%s", current_user.id, assessment_id)
    assessment = await session.get(LearningAssessment, assessment_id)
    if assessment is None or assessment.user_id != current_user.id:
        return HttpResponse.error(code=404, message="assessment_not_found")

    return HttpResponse.success(data=assessment.model_dump(mode="json"))


# 5. GET /api/v1/ai/evaluation/guidance-strategy -> 获取当前辅导策略
@router.get("/evaluation/guidance-strategy")
async def get_guidance_strategy(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """独立输出当前策略；供个人中心和生成服务读取。"""
    from app.infra.models import UserProfile
    profile = await session.scalar(select(UserProfile).where(UserProfile.user_id == current_user.id))

    if profile is None:
        return HttpResponse.success(data={
            "guidance_strategy": {},
            "guidance_updated_at": None,
            "last_assessment_id": None
        })

    return HttpResponse.success(data={
        "guidance_strategy": profile.guidance_strategy,
        "guidance_updated_at": profile.guidance_updated_at.isoformat() if profile.guidance_updated_at else None,
        "last_assessment_id": profile.last_assessment_id
    })


# 6. GET /api/v1/ai/evaluation/dashboard -> 个人中心看板数据
@router.get("/evaluation/dashboard")
async def get_dashboard_data(
    range_days: int = Query(default=7, description="统计天数窗口"),
    current_user: User = Depends(get_current_user_flexible),
    session: AsyncSession = Depends(get_session),
):
    """为个人中心看板聚合图表数据：学习时长走势、模块分布、练习正确率、资源使用等。"""
    logger.info("[EvalAPI] 查询看板数据: user_id=%s range_days=%d", current_user.id, range_days)
    if range_days < 1 or range_days > 90:
        return HttpResponse.error(code=400, message="range_days must be between 1 and 90")

    now_utc = datetime.now(timezone.utc)
    window_start = now_utc - timedelta(days=range_days)
    window_end = now_utc

    dashboard_data = await _build_dashboard_data(
        session,
        user_id=current_user.id,
        window_start=window_start,
        window_end=window_end,
        now_utc=now_utc,
        range_days=range_days,
    )
    return HttpResponse.success(data=dashboard_data)


# 7. GET /api/v1/ai/evaluation/assessments/{assessment_id}/dashboard -> 历史评估看板数据
@router.get("/evaluation/assessments/{assessment_id}/dashboard")
async def get_assessment_dashboard(
    assessment_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """根据历史评估的时间窗口重新计算看板数据，用于历史评估联动看板。"""
    assessment = await session.get(LearningAssessment, assessment_id)
    if assessment is None or assessment.user_id != current_user.id:
        return HttpResponse.error(code=404, message="assessment_not_found")

    dashboard_data = await _build_dashboard_data(
        session,
        user_id=current_user.id,
        window_start=assessment.window_start,
        window_end=assessment.window_end,
        now_utc=assessment.window_end,
        assessment_id=assessment_id,
        range_days=max(1, (assessment.window_end - assessment.window_start).days),
    )
    return HttpResponse.success(data=dashboard_data)


async def _build_dashboard_data(
    session: AsyncSession,
    *,
    user_id: int,
    window_start: datetime,
    window_end: datetime,
    now_utc: datetime,
    range_days: int,
    assessment_id: int | None = None,
) -> dict[str, Any]:
    """组装看板响应的共享逻辑，供 dashboard 和 assessment-dashboard 复用。"""
    from app.evaluation.facts import build_assessment_facts, to_shanghai_date
    from app.evaluation.guidance import get_effective_guidance_strategy

    # 1. 聚合事实数据
    facts = await build_assessment_facts(
        session, user_id=user_id, window_start=window_start, window_end=window_end
    )

    # 2. 获取当前辅导策略
    strategy = await get_effective_guidance_strategy(session, user_id)

    # 3. 获取评估文案
    if assessment_id is not None:
        latest_assessment = await session.get(LearningAssessment, assessment_id)
    else:
        latest_assessment = (await session.exec(
            select(LearningAssessment)
            .where(
                LearningAssessment.user_id == user_id,
                LearningAssessment.status == "ready"
            )
            .order_by(col(LearningAssessment.generated_at).desc())
            .limit(1)
        )).first()

    # 4. 组装看板响应
    activity = facts.get("activity", {})
    practice = facts.get("practice", {})
    resource_usage = facts.get("resource_usage", {})
    learning_path = facts.get("learning_path", {})
    data_quality = facts.get("data_quality", {})

    # 以完整统计窗口返回每日时长；没有会话的日期也显式返回 0，保证图表始终可绘制。
    daily_seconds_by_date = {
        item["date"]: item["minutes"] * 60
        for item in activity.get("daily_minutes", [])
    }
    login_end_date = date.fromisoformat(to_shanghai_date(now_utc))
    login_start_date = login_end_date - timedelta(days=range_days - 1)
    daily_breakdown = [
        {
            "date": (login_start_date + timedelta(days=offset)).isoformat(),
            "seconds": daily_seconds_by_date.get(
                (login_start_date + timedelta(days=offset)).isoformat(),
                0,
            ),
        }
        for offset in range(range_days)
    ]
    today_seconds = daily_seconds_by_date.get(login_end_date.isoformat(), 0)

    # 每日首次登录活跃：与学习行为、学习时长分开统计。
    active_login_days = (await session.exec(
        select(func.count())
        .select_from(UserDailyActivity)
        .where(
            UserDailyActivity.user_id == user_id,
            UserDailyActivity.activity_date >= login_start_date,
            UserDailyActivity.activity_date <= login_end_date,
        )
    )).one() or 0

    # 功能使用以学习事件次数为准，不混入会话时长。
    module_counts = {
        item["module"]: item["count"]
        for item in activity.get("module_distribution", [])
    }
    feature_usage = [
        {"key": "quiz", "name": "题库练习", "count": module_counts.get("quiz", 0)},
        {"key": "chat", "name": "AI 辅导", "count": module_counts.get("chat", 0)},
        {"key": "path", "name": "路径规划", "count": module_counts.get("path", 0)},
        {"key": "resource", "name": "智能推荐", "count": module_counts.get("resource", 0)},
        {"key": "assessment", "name": "学习评估", "count": module_counts.get("assessment", 0)},
    ]

    # 练习正确率按主题
    practice_by_topic_chart = []
    for t in practice.get("by_topic", []):
        practice_by_topic_chart.append({
            "topic": t["topic"],
            "accuracy": round(t["accuracy"] * 100, 1),
            "submitted": t["submitted"],
            "correct": t["correct"],
        })

    # 模块学习时长分布（饼图数据）
    module_time_breakdown = activity.get("module_time_breakdown", [])

    dashboard_data: dict[str, Any] = {
        # 学习时长走势（折线图）
        "time_stats": {
            "total_seconds": activity.get("total_minutes", 0) * 60,
            "today_seconds": today_seconds,
            "daily_breakdown": daily_breakdown,
        },
        "login_activity": {
            "active_days": active_login_days,
        },
        "feature_usage": feature_usage,
        # 评估摘要
        "evaluation_summary": {
            "completed_resources": resource_usage.get("completed", 0),
            "viewed_resources": resource_usage.get("viewed", 0),
            "generated_resources": resource_usage.get("generated", 0),
            "event_count": sum(item["count"] for item in activity.get("module_distribution", [])),
            "weak_topics": data_quality.get("insufficient_topics", []),
            "focus_topics": strategy.get("focus_topics", []),
            "recommendations": [
                strategy.get("conclusion"),
                strategy.get("reason"),
            ],
        },
        # 练习正确率
        "practice_chart": {
            "overall_accuracy": round(practice.get("accuracy", 0) * 100, 1),
            "total_submitted": practice.get("submitted", 0),
            "total_correct": practice.get("correct", 0),
            "by_topic": practice_by_topic_chart,
        },
        # 学习路径进度
        "learning_path": {
            "nodes_started": learning_path.get("nodes_started", 0),
            "nodes_completed": learning_path.get("nodes_completed", 0),
            "completion_rate": round(learning_path.get("completion_rate", 0) * 100, 1),
        },
        # 模块学习时长分布（饼图）
        "module_time_breakdown": module_time_breakdown,
        # 最新评估文案
        "latest_assessment": {
            "id": latest_assessment.id if latest_assessment else None,
            "assessment": latest_assessment.assessment if latest_assessment else None,
            "generated_at": latest_assessment.generated_at.isoformat() if latest_assessment and latest_assessment.generated_at else None,
        } if latest_assessment else None,
        # 辅导策略
        "guidance_strategy": strategy,
        # 窗口信息
        "window": facts.get("window", {}),
    }

    # 过滤掉 recommendations 中的 None 值
    dashboard_data["evaluation_summary"]["recommendations"] = [
        r for r in dashboard_data["evaluation_summary"]["recommendations"] if r
    ]

    return dashboard_data
