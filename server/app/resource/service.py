"""Public service seam for the resource domain — CRUD use cases only.

Orchestration entrypoint: app.resource.orchestrator
Path-domain helpers:     app.resource.path_helpers
"""

from __future__ import annotations

from typing import Any

from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.logging import get_module_logger
from app.resource.constants import STANDALONE_RESOURCE_SOURCES
from app.resource.events import resource_event_bus
from app.resource.persistence import (
    ResourceRepository,
    db_item_to_resource_item,
)
from app.resource.schemas import (
    AgentResult,
    GeneratedResourceItem,
    ResourceBundle,
    ResourceGenerationRequest,
    ReviewResult,
)
from app.resource.workflow.audit import (
    BUNDLE_AGENT_ID,
    PPT_AGENT_ID,
    PPT_REVIEW_AGENT_ID,
    PRE_REVIEW_AGENT_ID,
    VIDEO_AGENT_ID,
    VIDEO_REVIEW_AGENT_ID,
)
from app.resource.workflow.nodes import AGGREGATION_AGENT_IDS

logger = get_module_logger("resource", sub="service")


class ResourceService:
    """Public resource-domain use cases exposed to API and sibling domains."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = ResourceRepository(session)

    @staticmethod
    def release_write_lock(resource_id: int) -> None:
        ResourceRepository.release_write_lock(resource_id)

    async def start_resource_task(
        self,
        *,
        user_id: int,
        request: ResourceGenerationRequest,
        source: str = "standalone",
        profile: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self.repository.create_task(
            user_id=user_id,
            request=request,
            source=source,
        )

    async def get_generation_status(
        self,
        user_id: int,
        resource_id: int,
        *,
        allowed_sources: tuple[str, ...] | None = None,
    ) -> dict[str, Any] | None:
        resource = await self.repository.get_resource(user_id, resource_id, allowed_sources=allowed_sources)
        if resource is None:
            return None
        db_items = await self.repository.list_resource_items(user_id, resource_id)
        agent_snapshots = resource_event_bus.get_latest_snapshot(resource_id)
        merged_agent_snapshots = self._merge_persisted_items_into_snapshots(
            agent_snapshots.get("agent_snapshots", {}),
            db_items,
        )
        selected_agents = list(resource.selected_agents or [])
        return {
            "resource_id": resource_id,
            "status": resource.status,
            "selected_agents": selected_agents,
            "agent_snapshots": merged_agent_snapshots,
            "overall_progress": self._calculate_overall_progress(
                status=resource.status,
                selected_agents=selected_agents,
                agent_snapshots=merged_agent_snapshots,
            ),
            "current_message": agent_snapshots.get("current_message", ""),
            "resources": [
                db_item_to_resource_item(item).model_dump(mode="json")
                for item in db_items
            ],
        }

    async def update_resource_status(self, resource_id: int, status: str) -> None:
        await self.repository.update_resource_status(resource_id, status)

    async def list_resource_items(self, user_id: int, resource_id: int):
        return await self.repository.list_resource_items(user_id, resource_id)

    async def list_resource_type_summary(self, user_id: int, resource_ids: list[int]) -> dict[int, list[str]]:
        return await self.repository.list_resource_type_summary(user_id, resource_ids)

    async def save_agent_result(
        self,
        *,
        resource_id: int,
        user_id: int,
        result: AgentResult,
        depends_on_agents: list[str] | None = None,
    ):
        return await self.repository.save_agent_result(
            resource_id=resource_id,
            user_id=user_id,
            result=result,
            depends_on_agents=depends_on_agents,
        )

    async def results_for_review(
        self,
        user_id: int,
        resource_id: int,
        failures: dict[str, AgentResult],
    ) -> dict[str, AgentResult]:
        from app.resource.persistence import db_item_to_agent_result

        db_items = await self.repository.list_resource_items(user_id, resource_id)
        persisted = {
            item.agent_type: db_item_to_agent_result(item)
            for item in db_items
        }
        return {**persisted, **failures}

    async def save_generation_results(
        self,
        *,
        user_id: int,
        resource_id: int,
        request: ResourceGenerationRequest,
        results: dict[str, AgentResult],
        review_result: ReviewResult,
        teaching_plan,
    ) -> None:
        await self.repository.save_generation_results(
            user_id=user_id,
            resource_id=resource_id,
            request=request,
            results=results,
            review_result=review_result,
            teaching_plan=teaching_plan,
        )

    async def get_resource_bundle(
        self,
        user_id: int,
        resource_id: int,
        *,
        allowed_sources: tuple[str, ...] | None = None,
    ) -> ResourceBundle | None:
        resource = await self.repository.get_resource(user_id, resource_id, allowed_sources=allowed_sources)
        if resource is None:
            return None

        db_items = await self.repository.list_resource_items(user_id, resource_id)
        review_result = (
            ReviewResult.model_validate(resource.review_result)
            if isinstance(resource.review_result, dict)
            else None
        )
        metadata = {
            "source": "database",
            "failed_agents": resource.failed_agents or [],
            "teaching_plan": resource.teaching_plan or {},
        }
        return ResourceBundle(
            id=str(resource.id),
            task_id=str(resource.id),
            title="个性化学习资源包",
            learning_need=resource.learning_need or "",
            selected_agents=resource.selected_agents or [],
            resources=[db_item_to_resource_item(item) for item in db_items],
            review_result=review_result,
            status=resource.status,
            created_at=resource.created_at.isoformat() if resource.created_at else "",
            updated_at=resource.updated_at.isoformat() if resource.updated_at else "",
            metadata=metadata,
        )

    async def get_resource(
        self,
        user_id: int,
        resource_id: int,
        *,
        allowed_sources: tuple[str, ...] | None = None,
    ):
        return await self.repository.get_resource(user_id, resource_id, allowed_sources=allowed_sources)

    async def list_resources(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
        *,
        sources: tuple[str, ...] | None = None,
    ):
        return await self.repository.list_resources(user_id, limit, offset, sources=sources)

    async def count_resources(
        self,
        user_id: int,
        *,
        sources: tuple[str, ...] | None = None,
    ) -> int:
        return await self.repository.count_resources(user_id, sources=sources)

    @staticmethod
    def _merge_persisted_items_into_snapshots(
        agent_snapshots: dict[str, Any],
        db_items: list[Any],
    ) -> dict[str, Any]:
        merged = {
            agent_id: dict(snapshot)
            for agent_id, snapshot in agent_snapshots.items()
        }
        for item in db_items:
            previous = dict(merged.get(item.agent_type, {}))
            previous.update({
                "event_type": previous.get("event_type", "agent.artifact_ready"),
                "agent_id": item.agent_type,
                "status": "finished",
                "message": previous.get("message") or f"{item.agent_type} 资源已保存，可在产物坞预览",
                "progress": 100,
                "phase": "artifact_saved",
                "artifact_id": str(item.id),
            })
            merged[item.agent_type] = previous
        return merged

    @staticmethod
    def _calculate_overall_progress(
        *,
        status: str | None,
        selected_agents: list[str],
        agent_snapshots: dict[str, Any],
    ) -> int:
        if status in {"completed", "partial_completed"}:
            return 100
        if status == "pending" and not agent_snapshots:
            return 0

        def progress_for(agent_id: str) -> int:
            raw = agent_snapshots.get(agent_id, {}).get("progress", 0)
            try:
                return max(0, min(100, int(raw)))
            except (TypeError, ValueError):
                return 0

        worker_agents = [
            agent_id
            for agent_id in selected_agents
            if agent_id not in AGGREGATION_AGENT_IDS
        ]
        stages = [
            (15, progress_for("planning")),
        ]
        if worker_agents:
            stages.append((
                45,
                round(sum(progress_for(agent_id) for agent_id in worker_agents) / len(worker_agents)),
            ))
        stages.append((10, progress_for(PRE_REVIEW_AGENT_ID)))
        stages.append((10, progress_for(BUNDLE_AGENT_ID)))
        if PPT_AGENT_ID in selected_agents:
            stages.extend([
                (15, progress_for(PPT_AGENT_ID)),
                (5, progress_for(PPT_REVIEW_AGENT_ID)),
            ])
        if VIDEO_AGENT_ID in selected_agents:
            stages.extend([
                (15, progress_for(VIDEO_AGENT_ID)),
                (5, progress_for(VIDEO_REVIEW_AGENT_ID)),
            ])
        weight_total = sum(weight for weight, _ in stages)
        if weight_total <= 0:
            return 0
        return max(0, min(100, round(sum(weight * progress for weight, progress in stages) / weight_total)))


__all__ = [
    "ResourceService",
]
