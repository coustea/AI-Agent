"""记忆存储层 — 封装数据库 CRUD 操作。

模块职责：
- 会话管理：ChatSession CRUD
- 短期记忆：ChatMessage CRUD
- 会话概要：ChatSessionSummary CRUD
- 长期记忆：UserLongTermMemory CRUD（用户级单条）
- 用户画像：UserProfile CRUD

设计原则：
- 一个用户一个 module 下只有一条长期记忆
- 一个用户一个 module 下只有一条当前画像
- 会话概要不写入长期记忆
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.database import engine
from app.infra.llm import get_llm_manager
from app.infra.logging import get_logger
from app.infra.models import (
    ChatMessage,
    ChatSession,
    ChatSessionSummary,
    UserLongTermMemory,
    UserProfile,
    UserProfileHistory,
)
from app.memory.memory_types import (
    make_default_long_term_memory_json,
    make_default_profile_json,
    make_default_session_summary_json,
    render_long_term_memory_markdown,
    render_profile_markdown,
    render_session_summary_markdown,
)

logger = get_logger(__name__)
llm_manager = get_llm_manager()

SHORT_TERM_MESSAGE_EXPIRE_DAYS = 7
SESSION_SUMMARY_TOKEN_THRESHOLD = 150

_TERM_PATTERN = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]+", re.IGNORECASE)


class SessionTitleOutput(BaseModel):
    """会话标题结构化输出模型。"""
    title: str = Field(description="会话标题，不超过15个字")


def normalize_text(content: str) -> str:
    return " ".join((content or "").strip().lower().split())


def now() -> datetime:
    return datetime.now()


def message_expire_cutoff(days: int = SHORT_TERM_MESSAGE_EXPIRE_DAYS) -> datetime:
    return now() - timedelta(days=max(days, 0))


def estimate_token_count(text: str) -> int:
    stripped = (text or "").strip()
    if not stripped:
        return 0
    return max(max(1, len(stripped) // 4), len(stripped.split()))


def _strip_markdown_fence(content: str) -> str:
    text = (content or "").strip()
    if text.startswith("```markdown"):
        text = text[len("```markdown"):].strip()
    if text.startswith("```"):
        text = text[3:].strip()
    if text.endswith("```"):
        text = text[:-3].strip()
    return text


def _normalize_session_title(title: Any, fallback: str = "新对话") -> str:
    text = str(title or "").strip()
    if not text:
        return fallback
    return text[:15] if len(text) > 15 else text


class MemoryStore:
    """记忆存储核心类 — 封装所有数据库 CRUD 操作。"""

    def __init__(self) -> None:
        self.engine = engine

    # ------------------------------------------------------------------
    # 会话管理
    # ------------------------------------------------------------------

    async def create_chat_session(self, user_id: int, module: str, title: str = "新对话") -> ChatSession:
        async with AsyncSession(self.engine) as session:
            chat_session = ChatSession(user_id=user_id, module=module, title=title)
            session.add(chat_session)
            await session.commit()
            await session.refresh(chat_session)
            return chat_session

    async def get_chat_session(self, session_id: str) -> ChatSession | None:
        async with AsyncSession(self.engine) as session:
            stmt = select(ChatSession).where(ChatSession.id == session_id)
            return (await session.exec(stmt)).first()

    async def get_user_chat_sessions(self, user_id: int, module: str | None = None, limit: int = 20) -> list[ChatSession]:
        async with AsyncSession(self.engine) as session:
            stmt = select(ChatSession).where(ChatSession.user_id == user_id, ChatSession.is_archived == False)  # noqa: E712
            if module:
                stmt = stmt.where(ChatSession.module == module)
            stmt = stmt.order_by(ChatSession.updated_at.desc()).limit(limit)
            return list((await session.exec(stmt)).all())

    async def archive_chat_session(self, session_id: str, user_id: int) -> bool:
        async with AsyncSession(self.engine) as session:
            stmt = select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
            chat_session = (await session.exec(stmt)).first()
            if not chat_session:
                return False
            chat_session.is_archived = True
            session.add(chat_session)
            await session.commit()
            return True

    # ------------------------------------------------------------------
    # 短期记忆（消息）
    # ------------------------------------------------------------------

    async def save_message(
        self,
        user_id: int,
        session_id: str,
        module: str,
        role: str,
        content: str,
        attachments: str | None = None,
        tool_calls: str | None = None,
        diagram: dict | None = None,
    ) -> int:
        async with AsyncSession(self.engine) as session:
            session_stmt = select(ChatSession).where(ChatSession.id == session_id)
            chat_session = (await session.exec(session_stmt)).first()
            if chat_session:
                if chat_session.user_id != user_id or chat_session.module != module:
                    raise PermissionError("会话不属于当前用户或模块，禁止写入")
                chat_session.updated_at = now()
            else:
                chat_session = ChatSession(id=session_id, user_id=user_id, module=module, title="新对话")
            session.add(chat_session)
            session.add(
                ChatMessage(
                    user_id=user_id,
                    session_id=session_id,
                    module=module,
                    role=role,
                    content=content,
                    attachments=attachments,
                    tool_calls=tool_calls,
                    diagram=diagram,
                )
            )
            await session.commit()
        return await self.get_message_count(user_id, session_id, module)

    async def get_recent_messages(
        self,
        user_id: int,
        session_id: str,
        module: str,
        limit: int | None = None,
        days: int = SHORT_TERM_MESSAGE_EXPIRE_DAYS,
        only_unexpired: bool = True,
    ) -> list[ChatMessage]:
        async with AsyncSession(self.engine) as session:
            filters = [ChatMessage.user_id == user_id, ChatMessage.session_id == session_id, ChatMessage.module == module]
            if only_unexpired:
                filters.append(ChatMessage.created_at >= message_expire_cutoff(days))
            total = (await session.exec(select(func.count()).where(*filters))).one()
            stmt = select(ChatMessage).where(*filters).order_by(ChatMessage.created_at.asc())
            if limit is not None and limit > 0 and total > limit:
                stmt = stmt.offset(total - limit)
            return list((await session.exec(stmt)).all())

    async def get_message_count(self, user_id: int, session_id: str, module: str) -> int:
        async with AsyncSession(self.engine) as session:
            stmt = select(func.count()).where(
                ChatMessage.user_id == user_id,
                ChatMessage.session_id == session_id,
                ChatMessage.module == module,
            )
            return (await session.exec(stmt)).one()

    async def get_message_token_count(self, user_id: int, session_id: str, module: str) -> int:
        messages = await self.get_recent_messages(user_id, session_id, module, None)
        return sum(estimate_token_count(getattr(msg, "content", "")) for msg in messages)

    async def delete_old_messages(self, user_id: int, session_id: str, module: str, keep_recent: int = 10) -> int:
        async with AsyncSession(self.engine) as session:
            total = (
                await session.exec(
                    select(func.count()).where(
                        ChatMessage.user_id == user_id,
                        ChatMessage.session_id == session_id,
                        ChatMessage.module == module,
                    )
                )
            ).one()
            if total <= keep_recent:
                return 0
            cutoff_id = (
                await session.exec(
                    select(ChatMessage.id)
                    .where(
                        ChatMessage.user_id == user_id,
                        ChatMessage.session_id == session_id,
                        ChatMessage.module == module,
                    )
                    .order_by(ChatMessage.created_at.desc())
                    .offset(keep_recent - 1)
                    .limit(1)
                )
            ).first()
            if cutoff_id is None:
                return 0
            old_msgs = (
                await session.exec(
                    select(ChatMessage).where(
                        ChatMessage.user_id == user_id,
                        ChatMessage.session_id == session_id,
                        ChatMessage.module == module,
                        ChatMessage.id < cutoff_id,
                    )
                )
            ).all()
            deleted = len(old_msgs)
            for msg in old_msgs:
                await session.delete(msg)
            await session.commit()
            return deleted

    # ------------------------------------------------------------------
    # 会话概要
    # ------------------------------------------------------------------

    async def get_or_create_session_summary(
        self,
        user_id: int,
        session_id: str,
        module: str = "mentor",
    ) -> ChatSessionSummary:
        async with AsyncSession(self.engine) as session:
            stmt = select(ChatSessionSummary).where(
                ChatSessionSummary.user_id == user_id,
                ChatSessionSummary.session_id == session_id,
                ChatSessionSummary.module == module,
            ).order_by(ChatSessionSummary.created_at.desc())
            existing = (await session.exec(stmt)).first()
            if existing:
                return existing
            summary = ChatSessionSummary(
                user_id=user_id,
                session_id=session_id,
                module=module,
                summary_markdown="# 会话概要\n\n暂无概要信息。",
                summary_json=make_default_session_summary_json(),
            )
            session.add(summary)
            await session.commit()
            await session.refresh(summary)
            return summary

    async def create_session_summary(
        self,
        user_id: int,
        session_id: str,
        module: str,
        summary_markdown: str,
        summary_json: dict[str, Any] | None,
        start_message_id: int | None = None,
        end_message_id: int | None = None,
        summarized_message_count: int = 0,
        current_topic: str | None = None,
        current_goal: str | None = None,
        current_status: str | None = None,
        next_action: str | None = None,
    ) -> ChatSessionSummary:
        async with AsyncSession(self.engine) as session:
            summary = ChatSessionSummary(
                user_id=user_id,
                session_id=session_id,
                module=module,
                summary_markdown=summary_markdown,
                summary_json=summary_json or make_default_session_summary_json(),
                start_message_id=start_message_id,
                end_message_id=end_message_id,
                summarized_message_count=summarized_message_count,
                current_topic=current_topic,
                current_goal=current_goal,
                current_status=current_status,
                next_action=next_action,
            )
            session.add(summary)
            await session.commit()
            await session.refresh(summary)
            return summary

    async def list_session_summaries(
        self,
        user_id: int,
        session_id: str,
        module: str = "mentor",
        limit: int = 3,
    ) -> list[ChatSessionSummary]:
        async with AsyncSession(self.engine) as session:
            stmt = select(ChatSessionSummary).where(
                ChatSessionSummary.user_id == user_id,
                ChatSessionSummary.session_id == session_id,
                ChatSessionSummary.module == module,
            ).order_by(ChatSessionSummary.created_at.desc()).limit(limit)
            return list((await session.exec(stmt)).all())

    async def get_latest_session_summary(
        self,
        user_id: int,
        session_id: str,
        module: str = "mentor",
    ) -> ChatSessionSummary | None:
        summaries = await self.list_session_summaries(user_id, session_id, module, limit=1)
        return summaries[0] if summaries else None

    async def update_session_summary(
        self,
        summary_id: int,
        summary_markdown: str | None = None,
        summary_json: dict[str, Any] | None = None,
        current_topic: str | None = None,
        current_goal: str | None = None,
        current_status: str | None = None,
        next_action: str | None = None,
    ) -> ChatSessionSummary | None:
        async with AsyncSession(self.engine) as session:
            summary = await session.get(ChatSessionSummary, summary_id)
            if not summary:
                return None
            if summary_markdown is not None:
                summary.summary_markdown = summary_markdown
            if summary_json is not None:
                summary.summary_json = summary_json
            if current_topic is not None:
                summary.current_topic = current_topic
            if current_goal is not None:
                summary.current_goal = current_goal
            if current_status is not None:
                summary.current_status = current_status
            if next_action is not None:
                summary.next_action = next_action
            summary.updated_at = now()
            session.add(summary)
            await session.commit()
            await session.refresh(summary)
            return summary

    # ------------------------------------------------------------------
    # 长期记忆（用户级单条）
    # ------------------------------------------------------------------

    async def get_or_create_long_term_memory(
        self,
        user_id: int,
        module: str = "mentor",
    ) -> UserLongTermMemory:
        async with AsyncSession(self.engine) as session:
            stmt = select(UserLongTermMemory).where(
                UserLongTermMemory.user_id == user_id,
                UserLongTermMemory.module == module,
            )
            existing = (await session.exec(stmt)).first()
            if existing:
                return existing
            memory = UserLongTermMemory(
                user_id=user_id,
                module=module,
                memory_markdown="# 长期记忆\n\n暂无长期记忆信息。",
                memory_json=make_default_long_term_memory_json(),
            )
            session.add(memory)
            await session.commit()
            await session.refresh(memory)
            return memory

    async def get_long_term_memory(
        self,
        user_id: int,
        module: str = "mentor",
    ) -> UserLongTermMemory | None:
        async with AsyncSession(self.engine) as session:
            stmt = select(UserLongTermMemory).where(
                UserLongTermMemory.user_id == user_id,
                UserLongTermMemory.module == module,
            )
            return (await session.exec(stmt)).first()

    async def update_long_term_memory(
        self,
        user_id: int,
        module: str,
        memory_markdown: str,
        memory_json: dict[str, Any] | None = None,
        updated_reason: str | None = None,
        source_session_ids: list[str] | None = None,
        source_message_ids: list[int] | None = None,
        source_summary_ids: list[int] | None = None,
    ) -> UserLongTermMemory:
        async with AsyncSession(self.engine) as session:
            stmt = select(UserLongTermMemory).where(
                UserLongTermMemory.user_id == user_id,
                UserLongTermMemory.module == module,
            )
            memory = (await session.exec(stmt)).first()
            if not memory:
                memory = UserLongTermMemory(
                    user_id=user_id,
                    module=module,
                    memory_markdown=memory_markdown,
                    memory_json=memory_json or make_default_long_term_memory_json(),
                )
            else:
                memory.memory_markdown = memory_markdown
                if memory_json is not None:
                    memory.memory_json = memory_json
                memory.version = (memory.version or 1) + 1
            if updated_reason:
                memory.updated_reason = updated_reason
            if source_session_ids:
                memory.source_session_ids = source_session_ids
            if source_message_ids:
                memory.source_message_ids = source_message_ids
            if source_summary_ids:
                memory.source_summary_ids = source_summary_ids
            memory.updated_at = now()
            session.add(memory)
            await session.commit()
            await session.refresh(memory)
            return memory

    # ------------------------------------------------------------------
    # 用户画像
    # ------------------------------------------------------------------

    async def get_or_create_user_profile(
        self,
        user_id: int,
        module: str = "mentor",
    ) -> UserProfile:
        async with AsyncSession(self.engine) as session:
            stmt = select(UserProfile).where(
                UserProfile.user_id == user_id,
                UserProfile.module == module,
            )
            existing = (await session.exec(stmt)).first()
            if existing:
                return existing
            profile = UserProfile(
                user_id=user_id,
                module=module,
                profile_markdown="# 学生画像\n\n暂无画像信息。",
                profile_json=make_default_profile_json(),
            )
            session.add(profile)
            await session.commit()
            await session.refresh(profile)
            return profile

    async def get_user_profile(
        self,
        user_id: int,
        module: str = "mentor",
    ) -> UserProfile | None:
        async with AsyncSession(self.engine) as session:
            stmt = select(UserProfile).where(
                UserProfile.user_id == user_id,
                UserProfile.module == module,
            )
            return (await session.exec(stmt)).first()

    async def update_user_profile(
        self,
        user_id: int,
        module: str,
        profile_markdown: str,
        profile_json: dict[str, Any] | None = None,
        updated_reason: str | None = None,
        source_memory_version: int | None = None,
        source_session_ids: list[str] | None = None,
        source_summary_ids: list[int] | None = None,
        source_event_ids: list[int] | None = None,
        confidence: float = 0.7,
    ) -> UserProfile:
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                stmt = select(UserProfile).where(
                    UserProfile.user_id == user_id,
                    UserProfile.module == module,
                )
                profile = (await session.exec(stmt)).first()
                if not profile:
                    profile = UserProfile(
                        user_id=user_id,
                        module=module,
                        profile_markdown=profile_markdown,
                        profile_json=profile_json or make_default_profile_json(),
                        confidence=confidence,
                    )
                else:
                    profile.profile_markdown = profile_markdown
                    if profile_json is not None:
                        profile.profile_json = profile_json
                    profile.version = (profile.version or 1) + 1
                    profile.confidence = confidence
                if updated_reason:
                    profile.updated_reason = updated_reason
                if source_memory_version is not None:
                    profile.source_memory_version = source_memory_version
                if source_session_ids:
                    profile.source_session_ids = source_session_ids
                if source_summary_ids:
                    profile.source_summary_ids = source_summary_ids
                if source_event_ids:
                    profile.source_event_ids = source_event_ids
                session.add(profile)
                await session.flush()

                latest_version = (
                    await session.exec(
                        select(func.max(UserProfileHistory.version)).where(
                            UserProfileHistory.user_id == user_id,
                            UserProfileHistory.module == module,
                        )
                    )
                ).one()
                history = UserProfileHistory(
                    user_id=user_id,
                    module=module,
                    version=0 if latest_version is None else int(latest_version) + 1,
                    profile_markdown=profile_markdown,
                    profile_json=profile_json or make_default_profile_json(),
                    change_reason=updated_reason,
                    source_memory_version=source_memory_version,
                    source_session_ids=source_session_ids,
                    source_summary_ids=source_summary_ids,
                    source_event_ids=source_event_ids,
                )
                session.add(history)
            await session.refresh(profile)
            return profile

    async def get_profile_history(
        self,
        user_id: int,
        module: str = "mentor",
        limit: int = 20,
    ) -> list[UserProfileHistory]:
        async with AsyncSession(self.engine) as session:
            stmt = (
                select(UserProfileHistory)
                .where(UserProfileHistory.user_id == user_id, UserProfileHistory.module == module)
                .order_by(UserProfileHistory.created_at.desc())
                .limit(limit)
            )
            return list((await session.exec(stmt)).all())

    # ------------------------------------------------------------------
    # 会话 Token 计数
    # ------------------------------------------------------------------

    async def accumulate_session_tokens(
        self,
        user_id: int,
        session_id: str,
        module: str,
        content: str,
    ) -> int:
        token_delta = estimate_token_count(content)
        async with AsyncSession(self.engine) as session:
            stmt = select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id,
                ChatSession.module == module,
            )
            chat_session = (await session.exec(stmt)).first()
            if not chat_session:
                chat_session = ChatSession(id=session_id, user_id=user_id, module=module, title="新对话")
            chat_session.summary_token_count = max(0, (chat_session.summary_token_count or 0) + token_delta)
            chat_session.updated_at = now()
            session.add(chat_session)
            new_count = chat_session.summary_token_count
            await session.commit()
            return new_count

    async def get_session_token_count(self, user_id: int, session_id: str, module: str) -> int:
        async with AsyncSession(self.engine) as session:
            stmt = select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id,
                ChatSession.module == module,
            )
            chat_session = (await session.exec(stmt)).first()
            return chat_session.summary_token_count if chat_session else 0

    async def reset_session_token_count(self, user_id: int, session_id: str, module: str) -> None:
        async with AsyncSession(self.engine) as session:
            stmt = select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id,
                ChatSession.module == module,
            )
            chat_session = (await session.exec(stmt)).first()
            if chat_session:
                chat_session.summary_token_count = 0
                session.add(chat_session)
                await session.commit()

    async def should_create_session_summary(
        self,
        user_id: int,
        session_id: str,
        module: str,
        threshold: int = SESSION_SUMMARY_TOKEN_THRESHOLD,
    ) -> bool:
        return await self.get_session_token_count(user_id, session_id, module) >= threshold


memory_store = MemoryStore()
