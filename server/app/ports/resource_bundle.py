"""Resource bundle ports."""

from __future__ import annotations

from typing import Protocol

from sqlmodel.ext.asyncio.session import AsyncSession


class ResourceBundleStore(Protocol):
    async def list_resources(
        self,
        session: AsyncSession,
        user_id: int,
        limit: int = 20,
    ) -> list: ...

    async def get_resource(
        self,
        session: AsyncSession,
        user_id: int,
        resource_id: int,
    ): ...
