"""Long-term fact extraction and long-term memory helpers."""  # 长期事实提取服务：从对话中提取用户事实存入长期记忆

from __future__ import annotations

from datetime import timedelta

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.infra.llm import get_deepseek_llm
from app.infra.logging import get_logger
from app.memory.memory_types import FactAgentMemoryType
from app.memory._profile import (
    build_chat_history_text,
    build_memory_context_text,
    build_profile_text_from_model,
    has_extractable_signal,
    normalize_signal_text,
    select_dialogue_messages,
    MEMORY_NON_SIGNIFICANT_TEXTS,
    ProfileService,
)
from app.memory._store import MemoryStore, now

logger = get_logger(__name__)

FACT_EXTRACTION_PROMPT = """  # 事实提取提示词模板：从对话中提取值得长期记忆的用户事实
# 角色与目标
你是一个专业的长期记忆抽取引擎。你的任务是从用户的【最新导师对话记录】中，提取值得写入【长期记忆池】的用户事实、偏好、目标、背景或稳定弱点。

# 提取准则
1. 只关注核心事实、明确偏好、具体目标、背景信息和稳定弱点。
2. 忽略闲聊与通用问题，不要把一次性问题直接当长期事实。
3. 如与时间节点相关，请标记时效性并估算过期天数。
4. 如果没有值得记忆的内容，has_fact=false。
5. 不要重复已有长期记忆，只有更具体或更有价值时才输出。
6. 最多输出 3 条。

# 当前用户画像：
{profile_context}

# 已有长期记忆：
{memory_context}

# 最新对话记录：
{chat_history}

# 输出格式要求
{format_instructions}
"""


class ExtractedFactItem(BaseModel):  # 单条提取的事实项
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1)  # 事实内容
    memory_type: FactAgentMemoryType  # 记忆类型
    is_time_sensitive: bool = False  # 是否有时效性
    expires_in_days: int | None = Field(default=None, gt=0)  # 过期天数

    @field_validator("content")
    @classmethod
    def _clean_content(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("content 不能为空")
        return cleaned


class FactExtraction(BaseModel):  # 事实提取结果容器
    model_config = ConfigDict(extra="forbid")

    has_fact: bool  # 是否提取到事实
    facts: list[ExtractedFactItem] = Field(default_factory=list)  # 提取的事实列表


class FactExtractionService:  # 事实提取服务：从对话中提取并保存用户事实
    def __init__(self, *, module_name: str = "mentor", store: MemoryStore | None = None, profile_service: ProfileService | None = None) -> None:
        self.module_name = module_name
        self.store = store or MemoryStore()
        self.profile_service = profile_service or ProfileService()
        self.llm = get_deepseek_llm(temperature=0.1, streaming=False)  # 使用DeepSeek模型进行事实提取
        self.output_parser = PydanticOutputParser(pydantic_object=FactExtraction)  # 输出解析器
        self.prompt_template = ChatPromptTemplate.from_messages([("human", "{prompt_text}")])

    async def extract_and_save(self, user_id: int, session_id: str) -> bool:  # 从会话中提取事实并保存
        recent_msgs = await self.store.get_recent_messages(  # 获取最近8条消息
            user_id=user_id,
            session_id=session_id,
            module=self.module_name,
            limit=8,
        )
        if not recent_msgs:
            return True

        dialogue_msgs = select_dialogue_messages(recent_msgs)  # 筛选有效对话消息
        if not dialogue_msgs:
            return True

        user_texts = self._collect_user_texts(dialogue_msgs)  # 收集用户文本
        if not has_extractable_signal(user_texts):  # 检查是否有可提取信号
            return True

        chat_history = build_chat_history_text(dialogue_msgs)  # 构建对话历史文本
        profile_context = build_profile_text_from_model(await self.profile_service.get_user_profile(user_id))  # 构建画像上下文
        memory_context = await build_memory_context_text(self.store, user_id, self.module_name)  # 构建长期记忆上下文

        try:
            prompt_text = FACT_EXTRACTION_PROMPT.format(  # 组装提示词
                profile_context=profile_context,
                memory_context=memory_context,
                chat_history=chat_history,
                format_instructions=self.output_parser.get_format_instructions(),
            )
            response = await self.llm.ainvoke(self.prompt_template.format_messages(prompt_text=prompt_text))  # 调用LLM
            extracted = self.output_parser.parse(response.content if isinstance(response.content, str) else str(response.content))  # 解析结果
            if extracted.has_fact and extracted.facts:  # 有提取结果则保存
                for item in extracted.facts[:3]:  # 最多保存3条
                    expires_at = None
                    if item.is_time_sensitive and item.expires_in_days and item.expires_in_days > 0:  # 计算过期时间
                        expires_at = now() + timedelta(days=item.expires_in_days)
                    try:
                        await self.store.save_user_fact(
                            user_id=user_id,
                            content=item.content,
                            memory_type=item.memory_type,
                            session_id=session_id,
                            expires_at=expires_at,
                            module=self.module_name,
                        )
                    except ValueError:
                        continue
            return True
        except Exception as exc:
            logger.error("[FactExtraction] 事实提炼失败: %s", str(exc))
            return False

    def _collect_user_texts(self, messages: list) -> list[str]:  # 收集用户文本（过滤无意义内容）
        user_texts: list[str] = []
        ignore = {normalize_signal_text(text) for text in MEMORY_NON_SIGNIFICANT_TEXTS}  # 无意义文本集合
        for msg in messages[-6:]:
            if getattr(msg, "role", "") != "user":
                continue
            cleaned = normalize_signal_text(getattr(msg, "content", ""))
            if not cleaned or cleaned in ignore:
                continue
            user_texts.append(cleaned)
        return user_texts
