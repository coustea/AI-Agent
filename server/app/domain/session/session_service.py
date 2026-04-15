"""
会话管理服务。

从 MemoryService 拆分：ChatSession CRUD + token 累计。
"""

from typing import Optional, List

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.engine import engine
from app.core.logging import get_logger
from app.models.chat import ChatSession
from app.domain.memory.helpers import now, estimate_token_count

logger = get_logger(__name__)


class SessionService:
    """ChatSession CRUD 及 token 累计管理。"""

    def __init__(self) -> None:
        self.engine = engine

    async def _get_owned_session(
        self,
        session: AsyncSession,
        user_id: int,
        session_id: str,
        module: str | None = None,
    ) -> ChatSession | None:
        stmt = select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id,
        )
        if module is not None:
            stmt = stmt.where(ChatSession.module == module)
        result = await session.exec(stmt)
        return result.first()

    async def create_chat_session(
        self, user_id: int, module: str, title: str = "新对话"
    ) -> ChatSession:
        async with AsyncSession(self.engine) as session:
            chat_session = ChatSession(user_id=user_id, module=module, title=title)
            session.add(chat_session)
            await session.commit()
            await session.refresh(chat_session)
            return chat_session

    async def get_chat_session(self, session_id: str) -> Optional[ChatSession]:
        async with AsyncSession(self.engine) as session:
            stmt = select(ChatSession).where(ChatSession.id == session_id)
            result = await session.exec(stmt)
            return result.first()

    async def get_user_chat_sessions(
        self,
        user_id: int,
        module: Optional[str] = None,
        limit: int = 20,
    ) -> List[ChatSession]:
        async with AsyncSession(self.engine) as session:
            stmt = select(ChatSession).where(
                ChatSession.user_id == user_id,
                ChatSession.is_archived == False,  # noqa: E712
            )
            if module:
                stmt = stmt.where(ChatSession.module == module)
            stmt = stmt.order_by(ChatSession.updated_at.desc()).limit(limit)
            result = await session.exec(stmt)
            return list(result.all())

    async def archive_chat_session(self, session_id: str, user_id: int) -> bool:
        async with AsyncSession(self.engine) as session:
            stmt = select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id,
            )
            result = await session.exec(stmt)
            chat_session = result.first()
            if not chat_session:
                return False
            chat_session.is_archived = True
            session.add(chat_session)
            await session.commit()
            return True

    async def accumulate_session_tokens(
        self,
        user_id: int,
        session_id: str,
        module: str,
        content: str,
    ) -> tuple[int, int]:
        """累加会话 token 计数（长期记忆提取计数 + 画像更新计数）。"""
        token_delta = estimate_token_count(content)
        async with AsyncSession(self.engine) as session:
            chat_session = await self._get_owned_session(session, user_id, session_id, module)
            if not chat_session:
                chat_session = ChatSession(id=session_id, user_id=user_id, module=module, title="新对话")
            memory_token_count = max(0, chat_session.memory_token_count + token_delta)
            profile_token_count = max(0, chat_session.profile_token_count + token_delta)
            chat_session.memory_token_count = memory_token_count
            chat_session.profile_token_count = profile_token_count
            chat_session.updated_at = now()
            session.add(chat_session)
            await session.commit()
            return memory_token_count, profile_token_count

    async def get_session_token_counters(
        self, user_id: int, session_id: str, module: str
    ) -> tuple[int, int]:
        async with AsyncSession(self.engine) as session:
            chat_session = await self._get_owned_session(session, user_id, session_id, module)
            if not chat_session:
                return 0, 0
            return chat_session.memory_token_count, chat_session.profile_token_count

    async def should_trigger_memory_extraction(
        self,
        user_id: int,
        session_id: str,
        module: str,
        threshold: int = 80,
    ) -> bool:
        memory_tokens, _ = await self.get_session_token_counters(user_id, session_id, module)
        return memory_tokens >= threshold

    async def should_trigger_profile_update_by_tokens(
        self,
        user_id: int,
        session_id: str,
        module: str,
        threshold: int = 120,
    ) -> bool:
        _, profile_tokens = await self.get_session_token_counters(user_id, session_id, module)
        return profile_tokens >= threshold

    async def reset_memory_extraction_counter(
        self, user_id: int, session_id: str, module: str
    ) -> None:
        async with AsyncSession(self.engine) as session:
            chat_session = await self._get_owned_session(session, user_id, session_id, module)
            if not chat_session:
                return
            chat_session.memory_token_count = 0
            session.add(chat_session)
            await session.commit()

    async def reset_profile_update_counter(
        self, user_id: int, session_id: str, module: str
    ) -> None:
        async with AsyncSession(self.engine) as session:
            chat_session = await self._get_owned_session(session, user_id, session_id, module)
            if not chat_session:
                return
            chat_session.profile_token_count = 0
            session.add(chat_session)
            await session.commit()


session_service = SessionService()
