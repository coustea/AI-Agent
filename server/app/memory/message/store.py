"""消息存储层。

模块职责：
- 消息 CRUD 操作
- 消息查询
- 消息清理
"""

from __future__ import annotations

from sqlmodel import func, select

from app.infra.models import ChatMessage, ChatSession
from app.memory.core.base_store import BaseStore
from app.memory.core.utils import days_ago, now
from app.memory.message.types import MESSAGE_EXPIRE_DAYS


class MessageStore(BaseStore):
    """消息存储。"""

    async def save(
        self,
        user_id: int,
        session_id: str,
        module: str,
        role: str,
        content: str,
        attachments: dict | None = None,
        tool_calls: list | None = None,
        diagram: dict | None = None,
    ) -> int:
        """保存消息并返回消息总数。"""
        async with await self._get_session() as session:
            # 确保会话存在
            stmt = select(ChatSession).where(ChatSession.id == session_id)
            chat_session = (await session.exec(stmt)).first()
            if chat_session:
                if chat_session.user_id != user_id or chat_session.module != module:
                    raise PermissionError("会话不属于当前用户或模块")
                chat_session.updated_at = now()
            else:
                chat_session = ChatSession(
                    id=session_id,
                    user_id=user_id,
                    module=module,
                )
            session.add(chat_session)

            # 保存消息
            message = ChatMessage(
                user_id=user_id,
                session_id=session_id,
                module=module,
                role=role,
                content=content,
                attachments=attachments,
                tool_calls=tool_calls,
                diagram=diagram,
            )
            session.add(message)
            await session.commit()

        return await self.count(user_id, session_id, module)

    async def get_recent(
        self,
        user_id: int,
        session_id: str,
        module: str,
        limit: int | None = None,
        days: int = MESSAGE_EXPIRE_DAYS,
        only_unexpired: bool = True,
    ) -> list[ChatMessage]:
        """获取最近消息。"""
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

            result = await session.exec(stmt)
            return list(result.all())

    async def count(self, user_id: int, session_id: str, module: str) -> int:
        """获取消息数量。"""
        async with await self._get_session() as session:
            stmt = select(func.count()).where(
                ChatMessage.user_id == user_id,
                ChatMessage.session_id == session_id,
                ChatMessage.module == module,
            )
            return (await session.exec(stmt)).one()

    async def delete_old(
        self,
        user_id: int,
        session_id: str,
        module: str,
        keep_recent: int = 10,
    ) -> int:
        """删除旧消息，保留最近 N 条。"""
        async with await self._get_session() as session:
            total = (await session.exec(
                select(func.count()).where(
                    ChatMessage.user_id == user_id,
                    ChatMessage.session_id == session_id,
                    ChatMessage.module == module,
                )
            )).one()

            if total <= keep_recent:
                return 0

            # 找到保留的起始消息 ID
            cutoff_id = (await session.exec(
                select(ChatMessage.id)
                .where(
                    ChatMessage.user_id == user_id,
                    ChatMessage.session_id == session_id,
                    ChatMessage.module == module,
                )
                .order_by(ChatMessage.created_at.desc())
                .offset(keep_recent - 1)
                .limit(1)
            )).first()

            if cutoff_id is None:
                return 0

            # 删除旧消息
            old_msgs = (await session.exec(
                select(ChatMessage).where(
                    ChatMessage.user_id == user_id,
                    ChatMessage.session_id == session_id,
                    ChatMessage.module == module,
                    ChatMessage.id < cutoff_id,
                )
            )).all()

            deleted = len(old_msgs)
            for msg in old_msgs:
                await session.delete(msg)
            await session.commit()
            return deleted
