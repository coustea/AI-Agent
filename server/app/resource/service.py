"""
Resource service — 资源生成全流程：持久化 + 编排 + SSE 推送。
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.models import GeneratedResource
from app.infra.logging import get_logger
from app.resource.coordinator import AGENT_REGISTRY, CoordinatorAgent
from app.resource.events import AgentEventEmitter

logger = get_logger(__name__)


class ResourceService:
    """GeneratedResource 持久化 CRUD。"""

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


class ResourceGenerationRuntime:
    """资源生成运行时：DAG 编排 + SSE 推送。"""

    def list_agents(self) -> list[dict]:
        return [
            {"id": name, "role": info.role, "desc": info.desc, "type": info.type}
            for name, info in AGENT_REGISTRY.items()
        ]

    async def stream_bundle(
        self,
        *,
        user_id: int,
        task: dict,
        selected_resources: list[str] | None = None,
    ) -> AsyncGenerator[str, None]:
        emitter = AgentEventEmitter()
        coordinator = CoordinatorAgent(emitter)

        async def run_and_cleanup() -> None:
            try:
                await coordinator.run(
                    user_id=user_id,
                    task=task,
                    selected_resources=selected_resources,
                )
            except Exception as exc:
                await emitter.emit_agent_error("system", str(exc))
                await emitter.emit_done("资源生成异常终止")
            finally:
                await self._cleanup_plugins()

        runner = asyncio.create_task(run_and_cleanup())
        try:
            async for chunk in emitter.stream():
                yield chunk
        finally:
            await runner

    async def _cleanup_plugins(self) -> None:
        close_tasks = []
        for entry in AGENT_REGISTRY.values():
            agent = getattr(entry, "agent", None)
            plugin_manager = getattr(agent, "plugin_manager", None)
            if plugin_manager is not None and hasattr(plugin_manager, "aclose"):
                close_tasks.append(plugin_manager.aclose())
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)

    async def aclose(self) -> None:
        await self._cleanup_plugins()


class ResourceUseCases:
    """资源相关用例。"""

    def __init__(self, resource_svc: ResourceService, runtime: ResourceGenerationRuntime) -> None:
        self.resource_svc = resource_svc
        self.runtime = runtime

    async def stream_bundle(
        self,
        *,
        user_id: int,
        task: dict,
        selected_resources: list[str] | None = None,
    ):
        async for chunk in self.runtime.stream_bundle(
            user_id=user_id,
            task=task,
            selected_resources=selected_resources,
        ):
            yield chunk

    def list_agents(self) -> list[dict]:
        return self.runtime.list_agents()

    async def list_resources(self, session: AsyncSession, user_id: int, limit: int = 20):
        return await self.resource_svc.list_user_resources(session, user_id, limit)

    async def get_resource(self, session: AsyncSession, user_id: int, resource_id: int):
        return await self.resource_svc.get_user_resource(session, user_id, resource_id)


# 模块级单例
resource_service = ResourceService()
resource_runtime = ResourceGenerationRuntime()
resource_usecases = ResourceUseCases(resource_service, resource_runtime)
