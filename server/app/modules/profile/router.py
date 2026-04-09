"""Profile 路由：画像查询 + 画像历史。"""

from fastapi import APIRouter, Depends, Query

from app.core.response import HttpResponse
from app.core.security import get_current_user
from app.models.user import User
from app.services.memory import memory_service
from app.modules.profile.schemas import ProfileHistoryItem, ProfileResponse

router = APIRouter()


@router.get("/profile")
async def get_profile(
    current_user: User = Depends(get_current_user),
):
    """获取当前用户画像。"""
    profile = await memory_service.get_user_profile(current_user.id)
    if not profile:
        return HttpResponse.success(data=None, message="暂无画像数据")

    data = ProfileResponse(
        knowledge_level=profile.knowledge_level,
        knowledge_level_score=profile.knowledge_level_score,
        cognitive_style=profile.cognitive_style,
        cognitive_style_score=profile.cognitive_style_score,
        error_pattern=profile.error_pattern,
        error_pattern_score=profile.error_pattern_score,
        learning_goal=profile.learning_goal,
        learning_goal_score=profile.learning_goal_score,
        learning_history=profile.learning_history,
        learning_history_score=profile.learning_history_score,
        interest_preference=profile.interest_preference,
        interest_preference_score=profile.interest_preference_score,
        learning_pace=profile.learning_pace,
        learning_pace_score=profile.learning_pace_score,
        cognitive_level=profile.cognitive_level,
        cognitive_level_score=profile.cognitive_level_score,
        profile_summary=profile.profile_summary,
        updated_at=profile.updated_at,
    )
    return HttpResponse.success(data=data)


@router.get("/profile/history")
async def get_profile_history(
    limit: int = Query(default=20, ge=1, le=100, description="返回的历史条数"),
    current_user: User = Depends(get_current_user),
):
    """获取画像变更历史。"""
    history = await memory_service.get_profile_history(current_user.id, limit=limit)
    if not history:
        return HttpResponse.success(data=[], message="暂无变更历史")

    items = [
        ProfileHistoryItem(
            version=h.version,
            knowledge_level=h.knowledge_level,
            knowledge_level_score=h.knowledge_level_score,
            cognitive_style=h.cognitive_style,
            cognitive_style_score=h.cognitive_style_score,
            error_pattern=h.error_pattern,
            error_pattern_score=h.error_pattern_score,
            learning_goal=h.learning_goal,
            learning_goal_score=h.learning_goal_score,
            learning_history=h.learning_history,
            learning_history_score=h.learning_history_score,
            interest_preference=h.interest_preference,
            interest_preference_score=h.interest_preference_score,
            learning_pace=h.learning_pace,
            learning_pace_score=h.learning_pace_score,
            cognitive_level=h.cognitive_level,
            cognitive_level_score=h.cognitive_level_score,
            profile_summary=h.profile_summary,
            change_reason=h.change_reason,
            created_at=h.created_at,
        )
        for h in history
    ]
    return HttpResponse.success(data=items)
