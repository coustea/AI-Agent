"""基于 Redis 的会话管理路由。"""

from typing import List

from fastapi import APIRouter, Depends, status, HTTPException
from langchain_core.messages import HumanMessage, AIMessage

from api.core.dependencies import get_current_user, get_redis_client
from api.core.response import Response
from api.db.models import User, SessionCreate, ChatRequest
from api.services.redis_session_service import RedisSessionService

router = APIRouter(tags=["sessions"])


# ================= 会话管理 =================


@router.post(
    "/sessions",
    response_model=Response[dict],
    status_code=status.HTTP_201_CREATED,
    summary="创建新会话",
    description="为当前用户创建一个新的聊天会话（数据存储在 Redis）",
)
async def create_session(
    session_data: SessionCreate = SessionCreate(title="新会话"),
    redis = Depends(get_redis_client),
    current_user = Depends(get_current_user),
):
    """
    创建新会话。

    Args:
        session_data: 会话数据（标题）
        redis: Redis 客户端
        current_user: 当前认证用户

    Returns:
        Response: 新创建的会话信息

    Raises:
        401: 未认证
    """
    session_service = RedisSessionService(redis)
    session = session_service.create_session(current_user.id, session_data)

    return Response(
        data={
            "session_id": session.session_id,
            "title": session.title,
            "created_at": session.created_at,
            "ttl_days": 7,
        },
        message="Session created successfully",
    )


@router.get(
    "/sessions",
    response_model=Response[List[dict]],
    summary="获取会话列表",
    description="获取当前用户的所有会话列表",
)
async def list_sessions(
    redis = Depends(get_redis_client),
    current_user = Depends(get_current_user),
):
    """
    获取用户的会话列表。

    Args:
        redis: Redis 客户端
        current_user: 当前认证用户

    Returns:
        Response: 会话列表
    """
    session_service = RedisSessionService(redis)
    sessions = session_service.list_sessions(current_user.id)

    result = [
        {
            "session_id": s.session_id,
            "title": s.title,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
        }
        for s in sessions
    ]

    return Response(data=result, message="Sessions retrieved successfully")


@router.delete(
    "/sessions/{session_id}",
    response_model=Response[dict],
    summary="删除会话",
    description="删除指定会话及其所有消息",
)
async def delete_session(
    session_id: str,
    redis = Depends(get_redis_client),
    current_user = Depends(get_current_user),
):
    """
    删除会话。

    Args:
        session_id: 会话 ID
        redis: Redis 客户端
        current_user: 当前认证用户

    Returns:
        Response: 删除结果

    Raises:
        404: 会话不存在
        403: 无权限
    """
    session_service = RedisSessionService(redis)
    success = session_service.delete_session(session_id, current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or access denied",
        )

    return Response(data={"session_id": session_id}, message="Session deleted successfully")


# ================= 消息管理 =================


@router.get(
    "/sessions/{session_id}/messages",
    response_model=Response[List[dict]],
    summary="获取会话消息",
    description="获取指定会话的所有历史消息",
)
async def get_messages(
    session_id: str,
    redis = Depends(get_redis_client),
    current_user = Depends(get_current_user),
):
    """
    获取会话消息。

    Args:
        session_id: 会话 ID
        redis: Redis 客户端
        current_user: 当前认证用户

    Returns:
        Response: 消息列表

    Raises:
        404: 会话不存在
    """
    session_service = RedisSessionService(redis)
    messages = session_service.get_messages(session_id, current_user.id)

    result = [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at,
        }
        for m in messages
    ]

    return Response(data=result, message="Messages retrieved successfully")


# ================= 聊天接口 =================


@router.post(
    "/sessions/{session_id}/chat",
    response_model=Response[dict],
    summary="发送消息",
    description="向会话发送消息并返回聊天历史（Agent 调用由前端或独立服务处理）",
)
async def chat(
    session_id: str,
    request: ChatRequest,
    redis = Depends(get_redis_client),
    current_user = Depends(get_current_user),
):
    """
    发送消息。

    Args:
        session_id: 会话 ID
        request: 聊天请求（消息内容）
        redis: Redis 客户端
        current_user: 当前认证用户

    Returns:
        Response: 用户消息 ID + 完整聊天历史（用于 Agent 调用）

    Raises:
        404: 会话不存在
        400: 聊天失败

    工作流程：
        1. 保存用户消息到 Redis
        2. 获取完整聊天历史
        3. 转换为 LangChain 消息格式
        4. 返回给调用方（调用 Agent 并保存助手回复）
    """
    session_service = RedisSessionService(redis)

    # 验证会话
    session = session_service.get_session(current_user.id, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    # 1. 保存用户消息
    user_message = session_service.add_user_message(
        current_user.id, session_id, request.message
    )

    # 2. 获取历史消息（用于 Agent）
    chat_messages = session_service.get_chat_messages(current_user.id, session_id)

    # 3. 转换为 LangChain 消息格式
    langchain_messages = []
    for msg in chat_messages:
        if msg["role"] == "user":
            langchain_messages.append(HumanMessage(content=msg["content"]))
        else:
            langchain_messages.append(AIMessage(content=msg["content"]))

    # 4. 返回消息列表和 LangChain 格式
    return Response(
        data={
            "user_message_id": user_message.id,
            "session_id": session_id,
            "chat_history": chat_messages,
            "langchain_messages": [
                {"type": m.__class__.__name__, "content": m.content}
                for m in langchain_messages
            ],
        },
        message="Message saved, ready for Agent processing",
    )


# ================= 保存助手回复 =================


@router.post(
    "/sessions/{session_id}/assistant",
    response_model=Response[dict],
    summary="保存助手回复",
    description="保存 Agent 的助手回复到会话",
)
async def save_assistant_message(
    session_id: str,
    content: str,
    redis = Depends(get_redis_client),
    current_user = Depends(get_current_user),
):
    """
    保存助手回复。

    Args:
        session_id: 会话 ID
        content: 助手回复内容
        redis: Redis 客户端
        current_user: 当前认证用户

    Returns:
        Response: 保存的消息信息

    Raises:
        404: 会话不存在

    用途：
        前端调用 Agent 后，调用此接口保存助手回复。
    """
    session_service = RedisSessionService(redis)

    # 验证会话
    session = session_service.get_session(current_user.id, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    # 保存助手消息
    message = session_service.add_assistant_message(
        current_user.id, session_id, content
    )

    return Response(
        data={
            "message_id": message.id,
            "role": message.role,
            "content": message.content,
            "created_at": message.created_at,
        },
        message="Assistant message saved successfully",
    )


# ================= 流式聊天（可选）===================


@router.post(
    "/sessions/{session_id}/chat/stream",
    summary="流式发送消息（需要额外实现）",
    description="流式发送消息，实时返回 Agent 思考过程",
)
async def chat_stream(
    session_id: str,
    request: ChatRequest,
    redis = Depends(get_redis_client),
    current_user = Depends(get_current_user),
):
    """
    流式发送消息。

    注意：此接口需要使用 SSE（Server-Sent Events）实现。
    当前仅返回占位响应。

    TODO: 实现完整的流式聊天功能。
    """
    from fastapi.responses import StreamingResponse

    async def event_generator():
        """生成 SSE 事件。"""
        # 这里可以调用 Agent.stream() 方法
        # 逐个 yield events
        yield "data: {\"event\": \"status\", \"data\": \"Thinking...\"}\n\n"
        yield "data: {\"event\": \"message\", \"data\": \"Hello!\"}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
