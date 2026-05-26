"""
资源生成服务层。

整合资源生成工作流、数据库资源记录和 SSE 输出。
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.models import GeneratedResource, GeneratedResourceItem as GeneratedResourceItemModel
from app.resource import schemas
from app.resource.events import AgentEventEmitter, ResourceGenerateEvent
from app.resource.schemas import (
    ExecutionPlan,
    GeneratedResourceItem,
    ResourceBundle,
    ResourceGenerationRequest,
    ReviewResult,
    WorkerResult,
)
from app.resource.workflow import ResourceGenerationWorkflow
from app.infra.logging import get_logger

logger = get_logger(__name__)


class ResourceUsecases:
    """资源生成用例。"""

    def __init__(self, session: AsyncSession):
        self.session = session
        # LLM workers run concurrently, but a single AsyncSession must not commit concurrently.
        self._write_lock = asyncio.Lock()

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

    async def start_resource_task(
        self,
        *,
        user_id: int,
        request: ResourceGenerationRequest,
        source: str = "standalone",
        node_id: int | None = None,
        profile: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """统一入口：创建资源任务记录、读取画像、返回启动信息。

        实际后台任务调度由 API 层负责（需要 FastAPI BackgroundTasks）。
        """
        resource_record = await self.create_resource(user_id=user_id, request=request)
        resource_id = int(getattr(resource_record, "id", 0) or 0)

        # Read profile if not provided
        if profile is None:
            from app.memory.service import MemoryService
            memory_service = MemoryService(module="mentor")
            profile_record = await memory_service.get_profile(user_id=user_id)
            profile = profile_record.model_dump(exclude_none=True) if profile_record else {}

        # Set node to generating if path-driven
        if node_id:
            from app.infra.models import CoursePathNode
            node = await self.session.get(CoursePathNode, node_id)
            if node:
                node.resource_status = "generating"
                await self.session.commit()

        return {
            "resource_id": resource_id,
            "status": "pending",
            "node_id": node_id,
            "source": source,
        }

    def _initial_workflow_progress(self, selected_agents: list[str]) -> dict[str, Any]:
        nodes = ["planning", *selected_agents, "review", "bundle"]
        return {
            "stage": "pending",
            "progress": 0,
            "latest_message": "等待开始生成",
            "agents": {
                agent_id: {
                    "status": "waiting",
                    "progress": 0,
                    "message": "",
                    "steps": [],
                }
                for agent_id in nodes
            },
        }

    async def initialize_generation_progress(self, resource_id: int, selected_agents: list[str]) -> None:
        """写入任务的初始真实进度快照。"""
        async with self._write_lock:
            resource = await self.session.get(GeneratedResource, resource_id)
            if resource is None:
                raise ValueError("资源不存在")
            personalization = dict(resource.personalization or {})
            personalization["workflow_progress"] = self._initial_workflow_progress(selected_agents)
            resource.personalization = personalization
            resource.updated_at = datetime.now(timezone.utc)
            await self._commit_resource(resource)

    async def record_generation_event(self, resource_id: int, event: ResourceGenerateEvent) -> None:
        """将 Agent 发出的真实事件折叠为可轮询的轻量进度快照。"""
        async with self._write_lock:
            resource = await self.session.get(GeneratedResource, resource_id)
            if resource is None:
                return
            personalization = dict(resource.personalization or {})
            progress = personalization.get("workflow_progress")
            if not isinstance(progress, dict):
                progress = self._initial_workflow_progress(list(resource.selected_agents or []))
            agents = dict(progress.get("agents") or {})
            node_id = self._resolve_progress_node(event)

            if node_id:
                node = dict(agents.get(node_id) or self._initial_workflow_progress([])["agents"]["planning"])
                node["status"] = event.status
                event_node_progress = 100 if event.event_type == "resource" else int(event.progress or 0)
                node["progress"] = max(int(node.get("progress") or 0), event_node_progress)
                node["message"] = event.message
                if event.event_type == "agent_step" and event.message:
                    node["steps"] = [*(node.get("steps") or []), event.message][-12:]
                agents[node_id] = node

            stage, task_status = self._resolve_progress_stage(event)
            if event.event_type == "done" and resource.status in {"completed", "partial_completed", "failed"}:
                stage = resource.status
            progress["stage"] = stage or progress.get("stage", "pending")
            if event.event_type in {"workflow", "bundle", "done", "error"}:
                progress["progress"] = max(int(progress.get("progress") or 0), int(event.progress or 0))
            progress["latest_message"] = event.message or progress.get("latest_message", "")
            progress["agents"] = agents
            personalization["workflow_progress"] = progress
            resource.personalization = personalization
            if task_status and resource.status not in {"completed", "partial_completed", "failed"}:
                resource.status = task_status
            resource.updated_at = datetime.now(timezone.utc)
            await self._commit_resource(resource)

    async def get_generation_status(self, user_id: int, resource_id: int) -> dict[str, Any] | None:
        """读取任务总状态及数据库中记录的真实进度。"""
        resource = await self.get_resource(user_id, resource_id)
        if resource is None:
            return None
        personalization = resource.personalization if isinstance(resource.personalization, dict) else {}
        progress = personalization.get("workflow_progress")
        if not isinstance(progress, dict):
            progress = self._initial_workflow_progress(list(resource.selected_agents or []))
        return {
            "resource_id": resource_id,
            "status": resource.status,
            "progress": progress,
        }

    async def update_resource_status(
        self,
        resource_id: int,
        status: str,
    ) -> None:
        """更新资源状态。"""
        async with self._write_lock:
            resource = await self.session.get(GeneratedResource, resource_id)
            if resource:
                resource.status = status
                resource.updated_at = datetime.now(timezone.utc)
                await self._commit_resource(resource)

    def _resolve_progress_node(self, event: ResourceGenerateEvent) -> str | None:
        if event.event_type == "bundle" or event.agent == "assembler":
            return "bundle"
        if event.agent and event.agent != "coordinator":
            return event.agent
        if event.stage.startswith("planning"):
            return "planning"
        if event.stage == "reviewing":
            return "review"
        return None

    def _resolve_progress_stage(self, event: ResourceGenerateEvent) -> tuple[str | None, str | None]:
        if event.event_type == "done":
            return "completed", None
        if event.event_type == "bundle":
            return "assembling", None
        if event.stage == "reviewing" or event.agent == "review":
            return "reviewing", "reviewing"
        if event.stage == "generating" or (
            event.agent and event.agent not in {"coordinator", "planning", "review", "assembler"}
        ):
            return "generating", "generating"
        if event.stage.startswith("planning") or event.agent == "planning":
            return "planning", "planning"
        return event.stage or None, None

    async def _commit_resource(self, resource: GeneratedResource) -> None:
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
        async with self._write_lock:
            return await self._insert_resource_item(resource_id, user_id, item)

    async def _insert_resource_item(
        self,
        resource_id: int,
        user_id: int,
        item: schemas.GeneratedResourceItem,
    ) -> GeneratedResourceItemModel:
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

    async def save_worker_result(
        self,
        *,
        resource_id: int,
        user_id: int,
        result: WorkerResult,
    ) -> GeneratedResourceItemModel:
        """单个 Worker 成功后立即发布其数据库资源项。"""
        if not result.success or not result.content:
            raise ValueError("仅能保存已成功生成且含内容的资源")
        item = self._to_resource_item(resource_id=resource_id, result=result)
        return await self.save_resource_item(resource_id=resource_id, user_id=user_id, item=item)

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

    async def results_for_review(
        self,
        user_id: int,
        resource_id: int,
        failures: dict[str, WorkerResult],
    ) -> dict[str, WorkerResult]:
        """从已入库资源构造审阅输入，并附加本轮失败项。"""
        db_items = await self.list_resource_items(user_id, resource_id)
        persisted = {
            item.agent_type: self._db_item_to_worker_result(item)
            for item in db_items
        }
        return {**persisted, **failures}

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
        plan: ExecutionPlan,
    ) -> None:
        """保存审阅元数据和终态；Worker 结果已在完成节点逐条入库。"""
        saved_items = await self.list_resource_items(user_id, resource_id)
        failed_agents = [agent_id for agent_id, result in results.items() if not result.success]
        if not review_result.passed and "review" not in failed_agents:
            failed_agents.append("review")
        status = self._resolve_generation_status(
            successful_count=len(saved_items),
            failed_count=len(failed_agents),
        )
        async with self._write_lock:
            resource = await self.session.get(GeneratedResource, resource_id)
            if resource is None or resource.user_id != user_id:
                raise ValueError("资源不存在或无权限")

            personalization = dict(resource.personalization or {})
            personalization.update({
                "review_result": review_result.model_dump(mode="json"),
                "execution_plan": plan.model_dump(mode="json"),
                "failed_agents": failed_agents,
                "selected_agents": request.enabled_agent_ids(),
            })
            resource.status = status
            resource.updated_at = datetime.now(timezone.utc)
            resource.personalization = personalization
            await self._commit_resource(resource)

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

        review_result = ReviewResult.model_validate(review_data) if isinstance(review_data, dict) else None

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
            study_path=review_result.study_path if review_result else [],
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

    def _db_item_to_worker_result(self, item: GeneratedResourceItemModel) -> WorkerResult:
        resource_item = self._db_item_to_resource_item(item)
        content = resource_item.content
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False)
        return WorkerResult(
            success=True,
            content=content,
            file_type=resource_item.format,
            title=resource_item.title,
            summary=resource_item.summary,
            summary_data=resource_item.summary_data,
            metadata=resource_item.metadata,
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





async def bg_gen_task(
    user_id: int,
    request: ResourceGenerationRequest,
    profile: dict[str, Any],
    resource_id: int,
    node_id: int | None = None,
) -> None:
    """在后台执行资源包生成任务。

    根据工作流返回结果和实际保存的资源条目数量决定最终状态。
    只有成功且有条目时才将路径节点标记为 ready。
    """
    from app.infra.database import session_scope

    async with session_scope() as session:
        usecases = ResourceUsecases(session)
        await usecases.initialize_generation_progress(resource_id, request.enabled_agent_ids())

        async def persist_event(event: ResourceGenerateEvent) -> None:
            await usecases.record_generation_event(resource_id, event)

        emitter = AgentEventEmitter(resource_id=resource_id, event_sink=persist_event)
        workflow = ResourceGenerationWorkflow(
            emitter=emitter,
            resource_service=usecases,
        )

        try:
            result = await workflow.run(
                user_id=user_id,
                request=request,
                profile=profile,
                resource_id=resource_id,
            )

            # Read actual saved items from database
            saved_items = await usecases.list_resource_items(user_id, resource_id)
            item_count = len(saved_items)

            # Determine final status based on workflow result and saved items
            resource = await usecases.get_resource(user_id, resource_id)
            current_status = resource.status if resource else "failed"

            # completed/partial_completed with items -> node ready
            # failed or no items -> node failed
            if current_status in ("completed", "partial_completed") and item_count > 0:
                if node_id:
                    await _update_node_resource_status(
                        session, node_id, "ready", resource_id, user_id,
                    )
            else:
                await usecases.update_resource_status(resource_id, "failed")
                if node_id:
                    await _update_node_resource_status(
                        session, node_id, "failed", None, user_id,
                    )

        except Exception:
            logger.exception("后台资源生成任务异常")
            await usecases.update_resource_status(resource_id, "failed")
            if node_id:
                await _update_node_resource_status(
                    session, node_id, "failed", None, user_id,
                )


async def _update_node_resource_status(
    session: AsyncSession,
    node_id: int,
    status: str,
    resource_id: int | None,
    user_id: int,
) -> None:
    """Update a path node's resource_status and optionally bind resource."""
    from app.infra.models import CoursePathNode, CoursePathResourceBinding

    node = await session.get(CoursePathNode, node_id)
    if node:
        node.resource_status = status

    if status == "ready" and resource_id is not None:
        # Check if binding already exists
        binding_stmt = select(CoursePathResourceBinding).where(
            CoursePathResourceBinding.node_id == node_id,
            CoursePathResourceBinding.resource_id == resource_id,
        )
        existing = (await session.exec(binding_stmt)).first()
        if not existing:
            binding = CoursePathResourceBinding(
                user_id=user_id,
                node_id=node_id,
                resource_id=resource_id,
            )
            session.add(binding)

    await session.commit()
