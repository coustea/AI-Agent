"""学习评估 HTTP 路由。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import get_current_user, get_current_user_flexible
from app.evaluation.schemas import LearningEventCreate, LearningSessionCreate
from app.evaluation.service import evaluation_service, ConcurrencyError
from app.infra.database import get_session
from app.infra.logging import get_logger
from app.infra.models import LearningSession, User, LearningAssessment
from app.infra.response import HttpResponse

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
    range_days: Literal[3, 7, 14] = Field(..., description="评估天数，必须为 3、7 或 14")


# 1. POST /api/v1/ai/evaluation/assessments -> 生成学习评估
@router.post("/evaluation/assessments")
async def generate_assessment(
    payload: AssessmentGenerateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """手动触发生成学习评估；已有生成中评估返回 409。"""
    try:
        assessment = await evaluation_service.generate_assessment(
            session,
            user_id=current_user.id,
            trigger_source="manual",
            range_days=payload.range_days,
        )
        return HttpResponse.success(data=assessment.model_dump(mode="json"))
    except ConcurrencyError:
        return HttpResponse.error(
            code=409,
            message="assessment_generation_in_progress"
        )
    except ValueError as e:
        return HttpResponse.error(
            code=400,
            message=str(e)
        )


# 2. GET /api/v1/ai/evaluation/assessments/latest -> 获取最新 ready 评估
@router.get("/evaluation/assessments/latest")
async def get_latest_assessment(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """获取最新的一条 ready 评估；无评估则返回 null/None。"""
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
    range_days: Literal[3, 7, 14, 30] = Query(default=7, description="统计天数窗口"),
    current_user: User = Depends(get_current_user_flexible),
    session: AsyncSession = Depends(get_session),
):
    """为个人中心看板聚合图表数据：学习时长走势、模块分布、练习正确率、资源使用等。

    该端点按需计算，不依赖 facts_snapshot 持久化。
    返回结构覆盖 Profile.vue 所需的全部图表字段，前端单次请求即可渲染完整看板。
    """
    from app.evaluation.facts import build_assessment_facts
    from app.evaluation.guidance import get_effective_guidance_strategy

    now_utc = datetime.now(timezone.utc)
    from datetime import timedelta
    window_start = now_utc - timedelta(days=range_days)
    window_end = now_utc

    # 1. 聚合事实数据
    facts = await build_assessment_facts(
        session, user_id=current_user.id, window_start=window_start, window_end=window_end
    )

    # 2. 获取当前辅导策略
    strategy = await get_effective_guidance_strategy(session, current_user.id)

    # 3. 获取最新评估文案
    latest_assessment = (await session.exec(
        select(LearningAssessment)
        .where(
            LearningAssessment.user_id == current_user.id,
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

    # 模块分布映射为前端 context_breakdown 格式
    module_to_context = {
        "chat": "Tutor",
        "quiz": "QuestionBank",
        "path": "PathNodeStudy",
        "resource": "ResourceGenerator",
        "visualizer": "AlgorithmVisualizer",
    }
    context_breakdown: dict[str, int] = {}
    for item in activity.get("module_distribution", []):
        ctx_key = module_to_context.get(item["module"], item["module"])
        context_breakdown[ctx_key] = context_breakdown.get(ctx_key, 0) + item["count"]

    # 每日时长转为 seconds 格式
    daily_breakdown = [
        {"date": item["date"], "seconds": item["minutes"] * 60}
        for item in activity.get("daily_minutes", [])
    ]

    # 今日学习时长
    from app.evaluation.facts import to_shanghai_date
    today_key = to_shanghai_date(now_utc)
    today_seconds = 0
    for item in daily_breakdown:
        if item["date"] == today_key:
            today_seconds = item["seconds"]
            break

    # 练习正确率按主题 — 额外返回 chart 友好格式
    practice_by_topic_chart = []
    for t in practice.get("by_topic", []):
        practice_by_topic_chart.append({
            "topic": t["topic"],
            "accuracy": round(t["accuracy"] * 100, 1),
            "submitted": t["submitted"],
            "correct": t["correct"],
        })

    dashboard_data: dict[str, Any] = {
        # 学习时长走势（折线图）
        "time_stats": {
            "total_seconds": activity.get("total_minutes", 0) * 60,
            "today_seconds": today_seconds,
            "streak_days": activity.get("active_days", 0),
            "daily_breakdown": daily_breakdown,
            "context_breakdown": context_breakdown,
        },
        # 评估摘要（薄弱点、建议）
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
        # 练习正确率（柱状图 / 雷达图）
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

    return HttpResponse.success(data=dashboard_data)
