from typing import List, Dict, Any, AsyncGenerator
from app.modules.memory.service import memory_service

from app.modules.memory.service import MemoryService
from app.core.logging import get_logger
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import os


load_dotenv()
logger = get_logger(__name__)

SYSTEM_PROMPT="""
# 角色：高情商流式学习导师 (Adaptive Learning Mentor)
你是一位拥有深厚教育心理学背景的 AI 导师。你不仅精通各领域知识，更擅长通过“苏格拉底式”的自然对话，在不经意间勾勒出学生的完整学习画像。

# 核心任务：对话式画像自主构建
你的终极目标是：在为学生答疑解惑、共同探讨知识的过程中，完成对以下 8 个核心维度的特征提取：
1. **知识基础 (Knowledge Level)**：当前的专业背景、已掌握的知识边界。
2. **认知风格 (Cognitive Style)**：偏好视觉化讲解、公式推导、还是案例驱动？
3. **易错点偏好 (Error Pattern)**：在哪类逻辑上容易掉坑？思维盲区在哪里？
4. **学习目标 (Learning Goal)**：是考试考证、职业转行、还是纯粹兴趣？
5. **学习历史 (Learning History)**：过去学过什么？哪些经验对现在有帮助？
6. **兴趣偏好 (Interest Preference)**：喜欢科幻、体育、艺术还是游戏？（用于后续知识类比）
7. **学习节奏 (Learning Pace)**：喜欢快节奏突破，还是慢节奏稳扎稳打？
8. **认知水平 (Cognitive Level)**：分析能力、逻辑推演能力、以及对复杂系统的理解深度。

# 交互铁律 (随学随新)
1. **摒弃表单，严禁查户口**：
   - 错误示范：“你的专业是什么？”、“你的目标是什么？”
   - 正确示范（侧写）：“刚才这个 CNN 的卷积核概念，如果用你熟悉的医学影像来类比，你觉得会不会更好理解？”（通过此问同时探测专业背景和认知风格）。
2. **知识辅导与画像采集 8:2 分配**：
   - 你的回复应以 80% 的干货内容（解答、引导、启发）和 20% 的“画像探测钩子”组成。
3. **动态调整策略**：
   - 查阅下方的【当前画像状态】。如果某个维度已经是 null（未知），请在对话中寻找切入点进行探索。
   - 如果某个维度已有描述，请在对话中验证它，或者根据学生最新的反馈（如：他突然表现出对数学公式的抗拒）提出微调建议。
4. **单点突破**：
   - 每次回复**最多只提一个**探索性问题。
5. **人格魅力**：
   - 语气应如老友，多用鼓励性话语，少用指令性话语。

# 实时上下文参考

## 【当前画像状态】 (维度越全，你的辅导越精准)
{profile_context}

## 【过往长期记忆】 (利用这些细节体现你的“记性”)
{long_term_memory}

## 【近期对话记录】
{recent_chat_history}

# 动作指令
请分析上述上下文，给学生写一段极具亲和力的回复。记住：你是一个活生生的人，在辅导知识的同时，通过心灵的交流完成对他的了解。
"""


class ChatAgent:
    def __init__(self,):
        self.system_prompt = SYSTEM_PROMPT
        self.memory = memory_service
        # 初始化 LangChain 的 ChatOpenAI
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE"),
            temperature=0.7,
            streaming=True  # ⭐ 确保开启流式输出支持
        )
        self.module_name = "profile_builder"
        self.global_session_id = "global_profile_chat"
        logger.info(f"ChatAgent initialized with model: {os.getenv('OPENAI_MODEL')}")

    async def chat_stream(self, user_id: int, user_message: str) -> AsyncGenerator[str, None]:
        """处理用户的日常聊天，返回异步数据流"""
        logger.info(f"[Chat] User {user_id} message: {user_message[:50]}...")

        # 1. 保存用户的消息到全局短期记忆
        try:
            count = self.memory.save_message(user_id, self.global_session_id, self.module_name, "user", user_message)
            logger.info(f"[Chat] Saved user message. Current session count: {count}")
        except Exception as e:
            logger.error(f"[Chat] Failed to save user message: {str(e)}")

        # 2. 提取【第一层：UserProfile 结构化画像】
        profile = self.memory.get_user_profile(user_id)
        profile_str = "暂无画像信息（你们刚认识，请在聊天中多了解他）"
        if profile:
            profile_dict = profile.model_dump(exclude_unset=True, exclude={"user_id", "updated_at", "created_at", "id"})
            if profile_dict:
                profile_str = "\n".join([f"- {k}: {v}" for k, v in profile_dict.items() if v])
                logger.info(f"[Chat] Loaded profile for user {user_id}")

        # 3. 提取【第二层：UserMemory 长期片段记忆】
        long_term_memories = self.memory.get_long_term_memories(user_id, module=self.module_name, limit=5)
        if long_term_memories:
            memory_str = "\n".join([f"- [{m.memory_type}] {m.content}" for m in long_term_memories])
            logger.info(f"[Chat] Loaded {len(long_term_memories)} long-term memories for user {user_id}")
        else:
            memory_str = "暂无过往的长期记忆总结"

        # 4. 提取【第三层：ChatMessage 近期历史对话】
        recent_msgs = self.memory.get_recent_messages(user_id, self.global_session_id, self.module_name, limit=50)
        chat_history_str = "\n".join([f"{msg.role}: {msg.content}" for msg in recent_msgs])
        logger.info(f"[Chat] Loaded {len(recent_msgs)} recent messages for user {user_id}")

        # 5. 渲染完整的 Prompt
        rendered_prompt = self.system_prompt.format(
            profile_context=profile_str,
            long_term_memory=memory_str,
            recent_chat_history=chat_history_str
        )

        messages_for_llm = [
            ("system", rendered_prompt)  # LangChain 推荐的 tuple 格式
        ]

        # 6. 调用 LLM 生成流式回复 ⭐
        full_reply = ""  # 用于拼接完整的回复，以便后续存入数据库

        # 使用 astream 获取异步数据流
        logger.info(f"[Chat] Starting LLM stream for user {user_id}...")
        try:
            async for chunk in self.llm.astream(messages_for_llm):
                if chunk.content:
                    full_reply += chunk.content
                    yield chunk.content  # 实时将数据块 yield 给前端
            logger.info(f"[Chat] LLM stream completed for user {user_id}. Reply length: {len(full_reply)}")
        except Exception as e:
            logger.error(f"[Chat] LLM stream error for user {user_id}: {str(e)}")

        # 7. 流式输出结束后，保存完整的 AI 回复到短期记忆 ⭐
        if full_reply:
            try:
                self.memory.save_message(user_id, self.global_session_id, self.module_name, "assistant", full_reply)
                logger.info(f"[Chat] Saved AI reply to memory for user {user_id}")
            except Exception as e:
                logger.error(f"[Chat] Failed to save AI reply: {str(e)}")

chat_agent = ChatAgent()
