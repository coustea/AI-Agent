"""Resource-generation runtime."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

from app.ports.runtime import ResourceRuntime
from app.runtime.resource.coordinator import AGENT_REGISTRY, CoordinatorAgent
from app.runtime.resource.events import AgentEventEmitter


class ResourceGenerationRuntime(ResourceRuntime):
    def list_agents(self) -> list[dict]:
        return [
            {
                "id": name,
                "role": info.role,
                "desc": info.desc,
                "type": info.type,
            }
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
