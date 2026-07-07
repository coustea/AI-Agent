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
from app.profile.service import get_profile_service
from sqlmodel.ext.asyncio.session import AsyncSession

logger = get_logger(__name__)
router = APIRouter()


@router.get("/profile")
async def get_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """获取完整用户画像 — 聚合 base_info、dimensions 和 score。"""
    svc = get_profile_service()
    profile = await svc.get_profile(user_id=current_user.id, db=session)
    profile_json = profile.profile_json or {}
    score_json = profile.profile_score_json or {}
    base_info = profile_json.get("base_info") or {}

    return HttpResponse.success(data={
        "user_id": profile.user_id,
        "module": profile.module,
        "base_info": BaseInfoData(**base_info).model_dump(),
        "dimensions": profile_json.get("dimensions") or {},
        "profile_json": profile_json,
        "profile_score_json": score_json,
        "updated_at": profile.updated_at,
    })


@router.get("/profile/onboarding")
async def get_profile_onboarding(
    current_user: User = Depends(get_current_user),
):
    svc = get_profile_service()
    profile = await svc.get_profile(user_id=current_user.id)
    base_info = profile.profile_json.get("base_info") or {}
    return HttpResponse.success(data=OnboardingResponse(
        base_info=BaseInfoData(**base_info),
        student_profile=StudentProfileData.from_base_info(base_info),
        profile_initialized=bool(base_info.get("major")),
    ).model_dump())


@router.patch("/profile/onboarding")
async def update_profile_onboarding(
    payload: OnboardingUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """更新 onboarding 信息：同步保存基础信息 → 立即返回 → 后台异步推理画像+评分。

    前端调用后无需等待 LLM 推理完成，用户可立即进入首页。
    """
    payload_data = payload.model_dump()
    user_id = int(current_user.id)
    svc = get_profile_service()

    # 1. 同步保存基础信息到数据库，确保后续请求能获取到最新的基本资料
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
