"""Chat 领域工具定义与装配 —— 统一基于 app.shared.tools 的 @tool 注册。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.chat.memory.service import get_chat_memory_service
from app.chat.memory.types import LTM_CATEGORIES, compact_text
from app.config import user_chat_dir
from app.infra.logging import get_logger
from app.profile.service import get_profile_service
from app.rag.tools import build_knowledge_tool
from app.shared.cartoon.tool import build_cartoon_subagent_tool
from app.shared.ppt.tool import build_ppt_subagent_tool
from app.shared.tools import Tool, build_builtin_tools, tool

logger = get_logger(__name__)

LongTermMemoryCategory = Literal[
    "learning_background",
    "long_term_goals",
    "learning_preferences",
    "stable_weaknesses",
    "interaction_rules",
    "effective_strategies",
    "corrections",
]

LONG_TERM_MEMORY_CATEGORY_ALIASES: dict[str, str] = {
    "goals_progress": "long_term_goals",
}


class GetLearnerProfileArgs(BaseModel):
    """学习者画像查询工具参数。"""

    dimension: str | None = Field(
        default=None,
        description="Profile dimension to read, such as goals or preferences.",
    )
    reason: str = Field(
        default="",
        description="Why the tutor needs the profile.",
    )


class GetLongTermMemoryArgs(BaseModel):
    """长期记忆查询工具参数。"""

    category: LongTermMemoryCategory | str | None = Field(
        default=None,
        description="Canonical long-term-memory category.",
    )
    reason: str = Field(
        default="",
        description="Why the tutor needs durable memory.",
    )


def build_user_context_tools(
    user_id: int,
    *,
    profile_service: Any | None = None,
    memory_service: Any | None = None,
) -> list[Tool]:
    """构建绑定当前 user_id 的学习者画像与长期记忆工具。"""

    @tool(
        name="get_learner_profile",
        description="Read learner profile when personalization, goals, preferences, or background matter.",
        args_model=GetLearnerProfileArgs,
    )
    async def get_learner_profile(dimension: str | None = None, reason: str = "") -> str:
        svc = profile_service or get_profile_service()
        try:
            markdown = await svc.build_profile_markdown(user_id=user_id)
            return compact_text(f"画像读取原因: {reason or '未提供'}\n{markdown}")
        except Exception as exc:
            logger.warning("[get_learner_profile] 失败: %s", exc)
            return "暂时无法读取学习者画像。"

    @tool(
        name="get_long_term_memory",
        description="Read durable learning memory for previous goals, preferences, weaknesses, strategies, or corrections.",
        args_model=GetLongTermMemoryArgs,
    )
    async def get_long_term_memory(category: str | None = None, reason: str = "") -> str:
        svc = memory_service or get_chat_memory_service()
        raw_cat = str(category or "").strip()
        category_value = LONG_TERM_MEMORY_CATEGORY_ALIASES.get(raw_cat, raw_cat) or None
        if category_value and category_value not in LTM_CATEGORIES:
            return f"长期记忆分类无效: {category_value}"
        try:
            markdown = await svc.get_memory_markdown(user_id, category=category_value)
            return compact_text(f"长期记忆读取原因: {reason or '未提供'}\n{markdown}")
        except Exception as exc:
            logger.warning("[get_long_term_memory] 失败: %s", exc)
            return "暂时无法读取长期学习记忆。"

    return [get_learner_profile, get_long_term_memory]


def _default_workdir(username: str, session_id: str) -> Path:
    path = user_chat_dir(username, session_id) / "workspace"
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_tutor_tools(
    *,
    user_id: int,
    username: str,
    session_id: str,
    workdir: Path | None = None,
) -> list[Tool]:
    """装配本轮可用的完整工具集：内置工具 + 画像/记忆 + 知识库 + PPT/视频工具。"""
    effective_workdir = workdir or _default_workdir(username, session_id)
    return [
        *build_builtin_tools(effective_workdir),
        *build_user_context_tools(user_id),
        build_knowledge_tool(),
        build_ppt_subagent_tool(username=username, session_id=session_id),
        build_cartoon_subagent_tool(username=username, session_id=session_id),
    ]


__all__ = [
    "GetLearnerProfileArgs",
    "GetLongTermMemoryArgs",
    "LONG_TERM_MEMORY_CATEGORY_ALIASES",
    "LongTermMemoryCategory",
    "build_tutor_tools",
    "build_user_context_tools",
]
