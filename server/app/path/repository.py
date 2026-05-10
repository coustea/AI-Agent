"""Path planning repository.

提供学习路径规划相关的数据库访问操作。
"""

from __future__ import annotations

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.models import GeneratedResource


class PathRepository:
    async def get_latest_resource(self, session: AsyncSession, user_id: int) -> GeneratedResource | None:
        stmt = (
            select(GeneratedResource)
            .where(GeneratedResource.user_id == user_id)
            .order_by(GeneratedResource.created_at.desc())
            .limit(1)
        )
        result = await session.exec(stmt)
        return result.first()

    async def get_resource_by_id(
        self,
        session: AsyncSession,
        user_id: int,
        resource_id: int,
    ) -> GeneratedResource | None:
        resource = await session.get(GeneratedResource, resource_id)
        if resource is None or resource.user_id != user_id:
            return None
        return resource
