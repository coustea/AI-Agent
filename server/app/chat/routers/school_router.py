"""学校搜索路由（onboarding 流程使用）。"""

from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.database import engine
from app.infra.models import School
from app.infra.response import HttpResponse


def register_school_routes(router: APIRouter) -> None:
    """将学校搜索端点注册到给定 router。"""

    @router.get("/schools/search")
    async def search_schools(
        keyword: str = Query(default="", min_length=0, max_length=50),
        limit: int = Query(default=20, ge=1, le=100),
    ):
        async with AsyncSession(engine, expire_on_commit=False) as session:
            if keyword:
                stmt = (
                    select(School)
                    .where(School.name.contains(keyword))
                    .order_by(School.name)
                    .limit(limit)
                )
            else:
                stmt = select(School).order_by(School.id.desc()).limit(limit)

            schools = (await session.exec(stmt)).scalars().all()

        return HttpResponse.success(data=[
            {
                "id": school.id,
                "name": school.name,
                "level": school.tier or school.level,
                "tier": school.tier,
            }
            for school in schools
        ])