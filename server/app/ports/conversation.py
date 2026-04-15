"""Conversation ports."""

from __future__ import annotations

from typing import Protocol

from app.shared.dto.chat import ChatMessageItem


class ConversationStore(Protocol):
    async def list_sessions(self, user_id: int, limit: int = 20) -> list[dict]: ...

    async def create_session(self, user_id: int, title: str = "新对话") -> dict: ...

    async def archive_session(self, user_id: int, session_id: str) -> bool: ...

    async def get_history(
        self,
        *,
        user_id: int,
        session_id: str | None = None,
        limit: int = 50,
    ) -> list[ChatMessageItem]: ...
