"""记忆系统统一数据访问层。"""

from __future__ import annotations

from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.database import engine
from app.infra.models import (
    ChatMessage,
    ChatSession,
    ChatSessionSummary,
    UserLongTermMemory,
    UserProfile,
    UserProfileHistory,
)
from app.memory.types import (
    DEFAULT_SESSION_TITLE,
    MESSAGE_EXPIRE_DAYS,
    TITLE_MAX_LENGTH,
    days_ago,
    make_default_memory_markdown,
    make_default_profile_json,
    make_default_score_json,
    now,
)


class ConcurrentUpdateError(Exception):
    """画像并发更新冲突。"""


class MemoryStore:
    """统一封装 memory 相关表的读写。"""

    def __init__(self) -> None:
        self.engine = engine

    async def _get_session(self) -> AsyncSession:
        return AsyncSession(self.engine, expire_on_commit=False)

    async def create_session(self, *, user_id: int, module: str, title: str = DEFAULT_SESSION_TITLE) -> ChatSession:
        async with await self._get_session() as session:
            chat_session = ChatSession(user_id=user_id, module=module, title=title)
            session.add(chat_session)
            await session.commit()
            await session.refresh(chat_session)
            return chat_session

    async def get_session(self, session_id: str) -> ChatSession | None:
        async with await self._get_session() as session:
            return (await session.exec(select(ChatSession).where(ChatSession.id == session_id))).first()

    async def list_sessions(self, *, user_id: int, module: str | None = None, limit: int = 20) -> list[ChatSession]:
        async with await self._get_session() as session:
            stmt = select(ChatSession).where(ChatSession.user_id == user_id, ChatSession.is_archived.is_(False))
            if module:
                stmt = stmt.where(ChatSession.module == module)
            result = await session.exec(stmt.order_by(ChatSession.updated_at.desc()).limit(limit))
            return list(result.all())

    async def archive_session(self, *, user_id: int, session_id: str) -> bool:
        async with await self._get_session() as session:
            chat_session = (
                await session.exec(select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id))
            ).first()
            if not chat_session:
                return False
            chat_session.is_archived = True
            chat_session.updated_at = now()
            session.add(chat_session)
            await session.commit()
            return True

    async def update_session_title(self, *, user_id: int, session_id: str, title: str) -> bool:
        async with await self._get_session() as session:
            chat_session = (
                await session.exec(select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id))
            ).first()
            if not chat_session:
                return False
            chat_session.title = title[:TITLE_MAX_LENGTH]
            chat_session.updated_at = now()
            session.add(chat_session)
            await session.commit()
            return True

    async def update_attachment_analyses(self, *, session_id: str, user_id: int, analyses: dict[str, Any]) -> bool:
        """更新会话的附件预分析结果。"""
        async with await self._get_session() as session:
            chat_session = (
                await session.exec(select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id))
            ).first()
            if not chat_session:
                return False
            chat_session.attachment_analyses = analyses
            chat_session.updated_at = now()
            session.add(chat_session)
            await session.commit()
            return True

    async def get_session_token_count(self, session_id: str) -> int:
        session = await self.get_session(session_id)
        return session.summary_token_count if session else 0

    async def add_session_token_count(self, *, session_id: str, user_id: int, module: str, delta: int) -> int:
        async with await self._get_session() as session:
            chat_session = (
                await session.exec(
                    select(ChatSession).where(
                        ChatSession.id == session_id,
                        ChatSession.user_id == user_id,
                        ChatSession.module == module,
                    )
                )
            ).first()
            if not chat_session:
                chat_session = ChatSession(id=session_id, user_id=user_id, module=module, title=DEFAULT_SESSION_TITLE)
            chat_session.summary_token_count = max(0, (chat_session.summary_token_count or 0) + delta)
            chat_session.updated_at = now()
            session.add(chat_session)
            await session.commit()
            return chat_session.summary_token_count

    async def reset_session_token_count(self, session_id: str) -> None:
        async with await self._get_session() as session:
            chat_session = (await session.exec(select(ChatSession).where(ChatSession.id == session_id))).first()
            if chat_session:
                chat_session.summary_token_count = 0
                session.add(chat_session)
                await session.commit()

    async def save_message(
        self,
        *,
        user_id: int,
        session_id: str,
        module: str,
        role: str,
        content: str,
        attachments: list[dict[str, Any]] | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        teaching_diagram: dict[str, Any] | None = None,
    ) -> None:
        async with await self._get_session() as session:
            chat_session = (await session.exec(select(ChatSession).where(ChatSession.id == session_id))).first()
            if chat_session:
                if chat_session.user_id != user_id or chat_session.module != module:
                    raise PermissionError("会话不属于当前用户或模块")
                chat_session.updated_at = now()
            else:
                chat_session = ChatSession(id=session_id, user_id=user_id, module=module)
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
                    teaching_diagram=teaching_diagram,
                )
            )
            await session.commit()

    async def list_messages(
        self,
        *,
        user_id: int,
        session_id: str,
        module: str,
        limit: int | None = None,
        days: int = MESSAGE_EXPIRE_DAYS,
        only_unexpired: bool = True,
    ) -> list[ChatMessage]:
        async with await self._get_session() as session:
            filters = [
                ChatMessage.user_id == user_id,
                ChatMessage.session_id == session_id,
                ChatMessage.module == module,
            ]
            if only_unexpired:
                filters.append(ChatMessage.created_at >= days_ago(days))
            total = (await session.exec(select(func.count()).where(*filters))).one()
            stmt = select(ChatMessage).where(*filters).order_by(ChatMessage.created_at.asc())
            if limit is not None and limit > 0 and total > limit:
                stmt = stmt.offset(total - limit)
            return list((await session.exec(stmt)).all())

    async def count_messages(self, *, user_id: int, session_id: str, module: str) -> int:
        async with await self._get_session() as session:
            return (
                await session.exec(
                    select(func.count()).where(
                        ChatMessage.user_id == user_id,
                        ChatMessage.session_id == session_id,
                        ChatMessage.module == module,
                    )
                )
            ).one()

    async def delete_messages_before(self, *, user_id: int, session_id: str, module: str, before_message_id: int) -> int:
        async with await self._get_session() as session:
            messages = (
                await session.exec(
                    select(ChatMessage).where(
                        ChatMessage.user_id == user_id,
                        ChatMessage.session_id == session_id,
                        ChatMessage.module == module,
                        ChatMessage.id < before_message_id,
                    )
                )
            ).all()
            for message in messages:
                await session.delete(message)
            await session.commit()
            return len(messages)

    async def delete_session_messages(self, *, user_id: int, session_id: str, module: str) -> int:
        async with await self._get_session() as session:
            messages = (
                await session.exec(
                    select(ChatMessage).where(
                        ChatMessage.user_id == user_id,
                        ChatMessage.session_id == session_id,
                        ChatMessage.module == module,
                    )
                )
            ).all()
            for message in messages:
                await session.delete(message)
            await session.commit()
            return len(messages)

    async def create_summary(
        self,
        *,
        user_id: int,
        session_id: str,
        module: str,
        summary_markdown: str,
        summarized_message_count: int,
        start_message_id: int | None = None,
        end_message_id: int | None = None,
    ) -> ChatSessionSummary:
        async with await self._get_session() as session:
            summary = ChatSessionSummary(
                user_id=user_id,
                session_id=session_id,
                module=module,
                summary_markdown=summary_markdown,
                summarized_message_count=summarized_message_count,
                start_message_id=start_message_id,
                end_message_id=end_message_id,
            )
            session.add(summary)
            await session.commit()
            await session.refresh(summary)
            return summary

    async def list_summaries(self, *, user_id: int, session_id: str, module: str, limit: int = 3) -> list[ChatSessionSummary]:
        async with await self._get_session() as session:
            stmt = (
                select(ChatSessionSummary)
                .where(
                    ChatSessionSummary.user_id == user_id,
                    ChatSessionSummary.session_id == session_id,
                    ChatSessionSummary.module == module,
                )
                .order_by(ChatSessionSummary.created_at.desc())
                .limit(limit)
            )
            return list((await session.exec(stmt)).all())

    async def get_latest_summary(self, *, user_id: int, session_id: str, module: str) -> ChatSessionSummary | None:
        summaries = await self.list_summaries(user_id=user_id, session_id=session_id, module=module, limit=1)
        return summaries[0] if summaries else None

    async def get_profile(self, *, user_id: int, module: str) -> UserProfile | None:
        async with await self._get_session() as session:
            return (
                await session.exec(select(UserProfile).where(UserProfile.user_id == user_id, UserProfile.module == module))
            ).first()

    async def get_or_create_profile(self, *, user_id: int, module: str) -> UserProfile:
        async with await self._get_session() as session:
            profile = UserProfile(
                user_id=user_id,
                module=module,
                profile_json=make_default_profile_json(),
                profile_score_json=make_default_score_json(),
            )
            session.add(profile)
            try:
                await session.commit()
                await session.refresh(profile)
                return profile
            except IntegrityError:
                await session.rollback()
                existing = (
                    await session.exec(select(UserProfile).where(UserProfile.user_id == user_id, UserProfile.module == module))
                ).first()
                if existing:
                    return existing
                raise

    async def update_profile(
        self,
        *,
        user_id: int,
        module: str,
        profile_json: dict[str, Any],
        score_json: dict[str, Any],
        profile_markdown: str | None = None,
        updated_reason: str,
        source_session_ids: list[str] | None = None,
        source_summary_ids: list[int] | None = None,
        confidence: float = 0.7,
        expected_version: int | None = None,
    ) -> UserProfile:
        async with await self._get_session() as session:
            async with session.begin():
                profile = (
                    await session.exec(select(UserProfile).where(UserProfile.user_id == user_id, UserProfile.module == module))
                ).first()
                if not profile:
                    profile = UserProfile(user_id=user_id, module=module)
                elif expected_version is not None and profile.version != expected_version:
                    raise ConcurrentUpdateError(f"画像版本冲突: 期望 {expected_version}, 实际 {profile.version}")
                else:
                    profile.version = (profile.version or 1) + 1
                profile.profile_json = profile_json
                profile.profile_score_json = score_json
                profile.profile_markdown = profile_markdown
                profile.updated_reason = updated_reason
                profile.source_session_ids = source_session_ids
                profile.source_summary_ids = source_summary_ids
                profile.confidence = confidence
                profile.updated_at = now()
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
                session.add(
                    UserProfileHistory(
                        user_id=user_id,
                        module=module,
                        version=0 if latest_version is None else int(latest_version) + 1,
                        profile_json=profile_json,
                        profile_score_json=score_json,
                        profile_markdown=profile_markdown,
                        change_reason=updated_reason,
                        source_session_ids=source_session_ids,
                        source_summary_ids=source_summary_ids,
                    )
                )
            await session.refresh(profile)
            return profile

    async def list_profile_history(self, *, user_id: int, module: str, limit: int = 20) -> list[UserProfileHistory]:
        async with await self._get_session() as session:
            stmt = (
                select(UserProfileHistory)
                .where(UserProfileHistory.user_id == user_id, UserProfileHistory.module == module)
                .order_by(UserProfileHistory.created_at.desc())
                .limit(limit)
            )
            return list((await session.exec(stmt)).all())

    async def get_long_term_memory(self, *, user_id: int, module: str) -> UserLongTermMemory | None:
        async with await self._get_session() as session:
            return (
                await session.exec(select(UserLongTermMemory).where(UserLongTermMemory.user_id == user_id, UserLongTermMemory.module == module))
            ).first()

    async def get_or_create_long_term_memory(self, *, user_id: int, module: str) -> UserLongTermMemory:
        async with await self._get_session() as session:
            existing = (
                await session.exec(select(UserLongTermMemory).where(UserLongTermMemory.user_id == user_id, UserLongTermMemory.module == module))
            ).first()
            if existing:
                return existing
            memory = UserLongTermMemory(
                user_id=user_id,
                module=module,
                memory_markdown=make_default_memory_markdown(),
                category="general",
            )
            session.add(memory)
            await session.commit()
            await session.refresh(memory)
            return memory

    async def update_long_term_memory(
        self,
        *,
        user_id: int,
        module: str,
        memory_markdown: str,
        category: str = "general",
        updated_reason: str,
        source_session_ids: list[str] | None = None,
        source_message_ids: list[int] | None = None,
        source_summary_ids: list[int] | None = None,
    ) -> UserLongTermMemory:
        async with await self._get_session() as session:
            memory = (
                await session.exec(select(UserLongTermMemory).where(UserLongTermMemory.user_id == user_id, UserLongTermMemory.module == module))
            ).first()
            if not memory:
                memory = UserLongTermMemory(user_id=user_id, module=module)
            else:
                memory.version = (memory.version or 1) + 1
            memory.memory_markdown = memory_markdown
            memory.category = category
            memory.updated_reason = updated_reason
            memory.source_session_ids = source_session_ids
            memory.source_message_ids = source_message_ids
            memory.source_summary_ids = source_summary_ids
            memory.updated_at = now()
            session.add(memory)
            await session.commit()
            await session.refresh(memory)
            return memory
