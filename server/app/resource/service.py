"""
资源生成服务层。

整合新架构：ResourceWorkflow + Workspace + TraceLog
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncGenerator

from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.logging import get_logger
from app.infra.models import GeneratedResource
from app.resource.events import AgentEventEmitter
from app.resource.schemas import LearningTask
from app.resource.utils import get_agent_registry
from app.resource.graph import ResourceWorkflow
from app.shared.paths import RESOURCE_DIR

logger = get_logger(__name__)


class ResourceUsecases:
    """资源生成用例 — 封装业务逻辑。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_resource(
        self,
        user_id: int,
        course: str,
        gap: str,
        need: str,
        request_extra: str,
    ) -> GeneratedResource:
        """创建资源记录。"""
        resource = GeneratedResource(
            user_id=user_id,
            course=course,
            gap=gap,
            need=need,
            request_extra=request_extra,
            status="pending",
        )
        self.session.add(resource)
        await self.session.commit()
        await self.session.refresh(resource)
        return resource

    async def update_resource_status(
        self,
        resource_id: int,
        status: str,
        plan_result: str | None = None,
    ) -> None:
        """更新资源状态。"""
        resource = await self.session.get(GeneratedResource, resource_id)
        if resource:
            resource.status = status
            if plan_result:
                resource.plan_result = plan_result
            await self.session.commit()

    async def persist_result(
        self,
        resource_id: int,
        agent_name: str,
        result: dict[str, Any],
    ) -> None:
        """持久化单个 Agent 结果。"""
        resource = await self.session.get(GeneratedResource, resource_id)
        if not resource:
            return

        column_name = f"{agent_name}_result"
        if hasattr(resource, column_name):
            setattr(resource, column_name, json.dumps(result, ensure_ascii=False))
            await self.session.commit()

    async def persist_all_results(
        self,
        resource_id: int,
        results: dict[str, dict[str, Any]],
    ) -> None:
        """持久化所有 Agent 结果。"""
        resource = await self.session.get(GeneratedResource, resource_id)
        if not resource:
            return

        for agent_name, result in results.items():
            column_name = f"{agent_name}_result"
            if hasattr(resource, column_name):
                setattr(resource, column_name, json.dumps(result, ensure_ascii=False))

        await self.session.commit()
        logger.info("[ResourceUsecases] 结果已持久化: resource_id=%s agents=%s",
                   resource_id, list(results.keys()))

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
        from sqlmodel import col, select

        statement = (
            select(GeneratedResource)
            .where(GeneratedResource.user_id == user_id)
            .order_by(col(GeneratedResource.id).desc())
            .limit(limit)
        )
        result = await self.session.exec(statement)
        return list(result.all())


class ResourceStreamService:
    """资源生成流式服务 — SSE。"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.usecases = ResourceUsecases(session)

    async def stream_bundle(
        self,
        user_id: int,
        task: dict[str, Any],
        selected_resources: list[str] | None = None,
    ) -> AsyncGenerator[str, None]:
        """流式生成资源包。"""
        # 创建 SSE 发射器
        emitter = AgentEventEmitter()

        # 创建工作流
        workflow = ResourceWorkflow(
            emitter=emitter,
            resource_store=self.usecases,
        )

        async def _run_workflow() -> dict[str, Any]:
            try:
                result = await workflow.run(
                    user_id=user_id,
                    task=task,
                    selected_resources=selected_resources,
                )
                if not result.get("success"):
                    await emitter.emit("error", message=result.get("error", "生成失败"))
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
        registry = get_agent_registry()
        return [
            {
                "name": name,
                "role": entry.role,
                "desc": entry.desc,
                "type": entry.type,
                "stage": entry.stage,
            }
            for name, entry in registry.items()
        ]


# 兼容旧 API 的全局实例
async def get_resource_usecases(session: AsyncSession) -> ResourceUsecases:
    """获取 ResourceUsecases 实例。"""
    return ResourceUsecases(session)


async def get_stream_service(session: AsyncSession) -> ResourceStreamService:
    """获取 ResourceStreamService 实例。"""
    return ResourceStreamService(session)
