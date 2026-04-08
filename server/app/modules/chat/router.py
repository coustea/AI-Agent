"""Chat 路由：辅导对话 + 会话管理 + 聊天历史。

- /chat/stream: TutorAgent 前台辅导答疑，后台异步触发画像构建
- /chat/sessions, /chat/history: 会话与历史查询
"""

import asyncio

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.core.response import HttpResponse
from app.core.security import get_current_user
from app.models.user import User
from app.services.memory import memory_service
from app.modules.chat.tutor_agent import tutor_agent
from app.modules.chat.schemas import MentorChatRequest, ChatMessageItem
from app.modules.profile.profile_agent import profile_agent
from app.modules.profile.fact_agent import fact_agent

router = APIRouter()

# 画像更新触发阈值
PROFILE_THRESHOLD = 2
EARLY_TRIGGER = 2


@router.post("/chat/stream")
async def mentor_chat_stream(
    req: MentorChatRequest,
    current_user: User = Depends(get_current_user),
):
    """TutorAgent 辅导答疑（主功能），后台异步触发画像构建。"""
    effective_session = req.session_id or tutor_agent.global_session_id

    generator = tutor_agent.chat_stream(
        user_id=current_user.id,
        user_message=req.message,
        session_id=effective_session,
        image_url=req.image_url,
        file_urls=req.file_urls,
    )

    # 判断是否触发后台画像更新
    msg_count = await memory_service.get_message_count(
        user_id=current_user.id,
        session_id=effective_session,
        module=tutor_agent.module_name,
    )

    should_trigger = (
        msg_count == EARLY_TRIGGER
        or (msg_count > 0 and msg_count % PROFILE_THRESHOLD == 0)
    )
    if should_trigger:
        asyncio.create_task(profile_agent.build_profile(user_id=current_user.id, session_id=effective_session))

    # 每次对话都尝试提炼事实偏好（因为只看最近2条）
    asyncio.create_task(fact_agent.extract_and_save_fact(user_id=current_user.id, session_id=effective_session))

    # 短期→长期记忆压缩（消息过多时触发）
    asyncio.create_task(memory_service.summarize_and_compress(
        user_id=current_user.id,
        session_id=effective_session,
        module=tutor_agent.module_name,
    ))

    return StreamingResponse(generator, media_type="text/event-stream")


@router.get("/chat/sessions")
async def get_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """获取会话列表（不含已归档）"""
    sessions = await memory_service.get_user_chat_sessions(current_user.id, module=tutor_agent.module_name, limit=limit)
    return HttpResponse.success(data=[{"id": s.id, "title": s.title, "updated_at": s.updated_at} for s in sessions])


@router.post("/chat/sessions")
async def create_session(
    current_user: User = Depends(get_current_user),
):
    """创建新会话，返回会话 ID"""
    session = await memory_service.create_chat_session(
        user_id=current_user.id,
        module=tutor_agent.module_name,
        title="新对话",
    )
    return HttpResponse.success(data={"id": session.id, "title": session.title})


@router.delete("/chat/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    """归档（软删除）一个会话"""
    success = await memory_service.archive_chat_session(session_id, current_user.id)
    if not success:
        return HttpResponse.error(code=404, message="会话不存在或无权操作")
    return HttpResponse.success(message="会话已归档")


@router.get("/chat/history")
async def get_chat_history(
    session_id: str = Query(default=tutor_agent.global_session_id, description="指定会话ID"),
    limit: int = Query(default=50, ge=1, le=200, description="返回的消息条数"),
    current_user: User = Depends(get_current_user),
):
    """获取聊天历史。"""
    messages = await memory_service.get_recent_messages(
        user_id=current_user.id,
        session_id=session_id,
        module=tutor_agent.module_name,
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
