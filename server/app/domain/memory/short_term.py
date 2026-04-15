"""
短期记忆服务。

从 MemoryService 拆分：ChatMessage CRUD（保存、查询、计数、清理）。
"""

from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.engine import engine
from app.core.logging import get_logger
from app.models.chat import ChatMessage, ChatSession
from app.domain.memory.helpers import now, message_expire_cutoff

logger = get_logger(__name__)

SHORT_TERM_MESSAGE_EXPIRE_DAYS = 7


class ShortTermMemoryService:
    """短期记忆（ChatMessage）的读写与清理。"""

    def __init__(self) -> None:
        self.engine = engine

    async def save_message(
        self,
        user_id: int,
        session_id: str,
        module: str,
        role: str,
        content: str,
        attachments: str | None = None,
        tool_calls: str | None = None,
        resource_cards: str | None = None,
    ) -> int:
        """存入一条消息，返回当前会话消息总数。"""
        async with AsyncSession(self.engine) as session:
            session_stmt = select(ChatSession).where(ChatSession.id == session_id)
            result = await session.exec(session_stmt)
            chat_session = result.first()
            if chat_session:
                if chat_session.user_id != user_id or chat_session.module != module:
                    raise PermissionError("会话不属于当前用户或模块，禁止写入")
                chat_session.updated_at = now()
            else:
                chat_session = ChatSession(id=session_id, user_id=user_id, module=module, title=content[:20])
            session.add(chat_session)

            msg = ChatMessage(
                user_id=user_id,
                session_id=session_id,
                module=module,
                role=role,
                content=content,
                attachments=attachments,
                tool_calls=tool_calls,
                resource_cards=resource_cards,
            )
            session.add(msg)
            await session.commit()

        count = await self.get_message_count(user_id, session_id, module)
        return count

    async def get_recent_messages(
        self,
        user_id: int,
        session_id: str,
        module: str,
        limit: int | None = None,
        days: int = SHORT_TERM_MESSAGE_EXPIRE_DAYS,
        only_unexpired: bool = True,
    ) -> list[ChatMessage]:
        """获取指定会话的最近 N 条消息。"""
        async with AsyncSession(self.engine) as session:
            filters = [
                ChatMessage.user_id == user_id,
                ChatMessage.session_id == session_id,
                ChatMessage.module == module,
            ]
            if only_unexpired:
                filters.append(ChatMessage.created_at >= message_expire_cutoff(days))

            count_stmt = select(func.count()).where(*filters)
            count_result = await session.exec(count_stmt)
            total = count_result.one()

            stmt = select(ChatMessage).where(*filters).order_by(ChatMessage.created_at.asc())

            if limit is not None and limit > 0 and total > limit:
                stmt = stmt.offset(total - limit)

            result = await session.exec(stmt)
            return list(result.all())

    async def get_message_count(
        self, user_id: int, session_id: str, module: str
    ) -> int:
        async with AsyncSession(self.engine) as session:
            stmt = select(func.count()).where(
                ChatMessage.user_id == user_id,
                ChatMessage.session_id == session_id,
                ChatMessage.module == module,
            )
            result = await session.exec(stmt)
            return result.one()

    async def delete_old_messages(
        self,
        user_id: int,
        session_id: str,
        module: str,
        keep_recent: int = 10,
    ) -> int:
        """删除已被总结过的旧短期消息，仅保留最近 keep_recent 条。"""
        async with AsyncSession(self.engine) as session:
            count_stmt = select(func.count()).where(
                ChatMessage.user_id == user_id,
                ChatMessage.session_id == session_id,
                ChatMessage.module == module,
            )
            count_result = await session.exec(count_stmt)
            total = count_result.one()

            if total <= keep_recent:
                return 0

            keep_stmt = (
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
            result = await session.exec(keep_stmt)
            cutoff_id = result.first()

            if cutoff_id is None:
                return 0

            old_msgs_stmt = select(ChatMessage).where(
                ChatMessage.user_id == user_id,
                ChatMessage.session_id == session_id,
                ChatMessage.module == module,
                ChatMessage.id < cutoff_id,
            )
            old_msgs_result = await session.exec(old_msgs_stmt)
            old_msgs = old_msgs_result.all()

            deleted = len(old_msgs)
            for msg in old_msgs:
                await session.delete(msg)
            await session.commit()
            logger.info(f"[ShortTermMemory] 清理旧消息: user={user_id}, deleted={deleted}, kept={keep_recent}")
            return deleted

    async def cleanup_expired_short_term_messages(
        self,
        user_id: int,
        session_id: str,
        module: str,
        days: int = SHORT_TERM_MESSAGE_EXPIRE_DAYS,
    ) -> int:
        """物理删除超出有效期的短期消息。"""
        cutoff = message_expire_cutoff(days)
        async with AsyncSession(self.engine) as session:
            stmt = select(ChatMessage).where(
                ChatMessage.user_id == user_id,
                ChatMessage.session_id == session_id,
                ChatMessage.module == module,
                ChatMessage.created_at < cutoff,
            )
            result = await session.exec(stmt)
            expired_msgs = list(result.all())
            for msg in expired_msgs:
                await session.delete(msg)
            if expired_msgs:
                await session.commit()
            return len(expired_msgs)

    async def should_summarize(
        self, user_id: int, session_id: str, module: str, threshold: int = 20
    ) -> bool:
        """判断短期记忆是否达到总结阈值。"""
        count = await self.get_message_count(user_id, session_id, module)
        return count >= threshold


short_term_service = ShortTermMemoryService()
