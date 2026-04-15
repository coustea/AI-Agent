"""Resource persistence service."""

from __future__ import annotations

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.resource import GeneratedResource


class ResourceService:
    async def list_user_resources(
        self,
        session: AsyncSession,
        user_id: int,
        limit: int = 20,
    ) -> list[GeneratedResource]:
        stmt = (
            select(GeneratedResource)
            .where(GeneratedResource.user_id == user_id)
            .order_by(GeneratedResource.created_at.desc())
            .limit(limit)
        )
        result = await session.exec(stmt)
        return list(result.all())

    async def get_user_resource(
        self,
        session: AsyncSession,
        user_id: int,
        resource_id: int,
    ) -> GeneratedResource | None:
        resource = await session.get(GeneratedResource, resource_id)
        if resource is None or resource.user_id != user_id:
            return None
        return resource


resource_service = ResourceService()
