"""Profile HTTP 路由。

从 chat/api.py 迁移而来，保持 profile 路由独立。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, BackgroundTasks

from app.auth.security import get_current_user
from app.infra.database import get_session
from app.infra.logging import get_logger
from app.infra.models import User
from app.infra.response import HttpResponse
from app.profile import (
    BaseInfoData,
    OnboardingResponse,
    OnboardingUpdate,
    StudentProfileData,
)
from app.profile.service import get_profile_service, _user_base_info_dict
from sqlmodel.ext.asyncio.session import AsyncSession

logger = get_logger(__name__)
router = APIRouter()


@router.get("/profile")
async def get_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """获取完整用户画像 — 聚合 User.base_info、UserProfileDimension 和 UserProfile.score。"""
    svc = get_profile_service()
    profile = await svc.get_profile(user_id=current_user.id, db=session)
    dimensions = await svc.get_dimensions(user_id=current_user.id, db=session)
    base_info = _user_base_info_dict(current_user)

    dimension_scores = {
        key: dim.get("score", 0) for key, dim in dimensions.items()
    }

    return HttpResponse.success(data={
        "user_id": profile.user_id,
        "module": "mentor",
        "base_info": BaseInfoData(**base_info).model_dump(),
        "dimensions": dimensions,
        "profile_score_json": {
            "overall_score": profile.overall_score,
            "dimension_scores": dimension_scores,
            "scored_at": profile.scored_at.isoformat() if profile.scored_at else None,
        },
        "updated_at": profile.updated_at,
    })


@router.get("/profile/onboarding")
async def get_profile_onboarding(
    current_user: User = Depends(get_current_user),
):
    """获取 onboarding 基本信息 — 直接从 User 表读取。"""
    base_info = _user_base_info_dict(current_user)
    return HttpResponse.success(data=OnboardingResponse(
        base_info=BaseInfoData(**base_info),
        student_profile=StudentProfileData.from_base_info(base_info),
        profile_initialized=bool(current_user.major),
    ).model_dump())


@router.patch("/profile/onboarding")
async def update_profile_onboarding(
    payload: OnboardingUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """更新 onboarding 信息：同步保存基础信息到 User 表 → 立即返回 → 后台异步推理画像+评分。"""
    payload_data = payload.model_dump()
    user_id = int(current_user.id)
    svc = get_profile_service()
    logger.info("[ProfileAPI] 用户信息: %s", payload_data)
    # 1. 同步保存基础信息到 User 表
    await svc.save_onboarding_info(
        user_id=user_id,
        payload=payload_data,
        db=session,
    )
    logger.info("[ProfileAPI] onboarding base info saved synchronously: user_id=%s", user_id)

    # 2. 异步后台触发画像构建任务（推理 + 评分）
    background_tasks.add_task(
        svc.infer_profile_from_onboarding,
        user_id=user_id,
        payload=payload_data,
    )
    logger.info("[ProfileAPI] onboarding background task registered: user_id=%s", user_id)

    return HttpResponse.success(data={
        "inference_ok": True,
    })
