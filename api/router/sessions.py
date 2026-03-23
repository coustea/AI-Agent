"""会话管理路由。"""

from typing import List

from fastapi import APIRouter, Depends, status, HTTPException
from langchain_core.messages import HumanMessage, AIMessage

from api.core.dependencies import get_current_user, get_db_session
from api.core.response import Response
from api.db.models import User, SessionCreate, ChatRequest, ChatResponse
from api.services.session import SessionService

router = APIRouter(tags=["sessions"])


# ================= 会话管理 =================


@router.post(
    "/sessions",
    response_model=Response[dict],
    status_code=status.HTTP_201_CREATED,
    summary="创建新会话",
    description="为当前用户创建一个新的聊天会话",
)
async def create_session(
    session_data: SessionCreate = SessionCreate(title="新会话"),
    db = Depends(get_db_session),
    current_user = Depends(get_current_user),
):
    """
    创建新会话。

    Args:
        session_data: 会话数据（标题）
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        Response: 新创建的会话信息

    Raises:
        401: 未认证
    """
    session_service = SessionService(db)
    session = session_service.create_session(current_user.id, session_data)

    return Response(
        data={
            "session_id": session.session_id,
            "title": session.title,
            "created_at": session.created_at.isoformat(),
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
    skip: int = 0,
    limit: int = 100,
    db = Depends(get_db_session),
    current_user = Depends(get_current_user),
):
    """
    获取用户的会话列表。

    Args:
        skip: 跳过的数量（分页）
        limit: 返回的数量（分页）
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        Response: 会话列表
    """
    session_service = SessionService(db)
    sessions = session_service.list_sessions(current_user.id, skip, limit)

    result = [
        {
            "id": s.id,
            "session_id": s.session_id,
            "title": s.title,
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
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
    db = Depends(get_db_session),
    current_user = Depends(get_current_user),
):
    """
    删除会话。

    Args:
        session_id: 会话 ID
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        Response: 删除结果

    Raises:
        404: 会话不存在
        403: 无权限
    """
    session_service = SessionService(db)
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
    skip: int = 0,
    limit: int = 1000,
    db = Depends(get_db_session),
    current_user = Depends(get_current_user),
):
    """
    获取会话消息。

    Args:
        session_id: 会话 ID
        skip: 跳过的数量
        limit: 返回的数量
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        Response: 消息列表

    Raises:
        404: 会话不存在
    """
    session_service = SessionService(db)
    messages = session_service.get_messages(session_id, current_user.id, skip, limit)

    result = [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]

    return Response(data=result, message="Messages retrieved successfully")


# ================= 聊天接口 =================


@router.post(
    "/sessions/{session_id}/chat",
    response_model=Response[dict],
    summary="发送消息",
    description="向会话发送消息并调用 Agent",
)
async def chat(
    session_id: str,
    request: ChatRequest,
    db = Depends(get_db_session),
    current_user = Depends(get_current_user),
):
    """
    发送消息。

    Args:
        session_id: 会话 ID
        request: 聊天请求（消息内容）
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        Response: Agent 的回复

    Raises:
        404: 会话不存在
        400: 聊天失败

    注意：
        - 此接口仅保存用户消息和助手回复
        - Agent 调用需要在外部实现（或通过事件系统）
        - 返回的 assistant_message_id 可用于后续更新消息
    """
    session_service = SessionService(db)

    # 验证会话
    session = session_service.get_session(session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or access denied",
        )

    # 1. 保存用户消息
    user_message = session_service.add_user_message(
        session_id, current_user.id, request.message
    )

    # 2. 获取历史消息（用于 Agent）
    chat_messages = session_service.get_chat_messages(session_id, current_user.id)

    # 3. 转换为 LangChain 消息格式
    langchain_messages = []
    for msg in chat_messages:
        if msg["role"] == "user":
            langchain_messages.append(HumanMessage(content=msg["content"]))
        else:
            langchain_messages.append(AIMessage(content=msg["content"]))

    # 4. 返回消息列表和上下文（Agent 调用由外部处理）
    return Response(
        data={
            "user_message_id": user_message.id,
            "session_id": session_id,
            "chat_history": [
                {"role": m.role, "content": m.content}
                for m in chat_messages
            ],
            "langchain_messages": [
                {"type": m.__class__.__name__, "content": m.content}
                for m in langchain_messages
            ],
        },
        message="Message saved, ready for Agent processing",
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
    db = Depends(get_db_session),
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

    return StreamingResponse(
        event_generator(), media_type="text/event-stream"
    )
