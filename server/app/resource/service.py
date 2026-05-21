"""
资源生成服务层。

整合资源生成工作流、数据库资源记录和 SSE 输出。
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.models import GeneratedResource, GeneratedResourceItem as GeneratedResourceItemModel
from app.resource import schemas
from app.resource.events import AgentEventEmitter
from app.resource.schemas import (
    ExecutionPlan,
    GeneratedResourceItem,
    ResourceBundle,
    ResourceGenerationRequest,
    ReviewResult,
    StudyPathStep,
    WorkerResult,
)
from app.resource.workflow import ResourceGenerationWorkflow
from app.infra.logging import get_logger

logger = get_logger(__name__)


class ResourceUsecases:
    """资源生成用例。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_resource(
        self,
        user_id: int,
        request: ResourceGenerationRequest,
    ) -> GeneratedResource:
        """创建资源记录。"""
        resource = GeneratedResource(
            user_id=user_id,
            learning_need=request.learning_need,
            personalization={},
            selected_agents=request.enabled_agent_ids(),
            agent_configs=request.agent_configs.model_dump(mode="json"),
            status="pending",
        )
        self.session.add(resource)
        try:
            await self.session.commit()
        except Exception as exc:
            await self.session.rollback()
            raise exc
        await self.session.refresh(resource)
        return resource

    async def update_resource_status(
        self,
        resource_id: int,
        status: str,
    ) -> None:
        """更新资源状态。"""
        resource = await self.session.get(GeneratedResource, resource_id)
        if resource:
            resource.status = status
            resource.updated_at = datetime.now(timezone.utc)
            try:
                await self.session.commit()
            except Exception as exc:
                await self.session.rollback()
                raise exc
            await self.session.refresh(resource)

    async def save_resource_item(
        self,
        resource_id: int,
        user_id: int,
        item: schemas.GeneratedResourceItem,
    ) -> GeneratedResourceItemModel:
        """保存生成资源明细到数据库。"""
        content_json, content_text = self._split_item_content(item)
        resource_item = GeneratedResourceItemModel(
            resource_id=resource_id,
            user_id=user_id,
            agent_type=item.type.value,
            content_format=item.format,
            title=item.title,
            summary=item.summary,
            generated_by=item.type.value,
            content_json=content_json,
            content_text=content_text,
            metadata_json=item.metadata,
            execution_report=item.execution_report,
            status="completed",
            updated_at=datetime.now(timezone.utc),
        )
        self.session.add(resource_item)
        try:
            await self.session.commit()
        except Exception as exc:
            await self.session.rollback()
            raise exc
        await self.session.refresh(resource_item)
        return resource_item

    async def list_resource_items(
        self,
        user_id: int,
        resource_id: int,
    ) -> list[GeneratedResourceItemModel]:
        """列出指定资源的资源明细。"""
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
        """按资源汇总已保存的 Agent 类型。"""
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

    def _split_item_content(
        self,
        item: schemas.GeneratedResourceItem,
    ) -> tuple[dict[str, Any] | None, str | None]:
        fmt = item.format.lower()
        content = item.content
        envelope = {
            "title": item.title,
            "summary": item.summary,
            "summary_data": item.summary_data,
            "metadata": item.metadata,
            "format": item.format,
            "content": content,
        }
        if fmt in {"markdown", "mermaid", "text", "code"}:
            if isinstance(content, str):
                return envelope, content
            return envelope, json.dumps(content, ensure_ascii=False)
        if fmt == "json":
            if isinstance(content, dict):
                envelope["content"] = content
                return envelope, None
            if isinstance(content, list):
                envelope["content"] = {"items": content}
                return envelope, None
            if isinstance(content, str):
                try:
                    parsed = json.loads(content)
                except json.JSONDecodeError:
                    return envelope, content
                if isinstance(parsed, dict):
                    envelope["content"] = parsed
                    return envelope, None
                if isinstance(parsed, list):
                    envelope["content"] = {"items": parsed}
                    return envelope, None
                envelope["content"] = {"value": parsed}
                return envelope, None
            envelope["content"] = {"value": content}
            return envelope, None
        if isinstance(content, str):
            return envelope, content
        envelope["content"] = {"value": content}
        return envelope, None

    async def save_generation_results(
        self,
        *,
        user_id: int,
        resource_id: int,
        request: ResourceGenerationRequest,
        results: dict[str, WorkerResult],
        review_result: ReviewResult,
        study_path: list[StudyPathStep],
        plan: ExecutionPlan,
    ) -> None:
        """保存一次完整多智能体资源生成的结果。"""
        successful_results = [result for result in results.values() if result.success and result.content]
        for result in successful_results:
            await self.save_resource_item(
                resource_id=resource_id,
                user_id=user_id,
                item=self._to_resource_item(resource_id=resource_id, result=result),
            )

        failed_agents = [agent_id for agent_id, result in results.items() if not result.success]
        status = self._resolve_generation_status(
            successful_count=len(successful_results),
            failed_count=len(failed_agents),
        )
        resource = await self.session.get(GeneratedResource, resource_id)
        if resource is None or resource.user_id != user_id:
            raise ValueError("资源不存在或无权限")

        resource.status = status
        resource.updated_at = datetime.now(timezone.utc)
        resource.personalization = {
            "review_result": review_result.model_dump(mode="json"),
            "study_path": [step.model_dump(mode="json") for step in study_path],
            "execution_plan": plan.model_dump(mode="json"),
            "failed_agents": failed_agents,
            "selected_agents": request.enabled_agent_ids(),
        }
        try:
            await self.session.commit()
        except Exception as exc:
            await self.session.rollback()
            raise exc
        await self.session.refresh(resource)

    def _resolve_generation_status(self, *, successful_count: int, failed_count: int) -> str:
        if failed_count and successful_count:
            return "partial_completed"
        if failed_count and not successful_count:
            return "failed"
        return "completed"

    def _to_resource_item(self, *, resource_id: int, result: WorkerResult) -> GeneratedResourceItem:
        agent_id = str(result.metadata.get("agent_id") or "")
        return GeneratedResourceItem(
            id=f"{resource_id}-{agent_id}" if agent_id else "",
            type=agent_id,
            title=result.title or f"{agent_id} 资源",
            format=result.file_type,
            content=result.content,
            summary=result.summary,
            summary_data=result.summary_data,
            metadata=result.metadata,
        )

    async def get_resource_bundle(
        self,
        user_id: int,
        resource_id: int,
    ) -> ResourceBundle | None:
        """从数据库读取并组装前端资源包。"""
        resource = await self.get_resource(user_id, resource_id)
        if resource is None:
            return None

        db_items = await self.list_resource_items(user_id, resource_id)
        workflow_data = resource.personalization if isinstance(resource.personalization, dict) else {}
        review_data = workflow_data.get("review_result")
        study_path_data = workflow_data.get("study_path") or []

        review_result = ReviewResult.model_validate(review_data) if isinstance(review_data, dict) else None
        study_path = [
            StudyPathStep.model_validate(step)
            for step in study_path_data
            if isinstance(step, dict)
        ]

        metadata = {
            "source": "database",
            "failed_agents": workflow_data.get("failed_agents") or [],
        }
        if isinstance(workflow_data.get("execution_plan"), dict):
            metadata["execution_plan"] = workflow_data["execution_plan"]

        return ResourceBundle(
            id=str(resource.id),
            task_id=str(resource.id),
            title="个性化学习资源包",
            learning_need=resource.learning_need or "",
            selected_agents=resource.selected_agents or [],
            resources=[self._db_item_to_resource_item(item) for item in db_items],
            study_path=study_path,
            review_result=review_result,
            status=resource.status,
            created_at=resource.created_at.isoformat() if resource.created_at else "",
            updated_at=resource.updated_at.isoformat() if resource.updated_at else "",
            metadata=metadata,
        )

    def _db_item_to_resource_item(self, item: GeneratedResourceItemModel) -> GeneratedResourceItem:
        envelope = item.content_json if isinstance(item.content_json, dict) else {}
        content = envelope.get("content") if item.content_json is not None else item.content_text
        return GeneratedResourceItem(
            id=str(item.id),
            type=item.agent_type,
            title=envelope.get("title") or item.title or f"学习资源 - {item.agent_type}",
            format=envelope.get("format") or item.content_format,
            content=content,
            summary=envelope.get("summary") or item.summary or "",
            summary_data=envelope.get("summary_data") or {},
            execution_report=item.execution_report,
            metadata=envelope.get("metadata") or item.metadata_json or {},
        )

    async def get_resource(
        self,
        user_id: int,
        resource_id: int,
    ) -> GeneratedResource | None:
        """获取资源详情。"""
        resource = await self.session.get(GeneratedResource, resource_id)
        if resource and resource.user_id == user_id:
            return resource
        return None

    async def list_resources(
        self,
        user_id: int,
        limit: int = 20,
    ) -> list[GeneratedResource]:
        """列出用户资源。"""
        statement = (
            select(GeneratedResource)
            .where(GeneratedResource.user_id == user_id)
            .order_by(col(GeneratedResource.id).desc())
            .limit(limit)
        )
        result = await self.session.exec(statement)
        return list(result.all())


class ResourceStreamService:
    """资源生成流式服务。"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.usecases = ResourceUsecases(session)

    async def stream_bundle(
        self,
        user_id: int,
        request: ResourceGenerationRequest,
    ) -> AsyncGenerator[str, None]:
        """流式生成资源包。"""
        emitter = AgentEventEmitter()
        workflow = ResourceGenerationWorkflow(
            emitter=emitter,
            resource_service=self.usecases,
        )

        async def _run_workflow() -> dict[str, Any]:
            return await workflow.run(
                user_id=user_id,
                request=request,
            )

        workflow_task = asyncio.create_task(_run_workflow())
        try:
            async for event in emitter.stream():
                yield event
        finally:
            await workflow_task

    def list_agents(self) -> list[dict[str, Any]]:
        """列出可用 Agent。"""
        from app.resource.schemas import AGENT_META, AGENT_DEFAULT_ORDER

        agents: list[dict[str, Any]] = []
        for agent_id in AGENT_DEFAULT_ORDER:
            meta = AGENT_META.get(agent_id, {})
            agents.append({
                "id": agent_id,
                "name": meta.get("name", agent_id),
                "icon": meta.get("icon", ""),
                "description": meta.get("description", ""),
                "configurable": True,
            })

        return agents


async def get_resource_usecases(session: AsyncSession) -> ResourceUsecases:
    """获取 ResourceUsecases 实例。"""
    return ResourceUsecases(session)


async def get_stream_service(session: AsyncSession) -> ResourceStreamService:
    """获取 ResourceStreamService 实例。"""
    return ResourceStreamService(session)
