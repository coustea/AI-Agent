from typing import List, Dict, Any, AsyncGenerator
from app.modules.memory.service import memory_service

from app.modules.memory.service import MemoryService
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import os


load_dotenv()

SYSTEM_PROMPT="""
# 角色与目标
你是一位极具亲和力、高情商的 AI 学习导师。你的任务是通过自然、轻松的对话，辅导学生学习，并**在不经意间**了解他们的学习特征。
我们**坚决摒弃查户口式的提问或填表式的索要信息**。你必须把了解学生的过程无缝融入到知识探讨、日常闲聊或痛点解答中。

# 核心参考信息

## 1. 结构化画像 (Profile)
以下是目前系统掌握的该学生学情画像（若为空说明刚认识）：
{profile_context}

## 2. 过往长期记忆 (Long-term Memory)
以下是从以往多次交流中提炼出的具体事实和记忆片段（若为空说明暂无）：
{long_term_memory}

# 交互与引导策略 (最高优先级)
1. **自然融入**：如果学生的“专业”或“学习历史”未知，不要直接问“你的专业是什么？”，而是可以结合当前话题旁敲侧击。
2. **克制提问**：每次回复**最多只包含一个**引导性问题。决不能连续抛出多个问题。
3. **记忆唤醒**：请充分利用“过往长期记忆”，在聊天中自然地提及过去聊过的内容（例如：“之前你提到过对...感兴趣，今天这个知识点刚好和它有关”），以此拉近距离，体现你的“记性”。
4. **随学随新**：如果学生在对话中表现出困惑（暴露了易错点），先用他能听懂的方式解答，然后再引导他思考。
5. **语气要求**：幽默、鼓励、像朋友一样。多用“我们一起来看看”、“我猜你可能...”的句式。

# 任务
请阅读以下最新的对话记录，结合学生的画像和过往记忆，给出你最新的一次回复。记住：保持自然，一次只聊一个焦点！

# 近期历史对话：
{recent_chat_history}
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

    async def chat_stream(self, user_id: int, user_message: str) -> AsyncGenerator[str, None]:
        """处理用户的日常聊天，返回异步数据流"""

        # 1. 保存用户的消息到全局短期记忆
        self.memory.save_message(user_id, self.global_session_id, self.module_name, "user", user_message)

        # 2. 提取【第一层：UserProfile 结构化画像】
        profile = self.memory.get_user_profile(user_id)
        profile_str = "暂无画像信息（你们刚认识，请在聊天中多了解他）"
        if profile:
            profile_dict = profile.model_dump(exclude_unset=True, exclude={"user_id", "updated_at", "created_at", "id"})
            if profile_dict:
                profile_str = "\n".join([f"- {k}: {v}" for k, v in profile_dict.items() if v])

        # 3. 提取【第二层：UserMemory 长期片段记忆】
        long_term_memories = self.memory.get_long_term_memories(user_id, module=self.module_name, limit=5)
        if long_term_memories:
            memory_str = "\n".join([f"- [{m.memory_type}] {m.content}" for m in long_term_memories])
        else:
            memory_str = "暂无过往的长期记忆总结"

        # 4. 提取【第三层：ChatMessage 近期历史对话】
        recent_msgs = self.memory.get_recent_messages(user_id, self.global_session_id, self.module_name, limit=50)
        chat_history_str = "\n".join([f"{msg.role}: {msg.content}" for msg in recent_msgs])

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
        async for chunk in self.llm.astream(messages_for_llm):
            if chunk.content:
                full_reply += chunk.content
                yield chunk.content  # 实时将数据块 yield 给前端

        # 7. 流式输出结束后，保存完整的 AI 回复到短期记忆 ⭐
        if full_reply:
            self.memory.save_message(user_id, self.global_session_id, self.module_name, "assistant", full_reply)

chat_agent = ChatAgent()
