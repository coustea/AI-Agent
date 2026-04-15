"""Storage ports."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class FileStore(Protocol):
    def ensure_roots(self) -> None: ...

    async def save_upload(
        self,
        *,
        filename: str,
        content: bytes,
        user_id: int,
        session_id: str,
    ) -> dict: ...

    def resolve_user_file(
        self,
        *,
        current_user_id: int,
        owner_id: int,
        session_id: str,
        filename: str,
    ) -> Path: ...
