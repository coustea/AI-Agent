"""画像构建服务。

合并更新用户画像（8维度），服务于整个项目。
"""

from __future__ import annotations

from typing import Any

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Annotated

from app.infra.logging import get_logger
from app.infra.llm import get_deepseek_llm
from app.memory.long_term import long_term_service
from app.memory.service import memory_service
from app.profile.helpers import (
    build_chat_history_text,
    build_memory_context_text,
    build_profile_text_from_model,
    select_dialogue_messages,
)
from app.profile.policy import should_update_profile
from app.profile.prompts import render_profile_building_prompt

logger = get_logger(__name__)

# 评分类型：0-100 的整数
Score = Annotated[int, Field(ge=0, le=100)]


# ---------------------------------------------------------------------------
# Pydantic 输出模型
# ---------------------------------------------------------------------------

class ProfileExtraction(BaseModel):
    """LLM 提取的画像字段。"""
    model_config = ConfigDict(extra="forbid")

    should_update: bool = Field(
        default=False,
        description="是否需要更新画像。仅当最近对话出现稳定可复用学习特征变化时为 true，否则为 false。",
    )
    knowledge_level: str | None = Field(default=None, description="知识基础: 当前专业、学情边界")
    knowledge_level_score: Score | None = Field(default=None, description="知识基础评分(0-100)")
    cognitive_style: str | None = Field(default=None, description="认知风格: 偏好视觉/案例/推导等")
    cognitive_style_score: Score | None = Field(default=None, description="认知风格评分(0-100)")
    error_pattern: str | None = Field(default=None, description="易错点偏好: 逻辑盲区、常犯错误")
    error_pattern_score: Score | None = Field(default=None, description="易错模式评分(0-100)")
    learning_goal: str | None = Field(default=None, description="学习目标: 考试/兴趣/职业等")
    learning_goal_score: Score | None = Field(default=None, description="学习目标评分(0-100)")
    learning_history: str | None = Field(default=None, description="学习历史: 过去经验、相关背景")
    learning_history_score: Score | None = Field(default=None, description="学习历史评分(0-100)")
    interest_preference: str | None = Field(default=None, description="兴趣偏好: 个人喜好、关注点")
    interest_preference_score: Score | None = Field(default=None, description="兴趣偏好评分(0-100)")
    learning_pace: str | None = Field(default=None, description="学习节奏: 频率、时长、突击/平稳")
    learning_pace_score: Score | None = Field(default=None, description="学习节奏评分(0-100)")
    cognitive_level: str | None = Field(default=None, description="认知水平: 深度思考、逻辑推演能力")
    cognitive_level_score: Score | None = Field(default=None, description="认知水平评分(0-100)")
    profile_summary: str | None = Field(default=None, description="画像总结: 用一句话概括整体学习状态")


# ---------------------------------------------------------------------------
# 服务类
# ---------------------------------------------------------------------------

class ProfileBuildingService:
    """画像构建服务。

    职责：
    - 从对话中提取稳定的学习特征
    - 合并更新用户画像（8维度）
    - 调用 LLM 进行结构化提取
    - 持久化到 UserProfile 表（带版本历史）

    服务对象：全局（所有模块）
    """

    def __init__(self, *, module_name: str = "mentor") -> None:
        self.module_name = module_name
        self.llm = get_deepseek_llm(temperature=0.1, streaming=False)
        self.long_term = long_term_service
        self.memory = memory_service  # 用于获取对话历史
        self.output_parser = PydanticOutputParser(pydantic_object=ProfileExtraction)
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("human", "{prompt_text}")
        ])

    async def build_profile(
        self,
        user_id: int,
        session_id: str | None = None,
    ) -> tuple[bool, bool]:
        """构建或更新用户画像。

        Args:
            user_id: 用户 ID
            session_id: 会话 ID（可选，不传则使用最近会话）

        Returns:
            (success, updated): 是否成功，是否有更新
        """
        # 确定会话
        effective_session = session_id
        if effective_session is None:
            sessions = await self.memory.get_user_chat_sessions(
                user_id=user_id,
                module=self.module_name,
                limit=1,
            )
            if sessions:
                effective_session = sessions[0].id
            else:
                effective_session = f"user-{user_id}-default-mentor"

        logger.info(
            "[ProfileBuilding] 开始为用户 %s 执行画像合并更新 (session=%s)...",
            user_id,
            effective_session,
        )

        # 1. 获取近期对话
        recent_msgs = await self.memory.get_recent_messages(
            user_id=user_id,
            session_id=effective_session,
            module=self.module_name,
            limit=20,
        )

        if not recent_msgs:
            logger.info("[ProfileBuilding] 用户 %s 暂无新对话，无需更新。", user_id)
            return True, False

        # 2. 筛选有效对话
        dialogue_msgs = select_dialogue_messages(recent_msgs)
        if not dialogue_msgs:
            logger.info("[ProfileBuilding] 用户 %s 暂无有效对话，无需更新。", user_id)
            return True, False

        logger.info(
            "[ProfileBuilding] 找到用户 %s 的 %d 条有效近期对话，准备提取特征。",
            user_id,
            len(dialogue_msgs),
        )

        # 3. 构建上下文
        chat_history = build_chat_history_text(dialogue_msgs)
        memory_context = await build_memory_context_text(user_id, self.module_name)

        # 获取当前画像
        current_profile = await self.memory.get_user_profile(user_id)
        current_profile_str = build_profile_text_from_model(current_profile)

        if current_profile:
            logger.info("[ProfileBuilding] 已加载用户 %s 的现有画像。", user_id)

        # 4. 调用 LLM 提取
        logger.info("[ProfileBuilding] 正在请求 LLM 进行画像合并提取 (user_id=%s)...", user_id)

        try:
            prompt_text = render_profile_building_prompt(
                current_profile=current_profile_str,
                memory_context=memory_context,
                chat_history=chat_history,
                format_instructions=self.output_parser.get_format_instructions(),
            )
            updated_data = await self._invoke_llm(prompt_text)
            logger.info("[ProfileBuilding] LLM 提取成功 (user_id=%s)", user_id)

        except Exception as e:
            logger.error("[ProfileBuilding] 画像提取与合并失败: %s", str(e))
            return False, False

        # 5. 判断是否需要更新
        current_dict = current_profile.model_dump(exclude_unset=True) if current_profile else None
        if not should_update_profile(current_dict, updated_data.model_dump()):
            logger.info("[ProfileBuilding] 用户 %s 判定无需更新画像。", user_id)
            return True, False

        # 6. 提取有效字段
        final_features = updated_data.model_dump(exclude_none=True)
        final_features.pop("should_update", None)

        if not final_features:
            logger.info("[ProfileBuilding] 用户 %s 画像无实质性更新。", user_id)
            return True, False

        # 7. 持久化
        try:
            await self.memory.update_user_profile(
                user_id=user_id,
                features=final_features,
                change_reason=f"基于最近{len(dialogue_msgs)}条有效对话的显著特征增量合并",
            )
            logger.info(
                "[ProfileBuilding] 用户 %s 画像合并更新完毕！更新字段: %s",
                user_id,
                list(final_features.keys()),
            )
            return True, True

        except Exception as e:
            logger.error("[ProfileBuilding] 保存更新后的画像失败 (user_id=%s): %s", user_id, str(e))
            return False, False

    # ---------------------------------------------------------------------------
    # 内部方法
    # ---------------------------------------------------------------------------

    async def _invoke_llm(self, prompt_text: str) -> ProfileExtraction:
        """调用 LLM 并解析结构化输出。"""
        messages = self.prompt_template.format_messages(prompt_text=prompt_text)
        response = await self.llm.ainvoke(messages)
        content = response.content if isinstance(response.content, str) else str(response.content)
        return self.output_parser.parse(content)
