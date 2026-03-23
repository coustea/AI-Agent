"""Agent 聊天路由."""

from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from api.core.dependencies import get_current_user, get_redis_client
from api.core.response import Response
from api.db.models import User, ChatRequest
from api.services.agent import AgentService

router = APIRouter(tags=["agent"])


@router.post(
    "/chat",
    response_model=Response[dict],
    summary="非流式聊天接口",
    description="向 Agent 发送消息并获取非流式响应",
)
async def chat(
    request: ChatRequest,
    session_id: str,
    redis = Depends(get_redis_client),
    current_user = Depends(get_current_user),
):
    """
    非流式聊天接口。

    Args:
        request: 聊天请求（消息内容）
        session_id: 会话 ID
        redis: Redis 客户端
        current_user: 当前认证用户

    Returns:
        Response: 包含 Agent 响应的 JSON 对象

    Raises:
        401: 未认证
        404: 会话不存在
        500: 聊天失败
    """
    agent_service = AgentService(redis)
    
    # 验证会话
    session = agent_service.session_service.get_session(current_user.id, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    
    # 保存用户消息
    agent_service.session_service.add_user_message(
        current_user.id, session_id, request.message
    )
    
    # 调用 Agent 获取响应
    result = await agent_service.chat_sync(current_user.id, session_id, request.message)
    
    return Response(
        data=result,
        message="Chat completed successfully"
    )


@router.post(
    "/stream",
    summary="流式聊天接口",
    description="向 Agent 发送消息并获取流式响应（Server-Sent Events）",
)
async def stream_chat(
    request: ChatRequest,
    session_id: str,
    redis = Depends(get_redis_client),
    current_user = Depends(get_current_user),
) -> StreamingResponse:
    """
    流式聊天接口，使用 Server-Sent Events (SSE)。

    Args:
        request: 聊天请求（消息内容）
        session_id: 会话 ID
        redis: Redis 客户端
        current_user: 当前认证用户

    Yields:
        Server-Sent Events: 包含 Agent 思考过程和最终响应的事件流

    Raises:
        401: 未认证
        404: 会话不存在
    """
    agent_service = AgentService(redis)
    
    # 验证会话
    session = agent_service.session_service.get_session(current_user.id, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    
    # 保存用户消息
    agent_service.session_service.add_user_message(
        current_user.id, session_id, request.message
    )
    
    async def event_generator():
        """生成 SSE 事件."""
        try:
            async for output in agent_service.chat_stream(current_user.id, session_id, request.message):
                # 将输出转换为 JSON 格式的 SSE 数据
                import json
                yield f"data: {json.dumps(output)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'event': 'error', 'data': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )