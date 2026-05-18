"""概要存储层。

模块职责：
- 概要 CRUD 操作
- 概要查询
"""

from __future__ import annotations

from typing import Any

from sqlmodel import select

from app.infra.models import ChatSessionSummary
from app.memory.core.base_store import BaseStore
from app.memory.core.utils import now
from app.memory.summary.types import make_default_summary_json


class SummaryStore(BaseStore):
    """概要存储。"""

    async def get_or_create(
        self,
        user_id: int,
        session_id: str,
        module: str = "mentor",
    ) -> ChatSessionSummary:
        """获取或创建概要。"""
        async with await self._get_session() as session:
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
                summary_json=make_default_summary_json(),
            )
            session.add(summary)
            await session.commit()
            await session.refresh(summary)
            return summary

    async def create(
        self,
        user_id: int,
        session_id: str,
        module: str,
        summary_markdown: str,
        summary_json: dict[str, Any] | None,
        summarized_message_count: int = 0,
        current_topic: str | None = None,
        current_goal: str | None = None,
    ) -> ChatSessionSummary:
        """创建新概要。"""
        async with await self._get_session() as session:
            summary = ChatSessionSummary(
                user_id=user_id,
                session_id=session_id,
                module=module,
                summary_markdown=summary_markdown,
                summary_json=summary_json or make_default_summary_json(),
                summarized_message_count=summarized_message_count,
                current_topic=current_topic,
                current_goal=current_goal,
            )
            session.add(summary)
            await session.commit()
            await session.refresh(summary)
            return summary

    async def list(
        self,
        user_id: int,
        session_id: str,
        module: str = "mentor",
        limit: int = 3,
    ) -> list[ChatSessionSummary]:
        """列举概要。"""
        async with await self._get_session() as session:
            stmt = select(ChatSessionSummary).where(
                ChatSessionSummary.user_id == user_id,
                ChatSessionSummary.session_id == session_id,
                ChatSessionSummary.module == module,
            ).order_by(ChatSessionSummary.created_at.desc()).limit(limit)
            result = await session.exec(stmt)
            return list(result.all())

    async def get_latest(
        self,
        user_id: int,
        session_id: str,
        module: str = "mentor",
    ) -> ChatSessionSummary | None:
        """获取最新概要。"""
        summaries = await self.list(user_id, session_id, module, limit=1)
        return summaries[0] if summaries else None

    async def list_cross_session(
        self,
        user_id: int,
        module: str = "mentor",
        exclude_session_id: str | None = None,
        limit: int = 5,
    ) -> list[ChatSessionSummary]:
        """跨会话查询概要，用于检索其他会话的相关记忆。"""
        async with await self._get_session() as session:
            stmt = select(ChatSessionSummary).where(
                ChatSessionSummary.user_id == user_id,
                ChatSessionSummary.module == module,
            )
            if exclude_session_id:
                stmt = stmt.where(ChatSessionSummary.session_id != exclude_session_id)
            stmt = stmt.order_by(ChatSessionSummary.created_at.desc()).limit(limit)
            result = await session.exec(stmt)
            return list(result.all())
