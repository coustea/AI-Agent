"""Runtime ports."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Protocol


class ChatRuntime(Protocol):
    async def stream_chat(
        self,
        *,
        user_id: int,
        user_message: str,
        session_id: str | None = None,
        image_urls: list[str] | None = None,
        file_urls: list[str] | None = None,
    ) -> AsyncGenerator[str, None]: ...

    async def aclose(self) -> None: ...


class ProfileRuntime(Protocol):
    async def build_profile(self, user_id: int, session_id: str | None = None) -> bool: ...

    async def extract_facts(self, user_id: int, session_id: str) -> bool: ...


class ResourceRuntime(Protocol):
    async def stream_bundle(
        self,
        *,
        user_id: int,
        task: dict,
        selected_resources: list[str] | None = None,
    ) -> AsyncGenerator[str, None]: ...

    def list_agents(self) -> list[dict]: ...

    async def aclose(self) -> None: ...
