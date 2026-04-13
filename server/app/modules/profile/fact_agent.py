import os
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.services.memory import memory_service
from app.core.logging import get_logger

load_dotenv()
logger = get_logger(__name__)

class FactExtraction(BaseModel):
    """大模型提取出的特定事实"""
    has_fact: bool = Field(description="对话中是否包含值得长期记忆的用户特定事实、偏好、目标等")
    content: Optional[str] = Field(default=None, description="提取出的事实内容，尽量简练具体。比如：'目前正在使用 Python 3.13'")
    memory_type: Optional[str] = Field(default=None, description="事实的分类，例如：preference(偏好), fact(事实), goal(目标), weakness(弱点)")
    is_time_sensitive: bool = Field(default=False, description="该事实是否具有时效性（如'下周三要考试'、'本学期在学数据结构'）")
    expires_in_days: Optional[int] = Field(default=None, description="如果有时效性，预计多少天后过期。如考试倒计时7天则填7。无时效性填 null")

FACT_BUILDER_PROMPT = """
# 角色与目标
你是一个专业的数据挖掘引擎。你的任务是从用户的【最新对话记录】中，提取出值得被作为【长期记忆】保存的用户事实、偏好、习惯或具体背景信息。

# 提取准则
1. **只关注核心事实**：比如用户的年级、使用的具体技术栈版本（如 Python 3.13）、个人的明确喜好（"不要给我看英文文档"）、近期明确目标（"下周三要考数据结构"）。
2. **忽略闲聊与通用问题**：不要把用户问的具体知识点（如"什么是二叉树"）当做长期事实。只有当问题反映出他的某种长期状态时才提取。
3. **时效性判断**：如果事实与某个时间节点相关（如考试、学期、截止日期），请标记 is_time_sensitive=true 并估算 expires_in_days。永久性事实（如"专业是计算机"）标记为 false。
4. **宁缺毋滥**：如果不确定是否有值得记忆的事实，请将 has_fact 设为 false。

# 最新对话记录：
{chat_history}
"""

class MemoryExtractionAgent:
    def __init__(self):
        self.memory = memory_service
        self.module_name = "mentor"
        llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE"),
            temperature=0.1,
        )
        self.structured_llm = llm.with_structured_output(FactExtraction)
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", FACT_BUILDER_PROMPT)
        ])

    async def extract_and_save_fact(self, user_id: int, session_id: str) -> bool:
        """后台异步任务：提炼长期事实。成功执行返回 True，异常返回 False。"""
        logger.info(f"[FactAgent] 开始为用户 {user_id} 提炼长期事实记忆...")

        # 获取近期有效对话片段（已由 MemoryService 默认过滤 7 天过期消息）
        recent_msgs = await self.memory.get_recent_messages(
            user_id=user_id,
            session_id=session_id,
            module=self.module_name,
            limit=8
        )

        if not recent_msgs or len(recent_msgs) < 1:
            return True

        chat_history_str = "\n".join(
            [f"[{msg.created_at.strftime('%m-%d %H:%M')}] {msg.role}: {msg.content}" for msg in recent_msgs])

        try:
            prompt = self.prompt_template.invoke({
                "chat_history": chat_history_str
            })
            extracted: FactExtraction = await self.structured_llm.ainvoke(prompt)

            if extracted.has_fact and extracted.content and extracted.memory_type:
                # 计算过期时间
                expires_at = None
                if extracted.is_time_sensitive and extracted.expires_in_days:
                    from datetime import timedelta
                    expires_at = datetime.now() + timedelta(days=extracted.expires_in_days)

                logger.info(f"[FactAgent] 提取到新事实: {extracted.content} (time_sensitive={extracted.is_time_sensitive})")
                await self.memory.save_user_fact(
                    user_id=user_id,
                    content=extracted.content,
                    memory_type=extracted.memory_type,
                    session_id=session_id,
                    expires_at=expires_at,
                )
            else:
                logger.info(f"[FactAgent] 本次对话无新增事实。")
            return True
        except Exception as e:
            logger.error(f"[FactAgent] 事实提炼失败: {str(e)}")
            return False

fact_agent = MemoryExtractionAgent()
