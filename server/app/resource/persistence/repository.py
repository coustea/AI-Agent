"""Database-facing repository for the resource domain."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.models import GeneratedResource, GeneratedResourceItem as GeneratedResourceItemModel
from app.resource.persistence.mappers import content_envelope
from app.resource.schemas import AgentResult, ResourceGenerationRequest, TeachingPlan, ReviewResult


class ResourceRepository:
    """Owns resource persistence and write coordination."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._write_locks: dict[int, asyncio.Lock] = {}

    def _get_write_lock(self, resource_id: int) -> asyncio.Lock:
        if resource_id not in self._write_locks:
            self._write_locks[resource_id] = asyncio.Lock()
        return self._write_locks[resource_id]

    @staticmethod
    def release_write_lock(resource_id: int) -> None:
        """No-op: write locks are per-session-instance and auto-cleaned."""

    async def commit_refresh(self, obj: Any) -> None:
        try:
            await self.session.commit()
        except Exception as exc:
            await self.session.rollback()
            raise exc
        await self.session.refresh(obj)

    async def create_task(
        self,
        *,
        user_id: int,
        request: ResourceGenerationRequest,
        source: str,
    ) -> dict[str, Any]:
        resource = GeneratedResource(
            user_id=user_id,
            learning_need=request.learning_need,
            selected_agents=request.enabled_agent_ids(),
            agent_configs=request.agent_configs.model_dump(mode="json"),
            source=source,
            status="pending",
        )
        self.session.add(resource)
        try:
            await self.session.flush()
            resource_id = int(getattr(resource, "id", 0) or 0)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        await self.session.refresh(resource)
        return {
            "resource_id": resource_id,
            "status": "pending",
            "source": source,
        }

    async def update_resource_status(self, resource_id: int, status: str) -> None:
        async with self._get_write_lock(resource_id):
            resource = await self.session.get(GeneratedResource, resource_id)
            if resource:
                resource.status = status
                resource.updated_at = datetime.now(timezone.utc)
                await self.commit_refresh(resource)

    async def save_agent_result(
        self,
        *,
        resource_id: int,
        user_id: int,
        result: AgentResult,
        depends_on_agents: list[str] | None = None,
    ) -> GeneratedResourceItemModel:
        if not result.success or not result.content:
            raise ValueError("仅能保存已成功生成且含内容的资源")
        agent_id = str(result.metadata.get("agent_id") or "")
        title = result.title or f"{agent_id} 资源"
        content_json, content_text = content_envelope(result)
        resource_item = GeneratedResourceItemModel(
            resource_id=resource_id,
            user_id=user_id,
            agent_type=agent_id,
            content_format=result.file_type,
            title=title,
            summary=result.summary,
            generated_by=agent_id,
            content_json=content_json,
            content_text=content_text,
            metadata_json=result.metadata,
            metrics=result.metrics,
            downstream_context=result.downstream_context.model_dump(mode="json") if result.downstream_context else None,
            output_contract=result.downstream_context.schema_version if result.downstream_context else None,
            depends_on_agents=depends_on_agents or None,
            status="finished",
            updated_at=datetime.now(timezone.utc),
        )
        async with self._get_write_lock(resource_id):
            self.session.add(resource_item)
            await self.commit_refresh(resource_item)
        return resource_item

    async def list_resource_items(self, user_id: int, resource_id: int) -> list[GeneratedResourceItemModel]:
        statement = (
            select(GeneratedResourceItemModel)
            .where(GeneratedResourceItemModel.user_id == user_id)
            .where(GeneratedResourceItemModel.resource_id == resource_id)
            .order_by(col(GeneratedResourceItemModel.id).asc())
        )
        result = await self.session.exec(statement)
        return list(result.all())

    async def list_resource_type_summary(
        self,
        user_id: int,
        resource_ids: list[int],
    ) -> dict[int, list[str]]:
        if not resource_ids:
            return {}
        statement = (
            select(GeneratedResourceItemModel.resource_id, GeneratedResourceItemModel.agent_type)
            .where(GeneratedResourceItemModel.user_id == user_id)
            .where(col(GeneratedResourceItemModel.resource_id).in_(resource_ids))
            .order_by(
                col(GeneratedResourceItemModel.resource_id).asc(),
                col(GeneratedResourceItemModel.agent_type).asc(),
            )
        )
        result = await self.session.exec(statement)
        summary: dict[int, list[str]] = {resource_id: [] for resource_id in resource_ids}
        for resource_id, agent_type in result.all():
            if agent_type not in summary[resource_id]:
                summary[resource_id].append(agent_type)
        return summary

    async def save_generation_results(
        self,
        *,
        user_id: int,
        resource_id: int,
        request: ResourceGenerationRequest,
        results: dict[str, AgentResult],
        review_result: ReviewResult,
        teaching_plan: TeachingPlan,
    ) -> None:
        saved_items = await self.list_resource_items(user_id, resource_id)
        failed_agents = [agent_id for agent_id, result in results.items() if not result.success]
        for agent_id in review_result.failed_agents:
            if agent_id and agent_id not in failed_agents:
                failed_agents.append(agent_id)
        if not review_result.passed and "review" not in failed_agents:
            failed_agents.append("review")
        successful = len(saved_items)
        if failed_agents and successful:
            status = "partial_completed"
        elif failed_agents:
            status = "failed"
        else:
            status = "completed"
        async with self._get_write_lock(resource_id):
            resource = await self.session.get(GeneratedResource, resource_id)
            if resource is None or resource.user_id != user_id:
                raise ValueError("资源不存在或无权限")
            resource.teaching_plan = teaching_plan.model_dump(mode="json")
            resource.review_result = review_result.model_dump(mode="json")
            resource.failed_agents = failed_agents
            resource.workflow_metadata = {
                "selected_agents": request.enabled_agent_ids(),
            }
            resource.status = status
            resource.updated_at = datetime.now(timezone.utc)
            await self.commit_refresh(resource)

    async def get_resource(
        self,
        user_id: int,
        resource_id: int,
        *,
        allowed_sources: tuple[str, ...] | None = None,
    ) -> GeneratedResource | None:
        resource = await self.session.get(GeneratedResource, resource_id)
        if resource and resource.user_id == user_id and self._source_allowed(resource.source, allowed_sources):
            return resource
        return None

    async def list_resources(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
        *,
        sources: tuple[str, ...] | None = None,
    ) -> list[GeneratedResource]:
        statement = select(GeneratedResource).where(GeneratedResource.user_id == user_id)
        if sources:
            statement = statement.where(col(GeneratedResource.source).in_(sources))
        statement = statement.order_by(col(GeneratedResource.id).desc()).offset(offset).limit(limit)
        result = await self.session.exec(statement)
        return list(result.all())

    async def count_resources(
        self,
        user_id: int,
        *,
        sources: tuple[str, ...] | None = None,
    ) -> int:
        from sqlmodel import func

        statement = select(func.count(GeneratedResource.id)).where(GeneratedResource.user_id == user_id)
        if sources:
            statement = statement.where(col(GeneratedResource.source).in_(sources))
        result = await self.session.exec(statement)
        return result.one()

    @staticmethod
    def _source_allowed(source: str | None, allowed_sources: tuple[str, ...] | None) -> bool:
        if not allowed_sources:
            return True
        return (source or "standalone") in allowed_sources
