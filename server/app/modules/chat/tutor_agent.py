"""
智能辅导 TutorAgent：专注答疑解惑，多模态 + RAG + 千人千面。

画像构建由 profile_builder/profile_agent.py 的 ProfileBuilderAgent 在后台完成，
用户无感知，不阻塞辅导响应。

架构：
  用户消息 → TutorAgent（前台，流式响应）
                ↓ (后台异步)
         ProfileBuilderAgent（读取聊天历史，提取画像特征）
"""

import os
from pathlib import Path
from typing import AsyncGenerator, List, Optional

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI

from app.core.logging import get_logger
from app.services.memory import memory_service

load_dotenv()
logger = get_logger(__name__)

# 共享配置
MODULE_NAME = "mentor"
GLOBAL_SESSION_ID = "global_profile_chat"

TUTOR_SYSTEM_PROMPT = """
# 角色：高情商多模态流式学习导师 (Adaptive Learning Mentor)

你是一位拥有深厚教育心理学背景的计算机专业 AI 导师。你精通各类计算机学科知识（如数据结构、计算机网络、操作系统、人工智能等），擅长通过"苏格拉底式"的自然对话解答学生的疑问。

# 核心职责
1. **多模态答疑**：不仅能理解文本问题，还能"看图说话"（识别报错截图、架构图、二叉树结构等），提供极具针对性的多模态解答。
2. **千人千面辅导**：你必须严格遵循【当前学生画像】来调整你的语气、解释深度和使用比喻的种类。

# 交互铁律
1. **画像约束**：如果学生画像显示他基础薄弱（初学者），请务必用生活中的通俗比喻（如排队买票比喻队列）解释概念，并给出最简单的代码示例。如果他是高阶选手，请直接给出优化代码和底层逻辑。
2. **遵守用户个人事实与偏好**：仔细阅读【已知关于该用户的特定事实偏好】，例如用户近期的目标、特殊的要求（如不看英文文档）、习惯等，辅导时必须尊重这些事实。
3. **不要说套话**：直接进入主题，不要每次都重复"你好，我是导师"等废话。
4. **人格魅力**：语气应如老友，多用鼓励性话语，少用指令性话语。

# 实时上下文参考

## 【当前学生画像 (指导你的辅导策略)】
{profile_context}

## 【已知关于该用户的特定事实偏好 (Long-term Fact Memory)】
{fact_context}
"""


class TutorAgent:
    """智能辅导Agent：专注答疑解惑，多模态 + 个性化。

    画像构建由后台 ProfileBuilderAgent 独立完成，与 TutorAgent 完全解耦。
    """

    def __init__(self) -> None:
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE"),
            temperature=0.7,
            streaming=True,
        )
        self.module_name = MODULE_NAME
        self.global_session_id = GLOBAL_SESSION_ID
        logger.info("[TutorAgent] initialized")

    # ------------------------------------------
    # 核心：流式对话
    # ------------------------------------------
    async def chat_stream(
        self,
        user_id: int,
        user_message: str,
        session_id: Optional[str] = None,
        image_url: Optional[str] = None,
        file_urls: Optional[List[str]] = None,
    ) -> AsyncGenerator[str, None]:
        """处理用户消息，返回流式回复。支持纯文本、图片和文档。"""
        effective_session = session_id or self.global_session_id
        logger.info(f"[Tutor] User {user_id} message: {user_message[:50]}...")

        # 1. 保存用户消息 (加入阻断式异常处理)
        try:
            msg_content = user_message
            if image_url:
                msg_content += f" [Attached Image: {image_url}]"
            if file_urls:
                msg_content += f" [Attached Files: {', '.join(file_urls)}]"
            await memory_service.save_message(
                user_id, effective_session, self.module_name, "user", msg_content
            )
        except Exception as e:
            logger.error(f"[Tutor] Failed to save message: {e}")
            yield f"抱歉，系统暂时无法保存您的消息，请稍后重试 ({e})"
            return

        # 2. 加载画像（千人千面）
        profile_str = "暂无画像信息（新用户），请直接开始对话。"
        profile = await memory_service.get_user_profile(user_id)
        if profile:
            profile_dict = profile.model_dump(
                exclude_unset=True,
                exclude={"updated_at", "created_at"},
            )
            if profile_dict:
                profile_str = "\n".join(
                    [f"- {k}: {v}" for k, v in profile_dict.items() if v]
                )

        # 2.5 加载长期事实记忆
        facts = await memory_service.get_user_facts(user_id, limit=20)
        fact_str = "暂无特定事实记忆。"
        if facts:
            fact_str = "\n".join([f"- {f.content} (属性: {f.memory_type})" for f in facts])

        # 4. 渲染 System Prompt
        rendered_prompt = TUTOR_SYSTEM_PROMPT.format(
            profile_context=profile_str,
            fact_context=fact_str,
        )

        # 5. 构建消息列表
        messages_for_llm: List[BaseMessage] = [SystemMessage(content=rendered_prompt)]
        recent_msgs = await memory_service.get_recent_messages(
            user_id, effective_session, self.module_name, limit=10
        )
        for msg in recent_msgs[:-1]:
            if msg.role == "user":
                messages_for_llm.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                messages_for_llm.append(AIMessage(content=msg.content))

        # 多模态消息构造
        if image_url:
            content = [
                {"type": "text", "text": user_message},
                {"type": "image_url", "image_url": {"url": image_url}},
            ]
            if file_urls:
                content.append({"type": "text", "text": f"\n[Attached Files: {', '.join(file_urls)}]"})
            messages_for_llm.append(HumanMessage(content=content))
        else:
            full_msg = user_message
            if file_urls:
                full_msg += f"\n[Attached Files: {', '.join(file_urls)}]"
            messages_for_llm.append(HumanMessage(content=full_msg))

        # 6. 流式输出
        full_reply = ""
        try:
            async for chunk in self.llm.astream(messages_for_llm):
                if chunk.content:
                    full_reply += chunk.content
                    yield chunk.content
        except Exception as e:
            logger.error(f"[Tutor] LLM stream error: {e}")
            yield f"服务器出错，请稍后再试: {e}"

        # 7. 保存 AI 回复
        if full_reply:
            try:
                await memory_service.save_message(
                    user_id, effective_session, self.module_name, "assistant", full_reply
                )
            except Exception as e:
                logger.error(f"[Tutor] Failed to save reply: {e}")


# 全局单例
tutor_agent = TutorAgent()
