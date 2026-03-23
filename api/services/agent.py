"""Agent 服务层，处理与 Agent 的交互逻辑."""

import asyncio
from typing import List, Dict, Any, AsyncGenerator
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from fastapi import HTTPException

from agent.core.agent import Agent as ReActAgent
from agent.tools import get_tools
from api.core.config import settings
from api.services.redis_session_service import RedisSessionService
from api.services.user_memory_service import UserMemoryService
from langchain_openai import ChatOpenAI


class AgentService:
    """Agent 服务类，处理聊天逻辑."""

    def __init__(self, redis_client):
        """初始化 Agent 服务."""
        # 初始化 LLM
        self.llm = ChatOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model="qwen2.5:14b",  # 可以根据需要配置
            temperature=0.7,
        )
        
        # 初始化 Agent（完全独立，不访问任何记忆存储）
        self.agent = ReActAgent(
            llm=self.llm,
            tools=get_tools(),
            system_prompt="你是一个温柔、善良、贴心的智能助手，用清新的语气帮助用户解决问题。",
            prompts_dir="agent/prompts",
            skills_dir="agent/skills",
            max_iterations=5
        )
        
        # Redis 会话服务
        self.session_service = RedisSessionService(redis_client)

    async def chat_sync(self, user_id: int, session_id: str, message: str) -> Dict[str, Any]:
        """同步聊天接口 - 非流式输出."""
        try:
            # 获取会话历史消息（近期记忆）
            chat_history = self.session_service.get_chat_messages(user_id, session_id)
            
            # 构造完整的消息列表
            langchain_messages = []
            
            # 添加历史消息
            for msg in chat_history:
                if msg["role"] == "user":
                    langchain_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    langchain_messages.append(AIMessage(content=msg["content"]))
            
            # 添加新消息
            langchain_messages.append(HumanMessage(content=message))
            
            # 调用 Agent 获取结果（Agent 只处理消息，不访问任何存储）
            response = await self.agent.chat(langchain_messages, context={})
            
            # 保存助手回复到会话（近期记忆）
            self.session_service.add_assistant_message(user_id, session_id, response)
            
            return {
                "response": response,
                "session_id": session_id,
                "user_id": user_id
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

    async def chat_stream(self, user_id: int, session_id: str, message: str) -> AsyncGenerator[Dict[str, Any], None]:
        """流式聊天接口 - 逐步输出."""
        try:
            # 获取用户长期记忆
            long_term_memory = self.user_memory_service.get_formatted_memory_for_agent(user_id)
            
            # 获取会话历史消息（近期记忆）
            chat_history = self.session_service.get_chat_messages(user_id, session_id)
            
            # 构造完整的消息列表，包含长期记忆上下文
            langchain_messages = []
            
            # 如果有长期记忆，添加为系统上下文（在消息历史之前）
            if long_term_memory:
                langchain_messages.append(HumanMessage(content=f"[系统上下文 - 用户长期记忆]\n{long_term_memory}"))
            
            # 添加历史消息
            for msg in chat_history:
                if msg["role"] == "user":
                    langchain_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    langchain_messages.append(AIMessage(content=msg["content"]))
            
            # 添加新消息
            langchain_messages.append(HumanMessage(content=message))
            
            # 调用 Agent 流式输出（Agent 只处理消息，不访问任何存储）
            async for output in self.agent.stream(langchain_messages, context={}):
                yield output
            
            # 在流式完成后，获取最终结果并保存
            final_response = await self.agent.chat(langchain_messages, context={})
            
            # 保存助手回复到会话（近期记忆）
            self.session_service.add_assistant_message(user_id, session_id, final_response)
            
        except Exception as e:
            yield {"event": "error", "data": f"Stream error: {str(e)}"}