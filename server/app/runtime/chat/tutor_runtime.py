"""Tutor chat runtime."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from app.agents.chat import build_tutor_agent
from app.ports.runtime import ChatRuntime


class TutorChatRuntime(ChatRuntime):
    async def stream_chat(
        self,
        *,
        user_id: int,
        user_message: str,
        session_id: str | None = None,
        image_urls: list[str] | None = None,
        file_urls: list[str] | None = None,
    ) -> AsyncGenerator[str, None]:
        agent = build_tutor_agent()
        async for chunk in agent.chat_stream(
            user_id=user_id,
            user_message=user_message,
            session_id=session_id,
            image_urls=image_urls,
            file_urls=file_urls,
        ):
            yield chunk

    async def aclose(self) -> None:
        agent = build_tutor_agent()
        await agent.wait_for_background_tasks()
        if hasattr(agent, "plugin_manager"):
            await agent.plugin_manager.aclose()
