"""Profile persistence and profile-building logic."""  # 用户画像持久化与构建逻辑

from __future__ import annotations

import re
from typing import Final

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing_extensions import Annotated

from app.config import PROFILE_GATE_EVERY_N_ASSISTANT_TURNS
from app.infra.database import engine
from app.infra.llm import get_deepseek_llm
from app.infra.logging import get_logger
from app.infra.models import ChatMessage, UserProfile, UserProfileHistory
from app.memory.memory_types import (
    MEMORY_TYPE_BACKGROUND,
    MEMORY_TYPE_FACT,
    MEMORY_TYPE_GOAL,
    MEMORY_TYPE_PREFERENCE,
    MEMORY_TYPE_WEAKNESS,
)
from app.memory._store import MemoryStore, normalize_text

logger = get_logger(__name__)
Score = Annotated[int, Field(ge=0, le=100)]  # 评分类型：0-100的整数

PROFILE_BUILDING_PROMPT = """  # 画像构建提示词模板：从对话中提取8维学习画像
# 角色与目标
你是一个顶尖的 AI 教育心理学家和学习画像建模引擎。你的任务是根据学生【原有的学习画像】、【已有长期记忆】和【最新的一段导师对话记录】，提炼出稳定、可复用、足够抽象的学习特征，合并生成包含 **8 个核心维度** 的【最新全局学习画像】。

# 8 个核心维度矩阵：
1. 知识基础 (Knowledge Level)
2. 认知风格 (Cognitive Style)
3. 易错点偏好 (Error Pattern)
4. 学习目标 (Learning Goal)
5. 学习历史 (Learning History)
6. 兴趣偏好 (Interest Preference)
7. 学习节奏 (Learning Pace)
8. 认知水平 (Cognitive Level)

# 原有学习画像：
{current_profile}

# 已有长期记忆：
{memory_context}

# 最新对话记录：
{chat_history}

# 更新与合并规则
0. 若最近对话没有稳定可复用的学习特征变化，`should_update=false`。
1. 每个非空字段都必须能被原画像、长期记忆或最新对话支撑。
2. 最新稳定证据优先增量更新；无新证据时保留原有值。
3. 只有稳定、跨主题可复用的特征写入画像。
4. 具体临时事实应留在长期记忆，不要直接上升为画像。
5. 请输出 `profile_summary`。
6. 非空维度同时输出 0-100 的整数评分；证据不足则输出 null。

# 输出格式要求
{format_instructions}
"""

MEMORY_NON_SIGNIFICANT_TEXTS: Final[frozenset[str]] = frozenset({
    "谢谢", "好的", "收到", "明白了", "继续", "再来一道题", "ok", "OK"
})
MEMORY_QUESTION_MARKERS: Final[tuple[str, ...]] = (
    "什么是", "什么叫", "怎么", "如何", "为什么",
    "请解释", "解释一下", "讲讲", "介绍一下", "请问",
    "我想问", "能不能", "可不可以",
)
MEMORY_STABLE_SIGNAL_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"我(?:总是|经常|一直|老是|反复).*(?:出错|不会|卡住|卡在|记不住|搞不清|混淆|薄弱|边界)"),
    re.compile(r"我(?:喜欢|不喜欢|更喜欢|偏好|习惯)"),
    re.compile(r"我(?:在学|正在学|学过|以前学过|已经学过|准备|打算|想(?:学|考|准备|提高|练习))"),
    re.compile(r"我(?:下周|本学期|这学期|最近|目前|现在).*(?:学|补|复习|准备|做题|刷题|作业|实验|项目|考试)"),
    re.compile(r"(?:专业|年级|方向|课程|考试|证书|竞赛|实习|面试|项目|课设|论文)"),
)
_MEMORY_SIGNAL_PUNCT_RE: Final[re.Pattern[str]] = re.compile(r'[。！？!?；;，,、：:…""\"\'`（）()\[\]{}<>《》\s]+')


def select_dialogue_messages(messages: list) -> list[ChatMessage]:
    return [msg for msg in messages if getattr(msg, "role", "") in {"user", "assistant"} and getattr(msg, "content", "").strip()]


def clean_message_content(content: str) -> str:
    text = (content or "").strip()
    return text.replace("[Attached Files:", "\n[Attached Files:").replace("[Attached Image:", "\n[Attached Image:").strip()


def build_chat_history_text(messages: list[ChatMessage]) -> str:
    filtered = select_dialogue_messages(messages)
    return "\n".join(
        f"[{msg.created_at.strftime('%m-%d %H:%M')}] {msg.role}: {clean_message_content(msg.content)}"
        for msg in filtered
    )


async def build_memory_context_text(store: MemoryStore, user_id: int, module: str, per_type_limits: dict[str, int] | None = None) -> str:
    default_limits = {
        MEMORY_TYPE_PREFERENCE: 2,
        MEMORY_TYPE_GOAL: 2,
        MEMORY_TYPE_WEAKNESS: 2,
        MEMORY_TYPE_FACT: 2,
        MEMORY_TYPE_BACKGROUND: 2,
    }
    if per_type_limits:
        default_limits.update(per_type_limits)
    memories_by_type = await store.get_user_context_memories(user_id=user_id, module=module, per_type_limits=default_limits)
    lines: list[str] = []
    for memory_type, items in memories_by_type.items():
        if not items:
            continue
        lines.append(f"- {memory_type}: {'；'.join(item.content for item in items)}")
    return "\n".join(lines) if lines else "暂无已有长期记忆。"


def build_profile_text_from_model(profile: UserProfile | None) -> str:  # 从画像模型构建文本表示
    if not profile:
        return "暂无原有画像（新用户）"
    profile_dict = profile.model_dump(exclude_unset=True, exclude={"user_id", "updated_at", "created_at", "id"})
    if not profile_dict:
        return "暂无原有画像（新用户）"
    return "\n".join(f"- {k}: {v}" for k, v in profile_dict.items() if v) or "暂无原有画像（新用户）"


def normalize_signal_text(text: str) -> str:  # 标准化信号文本（去除标点、压缩空格）
    return _MEMORY_SIGNAL_PUNCT_RE.sub(" ", normalize_text(text)).strip()


def is_memory_worthy_text(text: str) -> bool:  # 判断文本是否值得记忆（非纯提问且有稳定信号）
    normalized = normalize_signal_text(text)
    if not normalized:
        return False
    has_question_shape = any(marker in normalized for marker in MEMORY_QUESTION_MARKERS)
    has_question_mark = "?" in text or "？" in text
    if (has_question_shape or has_question_mark) and not any(pattern.search(normalized) for pattern in MEMORY_STABLE_SIGNAL_PATTERNS):
        return False
    return any(pattern.search(normalized) for pattern in MEMORY_STABLE_SIGNAL_PATTERNS)


def has_extractable_signal(texts: list[str]) -> bool:  # 检查文本列表是否有可提取信号
    cleaned_texts = [normalize_signal_text(text) for text in texts]
    ignore = {normalize_signal_text(text) for text in MEMORY_NON_SIGNIFICANT_TEXTS}
    cleaned_texts = [text for text in cleaned_texts if text and text not in ignore]
    return any(is_memory_worthy_text(text) for text in cleaned_texts)


def should_update_profile(current_profile: dict | None, extracted_features: dict) -> bool:  # 判断是否需要更新画像
    if not extracted_features.get("should_update", True):
        return False
    features = {k: v for k, v in extracted_features.items() if k != "should_update" and v is not None}
    if not features:
        return False
    if not current_profile:
        return True
    return any(current_profile.get(key) != value for key, value in features.items())


class ProfileExtraction(BaseModel):  # 画像提取结果：8个维度及其评分
    model_config = ConfigDict(extra="forbid")

    should_update: bool = Field(default=False)  # 是否需要更新
    knowledge_level: str | None = None  # 知识基础
    knowledge_level_score: Score | None = None  # 知识基础评分
    cognitive_style: str | None = None  # 认知风格
    cognitive_style_score: Score | None = None  # 认知风格评分
    error_pattern: str | None = None  # 易错点偏好
    error_pattern_score: Score | None = None  # 易错点评分
    learning_goal: str | None = None  # 学习目标
    learning_goal_score: Score | None = None  # 学习目标评分
    learning_history: str | None = None  # 学习历史
    learning_history_score: Score | None = None  # 学习历史评分
    interest_preference: str | None = None  # 兴趣偏好
    interest_preference_score: Score | None = None  # 兴趣偏好评分
    learning_pace: str | None = None  # 学习节奏
    learning_pace_score: Score | None = None  # 学习节奏评分
    cognitive_level: str | None = None  # 认知水平
    cognitive_level_score: Score | None = None  # 认知水平评分
    profile_summary: str | None = None  # 画像摘要


class ProfileService:  # 画像持久化服务：管理用户画像的CRUD
    def __init__(self) -> None:
        self.engine = engine

    async def get_user_profile(self, user_id: int) -> UserProfile | None:  # 获取用户画像
        async with AsyncSession(self.engine) as session:
            return await session.get(UserProfile, user_id)

    async def update_user_profile(  # 更新用户画像（创建历史版本）
        self,
        user_id: int,
        features: dict,
        change_reason: str = "系统自动更新",
        source_memory_ids: list[int] | None = None,
    ) -> UserProfile:
        import json

        async with AsyncSession(self.engine) as session:
            async with session.begin():
                profile = await session.get(UserProfile, user_id)
                if not profile:
                    profile = UserProfile(user_id=user_id)
                for field, value in features.items():
                    if hasattr(profile, field):
                        setattr(profile, field, value)
                session.add(profile)
                await session.flush()
                latest_version = (
                    await session.exec(select(func.max(UserProfileHistory.version)).where(UserProfileHistory.user_id == user_id))
                ).one()
                history = UserProfileHistory(
                    user_id=user_id,
                    version=0 if latest_version is None else int(latest_version) + 1,
                    knowledge_level=profile.knowledge_level,
                    knowledge_level_score=profile.knowledge_level_score,
                    learning_goal=profile.learning_goal,
                    learning_goal_score=profile.learning_goal_score,
                    learning_history=profile.learning_history,
                    learning_history_score=profile.learning_history_score,
                    cognitive_style=profile.cognitive_style,
                    cognitive_style_score=profile.cognitive_style_score,
                    error_pattern=profile.error_pattern,
                    error_pattern_score=profile.error_pattern_score,
                    learning_pace=profile.learning_pace,
                    learning_pace_score=profile.learning_pace_score,
                    interest_preference=profile.interest_preference,
                    interest_preference_score=profile.interest_preference_score,
                    cognitive_level=profile.cognitive_level,
                    cognitive_level_score=profile.cognitive_level_score,
                    profile_summary=profile.profile_summary,
                    change_reason=change_reason,
                    source_memory_ids=json.dumps(source_memory_ids) if source_memory_ids else None,
                )
                session.add(history)
            await session.refresh(profile)
            return profile

    async def get_profile_history(self, user_id: int, limit: int = 20) -> list[UserProfileHistory]:  # 获取画像历史版本
        async with AsyncSession(self.engine) as session:
            stmt = (
                select(UserProfileHistory)
                .where(UserProfileHistory.user_id == user_id)
                .order_by(UserProfileHistory.created_at.desc())
                .limit(limit)
            )
            return list((await session.exec(stmt)).all())


class ProfileBuildingService:  # 画像构建服务：从对话中提取并合并用户画像
    def __init__(self, *, module_name: str = "mentor", store: MemoryStore | None = None, profile_service: ProfileService | None = None) -> None:
        self.module_name = module_name
        self.store = store or MemoryStore()
        self.profile_service = profile_service or ProfileService()
        self.llm = get_deepseek_llm(temperature=0.1, streaming=False)  # 使用DeepSeek模型
        self.output_parser = PydanticOutputParser(pydantic_object=ProfileExtraction)
        self.prompt_template = ChatPromptTemplate.from_messages([("human", "{prompt_text}")])

    async def build_profile(self, user_id: int, session_id: str | None = None) -> tuple[bool, bool]:  # 构建用户画像，返回(成功, 是否更新)
        effective_session = session_id
        if effective_session is None:  # 无指定会话时获取最近会话
            sessions = await self.store.get_user_chat_sessions(user_id=user_id, module=self.module_name, limit=1)
            effective_session = sessions[0].id if sessions else f"user-{user_id}-default-mentor"

        recent_msgs = await self.store.get_recent_messages(  # 获取最近20条消息
            user_id=user_id,
            session_id=effective_session,
            module=self.module_name,
            limit=20,
        )
        if not recent_msgs:
            return True, False
        dialogue_msgs = select_dialogue_messages(recent_msgs)
        if not dialogue_msgs:
            return True, False

        chat_history = build_chat_history_text(dialogue_msgs)  # 构建对话历史
        memory_context = await build_memory_context_text(self.store, user_id, self.module_name)  # 构建记忆上下文
        current_profile = await self.profile_service.get_user_profile(user_id)  # 获取当前画像
        current_profile_str = build_profile_text_from_model(current_profile)  # 转换为文本

        try:
            prompt_text = PROFILE_BUILDING_PROMPT.format(  # 组装提示词
                current_profile=current_profile_str,
                memory_context=memory_context,
                chat_history=chat_history,
                format_instructions=self.output_parser.get_format_instructions(),
            )
            response = await self.llm.ainvoke(self.prompt_template.format_messages(prompt_text=prompt_text))  # 调用LLM
            updated_data = self.output_parser.parse(response.content if isinstance(response.content, str) else str(response.content))  # 解析结果
        except Exception as exc:
            logger.error("[ProfileBuilding] 画像提取与合并失败: %s", str(exc))
            return False, False

        current_dict = current_profile.model_dump(exclude_unset=True) if current_profile else None
        if not should_update_profile(current_dict, updated_data.model_dump()):  # 检查是否需要更新
            return True, False

        final_features = updated_data.model_dump(exclude_none=True)  # 过滤空值
        final_features.pop("should_update", None)  # 移除控制字段
        if not final_features:
            return True, False

        try:
            await self.profile_service.update_user_profile(  # 保存更新后的画像
                user_id=user_id,
                features=final_features,
                change_reason=f"基于最近{len(dialogue_msgs)}条有效对话的显著特征增量合并",
            )
            return True, True
        except Exception as exc:
            logger.error("[ProfileBuilding] 保存更新后的画像失败 (user_id=%s): %s", user_id, str(exc))
            return False, False
