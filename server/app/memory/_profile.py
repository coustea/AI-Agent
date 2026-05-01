"""Profile persistence and profile-building logic.  # 用户画像持久化与构建逻辑

模块职责：
- 管理用户画像的 CRUD 操作
- 从对话中提取并生成 Markdown 用户画像
- 维护画像历史版本用于审计与回溯
- 提供辅助函数用于信号检测和上下文构建

核心类：
- ProfileService: 画像持久化服务，管理 UserProfile 表
- ProfileBuildingService: 画像构建服务，从对话中生成 Markdown 画像

设计原则：
- 用户画像主体只保存 Markdown
- 不要求大模型输出 JSON
- Markdown 使用固定结构，便于前端按 ## 切分
- 每次更新创建历史版本，支持审计与回溯

调用链：
chat/agent.py → MemoryLayer.post_turn_pipeline() → ProfileBuildingService.build_profile()
"""

from __future__ import annotations

import re
from typing import Final

from langchain_core.prompts import ChatPromptTemplate
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import PROFILE_GATE_EVERY_N_ASSISTANT_TURNS
from app.infra.database import engine
from app.infra.llm import get_llm_manager
from app.infra.logging import get_logger
from app.infra.models import ChatMessage, UserProfile, UserProfileHistory
from app.memory.memory_types import (
    MEMORY_TYPE_BACKGROUND,
    MEMORY_TYPE_CONSTRAINT,
    MEMORY_TYPE_CORRECTION,
    MEMORY_TYPE_FACT,
    MEMORY_TYPE_GOAL,
    MEMORY_TYPE_INTERACTION,
    MEMORY_TYPE_PREFERENCE,
    MEMORY_TYPE_STRATEGY,
    MEMORY_TYPE_SUMMARY,
    MEMORY_TYPE_WEAKNESS,
)
from app.memory._store import MemoryStore, normalize_text

logger = get_logger(__name__)

# 画像构建提示词：让大模型直接输出 Markdown
PROFILE_BUILDING_PROMPT = """# 角色与目标
你是学生画像构建器。请根据【旧画像】、【最近聊天记录】、【长期记忆】和【学习行为】生成一份完整的 Markdown 学生画像。
这是一个“对话式学习画像自主构建”流程：不要要求学生填写传统繁琐表单，而是从自然语言对话中结合学生的专业、学习目标、学习历史、知识基础、认知风格、易错点、偏好和纠正记录自动更新动态画像，并支持画像随学随新。

# 输出要求（严格遵守）
1. 直接输出 Markdown 内容，不要有任何前言、解释、说明或后记。
2. 不要输出 JSON，不要包裹在代码块中，不要添加 ```markdown 标记。
3. 开头直接是 `# 学生画像`，结尾直接结束，不要有多余文字。
4. 不要编造用户没有表达过的信息。
5. 如果某一项信息不足，请写"暂无明显信息"，不要强行推断。
6. 必须至少包含下方固定结构中的全部维度；优先保留用户明确纠正过的内容。

# 固定结构（必须按此顺序输出）

# 学生画像

## 基础信息与专业背景

## 学习目标

## 学习历史

## 知识基础

## 认知风格

## 学习偏好

## 易错点与薄弱点

## 交互偏好与禁忌

## AI 纠正记录

## 当前学习状态

## 推荐辅导策略

## 最近变化

## 不确定信息

【旧画像】
{current_profile}

【长期记忆】
{memory_context}

【最近聊天记录】
{chat_history}

【学习行为】
{learning_event_context}
"""

# 无意义短语集合：这些文本不应触发记忆提取
MEMORY_NON_SIGNIFICANT_TEXTS: Final[frozenset[str]] = frozenset({
    "谢谢", "好的", "收到", "明白了", "继续", "再来一道题", "ok", "OK"
})

# 问题标记词：出现这些词可能是纯提问，不一定是稳定信号
MEMORY_QUESTION_MARKERS: Final[tuple[str, ...]] = (
    "什么是", "什么叫", "怎么", "如何", "为什么",
    "请解释", "解释一下", "讲讲", "介绍一下", "请问",
    "我想问", "能不能", "可不可以",
)

# 稳定信号正则模式：匹配这些模式表示用户有稳定可复用的特征
MEMORY_STABLE_SIGNAL_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"我(?:总是|经常|一直|老是|反复).*(?:出错|不会|卡住|卡在|记不住|搞不清|混淆|薄弱|边界)"),
    re.compile(r"我(?:喜欢|不喜欢|更喜欢|偏好|习惯)"),
    re.compile(r"我(?:在学|正在学|学过|以前学过|已经学过|准备|打算|想(?:学|考|准备|提高|练习))"),
    re.compile(r"我(?:下周|本学期|这学期|最近|目前|现在).*(?:学|补|复习|准备|做题|刷题|作业|实验|项目|考试)"),
    re.compile(r"(?:专业|年级|方向|课程|考试|证书|竞赛|实习|面试|项目|课设|论文)"),
    re.compile(r"(?:你|ai|AI|助手).*(?:错了|理解错|误解|不对|遗漏|漏了|应该|不要|别|先问|记住|以后)"),
    re.compile(r"(?:以后|下次|后续).*(?:不要|别|先|必须|应该|保持|沿用|避免)"),
)
_MEMORY_SIGNAL_PUNCT_RE: Final[re.Pattern[str]] = re.compile(r'[。！？!?；;，,、：:…""\'\'`（）()\[\]{}<>《》\s]+')


def select_dialogue_messages(messages: list) -> list[ChatMessage]:
    """筛选对话消息。  # 只保留 user/assistant 角色且有内容的消息

    参数：
    - messages: 原始消息列表

    返回：
    - 过滤后的对话消息列表
    """
    return [msg for msg in messages if getattr(msg, "role", "") in {"user", "assistant"} and getattr(msg, "content", "").strip()]


def clean_message_content(content: str) -> str:
    """清理消息内容。  # 处理附件标记，确保格式整洁

    参数：
    - content: 原始消息内容

    返回：
    - 清理后的内容
    """
    text = (content or "").strip()
    return text.replace("[Attached Files:", "\n[Attached Files:").replace("[Attached Image:", "\n[Attached Image:").strip()


def build_chat_history_text(messages: list[ChatMessage]) -> str:
    """构建对话历史文本。  # 将消息列表格式化为可读的对话记录

    参数：
    - messages: 消息列表

    返回：
    - 格式化的对话历史文本
    """
    filtered = select_dialogue_messages(messages)
    return "\n".join(
        f"[{msg.created_at.strftime('%m-%d %H:%M')}] {msg.role}: {clean_message_content(msg.content)}"
        for msg in filtered
    )


async def build_memory_context_text(store: MemoryStore, user_id: int, module: str, per_type_limits: dict[str, int] | None = None) -> str:
    """构建记忆上下文文本。
    # 从长期记忆池提取各类型记忆并格式化

    参数：
    - store: 存储层实例
    - user_id: 用户ID
    - module: 模块名
    - per_type_limits: 每类记忆的上限，None 时使用默认值

    返回：
    - 格式化的记忆上下文文本
    """
    default_limits = {
        MEMORY_TYPE_CORRECTION: 2,
        MEMORY_TYPE_CONSTRAINT: 2,
        MEMORY_TYPE_INTERACTION: 2,
        MEMORY_TYPE_STRATEGY: 2,
        MEMORY_TYPE_PREFERENCE: 2,
        MEMORY_TYPE_GOAL: 2,
        MEMORY_TYPE_WEAKNESS: 2,
        MEMORY_TYPE_FACT: 2,
        MEMORY_TYPE_BACKGROUND: 2,
        MEMORY_TYPE_SUMMARY: 1,
    }
    if per_type_limits:
        default_limits.update(per_type_limits)
    memories_by_type = await store.get_user_context_memories(user_id=user_id, module=module, per_type_limits=default_limits)
    summary_by_type = await store.get_user_context_memories(
        user_id=user_id,
        module=module,
        memory_types=[MEMORY_TYPE_SUMMARY],
        per_type_limits={MEMORY_TYPE_SUMMARY: default_limits[MEMORY_TYPE_SUMMARY]},
        source=None,
    )
    memories_by_type.update(summary_by_type)
    lines: list[str] = []
    for memory_type, items in memories_by_type.items():
        if not items:
            continue
        lines.append(f"- {memory_type}: {'；'.join(item.content_markdown for item in items)}")
    return "\n".join(lines) if lines else "暂无已有长期记忆。"


def build_profile_text_from_model(profile: UserProfile | None) -> str:
    """从画像模型构建文本表示。  # 将 UserProfile 的 profile_markdown 直接返回

    参数：
    - profile: 用户画像模型实例

    返回：
    - 画像 Markdown 文本，无画像时返回默认提示
    """
    if not profile:
        return "暂无原有画像（新用户）"
    if not profile.profile_markdown or not profile.profile_markdown.strip():
        return "暂无原有画像（新用户）"
    return profile.profile_markdown


def normalize_signal_text(text: str) -> str:
    """标准化信号文本。  # 去除标点、压缩空格，用于信号匹配

    参数：
    - text: 原始文本

    返回：
    - 标准化后的文本
    """
    return _MEMORY_SIGNAL_PUNCT_RE.sub(" ", normalize_text(text)).strip()


def is_memory_worthy_text(text: str) -> bool:
    """判断文本是否值得记忆。
    # 非纯提问且有稳定信号才值得记忆

    参数：
    - text: 待判断的文本

    返回：
    - True: 值得记忆
    - False: 不值得记忆
    """
    normalized = normalize_signal_text(text)
    if not normalized:
        return False
    has_question_shape = any(marker in normalized for marker in MEMORY_QUESTION_MARKERS)
    has_question_mark = "?" in text or "？" in text
    if (has_question_shape or has_question_mark) and not any(pattern.search(normalized) for pattern in MEMORY_STABLE_SIGNAL_PATTERNS):
        return False
    return any(pattern.search(normalized) for pattern in MEMORY_STABLE_SIGNAL_PATTERNS)


def has_extractable_signal(texts: list[str]) -> bool:
    """检查文本列表是否有可提取信号。  # 用于门控判断是否需要调用 LLM

    参数：
    - texts: 文本列表

    返回：
    - True: 存在可提取信号
    - False: 无可提取信号
    """
    cleaned_texts = [normalize_signal_text(text) for text in texts]
    ignore = {normalize_signal_text(text) for text in MEMORY_NON_SIGNIFICANT_TEXTS}
    cleaned_texts = [text for text in cleaned_texts if text and text not in ignore]
    return any(is_memory_worthy_text(text) for text in cleaned_texts)


class ProfileService:
    """画像持久化服务。  # 管理 UserProfile 表的 CRUD 操作

    职责：
    - 读取用户画像
    - 更新用户画像（创建历史版本）
    - 查询画像历史

    设计原则：
    - 每次更新自动创建历史版本
    - 使用事务保证数据一致性
    """

    def __init__(self) -> None:
        """初始化画像服务。"""
        self.engine = engine

    async def get_user_profile(self, user_id: int) -> UserProfile | None:
        """获取用户画像。  # 按 user_id 读取当前画像

        参数：
        - user_id: 用户ID

        返回：
        - UserProfile 实例或 None
        """
        async with AsyncSession(self.engine) as session:
            return await session.get(UserProfile, user_id)

    async def update_user_profile(  # 更新用户画像（创建历史版本）
        self,
        user_id: int,
        profile_markdown: str,
        change_reason: str = "系统自动更新",
        source_session_ids: list[str] | None = None,
        source_memory_ids: list[int] | None = None,
        confidence: float = 0.7,
    ) -> UserProfile:
        """更新用户画像。  # 更新画像 Markdown 并创建历史版本

        参数：
        - user_id: 用户ID
        - profile_markdown: 画像 Markdown 内容
        - change_reason: 变更原因，用于审计
        - source_session_ids: 来源会话ID列表
        - source_memory_ids: 来源记忆ID列表
        - confidence: 画像置信度

        返回：
        - 更新后的 UserProfile 实例

        设计原则：
        - 使用事务保证画像更新和历史创建的原子性
        - 新用户自动创建画像记录
        - 历史版本号自动递增
        """
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                profile = await session.get(UserProfile, user_id)
                if not profile:
                    profile = UserProfile(
                        user_id=user_id,
                        profile_markdown=profile_markdown,
                        version=1,
                        confidence=confidence,
                        source_session_ids=source_session_ids,
                        source_memory_ids=source_memory_ids,
                        updated_reason=change_reason,
                    )
                else:
                    profile.profile_markdown = profile_markdown
                    profile.version = (profile.version or 1) + 1
                    profile.confidence = confidence
                    profile.source_session_ids = source_session_ids
                    profile.source_memory_ids = source_memory_ids
                    profile.updated_reason = change_reason
                session.add(profile)
                await session.flush()
                latest_version = (
                    await session.exec(select(func.max(UserProfileHistory.version)).where(UserProfileHistory.user_id == user_id))
                ).one()
                history = UserProfileHistory(
                    user_id=user_id,
                    version=0 if latest_version is None else int(latest_version) + 1,
                    profile_markdown=profile_markdown,
                    change_reason=change_reason,
                    source_session_ids=source_session_ids,
                    source_memory_ids=source_memory_ids,
                )
                session.add(history)
            await session.refresh(profile)
            return profile

    async def get_profile_history(self, user_id: int, limit: int = 20) -> list[UserProfileHistory]:
        """获取画像历史版本。  # 按时间倒序返回历史记录

        参数：
        - user_id: 用户ID
        - limit: 返回数量上限

        返回：
        - UserProfileHistory 列表
        """
        async with AsyncSession(self.engine) as session:
            stmt = (
                select(UserProfileHistory)
                .where(UserProfileHistory.user_id == user_id)
                .order_by(UserProfileHistory.created_at.desc())
                .limit(limit)
            )
            return list((await session.exec(stmt)).all())


class ProfileBuildingService:
    """画像构建服务。  # 从对话中生成 Markdown 用户画像

    职责：
    - 从最近对话中提取学习特征
    - 生成 Markdown 格式的用户画像
    - 判断是否需要更新，避免无意义写入

    调用入口：
    - build_profile(user_id, session_id) -> tuple[bool, bool]

    设计原则：
    - 使用 Spark X 模型做特征提取
    - 直接输出 Markdown，不要求 JSON
    - 门控检查：无变化时不写入数据库
    """

    def __init__(self, *, module_name: str = "mentor", store: MemoryStore | None = None, profile_service: ProfileService | None = None) -> None:
        """初始化画像构建服务。

        参数：
        - module_name: 模块名，参与存储分区
        - store: 存储层实例
        - profile_service: 画像持久化服务实例
        """
        self.module_name = module_name
        self.store = store or MemoryStore()
        self.profile_service = profile_service or ProfileService()
        self.llm_manager = get_llm_manager()
        self.model_kwargs = {"temperature": 0.1, "streaming": False}
        self.prompt_template = ChatPromptTemplate.from_messages([("human", "{prompt_text}")])

    async def build_profile(self, user_id: int, session_id: str | None = None) -> tuple[bool, bool]:
        """构建用户画像。  # 主入口：从对话中提取特征并生成 Markdown 画像

        参数：
        - user_id: 用户ID
        - session_id: 会话ID，None 时使用最近会话

        返回：
        - tuple[成功, 是否更新]：(True, True) 成功且有更新；(True, False) 成功但无更新；(False, *) 失败

        流程：
        1. 确定会话ID
        2. 获取最近 20 条消息
        3. 构建上下文（对话历史 + 长期记忆 + 当前画像）
        4. 调用 LLM 生成 Markdown 画像
        5. 判断是否需要更新
        6. 写入数据库并创建历史版本
        """
        effective_session = session_id
        if effective_session is None:  # 无指定会话时获取最近会话
            sessions = await self.store.get_user_chat_sessions(user_id=user_id, module=self.module_name, limit=1)
            effective_session = sessions[0].id if sessions else f"user-{user_id}-default-mentor"

        recent_msgs = await self.store.get_recent_messages(  # 获取最近 20 条消息
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

        # 学习行为上下文（当前简化处理）
        learning_event_context = "暂无学习行为数据。"

        try:
            prompt_text = PROFILE_BUILDING_PROMPT.format(  # 组装提示词
                current_profile=current_profile_str,
                memory_context=memory_context,
                chat_history=chat_history,
                learning_event_context=learning_event_context,
            )
            response = await self.llm_manager.ainvoke(  # 调用 LLM
                "spark_x",
                self.prompt_template.format_messages(prompt_text=prompt_text),
                model_kwargs=self.model_kwargs,
            )
            profile_markdown = response.content if isinstance(response.content, str) else str(response.content)
        except Exception as exc:
            logger.error("[ProfileBuilding] 画像生成失败: %s", str(exc))
            return False, False

        # 清理 Markdown 内容（去除可能的代码块包裹）
        profile_markdown = profile_markdown.strip()
        if profile_markdown.startswith("```markdown"):
            profile_markdown = profile_markdown[len("```markdown"):].strip()
        if profile_markdown.startswith("```"):
            profile_markdown = profile_markdown[3:].strip()
        if profile_markdown.endswith("```"):
            profile_markdown = profile_markdown[:-3].strip()

        # 检查是否为有效内容
        if not profile_markdown or not profile_markdown.strip():
            logger.warning("[ProfileBuilding] LLM 返回空内容，跳过更新")
            return True, False

        # 检查是否需要更新（与旧画像比较）
        if current_profile and current_profile.profile_markdown:
            if normalize_text(profile_markdown) == normalize_text(current_profile.profile_markdown):
                return True, False  # 内容相同，无需更新

        try:
            await self.profile_service.update_user_profile(  # 保存更新后的画像
                user_id=user_id,
                profile_markdown=profile_markdown,
                change_reason=f"基于最近{len(dialogue_msgs)}条有效对话生成画像",
                source_session_ids=[effective_session],
            )
            return True, True
        except Exception as exc:
            logger.error("[ProfileBuilding] 保存更新后的画像失败 (user_id=%s): %s", user_id, str(exc))
            return False, False
