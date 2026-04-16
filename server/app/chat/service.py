"""Chat service — 用例编排层。

调用链: api.py → ChatUseCases → TutorChatRuntime → TutorAgent (agent.py)
                                              ↕
                                   SqlConversationStore  LocalFileStore
"""

from __future__ import annotations

import json
from pathlib import Path

from app.memory.short_term import short_term_service
from app.memory.session import session_service
from app.chat.schemas import AttachmentInfo, ChatMessageItem, ToolCallRecord

CHAT_MODULE_NAME = "mentor"


class SqlConversationStore:
    """对话会话持久化。"""


    async def list_sessions(self, user_id: int, limit: int = 30) -> list[dict]:
        sessions = await session_service.get_user_chat_sessions(
            user_id=user_id, module=CHAT_MODULE_NAME, limit=limit,
        ) 
        return [{"id": s.id, "title": s.title, "updated_at": s.updated_at} for s in sessions]

    async def create_session(self, user_id: int, title: str = "新对话") -> dict:
        session = await session_service.create_chat_session(
            user_id=user_id, module=CHAT_MODULE_NAME, title=title,
        )
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
        # 未指定 session 时取最近一个
        target_session = session_id
        if not target_session:
            sessions = await session_service.get_user_chat_sessions(
                user_id=user_id, module=CHAT_MODULE_NAME, limit=1,
            )
            if not sessions:
                return []
            target_session = sessions[0].id

        messages = await short_term_service.get_recent_messages(
            user_id=user_id,
            session_id=target_session,
            module=CHAT_MODULE_NAME,
            limit=limit,
        )

        # 将 DB 模型转为前端 DTO，反序列化 JSON 字段
        items: list[ChatMessageItem] = []
        for msg in messages:
            attachments = None
            if msg.attachments:
                try:
                    attachments = [AttachmentInfo(**v) for v in json.loads(msg.attachments)]
                except (json.JSONDecodeError, TypeError):
                    attachments = None

            tool_calls = None
            raw_tc = None
            if msg.tool_calls:
                try:
                    raw_tc = json.loads(msg.tool_calls)
                    tool_calls = [ToolCallRecord(**v) for v in raw_tc]
                except (json.JSONDecodeError, TypeError):
                    tool_calls = None
                    raw_tc = None

            items.append(
                ChatMessageItem(
                    role=msg.role,
                    content=msg.content,
                    attachments=attachments,
                    tool_calls=tool_calls,
                    created_at=msg.created_at,
                )
            )
        return items


class ChatUseCases:
    """对话相关用例：流式聊天、文件上传、会话管理。"""

    def __init__(
        self,
        conversation_store: SqlConversationStore,
        file_store,
    ) -> None:
        self.conversation_store = conversation_store
        self.file_store = file_store

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
        """委托给 TutorChatRuntime，透传流式输出。"""
        from app.chat.service import tutor_chat_runtime
        async for chunk in tutor_chat_runtime.stream_chat(
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


class TutorChatRuntime:
    """对话运行时：每次请求创建 TutorAgent 实例并流式输出。"""

    async def stream_chat(
        self,
        *,
        user_id: int,
        user_message: str,
        session_id: str,
        image_urls: list[str] | None = None,
        file_urls: list[str] | None = None,
    ):
        from app.chat.agent import TutorAgent
        from app.chat.context import set_user_id

        set_user_id(user_id)
        # 每次请求创建新 Agent 实例
        agent = TutorAgent()
        try:
            async for chunk in agent.chat_stream(
                user_id=user_id,
                user_message=user_message,
                session_id=session_id,
                image_urls=image_urls,
                file_urls=file_urls,
            ):
                yield chunk
        finally:
            pass  # 清理资源


# 模块级单例
conversation_store = SqlConversationStore()  # 会话存储（委托 session_service）
tutor_chat_runtime = TutorChatRuntime()      # Agent 运行时


def _get_chat_usecases():
    """懒加载 ChatUseCases（避免循环导入）。"""
    from app.shared.storage import local_file_store
    return ChatUseCases(conversation_store=conversation_store, file_store=local_file_store)


chat_usecases = None  # 延迟初始化单例


def get_chat_usecases() -> ChatUseCases:
    """获取 ChatUseCases 单例（首次调用时创建）。"""
    global chat_usecases
    if chat_usecases is None:
        chat_usecases = _get_chat_usecases()
    return chat_usecases
