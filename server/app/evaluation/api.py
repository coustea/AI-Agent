"""学习评估 HTTP 路由。

包含首页仪表盘相关端点（从 dashboard 模块迁移）。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import get_current_user, get_current_user_flexible
from app.evaluation.schemas import LearningEventCreate, LearningSessionCreate
from app.evaluation.service import evaluation_service, ConcurrencyError
from app.infra.database import get_session
from app.infra.logging import get_logger
from app.infra.models import LearningSession, User, LearningAssessmentReport
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
    # 记录学习事件后写审计日志
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
    # 记录学习会话后写审计日志
    logger.info(
        "[EvalAPI] 学习会话已记录: user_id=%s page=%s duration=%ss deduplicated=%s",
        current_user.id,
        payload.source_page,
        payload.duration_seconds,
        deduplicated,
    )
    return HttpResponse.success(data={"id": learning_session.id, "deduplicated": deduplicated})


from pydantic import BaseModel, Field

class ReportGenerateRequest(BaseModel):
    range_days: int = Field(..., description="评估天数，必须为 7、14 或 30")


# 1. POST /api/v1/ai/evaluation/reports -> 建立并同步生成报告
@router.post("/evaluation/reports")
async def generate_assessment_report(
    payload: ReportGenerateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """建立并同步生成报告；已有生成中报告返回 409。"""
    try:
        report = await evaluation_service.generate_report(
            session,
            user_id=current_user.id,
            range_days=payload.range_days
        )
        return HttpResponse.success(data=report.model_dump(mode="json"))
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


# 2. GET /api/v1/ai/evaluation/reports/latest -> 获取最新 ready 报告
@router.get("/evaluation/reports/latest")
async def get_latest_report(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """获取最新的一条 ready 报告；无报告则返回 null/None。"""
    report = (await session.exec(
        select(LearningAssessmentReport)
        .where(
            LearningAssessmentReport.user_id == current_user.id,
            LearningAssessmentReport.status == "ready"
        )
        .order_by(col(LearningAssessmentReport.generated_at).desc())
        .limit(1)
    )).first()
    
    if report is None:
        return HttpResponse.success(data=None)
    return HttpResponse.success(data=report.model_dump(mode="json"))


# 3. GET /api/v1/ai/evaluation/reports -> 获取历史报告分页列表
@router.get("/evaluation/reports")
async def get_reports_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """历史分页列表。不回传 facts_snapshot 或 report_markdown 正文以减小带宽。"""
    total = (await session.exec(
        select(func.count())
        .select_from(LearningAssessmentReport)
        .where(LearningAssessmentReport.user_id == current_user.id)
    )).one() or 0

    offset = (page - 1) * page_size
    stmt = (
        select(LearningAssessmentReport)
        .where(LearningAssessmentReport.user_id == current_user.id)
        .order_by(col(LearningAssessmentReport.created_at).desc())
        .offset(offset)
        .limit(page_size)
    )
    reports = (await session.exec(stmt)).all()
    
    items = []
    for r in reports:
        d = r.model_dump(mode="json")
        d.pop("facts_snapshot", None)
        d.pop("report_markdown", None)
        items.append(d)
        
    return HttpResponse.success(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    })


# 4. GET /api/v1/ai/evaluation/reports/{report_id} -> 获取单次报告详情
@router.get("/evaluation/reports/{report_id}")
async def get_report_detail(
    report_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """获取单次报告详情。如果非本人拥有，返回 404，不泄露存在性。"""
    report = await session.get(LearningAssessmentReport, report_id)
    if report is None or report.user_id != current_user.id:
        return HttpResponse.error(code=404, message="report_not_found")
        
    return HttpResponse.success(data=report.model_dump(mode="json"))


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
            "last_assessment_report_id": None
        })
        
    return HttpResponse.success(data={
        "guidance_strategy": profile.guidance_strategy,
        "guidance_updated_at": profile.guidance_updated_at.isoformat() if profile.guidance_updated_at else None,
        "last_assessment_report_id": profile.last_assessment_report_id
    })