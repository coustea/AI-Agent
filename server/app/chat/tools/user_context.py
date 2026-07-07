"""用户上下文工具 — 学习者画像 + 长期记忆读取。"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Literal

from pydantic import BaseModel, Field

from app.chat.memory.service import get_chat_memory_service
from app.chat.utils import compact_text
from app.chat.memory.types import LTM_CATEGORIES
from app.chat.schemas import TutorRequestContext
from app.infra.logging import get_logger
from app.infra.tool_excute import Tool
from app.profile.service import get_profile_service

logger = get_logger(__name__)


# ── 学习者画像 ──


class GetLearnerProfileArgs(BaseModel):
    dimension: str | None = Field(default=None, description="Profile dimension to read, such as goals or preferences.")
    reason: str = Field(default="", description="Why the tutor needs the profile.")


def make_get_learner_profile(
    request: TutorRequestContext,
    profile_service: Any | None = None,
) -> Callable[..., Awaitable[str]]:
    """工厂函数：创建闭包绑定当前请求的画像查询工具。"""

    async def _impl(
        dimension: str | None = None,
        reason: str = "",
    ) -> str:
        svc = profile_service or get_profile_service()
        try:
            markdown = await svc.build_profile_markdown(user_id=request.user_id)
            return compact_text(f"画像读取原因: {reason or '未提供'}\n{markdown}")
        except Exception as exc:
            logger.warning("[get_learner_profile] failed: %s", exc)
            return "暂时无法读取学习者画像。"

    return _impl


# ── 长期记忆 ──

LongTermMemoryCategory = Literal[
    "learning_background",
    "long_term_goals",
    "learning_preferences",
    "stable_weaknesses",
    "interaction_rules",
    "effective_strategies",
    "corrections",
]


class GetLongTermMemoryArgs(BaseModel):
    """长期记忆查询工具的输入参数模型。"""
    category: LongTermMemoryCategory | None = Field(default=None, description="Canonical long-term-memory category.")
    reason: str = Field(default="", description="Why the tutor needs durable memory.")


LONG_TERM_MEMORY_CATEGORY_ALIASES: dict[str, str] = {
    "goals_progress": "long_term_goals",
}


def make_get_long_term_memory(
    request: TutorRequestContext,
    memory_service: Any | None = None,
) -> Callable[..., Awaitable[str]]:
    """工厂函数：创建闭包绑定当前请求的长期记忆查询工具。"""

    async def _impl(
        category: LongTermMemoryCategory | None = None,
        reason: str = "",
    ) -> str:
        svc = memory_service or get_chat_memory_service()
        category_value = str(category or "").strip() or None
        if category_value and category_value not in LTM_CATEGORIES:
            return f"长期记忆分类无效: {category_value}"
        try:
            markdown = await svc.get_memory_markdown(request.user_id, category=category_value)
            return compact_text(f"长期记忆读取原因: {reason or '未提供'}\n{markdown}")
        except Exception as exc:
            logger.warning("[get_long_term_memory] failed: %s", exc)
            return "暂时无法读取长期学习记忆。"

    return _impl


def as_tool(request: TutorRequestContext) -> list[Tool]:
    """返回画像和长期记忆工具的 Tool 对象列表。"""
    return [
        Tool(
            "get_learner_profile",
            "Read learner profile when personalization, goals, preferences, or background matter.",
            GetLearnerProfileArgs,
            make_get_learner_profile(request),
        ),
        Tool(
            "get_long_term_memory",
            "Read durable learning memory for previous goals, preferences, weaknesses, strategies, or corrections.",
            GetLongTermMemoryArgs,
            make_get_long_term_memory(request),
        ),
    ]
