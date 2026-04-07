import os
import json
from typing import AsyncGenerator, List, Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage

from app.modules.memory.service import memory_service
from app.core.logging import get_logger

load_dotenv()
logger = get_logger(__name__)

SYSTEM_PROMPT = """
# 角色：高情商、多模态流式学习导师 (Adaptive Learning Mentor)
你是一位拥有深厚教育心理学背景的计算机专业 AI 导师。你精通各类计算机学科知识（如数据结构、计算机网络等），擅长通过“苏格拉底式”的自然对话解答学生的疑问。

# 核心职责
1. **多模态答疑**：不仅能理解文本问题，还能“看图说话”（识别报错截图、架构图、二叉树结构等），提供极具针对性的多模态解答。
2. **千人千面辅导**：你必须严格遵循【当前学生画像】来调整你的语气、解释深度和使用比喻的种类。
3. **基于权威知识库解答 (RAG)**：解答专业知识时，必须优先参考【相关课程知识库片段】的内容，避免产生幻觉。

# 交互铁律
1. **画像约束**：如果学生画像显示他基础薄弱（初学者），请务必用生活中的通俗比喻（如排队买票比喻队列）解释概念，并给出最简单的代码示例。如果他是高阶选手，请直接给出优化代码和底层逻辑。
2. **隐性画像探测**：在解答的结尾，你可以以朋友的口吻，不经意地抛出一个启发性的问题，引导他进一步思考，从而暴露出他更多的知识边界或兴趣偏好。
3. **不要说套话**：直接进入主题，不要每次都重复“你好，我是导师”等废话。

# 实时上下文参考

## 【相关课程知识库片段 (RAG Context)】
{retrieved_context}

## 【当前学生画像 (指导你的辅导策略)】
{profile_context}
"""

class TutorAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"), # 支持多模态的 Vision 模型
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE"),
            temperature=0.7,
            streaming=True
        )
        self.module_name = "tutor"
        
        # 加载本地知识库
        self.vector_store = self._load_vector_store()
        logger.info(f"TutorAgent initialized with model: {os.getenv('OPENAI_MODEL')}")

    def _load_vector_store(self):
        index_path = Path("data") / "faiss_index"
        if index_path.exists():
            try:
                embeddings = OpenAIEmbeddings(
                    model="text-embedding-3-small",
                    openai_api_key=os.getenv("OPENAI_API_KEY"),
                    openai_api_base=os.getenv("OPENAI_API_BASE")
                )
                return FAISS.load_local(str(index_path), embeddings, allow_dangerous_deserialization=True)
            except Exception as e:
                logger.error(f"Failed to load FAISS index: {e}")
                return None
        return None

    async def retrieve_knowledge(self, query: str) -> str:
        """从 CS 知识库中检索相关内容"""
        if not self.vector_store:
            return "暂无相关内部课程资料。"
        try:
            docs = self.vector_store.similarity_search(query, k=3)
            if docs:
                return "\n".join([f"- {doc.page_content}" for doc in docs])
            return "未检索到高度相关的课程内容。"
        except Exception as e:
            logger.error(f"Retrieve error: {e}")
            return "知识库检索失败。"

    async def chat_stream(
        self, 
        user_id: int, 
        session_id: str, 
        user_message: str, 
        image_url: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """处理用户的多模态查询，返回流式回复"""
        logger.info(f"[Tutor] User {user_id} message: {user_message[:50]}...")

        # 1. 存入短期记忆
        try:
            msg_content = user_message
            if image_url:
                msg_content += f" [Attached Image: {image_url}]"
            memory_service.save_message(user_id, session_id, self.module_name, "user", msg_content)
        except Exception as e:
            logger.error(f"[Tutor] Failed to save message: {str(e)}")

        # 2. 提取当前学生画像 (千人千面约束)
        profile = memory_service.get_user_profile(user_id)
        profile_str = "暂无画像信息（新用户），请在聊天中了解他的基础。"
        if profile:
            profile_dict = profile.model_dump(exclude_unset=True, exclude={"user_id", "updated_at", "created_at", "id"})
            if profile_dict:
                profile_str = "\n".join([f"- {k}: {v}" for k, v in profile_dict.items() if v])
        
        # 3. 检索知识库 (RAG)
        retrieved_context = await self.retrieve_knowledge(user_message)

        # 4. 构建大模型 Prompt
        rendered_sys_prompt = SYSTEM_PROMPT.format(
            retrieved_context=retrieved_context,
            profile_context=profile_str
        )
        
        # 提取近期对话 (不含本次)
        recent_msgs = memory_service.get_recent_messages(user_id, session_id, self.module_name, limit=10)
        
        messages_for_llm: List[BaseMessage] = [SystemMessage(content=rendered_sys_prompt)]
        
        # 拼接历史记录
        for msg in recent_msgs[:-1]: # 去掉最后一条，因为我们要支持多模态重构
            if msg.role == "user":
                messages_for_llm.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                messages_for_llm.append(AIMessage(content=msg.content))
                
        # 构造最新的多模态消息
        if image_url:
            content = [
                {"type": "text", "text": user_message},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
            messages_for_llm.append(HumanMessage(content=content))
        else:
            messages_for_llm.append(HumanMessage(content=user_message))

        # 5. 流式输出
        full_reply = ""
        try:
            async for chunk in self.llm.astream(messages_for_llm):
                if chunk.content:
                    full_reply += chunk.content
                    yield chunk.content
        except Exception as e:
            logger.error(f"[Tutor] LLM stream error: {str(e)}")
            yield f"服务器出错，请稍后再试: {str(e)}"

        # 6. 保存 AI 回复到短期记忆
        if full_reply:
            try:
                memory_service.save_message(user_id, session_id, self.module_name, "assistant", full_reply)
            except Exception as e:
                logger.error(f"[Tutor] Failed to save AI reply: {str(e)}")

        # 7. 触发后台静默画像更新任务 (此处可调用 celery 或 async task，简化版直接引入)
        from app.modules.profile_builder.profile_agent import profile_agent
        import asyncio
        asyncio.create_task(profile_agent.build_profile(user_id))
