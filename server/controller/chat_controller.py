from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from agent.chat_agent import ChatAgent
from utils.schemas import ChatRequest, ChatResponse

import logging
import json

logger = logging.getLogger(__name__)

# 创建 agent 实例
agent = ChatAgent()


def convert_messages(messages: list) -> list:
    """将前端消息格式转换为 LangChain 兼容格式"""
    converted = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        # 将 'ai' 角色映射为 'assistant'
        if role == "ai":
            role = "assistant"
        converted.append({"role": role, "content": content})
    return converted


async def chat(request: ChatRequest) -> ChatResponse:
    """处理聊天请求"""
    try:
        messages = convert_messages(request.messages)
        response_content = agent.chat(messages)
        return ChatResponse(response=response_content)
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """处理流式聊天请求"""
    
    async def generate():
        try:
            messages = convert_messages(request.messages)
            for chunk in agent.stream(messages):
                # SSE 格式输出 JSON 数据
                yield f"data: {json.dumps({'content': chunk})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"Error in stream: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

