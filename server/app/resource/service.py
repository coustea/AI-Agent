"""
资源生成服务层。

整合新架构：ResourceWorkflow + Workspace + TraceLog
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
from app.resource.schemas import ResourceGenerationRequest
from app.resource.orchestrator import ResourceWorkflow
from app.resource.registry import ensure_initialized, get_enabled_agent_ids, get_agent_entry

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
        except Exception:
            await self.session.rollback()
            raise
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
            except Exception:
                await self.session.rollback()
                raise
            await self.session.refresh(resource)

    async def save_resource_item(
        self,
        resource_id: int,
        user_id: int,
        item: schemas.GeneratedResourceItem,
    ) -> GeneratedResourceItemModel:
        """保存生成资源明细到数据库。"""
        # 兼容当前表结构：把标题/摘要/结构化摘要一起落到 content_json，避免刷新后丢字段
        content_json, content_text = self._split_item_content(item)
        resource_item = GeneratedResourceItemModel(
            resource_id=resource_id,
            user_id=user_id,
            agent_type=item.type.value,
            content_format=item.format,
            content_json=content_json,
            content_text=content_text,
            execution_report=item.execution_report,
            status="completed",
            updated_at=datetime.now(timezone.utc),
        )
        self.session.add(resource_item)
        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
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
        workflow = ResourceWorkflow(
            emitter=emitter,
            resource_store=self.usecases,
        )

        async def _run_workflow() -> dict[str, Any]:
            try:
                result = await workflow.run(
                    user_id=user_id,
                    request=request,
                )
                if not result.get("success"):
                    await emitter.emit_error(task_id="unknown", message=result.get("error", "生成失败"))
                return result
            finally:
                await emitter.close()

        workflow_task = asyncio.create_task(_run_workflow())
        try:
            async for event in emitter.stream():
                yield event
        finally:
            await workflow_task

    def list_agents(self) -> list[dict[str, Any]]:
        """列出可用 Agent。"""
        ensure_initialized()
        agent_ids = get_enabled_agent_ids()
        agents: list[dict[str, Any]] = []

        for agent_id in agent_ids:
            entry = get_agent_entry(agent_id)
            if entry:
                agents.append({
                    "id": agent_id,
                    "name": entry.agent_class.__name__,
                    "role": entry.role,
                    "description": entry.description,
                    "dependencies": entry.dependencies,
                    "execution_layer": entry.execution_layer,
                    "configurable": True,
                })

        return agents


async def get_resource_usecases(session: AsyncSession) -> ResourceUsecases:
    """获取 ResourceUsecases 实例。"""
    return ResourceUsecases(session)


async def get_stream_service(session: AsyncSession) -> ResourceStreamService:
    """获取 ResourceStreamService 实例。"""
    return ResourceStreamService(session)
