"""Resource use cases."""

from __future__ import annotations

from sqlmodel.ext.asyncio.session import AsyncSession

from app.ports.resource_bundle import ResourceBundleStore
from app.ports.runtime import ResourceRuntime


class ResourceUseCases:
    def __init__(self, bundle_store: ResourceBundleStore, resource_runtime: ResourceRuntime) -> None:
        self.bundle_store = bundle_store
        self.resource_runtime = resource_runtime

    async def stream_bundle(
        self,
        *,
        user_id: int,
        task: dict,
        selected_resources: list[str] | None = None,
    ):
        async for chunk in self.resource_runtime.stream_bundle(
            user_id=user_id,
            task=task,
            selected_resources=selected_resources,
        ):
            yield chunk

    def list_agents(self) -> list[dict]:
        return self.resource_runtime.list_agents()

    async def list_resources(self, session: AsyncSession, user_id: int, limit: int = 20):
        return await self.bundle_store.list_resources(session, user_id, limit)

    async def get_resource(self, session: AsyncSession, user_id: int, resource_id: int):
        return await self.bundle_store.get_resource(session, user_id, resource_id)
