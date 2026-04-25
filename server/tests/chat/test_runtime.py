from __future__ import annotations

import sys
from pathlib import Path

import pytest
from langchain_core.messages import HumanMessage

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.chat.runtime import prepare_tutor_turn


class FakeTutorContextService:
    async def build_profile_context(self, user_id: int) -> str:
        return f"profile:{user_id}"

    async def build_long_term_memory_context(self, user_id: int) -> str:
        return f"facts:{user_id}"

    async def build_recent_chat_context(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str,
        image_urls: list[str],
        file_urls: list[str],
    ):
        return [HumanMessage(content=user_message)], "recent context"

    @staticmethod
    def build_file_context(image_urls: list[str], file_urls: list[str]) -> str:
        return f"images={len(image_urls)} files={len(file_urls)}"


@pytest.mark.asyncio
async def test_prepare_tutor_turn_carries_need_diagram_state() -> None:
    prepared = await prepare_tutor_turn(
        ctx_service=FakeTutorContextService(),
        prompts={
            "direct_system": (
                "profile={profile_context} fact={fact_context} recent={recent_chat_context}"
            )
        },
        user_id=7,
        user_message="Explain TCP handshakes",
        session_id=None,
        image_urls=None,
        file_urls=None,
        enable_search=False,
        attachment_analysis=None,
        need_diagram=True,
    )

    assert prepared.initial_state["need_diagram"] is True
    assert prepared.initial_state["diagram"] is None
    assert prepared.initial_state["diagram_error"] is None
