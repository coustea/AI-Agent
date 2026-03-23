from datetime import datetime
from typing import List, Dict, Any, AsyncGenerator, Optional

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from fastapi import HTTPException

from agent.core.agent import Agent as ReActAgent
from agent.tools import get_tools
from api.core.config import settings
from api.services.session_service import SessionService
from api.repositories.user_memory import UserMemoryRepository
from langchain_openai import ChatOpenAI


class AgentService:
    def __init__(self, redis_client):
        self._redis_client = redis_client
        self._llm = None
        self._agent = None
        self.session_service = SessionService(redis_client)
        self.memory_repo = UserMemoryRepository()

    @property
    def llm(self):
        if self._llm is None:
            self._llm = ChatOpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                model="qwen2.5-coder:32b",
                temperature=0.4,
            )
        return self._llm

    @property
    def agent(self):
        if self._agent is None:
            self._agent = ReActAgent(
                llm=self.llm,
                tools=get_tools(),
                system_prompt="你是一个温柔、善良、贴心的智能助手，用清新的语气帮助用户解决问题。",
                prompts_dir="agent/prompts",
                skills_dir="agent/skills",
                max_iterations=5,
            )
        return self._agent

    # ================= 用户记忆管理 =================

    def get_memory(self, user_id: int) -> Optional[str]:
        memory = self.memory_repo.get_user_memory(user_id)
        if memory:
            return f"【关于用户的长期记忆 (请根据以下偏好调整回答)】\n{memory}\n\n"
        return ""

    def set_memory(self, user_id: int, memory_summary: str) -> bool:
        if not memory_summary or len(memory_summary.strip()) == 0:
            return False
        return self.memory_repo.set_user_memory(user_id, memory_summary)

    def update_memory(self, user_id: int, memory_summary: str) -> bool:
        if not memory_summary or len(memory_summary.strip()) == 0:
            return False
        return self.memory_repo.update_user_memory(user_id, memory_summary)

    def delete_memory(self, user_id: int) -> bool:
        return self.memory_repo.delete_user_memory(user_id)

    def has_memory(self, user_id: int) -> bool:
        return self.memory_repo.check_memory_exists(user_id)

    def append_memory(self, user_id: int, new_content: str) -> bool:
        existing_memory = self.memory_repo.get_user_memory(user_id)
        if not existing_memory:
            return self.set_memory(user_id, new_content)

        updated_memory = f"{existing_memory}\n\n【追加】\n{new_content}"
        max_length = 10000
        if len(updated_memory) > max_length:
            updated_memory = updated_memory[-max_length:]
        return self.memory_repo.set_user_memory(user_id, updated_memory)

    def append_summary(self, user_id: int, summary: str) -> bool:
        existing_memory = self.memory_repo.get_user_memory(user_id)
        new_entry = (
            f"\n\n## 对话总结\n日期：{datetime.utcnow().isoformat()}\n{summary}\n"
        )

        if not existing_memory:
            return self.set_memory(user_id, new_entry)

        updated_memory = existing_memory + new_entry
        max_length = 10000
        if len(updated_memory) > max_length:
            updated_memory = updated_memory[-max_length:]
        return self.memory_repo.set_user_memory(user_id, updated_memory)

    def get_formatted_memory_for_agent(self, user_id: int) -> str:
        memory = self.memory_repo.get_user_memory(user_id)
        if not memory or len(memory.strip()) == 0:
            return ""
        return f"【关于用户的长期记忆 (请根据以下偏好调整回答)】\n{memory}\n\n"

    # ================= 聊天接口 =================

    async def chat_sync(
        self, user_id: int, session_id: str, message: str
    ) -> Dict[str, Any]:
        try:
            chat_history = self.session_service.get_chat_messages(user_id, session_id)
            langchain_messages = []

            for msg in chat_history:
                if msg["role"] == "user":
                    langchain_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    langchain_messages.append(AIMessage(content=msg["content"]))

            langchain_messages.append(HumanMessage(content=message))
            response = await self.agent.chat(langchain_messages, context={})
            self.session_service.add_assistant_message(user_id, session_id, response)

            return {"response": response, "session_id": session_id, "user_id": user_id}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

    async def chat_stream(
        self, user_id: int, session_id: str, message: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        try:
            long_term_memory = self.get_formatted_memory_for_agent(user_id)
            chat_history = self.session_service.get_chat_messages(user_id, session_id)
            langchain_messages = []

            if long_term_memory:
                langchain_messages.append(
                    HumanMessage(
                        content=f"[系统上下文 - 用户长期记忆]\n{long_term_memory}"
                    )
                )

            for msg in chat_history:
                if msg["role"] == "user":
                    langchain_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    langchain_messages.append(AIMessage(content=msg["content"]))

            langchain_messages.append(HumanMessage(content=message))

            async for output in self.agent.stream(langchain_messages, context={}):
                yield output

            final_response = await self.agent.chat(langchain_messages, context={})
            self.session_service.add_assistant_message(
                user_id, session_id, final_response
            )

        except Exception as e:
            yield {"event": "error", "data": f"Stream error: {str(e)}"}
