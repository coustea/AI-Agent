"""Profile HTTP 路由。

从 chat/api.py 迁移而来，保持 profile 路由独立。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth.security import get_current_user
from app.infra.logging import get_logger
from app.infra.models import User
from app.infra.response import HttpResponse
from app.profile import (
    BaseInfoData,
    GlobalProfileResponse,
    GlobalScoreResponse,
    GlobalTutoringProfileUpdate,
    CourseTutoringProfileUpdate,
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


@router.get("/profile/score")
async def get_profile_score(current_user: User = Depends(get_current_user)):
    profile_builder = get_profile_service()
    profile = await profile_builder.get_or_create_global_profile(user_id=current_user.id)
    score_json = profile.profile_score_json or {}

    scores = score_json.get("dimension_scores") or {}
    evidences = score_json.get("dimension_evidence") or {}

    from app.profile.types import SCORE_DIMENSIONS, DIMENSION_NAMES
    dimensions = []
    for key in SCORE_DIMENSIONS:
        score = scores.get(key)
        dimensions.append({
            "key": key,
            "label": DIMENSION_NAMES.get(key, key),
            "score": score if isinstance(score, (int, float)) else None,
            "evidence": evidences.get(key) or [],
        })

    return HttpResponse.success(data=GlobalScoreResponse(
        user_id=profile.user_id,
        module=profile.module,
        score=score_json.get("overall_score"),
        metrics={
            "dimension_scores": scores,
            "dimension_evidence": evidences,
        },
        dimensions=dimensions,
        scored_at=score_json.get("scored_at"),
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
        student_profile=StudentProfileData(
            school=base_info.get("school"),
            school_level=base_info.get("school_level"),
            major=base_info.get("major"),
            grade=base_info.get("grade"),
            courses=base_info.get("courses", []),
            learning_goal=base_info.get("global_learning_goal"),
            preferred_language=", ".join(base_info.get("programming_languages", [])),
        ),
        profile_initialized=bool(base_info.get("major")),
    ).model_dump())


@router.patch("/profile/onboarding")
async def update_profile_onboarding(
    payload: OnboardingUpdate,
    current_user: User = Depends(get_current_user),
):
    profile_builder = get_profile_service()
    payload_data = payload.model_dump()
    user_id = int(current_user.id)

    try:
        result = await profile_builder.update_from_onboarding(
            user_id=user_id,
            payload=payload_data,
        )
        logger.info("[ProfileAPI] onboarding complete: user_id=%s", user_id)
    except Exception as e:
        logger.warning("[ProfileAPI] onboarding update failed: user_id=%s err=%s", user_id, e)
        return HttpResponse.error(code=400, message=str(e))

    return HttpResponse.success(data={
        "profile": result,
        "inference_scheduled": True,
    })


@router.patch("/profile/global/tutoring-update")
async def update_global_profile_from_tutoring(
    payload: GlobalTutoringProfileUpdate,
    current_user: User = Depends(get_current_user),
):
    profile_builder = get_profile_service()
    try:
        logger.info("[ProfileAPI] 收到全局画像更新请求: user_id=%s", current_user.id)
        result = await profile_builder.update_global_from_tutoring(
            user_id=current_user.id,
            session_id=payload.session_id,
        )
        return HttpResponse.success(data=result)
    except Exception as e:
        logger.warning("[ProfileAPI] global profile update failed: user_id=%s err=%s", current_user.id, e)
        return HttpResponse.error(code=400, message=str(e))


@router.patch("/profile/course/tutoring-update")
async def update_course_profile_from_tutoring(
    payload: CourseTutoringProfileUpdate,
    current_user: User = Depends(get_current_user),
):
    profile_builder = get_profile_service()
    try:
        logger.info("[ProfileAPI] 收到课程画像更新请求: user_id=%s", current_user.id)
        result = await profile_builder.update_course_from_tutoring(
            user_id=current_user.id,
            session_id=payload.session_id,
            course_name=payload.course_name,
            active_topic=payload.active_topic,
        )
        return HttpResponse.success(data=result)
    except Exception as e:
        logger.warning("[ProfileAPI] course profile update failed: user_id=%s err=%s", current_user.id, e)
        return HttpResponse.error(code=400, message=str(e))
