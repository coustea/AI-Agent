"""Profile HTTP 路由。

从 chat/api.py 迁移而来，保持 profile 路由独立。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

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
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """更新 onboarding 信息：同步保存基础信息 → 同步 LLM 推理 → 同步评分。

    全部同步完成后再返回，确保前端进入个人中心时画像和分数一定存在。
    如果 LLM 推理失败，基础信息仍然保存成功，但返回警告。
    """
    payload_data = payload.model_dump()
    user_id = int(current_user.id)
    svc = get_profile_service()

    # 1. 同步保存基础信息
    await svc.save_onboarding_info(
        user_id=user_id,
        payload=payload_data,
        db=session,
    )
    logger.info("[ProfileAPI] onboarding base info saved: user_id=%s", user_id)

    # 2. 同步 LLM 推理 + 评分（在同一个请求内完成）
    inference_ok = False
    try:
        await svc.infer_profile_from_onboarding(
            user_id=user_id,
            payload=payload_data,
        )
        inference_ok = True
        logger.info("[ProfileAPI] onboarding inference + scoring done: user_id=%s", user_id)
    except Exception as exc:
        logger.error("[ProfileAPI] onboarding inference failed: user_id=%s err=%s", user_id, exc)

    return HttpResponse.success(data={
        "inference_ok": inference_ok,
    })
