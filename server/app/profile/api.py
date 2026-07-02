"""Profile HTTP 路由。

从 chat/api.py 迁移而来，保持 profile 路由独立。
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends

from app.auth.security import get_current_user
from app.infra.logging import get_logger
from app.infra.models import User
from app.infra.response import HttpResponse
from app.profile import (
    BaseInfoData,
    GlobalProfileResponse,
    OnboardingResponse,
    OnboardingUpdate,
    StudentProfileData,
)
from app.profile.service import get_profile_service

logger = get_logger(__name__)
router = APIRouter()


@router.get("/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    profile_builder = get_profile_service()
    profile = await profile_builder.get_or_create_global_profile(user_id=current_user.id)
    profile_json = profile.profile_json or {}

    return HttpResponse.success(data=GlobalProfileResponse(
        user_id=profile.user_id,
        module=profile.module,
        base_info=BaseInfoData(**(profile_json.get("base_info") or {})),
        dimensions=profile_json.get("dimensions") or {},
        profile_json=profile.profile_json or {},
        profile_score_json=profile.profile_score_json or {},
        updated_at=profile.updated_at,
    ))


@router.get("/profile/onboarding")
async def get_profile_onboarding(
    current_user: User = Depends(get_current_user),
):
    profile_builder = get_profile_service()
    profile = await profile_builder.get_or_create_global_profile(user_id=current_user.id)
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
):
    """更新 onboarding 信息并触发 LLM 推理生成画像和评分。

    流程：
    1. 先保存基础信息到数据库（快速返回）
    2. 后台异步触发 LLM 推理，生成 7 维度文字画像
    3. 自动计算并更新分数画像
    """
    profile_builder = get_profile_service()
    payload_data = payload.model_dump()
    user_id = int(current_user.id)

    try:
        # 1. 同步保存基础信息（快速响应前端）
        result = await profile_builder.update_from_onboarding(
            user_id=user_id,
            payload=payload_data,
        )

        # 2. 后台异步触发 LLM 推理 + 评分
        asyncio.create_task(
            _run_onboarding_inference_async(user_id, payload_data),
            name=f"onboarding_inference_{user_id}",
        )

        logger.info("[ProfileAPI] onboarding complete, inference scheduled: user_id=%s", user_id)
    except Exception as e:
        logger.warning("[ProfileAPI] onboarding update failed: user_id=%s err=%s", user_id, e)
        return HttpResponse.error(code=400, message=str(e))

    return HttpResponse.success(data={
        "profile": result,
        "inference_scheduled": True,
    })


async def _run_onboarding_inference_async(user_id: int, payload: dict) -> None:
    """后台异步运行 onboarding 推理和评分。"""
    try:
        profile_builder = get_profile_service()
        await profile_builder.run_onboarding_inference(
            user_id=user_id,
            payload=payload,
        )
    except Exception as exc:
        logger.error("[ProfileAPI] onboarding inference failed: user_id=%s err=%s", user_id, exc)
