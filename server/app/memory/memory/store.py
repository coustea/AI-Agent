"""长期记忆存储层。

模块职责：
- 长期记忆 CRUD 操作
- 用户级单条记忆管理
"""

from __future__ import annotations

from typing import Any

from sqlmodel import select

from app.infra.models import UserLongTermMemory
from app.memory.core.base_store import BaseStore
from app.memory.core.utils import now
from app.memory.memory.types import make_default_memory_json


class LongTermMemoryStore(BaseStore):
    """长期记忆存储。"""

    async def get_or_create(
        self,
        user_id: int,
        module: str = "mentor",
    ) -> UserLongTermMemory:
        """获取或创建长期记忆（一个用户一个 module 只有一条）。"""
        async with await self._get_session() as session:
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
                memory_json=make_default_memory_json(),
            )
            session.add(memory)
            await session.commit()
            await session.refresh(memory)
            return memory

    async def get(
        self,
        user_id: int,
        module: str = "mentor",
    ) -> UserLongTermMemory | None:
        """获取长期记忆。"""
        async with await self._get_session() as session:
            stmt = select(UserLongTermMemory).where(
                UserLongTermMemory.user_id == user_id,
                UserLongTermMemory.module == module,
            )
            return (await session.exec(stmt)).first()

    async def update(
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
        """更新长期记忆。"""
        async with await self._get_session() as session:
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
                    memory_json=memory_json or make_default_memory_json(),
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
