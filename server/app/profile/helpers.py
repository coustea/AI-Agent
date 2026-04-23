"""Profile 模块共享工具函数。

提供对话筛选、上下文构建等共享逻辑，供 FactExtractionService 和 ProfileBuildingService 使用。
"""

from __future__ import annotations

from datetime import datetime

from app.infra.models import ChatMessage, UserProfile
from app.memory.long_term import long_term_service
from app.memory.memory_types import (
    MEMORY_TYPE_BACKGROUND,
    MEMORY_TYPE_FACT,
    MEMORY_TYPE_GOAL,
    MEMORY_TYPE_PREFERENCE,
    MEMORY_TYPE_WEAKNESS,
)
from app.profile.service import profile_service


# ---------------------------------------------------------------------------
# 对话消息筛选
# ---------------------------------------------------------------------------

def select_dialogue_messages(messages: list) -> list[ChatMessage]:
    """筛选有效的对话消息，只保留 user 和 assistant 角色。"""
    return [
        msg
        for msg in messages
        if getattr(msg, "role", "") in {"user", "assistant"}
        and getattr(msg, "content", "").strip()
    ]


def clean_message_content(content: str) -> str:
    """清理消息内容，处理附件标记。"""
    text = (content or "").strip()
    return (
        text.replace("[Attached Files:", "\n[Attached Files:")
        .replace("[Attached Image:", "\n[Attached Image:")
        .strip()
    )


# ---------------------------------------------------------------------------
# 上下文构建
# ---------------------------------------------------------------------------

def build_chat_history_text(messages: list[ChatMessage]) -> str:
    """构建对话历史文本，用于 LLM 提示。"""
    filtered = select_dialogue_messages(messages)
    return "\n".join(
        f"[{msg.created_at.strftime('%m-%d %H:%M')}] {msg.role}: {clean_message_content(msg.content)}"
        for msg in filtered
    )


async def build_memory_context_text(
    user_id: int,
    module: str,
    per_type_limits: dict[str, int] | None = None,
) -> str:
    """构建长期记忆上下文文本。

    Args:
        user_id: 用户 ID
        module: 模块名称（mentor / avatar）
        per_type_limits: 各类型记忆数量限制

    Returns:
        格式化的记忆上下文文本
    """
    default_limits = {
        MEMORY_TYPE_PREFERENCE: 2,
        MEMORY_TYPE_GOAL: 2,
        MEMORY_TYPE_WEAKNESS: 2,
        MEMORY_TYPE_FACT: 2,
        MEMORY_TYPE_BACKGROUND: 2,
    }
    if per_type_limits:
        default_limits.update(per_type_limits)

    memories_by_type = await long_term_service.get_user_context_memories(
        user_id=user_id,
        module=module,
        per_type_limits=default_limits,
    )

    lines: list[str] = []
    for memory_type, items in memories_by_type.items():
        if not items:
            continue
        joined = "；".join(item.content for item in items)
        lines.append(f"- {memory_type}: {joined}")

    return "\n".join(lines) if lines else "暂无已有长期记忆。"


async def build_profile_context_text(user_id: int) -> str:
    """构建用户画像上下文文本。

    Args:
        user_id: 用户 ID

    Returns:
        格式化的画像上下文文本
    """
    profile = await profile_service.get_user_profile(user_id)
    if not profile:
        return "暂无用户画像。"

    profile_dict = profile.model_dump(
        exclude_unset=True,
        exclude={"user_id", "updated_at", "created_at", "id"},
    )
    if not profile_dict:
        return "暂无用户画像。"

    profile_lines = [f"- {key}: {value}" for key, value in profile_dict.items() if value]
    return "\n".join(profile_lines) if profile_lines else "暂无用户画像。"


def build_profile_text_from_model(profile: UserProfile | None) -> str:
    """从 UserProfile 模型构建画像文本（同步版本）。

    用于已有 profile 对象的场景，避免重复查询数据库。
    """
    if not profile:
        return "暂无原有画像（新用户）"

    profile_dict = profile.model_dump(
        exclude_unset=True,
        exclude={"user_id", "updated_at", "created_at", "id"},
    )
    if not profile_dict:
        return "暂无原有画像（新用户）"

    profile_lines = [f"- {k}: {v}" for k, v in profile_dict.items() if v]
    return "\n".join(profile_lines) if profile_lines else "暂无原有画像（新用户）"
