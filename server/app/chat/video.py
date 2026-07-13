"""Explicit chat video tasks.

This module deliberately does not participate in TutorAgent tool construction.
Only the HTTP endpoint initiated by a user can create a task; ToolExcute is used
as the project's execution boundary after that explicit request is accepted.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from sqlmodel import select

from app.chat.context_builder import build_user_content
from app.chat.memory.service import get_chat_memory_service
from app.infra.database import session_scope
from app.infra.models import ChatMessage, ChatSession
from app.infra.tool_excute import Tool, ToolExcute
from app.shared.cartoon.service import CartoonService


class GenerateChatVideoArgs(BaseModel):
    """Arguments accepted by the explicit chat-video execution tool."""

    topic: str = Field(min_length=1, max_length=500)


class ChatVideoService:
    """Persist and execute an explicit cartoon task attached to one user message."""

    def __init__(self, *, cartoon_service: CartoonService | None = None) -> None:
        self._cartoon_service = cartoon_service or CartoonService()

    async def create_task(
        self,
        *,
        user_id: int,
        session_id: str,
        topic: str,
    ) -> dict[str, Any]:
        normalized_topic = topic.strip()
        if not normalized_topic:
            raise ValueError("请输入视频主题")

        message = await get_chat_memory_service().save_message(
            user_id=user_id,
            session_id=session_id,
            role="user",
            content=build_user_content(normalized_topic, []),
            usage_metadata={"video": {"status": "queued", "topic": normalized_topic}},
        )
        if message.id is None:
            raise RuntimeError("视频任务消息保存失败")

        task_id = f"chat-video-{message.id}"
        video = {"task_id": task_id, "status": "queued", "topic": normalized_topic}
        await self._set_video_state(
            user_id=user_id,
            session_id=session_id,
            message_id=message.id,
            video=video,
        )
        return {"user_message_id": message.id, "session_id": session_id, "video": video}

    async def run_task(
        self,
        *,
        user_id: int,
        username: str,
        session_id: str,
        user_message_id: int,
        topic: str,
    ) -> None:
        task_id = f"chat-video-{user_message_id}"
        await self._set_video_state(
            user_id=user_id,
            session_id=session_id,
            message_id=user_message_id,
            video={"task_id": task_id, "status": "running", "topic": topic},
        )

        async def generate_chat_video(topic: str) -> dict[str, Any]:
            artifact = await self._cartoon_service.generate_for_chat(
                topic=topic,
                username=username,
                session_id=session_id,
                message_id=user_message_id,
            )
            return {
                "title": artifact.title,
                "video_url": artifact.video_url,
                "preview_url": artifact.preview_url,
                "duration_seconds": artifact.duration_seconds,
                "scene_count": artifact.scene_count,
            }

        executor = ToolExcute(tools=[
            Tool(
                name="generate_chat_video",
                description="Generate an educational cartoon video after an explicit user request.",
                args_model=GenerateChatVideoArgs,
                handler=generate_chat_video,
            ),
        ])
        try:
            result = await executor.execute({
                "id": task_id,
                "name": "generate_chat_video",
                "args": {"topic": topic},
            })
        except Exception:
            await self._set_video_state(
                user_id=user_id,
                session_id=session_id,
                message_id=user_message_id,
                video={
                    "task_id": task_id,
                    "status": "failed",
                    "topic": topic,
                    "error": "视频生成失败，请重新发起请求。",
                },
            )
            raise

        await self._set_video_state(
            user_id=user_id,
            session_id=session_id,
            message_id=user_message_id,
            video={"task_id": task_id, "status": "completed", "topic": topic, **result},
        )

    async def get_task(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message_id: int,
    ) -> dict[str, Any] | None:
        async with session_scope() as db:
            message = (await db.exec(
                select(ChatMessage)
                .join(ChatSession, ChatSession.id == ChatMessage.session_id)
                .where(
                    ChatMessage.id == user_message_id,
                    ChatMessage.session_id == session_id,
                    ChatMessage.role == "user",
                    ChatSession.user_id == user_id,
                )
            )).first()
            if message is None or not isinstance(message.usage_metadata, dict):
                return None
            video = message.usage_metadata.get("video")
            return dict(video) if isinstance(video, dict) else None

    async def _set_video_state(
        self,
        *,
        user_id: int,
        session_id: str,
        message_id: int,
        video: dict[str, Any],
    ) -> None:
        async with session_scope() as db:
            message = (await db.exec(
                select(ChatMessage)
                .join(ChatSession, ChatSession.id == ChatMessage.session_id)
                .where(
                    ChatMessage.id == message_id,
                    ChatMessage.session_id == session_id,
                    ChatMessage.role == "user",
                    ChatSession.user_id == user_id,
                )
            )).first()
            if message is None:
                raise ValueError("视频任务消息不存在或无权限")
            metadata = dict(message.usage_metadata or {})
            metadata["video"] = video
            message.usage_metadata = metadata
            db.add(message)
            await db.commit()


_chat_video_service: ChatVideoService | None = None


def get_chat_video_service() -> ChatVideoService:
    global _chat_video_service
    if _chat_video_service is None:
        _chat_video_service = ChatVideoService()
    return _chat_video_service
