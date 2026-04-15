"""
MemoryService — 兼容外观层。

原 MemoryService 已拆分为独立的领域服务：
  - app.domain.session.session_service     → 会话管理 + token 累计
  - app.domain.memory.short_term            → 短期记忆 (ChatMessage CRUD)
  - app.domain.memory.long_term             → 长期记忆 (UserMemory 读写/去重)
  - app.domain.memory.compression           → 短期→长期压缩
  - app.domain.profile.profile_service      → 用户画像 + 历史版本
  - app.domain.memory.helpers               → normalize_text 等共享工具

此类保持向后兼容，所有方法委托给对应领域服务。
新代码应直接导入领域服务。
"""

from __future__ import annotations

from typing import List, Optional, Iterable

from app.core.logging import get_logger
from app.models.chat import ChatMessage, ChatSession
from app.models.memory import UserMemory
from app.models.profile import UserProfile, UserProfileHistory

# 领域服务导入
from app.domain.session.session_service import session_service
from app.domain.memory.short_term import short_term_service
from app.domain.memory.long_term import long_term_service
from app.domain.memory.compression import compression_service
from app.domain.profile.profile_service import profile_service
from app.domain.memory.helpers import normalize_text, estimate_token_count

logger = get_logger(__name__)

# 常量重导出（保持旧代码兼容）
SHORT_TERM_MESSAGE_EXPIRE_DAYS = 7
MEMORY_EXTRACTION_TOKEN_THRESHOLD = 80
PROFILE_UPDATE_TOKEN_THRESHOLD = 120


class MemoryService:
    """
    兼容外观：委托给拆分后的领域服务。
    新代码请直接使用领域服务，不再经过此类。
    """

    def __init__(self):
        pass  # 引擎由各领域服务自行持有

    # -- helpers --
    @staticmethod
    def _normalize_text(content: str) -> str:
        return normalize_text(content)

    def estimate_token_count(self, text: str) -> int:
        return estimate_token_count(text)

    # -- 会话管理 (委托 session_service) --
    async def create_chat_session(self, user_id: int, module: str, title: str = "新对话") -> ChatSession:
        return await session_service.create_chat_session(user_id, module, title)

    async def get_chat_session(self, session_id: str) -> Optional[ChatSession]:
        return await session_service.get_chat_session(session_id)

    async def get_user_chat_sessions(self, user_id: int, module: Optional[str] = None, limit: int = 20) -> List[ChatSession]:
        return await session_service.get_user_chat_sessions(user_id, module, limit)

    async def archive_chat_session(self, session_id: str, user_id: int) -> bool:
        return await session_service.archive_chat_session(session_id, user_id)

    # -- 短期记忆 (委托 short_term_service) --
    async def save_message(
        self, user_id: int, session_id: str, module: str, role: str, content: str,
        attachments: str | None = None, tool_calls: str | None = None,
        resource_cards: str | None = None,
    ) -> int:
        return await short_term_service.save_message(
            user_id, session_id, module, role, content, attachments, tool_calls, resource_cards,
        )

    async def get_recent_messages(
        self, user_id: int, session_id: str, module: str, limit: int | None = None,
        days: int = SHORT_TERM_MESSAGE_EXPIRE_DAYS, only_unexpired: bool = True,
    ) -> list[ChatMessage]:
        return await short_term_service.get_recent_messages(
            user_id, session_id, module, limit, days, only_unexpired,
        )

    async def get_message_count(self, user_id: int, session_id: str, module: str) -> int:
        return await short_term_service.get_message_count(user_id, session_id, module)

    async def delete_old_messages(self, user_id: int, session_id: str, module: str, keep_recent: int = 10) -> int:
        return await short_term_service.delete_old_messages(user_id, session_id, module, keep_recent)

    async def cleanup_expired_short_term_messages(
        self, user_id: int, session_id: str, module: str, days: int = SHORT_TERM_MESSAGE_EXPIRE_DAYS,
    ) -> int:
        return await short_term_service.cleanup_expired_short_term_messages(user_id, session_id, module, days)

    async def should_summarize(self, user_id: int, session_id: str, module: str, threshold: int = 20) -> bool:
        return await short_term_service.should_summarize(user_id, session_id, module, threshold)

    # -- 长期记忆 (委托 long_term_service) --
    async def get_long_term_memories(
        self, user_id: int, module: str | None = None, limit: int = 10, only_unexpired: bool = True,
    ) -> list[UserMemory]:
        return await long_term_service.get_long_term_memories(user_id, module, limit, only_unexpired)

    async def save_user_fact(
        self, user_id: int, content: str, memory_type: str,
        session_id: Optional[str] = None, expires_at=None,
    ) -> UserMemory:
        return await long_term_service.save_user_fact(user_id, content, memory_type, session_id, expires_at)

    async def get_user_facts(self, user_id: int, limit: int = 50) -> List[UserMemory]:
        return await long_term_service.get_user_facts(user_id, limit)

    async def get_user_context_memories(
        self, user_id: int, memory_types: Iterable[str] | None = None,
        per_type_limits: dict[str, int] | None = None, only_unexpired: bool = True,
    ) -> dict[str, list[UserMemory]]:
        return await long_term_service.get_user_context_memories(
            user_id, memory_types, per_type_limits, only_unexpired,
        )

    async def save_long_term_memory(
        self, user_id: int, session_id: str, content: str, memory_type: str,
        dimension: str | None = None, importance: float = 0.5,
        source: str = "conversation", source_message_count: int = 0,
    ) -> UserMemory:
        return await long_term_service.save_long_term_memory(
            user_id, session_id, content, memory_type, dimension, importance, source, source_message_count,
        )

    # -- 压缩 (委托 compression_service) --
    async def summarize_and_compress(
        self, user_id: int, session_id: str, module: str, threshold: int = 30, keep_recent: int = 10,
    ) -> None:
        await compression_service.summarize_and_compress(user_id, session_id, module, threshold, keep_recent)

    # -- 画像 (委托 profile_service) --
    async def get_user_profile(self, user_id: int) -> UserProfile | None:
        return await profile_service.get_user_profile(user_id)

    async def update_user_profile(
        self, user_id: int, features: dict, change_reason: str = "系统自动更新",
        source_memory_ids: list[int] | None = None,
    ) -> UserProfile:
        return await profile_service.update_user_profile(user_id, features, change_reason, source_memory_ids)

    async def get_profile_history(self, user_id: int, limit: int = 20) -> list[UserProfileHistory]:
        return await profile_service.get_profile_history(user_id, limit)

    # -- token 计数 (委托 session_service) --
    async def accumulate_session_tokens(
        self, user_id: int, session_id: str, module: str, content: str,
    ) -> tuple[int, int]:
        return await session_service.accumulate_session_tokens(user_id, session_id, module, content)

    async def get_session_token_counters(self, user_id: int, session_id: str, module: str) -> tuple[int, int]:
        return await session_service.get_session_token_counters(user_id, session_id, module)

    async def should_trigger_memory_extraction(
        self, user_id: int, session_id: str, module: str, threshold: int = MEMORY_EXTRACTION_TOKEN_THRESHOLD,
    ) -> bool:
        return await session_service.should_trigger_memory_extraction(user_id, session_id, module, threshold)

    async def should_trigger_profile_update_by_tokens(
        self, user_id: int, session_id: str, module: str, threshold: int = PROFILE_UPDATE_TOKEN_THRESHOLD,
    ) -> bool:
        return await session_service.should_trigger_profile_update_by_tokens(user_id, session_id, module, threshold)

    async def reset_memory_extraction_counter(self, user_id: int, session_id: str, module: str) -> None:
        await session_service.reset_memory_extraction_counter(user_id, session_id, module)

    async def reset_profile_update_counter(self, user_id: int, session_id: str, module: str) -> None:
        await session_service.reset_profile_update_counter(user_id, session_id, module)


# 初始化实例 — 保持旧代码兼容
memory_service = MemoryService()
