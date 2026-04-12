from __future__ import annotations

from typing import List, Optional
from collections.abc import Awaitable, Callable

from sqlmodel import func, select
from sqlalchemy import or_
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.engine import engine
from app.core.logging import get_logger
from app.models.chat import ChatMessage, ChatSession
from app.models.memory import UserMemory
from app.models.profile import UserProfile, UserProfileHistory

logger = get_logger(__name__)


class MemoryService:
    """
    统一记忆管理服务 (多 Agent 共享中枢)
    无需外部传入 Session，内部自动管理数据库连接生命周期。
    注意：现在所有方法均为 async，请使用 await 调用。
    """

    def __init__(self):
        # 绑定引擎，供所有的 async with 语句使用
        self.engine = engine

    # ==========================================
    # 0. 会话管理 (基于 user_id + session_id)
    # ==========================================
    async def create_chat_session(self, user_id: int, module: str, title: str = "新对话") -> ChatSession:
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

    async def get_user_chat_sessions(self, user_id: int, module: Optional[str] = None, limit: int = 20) -> List[ChatSession]:
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
        """软删除（归档）一个会话"""
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

    # ==========================================
    # 1. 动态画像管理 (基于 user_id 共享)
    # ==========================================
    async def get_user_profile(self, user_id: int) -> UserProfile | None:
        """获取用户的完整画像记录"""
        async with AsyncSession(self.engine) as session:
            stmt = select(UserProfile).where(UserProfile.user_id == user_id)
            result = await session.exec(stmt)
            return result.first()

    async def update_user_profile(self, user_id: int, features: dict, change_reason: str = "系统自动更新", source_memory_ids: list[int] | None = None) -> UserProfile:
        """更新用户的画像特征，并自动记录快照历史"""
        import json
        async with AsyncSession(self.engine) as session:
            stmt = select(UserProfile).where(UserProfile.user_id == user_id).with_for_update()
            result = await session.exec(stmt)
            profile = result.first()

            if not profile:
                profile = UserProfile(user_id=user_id)

            # 动态更新非空字段
            for key, value in features.items():
                if hasattr(profile, key) and value is not None:
                    setattr(profile, key, value)

            session.add(profile)
            await session.commit()
            await session.refresh(profile)

            # 获取最新完整画像数据（避免只存增量Diff）
            full_profile_data = profile.model_dump(exclude={"user_id", "updated_at", "created_at"})

            # 记录历史快照
            history_stmt = select(func.max(UserProfileHistory.version)).where(UserProfileHistory.user_id == user_id)
            result = await session.exec(history_stmt)
            max_version = result.one_or_none() or 0

            snapshot = UserProfileHistory(
                user_id=user_id,
                version=max_version + 1,
                change_reason=change_reason,
                source_memory_ids=json.dumps(source_memory_ids) if source_memory_ids else None,
                **full_profile_data
            )
            session.add(snapshot)
            await session.commit()
            return profile

    # ==========================================
    # 2. 短期记忆管理 (基于 user_id + session_id 共享)
    # ==========================================
    async def save_message(self, user_id: int, session_id: str, module: str, role: str, content: str, attachments: str | None = None, tool_calls: str | None = None) -> int:
        """存入一条消息，返回当前会话消息总数。

        Args:
            attachments: JSON 数组字符串，格式如
                '[{"url": "/uploads/1/abc.pdf", "type": "document", "name": "report.pdf"}]'
            tool_calls: JSON 数组字符串，记录该消息触发的工具调用链，格式如
                '[{"tool": "read_uploaded_file", "args": {...}, "result": "...", "status": "success"}]'
        """
        from datetime import datetime
        async with AsyncSession(self.engine) as session:
            session_stmt = select(ChatSession).where(ChatSession.id == session_id)
            result = await session.exec(session_stmt)
            chat_session = result.first()
            if chat_session:
                if chat_session.user_id != user_id or chat_session.module != module:
                    raise PermissionError("会话不属于当前用户或模块，禁止写入")
                chat_session.updated_at = datetime.now()
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
            )
            session.add(msg)
            await session.commit()

        count = await self.get_message_count(user_id, session_id, module)
        return count

    async def get_recent_messages(self, user_id: int, session_id: str, module: str, limit: int | None = None) -> list[ChatMessage]:
        """获取指定会话的最近 N 条消息"""
        async with AsyncSession(self.engine) as session:
            count_stmt = select(func.count()).where(
                ChatMessage.user_id == user_id,
                ChatMessage.session_id == session_id,
                ChatMessage.module == module,
            )
            count_result = await session.exec(count_stmt)
            total = count_result.one()

            stmt = select(ChatMessage).where(
                ChatMessage.user_id == user_id,
                ChatMessage.session_id == session_id,
                ChatMessage.module == module,
            ).order_by(ChatMessage.created_at.asc())

            if limit is not None and limit > 0 and total > limit:
                stmt = stmt.offset(total - limit)

            result = await session.exec(stmt)
            return list(result.all())

    async def get_message_count(self, user_id: int, session_id: str, module: str) -> int:
        async with AsyncSession(self.engine) as session:
            stmt = select(func.count()).where(
                ChatMessage.user_id == user_id,
                ChatMessage.session_id == session_id,
                ChatMessage.module == module,
            )
            result = await session.exec(stmt)
            return result.one()

    # ==========================================
    # 3. 长期记忆管理 (基于 user_id 共享)
    # ==========================================
    async def get_long_term_memories(self, user_id: int, module: str | None = None, limit: int = 10) -> list[UserMemory]:
        """获取用户的长期记忆列表 (旧版 UserMemory)"""
        async with AsyncSession(self.engine) as session:
            stmt = select(UserMemory).where(UserMemory.user_id == user_id)
            if module is not None:
                stmt = stmt.where(UserMemory.source == module)
            stmt = stmt.order_by(UserMemory.created_at.desc()).limit(limit)
            result = await session.exec(stmt)
            return list(result.all())

    async def should_summarize(self, user_id: int, session_id: str, module: str, threshold: int = 20) -> bool:
        """判断短期记忆是否达到总结阈值"""
        count = await self.get_message_count(user_id, session_id, module)
        return count >= threshold

    # ==========================================
    # 4. 用户事实/偏好记忆 (统一使用 UserMemory)
    # ==========================================
    async def save_user_fact(self, user_id: int, content: str, memory_type: str, session_id: Optional[str] = None, expires_at=None) -> UserMemory:
        """保存单条用户事实/偏好到 UserMemory 表"""
        from datetime import datetime as dt
        async with AsyncSession(self.engine) as session:
            now = dt.now()
            duplicate_stmt = (
                select(UserMemory)
                .where(
                    UserMemory.user_id == user_id,
                    UserMemory.source == "fact_agent",
                    UserMemory.memory_type == memory_type,
                    UserMemory.content == content,
                    or_(UserMemory.expires_at == None, UserMemory.expires_at > now),  # noqa: E711
                )
                .order_by(UserMemory.created_at.desc())
                .limit(1)
            )
            duplicate = (await session.exec(duplicate_stmt)).first()
            if duplicate:
                return duplicate

            memory = UserMemory(
                user_id=user_id,
                session_id=session_id or "",
                content=content,
                memory_type=memory_type,
                source="fact_agent",
                expires_at=expires_at,
            )
            session.add(memory)
            await session.commit()
            await session.refresh(memory)
            return memory

    async def get_user_facts(self, user_id: int, limit: int = 50) -> List[UserMemory]:
        """获取用户的未过期事实/偏好记忆"""
        from datetime import datetime as dt
        async with AsyncSession(self.engine) as session:
            now = dt.now()
            stmt = select(UserMemory).where(
                UserMemory.user_id == user_id,
                UserMemory.source == "fact_agent",
                or_(UserMemory.expires_at == None, UserMemory.expires_at > now),  # noqa: E711
            ).order_by(UserMemory.created_at.desc()).limit(limit)
            result = await session.exec(stmt)
            return list(result.all())

    # ==========================================
    # 5. 长期记忆写入 & 短期消息清理
    # ==========================================
    async def save_long_term_memory(
        self,
        user_id: int,
        session_id: str,
        content: str,
        memory_type: str,
        dimension: str | None = None,
        importance: float = 0.5,
        source: str = "conversation",
        source_message_count: int = 0,
    ) -> UserMemory:
        """将 LLM 提炼的长期记忆条目写入 user_memory 表"""
        async with AsyncSession(self.engine) as session:
            memory = UserMemory(
                user_id=user_id,
                session_id=session_id,
                content=content,
                memory_type=memory_type,
                dimension=dimension,
                importance=importance,
                source=source,
                source_message_count=source_message_count,
            )
            session.add(memory)
            await session.commit()
            await session.refresh(memory)
            logger.info(f"[MemoryService] 保存长期记忆: user={user_id}, type={memory_type}")
            return memory

    async def delete_old_messages(
        self,
        user_id: int,
        session_id: str,
        module: str,
        keep_recent: int = 10,
    ) -> int:
        """删除已被总结过的旧短期消息，仅保留最近 keep_recent 条"""
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
            logger.info(f"[MemoryService] 清理旧消息: user={user_id}, deleted={deleted}, kept={keep_recent}")
            return deleted

    # ==========================================
    # 6. 短期→长期记忆压缩
    # ==========================================
    async def summarize_and_compress(
        self,
        user_id: int,
        session_id: str,
        module: str,
        threshold: int = 30,
        keep_recent: int = 10,
    ) -> None:
        """如果短期消息达到阈值，调用 LLM 总结为长期记忆并清理旧消息。"""
        if not await self.should_summarize(user_id, session_id, module, threshold):
            return

        import os
        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import ChatPromptTemplate

        recent_msgs = await self.get_recent_messages(user_id, session_id, module)
        if not recent_msgs:
            return

        chat_text = "\n".join(
            f"[{m.created_at.strftime('%m-%d %H:%M')}] {m.role}: {m.content}"
            for m in recent_msgs[:-keep_recent]
        )
        if not chat_text.strip():
            return

        summarize_prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "你是一个记忆压缩引擎。请将以下对话记录提炼为若干条关键知识点和结论。\n"
                "每条用一行表示，格式：`类别|内容`，类别包括 knowledge/error/behavior/interest/question/answer。\n"
                "只输出有价值的条目，忽略闲聊。"
            )),
            ("human", "{chat_text}"),
        ])

        try:
            llm = ChatOpenAI(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_API_BASE"),
                temperature=0.1,
            )
            prompt = summarize_prompt.invoke({"chat_text": chat_text})
            result = await llm.ainvoke(prompt)

            summarized_ids = [m.id for m in recent_msgs[:-keep_recent]]
            await self.save_long_term_memory(
                user_id=user_id,
                session_id=session_id,
                content=result.content,
                memory_type="summary",
                source=module,
                source_message_count=len(summarized_ids),
            )

            deleted = await self.delete_old_messages(user_id, session_id, module, keep_recent)
            logger.info(f"[MemoryService] 压缩完成: user={user_id}, summarized={len(summarized_ids)}, deleted={deleted}")
        except Exception as e:
            logger.error(f"[MemoryService] 短期→长期压缩失败: {e}")

    # ==========================================
    # 7. 画像历史查询
    # ==========================================
    async def get_profile_history(self, user_id: int, limit: int = 20) -> list[UserProfileHistory]:
        """获取用户画像的变更历史快照列表"""
        async with AsyncSession(self.engine) as session:
            stmt = (
                select(UserProfileHistory)
                .where(UserProfileHistory.user_id == user_id)
                .order_by(UserProfileHistory.version.desc())
                .limit(limit)
            )
            result = await session.exec(stmt)
            return list(result.all())


# 初始化实例
memory_service = MemoryService()
