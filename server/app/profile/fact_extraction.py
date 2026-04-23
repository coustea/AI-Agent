"""长期记忆提取服务。

从对话中提取用户事实、偏好、目标、背景等长期记忆。
服务于聊天智能体和数字人。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.infra.logging import get_logger
from app.infra.llm import get_deepseek_llm
from app.memory.long_term import long_term_service
from app.memory.memory_types import FactAgentMemoryType
from app.memory.service import memory_service
from app.profile.helpers import (
    build_chat_history_text,
    build_memory_context_text,
    build_profile_context_text,
    select_dialogue_messages,
)
from app.profile.policy import (
    has_extractable_signal,
    normalize_signal_text,
    MEMORY_NON_SIGNIFICANT_TEXTS,
)
from app.profile.prompts import render_fact_extraction_prompt

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Pydantic 输出模型
# ---------------------------------------------------------------------------

class ExtractedFactItem(BaseModel):
    """单条候选长期记忆。"""
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, description="提取出的事实内容，尽量简练具体。比如：'目前正在使用 Python 3.13'")
    memory_type: FactAgentMemoryType = Field(description="事实分类：preference / fact / goal / weakness / background")
    is_time_sensitive: bool = Field(default=False, description="该事实是否具有时效性（如'下周三要考试'、'本学期在学数据结构'）")
    expires_in_days: int | None = Field(default=None, gt=0, description="如果有时效性，预计多少天后过期。如考试倒计时7天则填7。无时效性填 null")

    @field_validator("content")
    @classmethod
    def _clean_content(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("content 不能为空")
        return cleaned


class FactExtraction(BaseModel):
    """LLM 提取的长期记忆批次。"""
    model_config = ConfigDict(extra="forbid")

    has_fact: bool = Field(description="对话中是否包含值得长期记忆的用户特定事实、偏好、目标等")
    facts: list[ExtractedFactItem] = Field(default_factory=list, description="提取出的长期记忆候选列表，最多 3 条")


# ---------------------------------------------------------------------------
# 服务类
# ---------------------------------------------------------------------------

class FactExtractionService:
    """长期记忆提取服务。

    职责：
    - 从对话中提取用户事实、偏好、目标、背景
    - 调用 LLM 进行结构化提取
    - 持久化到 UserMemory 表（带去重/合并）

    服务对象：聊天智能体、数字人
    """

    def __init__(self, *, module_name: str = "mentor") -> None:
        self.module_name = module_name
        self.llm = get_deepseek_llm(temperature=0.1, streaming=False)
        self.long_term = long_term_service
        self.memory = memory_service  # 用于获取对话历史
        self.output_parser = PydanticOutputParser(pydantic_object=FactExtraction)
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("human", "{prompt_text}")
        ])

    async def extract_and_save(self, user_id: int, session_id: str) -> bool:
        """从对话中提取并保存长期记忆。

        Args:
            user_id: 用户 ID
            session_id: 会话 ID

        Returns:
            是否成功完成（即使没有提取到新记忆也返回 True）
        """
        logger.info("[FactExtraction] 开始为用户 %s 提炼长期事实记忆...", user_id)

        # 1. 获取近期对话
        recent_msgs = await self.memory.get_recent_messages(
            user_id=user_id,
            session_id=session_id,
            module=self.module_name,
            limit=8,
        )

        if not recent_msgs:
            return True

        # 2. 筛选有效对话
        dialogue_msgs = select_dialogue_messages(recent_msgs)
        if not dialogue_msgs:
            return True

        # 3. 快速信号检测，无信号则跳过 LLM
        user_texts = self._collect_user_texts(dialogue_msgs)
        if not has_extractable_signal(user_texts):
            logger.info("[FactExtraction] 最近对话缺少长期记忆信号，跳过提取。")
            return True

        # 4. 构建上下文
        chat_history = build_chat_history_text(dialogue_msgs)
        profile_context = await build_profile_context_text(user_id)
        memory_context = await build_memory_context_text(user_id, self.module_name)

        # 5. 调用 LLM 提取
        try:
            prompt_text = render_fact_extraction_prompt(
                profile_context=profile_context,
                memory_context=memory_context,
                chat_history=chat_history,
                format_instructions=self.output_parser.get_format_instructions(),
            )
            extracted = await self._invoke_llm(prompt_text)

            # 6. 持久化
            if extracted.has_fact and extracted.facts:
                saved_count = 0
                for item in extracted.facts[:3]:
                    expires_at = None
                    if item.is_time_sensitive and item.expires_in_days and item.expires_in_days > 0:
                        expires_at = datetime.now() + timedelta(days=item.expires_in_days)

                    logger.info("[FactExtraction] 提取到新事实: %s (type=%s)", item.content, item.memory_type)
                    try:
                        await self.long_term.save_user_fact(
                            user_id=user_id,
                            content=item.content,
                            memory_type=item.memory_type,
                            session_id=session_id,
                            expires_at=expires_at,
                            module=self.module_name,
                        )
                    except ValueError as exc:
                        logger.info(
                            "[FactExtraction] 跳过无效事实: content=%r type=%s reason=%s",
                            item.content,
                            item.memory_type,
                            exc,
                        )
                        continue
                    saved_count += 1

                logger.info("[FactExtraction] 本轮共处理 %d 条长期记忆候选。", saved_count)
            else:
                logger.info("[FactExtraction] 本次对话无新增事实。")

            return True

        except Exception as e:
            logger.error("[FactExtraction] 事实提炼失败: %s", str(e))
            return False

    # ---------------------------------------------------------------------------
    # 内部方法
    # ---------------------------------------------------------------------------

    def _collect_user_texts(self, messages: list) -> list[str]:
        """收集用户消息文本用于信号检测。"""
        user_texts: list[str] = []
        ignore = {normalize_signal_text(t) for t in MEMORY_NON_SIGNIFICANT_TEXTS}

        for msg in messages[-6:]:
            if getattr(msg, "role", "") != "user":
                continue
            cleaned = normalize_signal_text(getattr(msg, "content", ""))
            if not cleaned or cleaned in ignore:
                continue
            user_texts.append(cleaned)

        return user_texts

    async def _invoke_llm(self, prompt_text: str) -> FactExtraction:
        """调用 LLM 并解析结构化输出。"""
        messages = self.prompt_template.format_messages(prompt_text=prompt_text)
        response = await self.llm.ainvoke(messages)
        content = response.content if isinstance(response.content, str) else str(response.content)
        return self.output_parser.parse(content)
