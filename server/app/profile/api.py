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

# 正在执行的 onboarding task，用于防抖去重
_onboarding_tasks: dict[int, asyncio.Task] = {}


@router.get("/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    svc = get_profile_service()
    profile = await svc.get_profile(user_id=current_user.id)
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
):
    """更新 onboarding 信息并触发 LLM 推理生成画像和评分。

    流程：
    1. 立即返回成功，用户可继续进入系统
    2. 后台异步保存基础信息到数据库
    3. 后台异步触发 LLM 推理，生成 7 维度文字画像
    4. 自动计算并更新分数画像
    """
    payload_data = payload.model_dump()
    user_id = int(current_user.id)

    # 取消同用户正在运行的旧 task（防抖去重）
    old_task = _onboarding_tasks.get(user_id)
    if old_task and not old_task.done():
        old_task.cancel()
        logger.info("[ProfileAPI] cancelled previous onboarding task: user_id=%s", user_id)

    # 全部后台执行，不阻塞用户
    task = asyncio.create_task(
        _run_onboarding_full_async(user_id, payload_data),
        name=f"onboarding_full_{user_id}",
    )
    _onboarding_tasks[user_id] = task
    task.add_done_callback(lambda t: _onboarding_tasks.pop(user_id, None))

    logger.info("[ProfileAPI] onboarding accepted, background scheduled: user_id=%s", user_id)

    return HttpResponse.success(data={
        "inference_scheduled": True,
    })


async def _run_onboarding_full_async(user_id: int, payload: dict) -> None:
    """后台异步运行 onboarding 全流程：保存基础信息 → LLM 推理 → 评分。"""
    svc = get_profile_service()
    try:
        # 1. 保存基础信息到数据库
        await svc.save_onboarding_info(
            user_id=user_id,
            payload=payload,
        )
        logger.info("[ProfileAPI] onboarding save complete: user_id=%s", user_id)
    except Exception as exc:
        logger.error("[ProfileAPI] onboarding save failed: user_id=%s err=%s", user_id, exc)
        return  # 保存失败则不继续推理

    try:
        # 2. LLM 推理 + 评分
        await svc.infer_profile_from_onboarding(
            user_id=user_id,
            payload=payload,
        )
    except Exception as exc:
        logger.error("[ProfileAPI] onboarding inference failed: user_id=%s err=%s", user_id, exc)
