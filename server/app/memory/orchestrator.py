"""Memory orchestration for post-chat pipelines.

This module centralizes memory extraction, profile refresh, and compression
triggering so chat-facing services keep a small responsibility surface.
"""

from __future__ import annotations

from typing import Protocol

from app.config import PROFILE_GATE_EVERY_N_ASSISTANT_TURNS
from app.infra.logging import get_logger
from app.memory.service import (
    MEMORY_COMPRESSION_TOKEN_THRESHOLD,
    MEMORY_EXTRACTION_TOKEN_THRESHOLD,
    memory_service,
)
from app.profile import build_fact_extraction_service, build_profile_building_service
from app.profile.fact_extraction import FactExtractionService
from app.profile.profile_building import ProfileBuildingService

logger = get_logger(__name__)


class MemoryBackends(Protocol):
    async def accumulate_session_tokens(
        self, user_id: int, session_id: str, module: str, content: str
    ) -> tuple[int, int]:
        ...

    async def should_trigger_memory_extraction(
        self, user_id: int, session_id: str, module: str, threshold: int
    ) -> bool:
        ...

    async def reset_memory_extraction_counter(self, user_id: int, session_id: str, module: str) -> None:
        ...

    async def reset_profile_update_counter(self, user_id: int, session_id: str, module: str) -> None:
        ...

    async def get_recent_messages(
        self,
        user_id: int,
        session_id: str,
        module: str,
        limit: int | None = None,
        days: int = 7,
        only_unexpired: bool = True,
    ) -> list:
        ...

    async def summarize_and_compress(
        self, user_id: int, session_id: str, module: str, threshold: int
    ) -> None:
        ...


class PostChatMemoryOrchestrator:
    """Coordinates post-chat memory and profile maintenance."""

    def __init__(
        self,
        *,
        module_name: str,
        memory: MemoryBackends = memory_service,
        fact_extraction: FactExtractionService | None = None,
        profile_building: ProfileBuildingService | None = None,
    ) -> None:
        self.module_name = module_name
        self.memory = memory
        self.fact_extraction = fact_extraction or build_fact_extraction_service(module_name=module_name)
        self.profile_building = profile_building or build_profile_building_service(module_name=module_name)

    async def run(self, *, user_id: int, session_id: str, user_message: str, assistant_reply: str) -> None:
        """Run memory extraction -> profile refresh -> compression pipeline."""
        logger.debug("[%s] Orchestrator start user=%s session=%s", self.module_name, user_id, session_id)
        await self.memory.accumulate_session_tokens(
            user_id=user_id,
            session_id=session_id,
            module=self.module_name,
            content=f"{user_message}\n{assistant_reply}",
        )
        await self._try_extract_memory(user_id=user_id, session_id=session_id)
        await self._try_update_profile(user_id=user_id, session_id=session_id)
        await self._try_compress_memory(user_id=user_id, session_id=session_id)
        logger.debug("[%s] Orchestrator done user=%s session=%s", self.module_name, user_id, session_id)

    async def _try_extract_memory(self, *, user_id: int, session_id: str) -> None:
        should_trigger = await self.memory.should_trigger_memory_extraction(
            user_id=user_id,
            session_id=session_id,
            module=self.module_name,
            threshold=MEMORY_EXTRACTION_TOKEN_THRESHOLD,
        )
        logger.info(
            "[%s] Memory extraction check user=%s session=%s trigger=%s",
            self.module_name,
            user_id,
            session_id,
            should_trigger,
        )
        if not should_trigger:
            return

        success = await self.fact_extraction.extract_and_save(user_id=user_id, session_id=session_id)
        if success:
            await self.memory.reset_memory_extraction_counter(
                user_id=user_id,
                session_id=session_id,
                module=self.module_name,
            )
            logger.debug("[%s] Memory extraction success user=%s session=%s", self.module_name, user_id, session_id)
            return
        logger.warning("[%s] Memory extraction returned no update user=%s session=%s", self.module_name, user_id, session_id)

    async def _try_update_profile(self, *, user_id: int, session_id: str) -> None:
        recent_msgs = await self.memory.get_recent_messages(
            user_id=user_id,
            session_id=session_id,
            module=self.module_name,
            limit=80,
        )
        assistant_turns = sum(1 for msg in recent_msgs if getattr(msg, "role", "") == "assistant")
        if assistant_turns == 0 or assistant_turns % PROFILE_GATE_EVERY_N_ASSISTANT_TURNS != 0:
            logger.debug(
                "[%s] Profile refresh skipped user=%s session=%s assistant_turns=%s",
                self.module_name,
                user_id,
                session_id,
                assistant_turns,
            )
            return

        dialogue_msgs = [
            msg
            for msg in recent_msgs
            if getattr(msg, "role", "") in {"user", "assistant"} and getattr(msg, "content", "").strip()
        ]
        if not dialogue_msgs:
            logger.debug("[%s] Profile refresh skipped user=%s session=%s empty_dialogue", self.module_name, user_id, session_id)
            return

        success, updated = await self.profile_building.build_profile(user_id=user_id, session_id=session_id)
        if success:
            await self.memory.reset_profile_update_counter(
                user_id=user_id,
                session_id=session_id,
                module=self.module_name,
            )
            logger.debug(
                "[%s] Profile refresh finished user=%s session=%s updated=%s",
                self.module_name,
                user_id,
                session_id,
                updated,
            )
            return
        logger.warning("[%s] Profile refresh failed user=%s session=%s", self.module_name, user_id, session_id)

    async def _try_compress_memory(self, *, user_id: int, session_id: str) -> None:
        await self.memory.summarize_and_compress(
            user_id=user_id,
            session_id=session_id,
            module=self.module_name,
            threshold=MEMORY_COMPRESSION_TOKEN_THRESHOLD,
        )
        logger.debug("[%s] Memory compression done user=%s session=%s", self.module_name, user_id, session_id)
