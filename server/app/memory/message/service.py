"""消息服务层。

模块职责：
- 消息业务逻辑
"""

from __future__ import annotations

from app.infra.models import ChatMessage
from app.memory.message.store import MessageStore
from app.memory.message.types import DIALOGUE_ROLES


class MessageService:
    """消息服务。"""

    def __init__(self, module: str = "mentor") -> None:
        self.module = module
        self.store = MessageStore()

    async def save(
        self,
        user_id: int,
        session_id: str,
        role: str,
        content: str,
        attachments: dict | None = None,
        tool_calls: list | None = None,
        diagram: dict | None = None,
    ) -> int:
        """保存消息。"""
        return await self.store.save(
            user_id=user_id,
            session_id=session_id,
            module=self.module,
            role=role,
            content=content,
            attachments=attachments,
            tool_calls=tool_calls,
            diagram=diagram,
        )

    async def list(
        self,
        user_id: int,
        session_id: str,
        limit: int | None = None,
        days: int = 7,
        only_unexpired: bool = True,
    ) -> list[ChatMessage]:
        """获取消息列表。"""
        return await self.store.get_recent(
            user_id=user_id,
            session_id=session_id,
            module=self.module,
            limit=limit,
            days=days,
            only_unexpired=only_unexpired,
        )

    async def count(self, user_id: int, session_id: str) -> int:
        """获取消息数量。"""
        return await self.store.count(user_id, session_id, self.module)

    async def list_dialogue(
        self,
        user_id: int,
        session_id: str,
        limit: int | None = None,
    ) -> list[ChatMessage]:
        """获取对话消息（仅 user/assistant）。"""
        messages = await self.list(user_id, session_id, limit)
        return [
            m for m in messages
            if m.role in DIALOGUE_ROLES and m.content.strip()
        ]

    async def count_assistant_turns(self, user_id: int, session_id: str) -> int:
        """统计助手回复轮数。"""
        messages = await self.list(user_id, session_id, limit=100)
        return sum(1 for m in messages if m.role == "assistant")
