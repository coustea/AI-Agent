"""Resource bundle repository adapter."""

from __future__ import annotations

from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.resource.resource_service import resource_service
from app.ports.resource_bundle import ResourceBundleStore


class SqlResourceBundleStore(ResourceBundleStore):
    async def list_resources(
        self,
        session: AsyncSession,
        user_id: int,
        limit: int = 20,
    ) -> list:
        return await resource_service.list_user_resources(session, user_id, limit)

    async def get_resource(
        self,
        session: AsyncSession,
        user_id: int,
        resource_id: int,
    ):
        return await resource_service.get_user_resource(session, user_id, resource_id)
