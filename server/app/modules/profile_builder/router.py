import asyncio

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.core.response import HttpResponse
from app.core.security import get_current_user
from app.models.user import User
from app.modules.memory.service import memory_service
from app.modules.profile_builder.chat_agent import chat_agent
from app.modules.profile_builder.profile_agent import ProfileBuilderAgent
from app.modules.profile_builder.schema import (
    ChatMessageItem,
    ChatRequest,
    ProfileHistoryItem,
    ProfileResponse,
)

router = APIRouter()

# 触发画像更新的消息阈值
PROFILE_THRESHOLD = 20
# 新用户首次触发的消息数（较低阈值，尽早建立初始画像）
EARLY_TRIGGER = 3

@router.post("/chat/stream")
async def chat_stream_endpoint(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    generator = chat_agent.chat_stream(user_id=current_user.id, user_message=req.message)

    # 获取消息计数，决定是否触发后台任务
    msg_count = memory_service.get_message_count(
        user_id=current_user.id,
        session_id=chat_agent.global_session_id,
        module=chat_agent.module_name,
    )

    should_trigger = (
        msg_count == EARLY_TRIGGER  # 新用户首次触发（第 3 条消息）
        or (msg_count > 0 and msg_count % PROFILE_THRESHOLD == 0)  # 常规周期触发
    )

    if should_trigger:
        profile_agent = ProfileBuilderAgent()
        asyncio.create_task(profile_agent.build_profile(user_id=current_user.id))

    return StreamingResponse(generator, media_type="text/event-stream")



@router.get("/profile")
async def get_profile(
    current_user: User = Depends(get_current_user),
):
    profile = memory_service.get_user_profile(current_user.id)
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
    history = memory_service.get_profile_history(current_user.id, limit=limit)
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



@router.get("/chat/history")
async def get_chat_history(
    limit: int = Query(default=50, ge=1, le=200, description="返回的消息条数"),
    current_user: User = Depends(get_current_user),
):
    messages = memory_service.get_recent_messages(
        user_id=current_user.id,
        session_id=chat_agent.global_session_id,
        module=chat_agent.module_name,
        limit=limit,
    )

    items = [
        ChatMessageItem(
            role=msg.role,
            content=msg.content,
            created_at=msg.created_at,
        )
        for msg in messages
    ]
    return HttpResponse.success(data=items)