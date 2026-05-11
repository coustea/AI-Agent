"""会话存储层。

模块职责：
- 会话 CRUD 操作
- 会话查询
"""

from __future__ import annotations

from sqlmodel import select

from app.infra.models import ChatSession
from app.memory.core.base_store import BaseStore
from app.memory.core.utils import now
from app.memory.session.types import DEFAULT_SESSION_TITLE, TITLE_MAX_LENGTH


class SessionStore(BaseStore):
    """会话存储。"""

    async def create(
        self,
        user_id: int,
        module: str,
        title: str = DEFAULT_SESSION_TITLE,
    ) -> ChatSession:
        """创建会话。"""
        async with await self._get_session() as session:
            chat_session = ChatSession(user_id=user_id, module=module, title=title)
            session.add(chat_session)
            await session.commit()
            await session.refresh(chat_session)
            return chat_session

    async def get(self, session_id: str) -> ChatSession | None:
        """获取会话。"""
        async with await self._get_session() as session:
            stmt = select(ChatSession).where(ChatSession.id == session_id)
            result = await session.exec(stmt)
            return result.first()

    async def list_by_user(
        self,
        user_id: int,
        module: str | None = None,
        limit: int = 20,
    ) -> list[ChatSession]:
        """获取用户会话列表。"""
        async with await self._get_session() as session:
            stmt = select(ChatSession).where(
                ChatSession.user_id == user_id,
                ChatSession.is_archived.is_(False),
            )
            if module:
                stmt = stmt.where(ChatSession.module == module)
            stmt = stmt.order_by(ChatSession.updated_at.desc()).limit(limit)
            result = await session.exec(stmt)
            return list(result.all())

    async def archive(self, session_id: str, user_id: int) -> bool:
        """归档会话。"""
        async with await self._get_session() as session:
            stmt = select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id,
            )
            chat_session = (await session.exec(stmt)).first()
            if not chat_session:
                return False
            chat_session.is_archived = True
            session.add(chat_session)
            await session.commit()
            return True

    async def update_title(
        self,
        session_id: str,
        user_id: int,
        title: str,
    ) -> bool:
        """更新会话标题。"""
        async with await self._get_session() as session:
            stmt = select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id,
            )
            chat_session = (await session.exec(stmt)).first()
            if not chat_session:
                return False
            chat_session.title = title[:TITLE_MAX_LENGTH]
            session.add(chat_session)
            await session.commit()
            return True

    async def touch(self, session_id: str) -> None:
        """更新会话时间戳。"""
        async with await self._get_session() as session:
            stmt = select(ChatSession).where(ChatSession.id == session_id)
            chat_session = (await session.exec(stmt)).first()
            if chat_session:
                chat_session.updated_at = now()
                session.add(chat_session)
                await session.commit()

    async def get_token_count(self, session_id: str) -> int:
        """获取会话 token 计数。"""
        async with await self._get_session() as session:
            stmt = select(ChatSession).where(ChatSession.id == session_id)
            chat_session = (await session.exec(stmt)).first()
            return chat_session.summary_token_count if chat_session else 0

    async def add_token_count(
        self,
        session_id: str,
        user_id: int,
        module: str,
        delta: int,
    ) -> int:
        """累加 token 计数。"""
        async with await self._get_session() as session:
            stmt = select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id,
                ChatSession.module == module,
            )
            chat_session = (await session.exec(stmt)).first()
            if not chat_session:
                chat_session = ChatSession(
                    id=session_id,
                    user_id=user_id,
                    module=module,
                    title=DEFAULT_SESSION_TITLE,
                )
            chat_session.summary_token_count = max(
                0, (chat_session.summary_token_count or 0) + delta
            )
            chat_session.updated_at = now()
            session.add(chat_session)
            await session.commit()
            return chat_session.summary_token_count

    async def reset_token_count(self, session_id: str) -> None:
        """重置 token 计数。"""
        async with await self._get_session() as session:
            stmt = select(ChatSession).where(ChatSession.id == session_id)
            chat_session = (await session.exec(stmt)).first()
            if chat_session:
                chat_session.summary_token_count = 0
                session.add(chat_session)
                await session.commit()
