"""Conversation repository adapter."""

from __future__ import annotations

import json

from app.domain.memory.short_term import short_term_service
from app.domain.session.session_service import session_service
from app.shared.resource_cards import build_resource_cards_from_tool_calls
from app.ports.conversation import ConversationStore
from app.shared.dto.chat import AttachmentInfo, ChatMessageItem, ResourceCard, ToolCallRecord

CHAT_MODULE_NAME = "mentor"


class SqlConversationStore(ConversationStore):
    async def list_sessions(self, user_id: int, limit: int = 20) -> list[dict]:
        sessions = await session_service.get_user_chat_sessions(user_id=user_id, module=CHAT_MODULE_NAME, limit=limit)
        return [{"id": s.id, "title": s.title, "updated_at": s.updated_at} for s in sessions]

    async def create_session(self, user_id: int, title: str = "新对话") -> dict:
        session = await session_service.create_chat_session(user_id=user_id, module=CHAT_MODULE_NAME, title=title)
        return {"id": session.id, "title": session.title}

    async def archive_session(self, user_id: int, session_id: str) -> bool:
        return await session_service.archive_chat_session(session_id, user_id)

    async def get_history(
        self,
        *,
        user_id: int,
        session_id: str | None = None,
        limit: int = 50,
    ) -> list[ChatMessageItem]:
        target_session = session_id
        if not target_session:
            sessions = await session_service.get_user_chat_sessions(user_id=user_id, module=CHAT_MODULE_NAME, limit=1)
            if not sessions:
                return []
            target_session = sessions[0].id

        messages = await short_term_service.get_recent_messages(
            user_id=user_id,
            session_id=target_session,
            module=CHAT_MODULE_NAME,
            limit=limit,
        )

        items: list[ChatMessageItem] = []
        for msg in messages:
            attachments = None
            if msg.attachments:
                try:
                    attachments = [AttachmentInfo(**value) for value in json.loads(msg.attachments)]
                except (json.JSONDecodeError, TypeError):
                    attachments = None

            tool_calls = None
            raw_tc = None
            if msg.tool_calls:
                try:
                    raw_tc = json.loads(msg.tool_calls)
                    tool_calls = [ToolCallRecord(**value) for value in raw_tc]
                except (json.JSONDecodeError, TypeError):
                    tool_calls = None
                    raw_tc = None

            resource_cards = None
            if msg.resource_cards:
                try:
                    resource_cards = [ResourceCard(**value) for value in json.loads(msg.resource_cards)]
                except (json.JSONDecodeError, TypeError):
                    resource_cards = None
            elif raw_tc:
                derived_cards = build_resource_cards_from_tool_calls(raw_tc)
                if derived_cards:
                    resource_cards = [ResourceCard(**value) for value in derived_cards]

            items.append(
                ChatMessageItem(
                    role=msg.role,
                    content=msg.content,
                    attachments=attachments,
                    tool_calls=tool_calls,
                    resource_cards=resource_cards,
                    created_at=msg.created_at,
                )
            )
        return items
