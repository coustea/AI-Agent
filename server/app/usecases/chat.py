"""Chat use cases."""

from __future__ import annotations

from app.ports.conversation import ConversationStore
from app.ports.runtime import ChatRuntime
from app.ports.storage import FileStore

CHAT_MODULE_NAME = "mentor"


class ChatUseCases:
    def __init__(
        self,
        conversation_store: ConversationStore,
        file_store: FileStore,
        chat_runtime: ChatRuntime,
    ) -> None:
        self.conversation_store = conversation_store
        self.file_store = file_store
        self.chat_runtime = chat_runtime

    @staticmethod
    def default_session_id(user_id: int) -> str:
        return f"user-{user_id}-default-{CHAT_MODULE_NAME}"

    async def stream_chat(
        self,
        *,
        user_id: int,
        user_message: str,
        session_id: str | None = None,
        image_urls: list[str] | None = None,
        file_urls: list[str] | None = None,
    ):
        async for chunk in self.chat_runtime.stream_chat(
            user_id=user_id,
            user_message=user_message,
            session_id=session_id or self.default_session_id(user_id),
            image_urls=image_urls,
            file_urls=file_urls,
        ):
            yield chunk

    async def save_upload(
        self,
        *,
        filename: str,
        content: bytes,
        user_id: int,
        session_id: str,
    ) -> dict:
        return await self.file_store.save_upload(
            filename=filename,
            content=content,
            user_id=user_id,
            session_id=session_id,
        )

    def resolve_uploaded_file(
        self,
        *,
        current_user_id: int,
        owner_id: int,
        session_id: str,
        filename: str,
    ):
        return self.file_store.resolve_user_file(
            current_user_id=current_user_id,
            owner_id=owner_id,
            session_id=session_id,
            filename=filename,
        )

    async def list_sessions(self, user_id: int, limit: int = 20) -> list[dict]:
        return await self.conversation_store.list_sessions(user_id, limit)

    async def create_session(self, user_id: int, title: str = "新对话") -> dict:
        return await self.conversation_store.create_session(user_id, title)

    async def archive_session(self, user_id: int, session_id: str) -> bool:
        return await self.conversation_store.archive_session(user_id, session_id)

    async def get_history(
        self,
        *,
        user_id: int,
        session_id: str | None = None,
        limit: int = 50,
    ):
        return await self.conversation_store.get_history(
            user_id=user_id,
            session_id=session_id,
            limit=limit,
        )
