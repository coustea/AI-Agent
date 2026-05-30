"""
资源生成服务层。

整合资源生成工作流、数据库资源记录和 SSE 输出。
"""

from __future__ import annotations

import time
import asyncio
import json
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.models import GeneratedResource, GeneratedResourceItem as GeneratedResourceItemModel
from app.resource.events import AgentEventEmitter, ResourceGenerateEvent
from app.resource.schemas import (
    ExecutionPlan,
    GeneratedResourceItem,
    ResourceBundle,
    ResourceGenerationRequest,
    ReviewResult,
    WorkerResult,
)
from app.infra.logging import get_module_logger

logger = get_module_logger("resource", sub="workflow")


class ResourceUsecases:
    """资源生成用例。"""

    def __init__(self, session: AsyncSession):
        self.session = session
        # LLM workers run concurrently, but a single AsyncSession must not commit concurrently.
        self._write_lock = asyncio.Lock()

    async def start_resource_task(
        self,
        *,
        user_id: int,
        request: ResourceGenerationRequest,
        source: str = "standalone",
        node_id: int | None = None,
        profile: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """统一入口：创建资源任务记录，并原子绑定路径节点任务。

        实际后台任务调度由 API 层负责（需要 FastAPI BackgroundTasks）。
        """
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
            await self.session.flush()
            resource_id = int(getattr(resource, "id", 0) or 0)
            if node_id is not None:
                from app.infra.models import CoursePathNode, CoursePathResourceBinding

                node = await self.session.get(CoursePathNode, node_id)
                if node is None or node.user_id != user_id:
                    raise ValueError("路径节点不存在或不属于当前用户")
                node.resource_status = "generating"
                binding_stmt = (
                    select(CoursePathResourceBinding)
                    .where(
                        CoursePathResourceBinding.node_id == node_id,
                        CoursePathResourceBinding.user_id == user_id,
                    )
                    .order_by(col(CoursePathResourceBinding.created_at).desc())
                )
                binding = (await self.session.exec(binding_stmt)).first()
                if binding:
                    binding.resource_id = resource_id
                    binding.resource_item_id = None
                else:
                    self.session.add(
                        CoursePathResourceBinding(
                            user_id=user_id,
                            node_id=node_id,
                            resource_id=resource_id,
                        )
                    )
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        await self.session.refresh(resource)

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
            await self._commit(resource)

    async def record_generation_event(self, resource_id: int, event: ResourceGenerateEvent) -> None:
        """将 Agent 发出的真实事件折叠为可轮询的轻量进度快照。"""
        async with self._write_lock:
            resource = await self.session.get(GeneratedResource, resource_id)
            if resource is None:
                return
            personalization = deepcopy(resource.personalization or {})
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
            self._mark_json_modified(resource, "personalization")
            if task_status and resource.status not in {"completed", "partial_completed", "failed"}:
                resource.status = task_status
            resource.updated_at = datetime.now(timezone.utc)
            await self._commit(resource)

    async def get_generation_status(self, user_id: int, resource_id: int) -> dict[str, Any] | None:
        """读取任务总状态及数据库中记录的真实进度。"""
        resource = await self.get_resource(user_id, resource_id)
        if resource is None:
            return None
        personalization = resource.personalization if isinstance(resource.personalization, dict) else {}
        progress = personalization.get("workflow_progress")
        if not isinstance(progress, dict):
            progress = self._initial_workflow_progress(list(resource.selected_agents or []))
        db_items: list[GeneratedResourceItemModel] = []
        if hasattr(self.session, "exec"):
            db_items = await self.list_resource_items(user_id, resource_id)
        return {
            "resource_id": resource_id,
            "status": resource.status,
            "progress": progress,
            "resources": [
                self._db_item_to_resource_item(item).model_dump(mode="json")
                for item in db_items
            ],
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
                await self._commit(resource)

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

    async def _commit(self, obj: Any) -> None:
        """提交并刷新数据库对象。"""
        try:
            await self.session.commit()
        except Exception as exc:
            await self.session.rollback()
            raise exc
        await self.session.refresh(obj)

    def _mark_json_modified(self, obj: Any, field_name: str) -> None:
        """Mark SQLAlchemy JSON/JSONB fields dirty after nested snapshot rewrites."""
        try:
            flag_modified(obj, field_name)
        except Exception:
            # Unit-test fakes and simple namespace objects are not SQLAlchemy-mapped.
            return

    def _content_envelope(self, result: WorkerResult) -> tuple[dict[str, Any] | None, str | None]:
        """根据格式拆分 WorkerResult 内容为 content_json 和 content_text。"""
        fmt = result.file_type.lower()
        content = result.content
        envelope = {
            "title": result.title,
            "summary": result.summary,
            "summary_data": result.summary_data,
            "metadata": result.metadata,
            "format": result.file_type,
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
        agent_id = str(result.metadata.get("agent_id") or "")
        title = result.title or f"{agent_id} 资源"
        content_json, content_text = self._content_envelope(result)
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
            status="completed",
            updated_at=datetime.now(timezone.utc),
        )
        async with self._write_lock:
            self.session.add(resource_item)
            await self._commit(resource_item)
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
        successful = len(saved_items)
        if failed_agents and successful:
            status = "partial_completed"
        elif failed_agents:
            status = "failed"
        else:
            status = "completed"
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
            await self._commit(resource)

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

    def _envelope_from_item(self, item: GeneratedResourceItemModel) -> dict[str, Any]:
        """从 DB 资源明细提取 content_json envelope，兜底为空字典。"""
        return dict(item.content_json) if isinstance(item.content_json, dict) else {}

    def _db_item_to_resource_item(self, item: GeneratedResourceItemModel) -> GeneratedResourceItem:
        envelope = self._envelope_from_item(item)
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
            status=item.status,
            error_message=item.error_message,
            created_at=item.created_at.isoformat() if item.created_at else None,
            updated_at=item.updated_at.isoformat() if item.updated_at else None,
        )

    def _db_item_to_worker_result(self, item: GeneratedResourceItemModel) -> WorkerResult:
        envelope = self._envelope_from_item(item)
        content = envelope.get("content") if item.content_json is not None else item.content_text
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False)
        return WorkerResult(
            success=True,
            content=content,
            file_type=envelope.get("format") or item.content_format,
            title=envelope.get("title") or item.title or "",
            summary=envelope.get("summary") or item.summary or "",
            summary_data=envelope.get("summary_data") or {},
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


async def bg_gen_task(
    user_id: int,
    request: ResourceGenerationRequest,
    profile: dict[str, Any],
    resource_id: int,
    node_id: int | None = None,
) -> None:
    """在后台执行多智能体资源生成任务。

    流程：PlanningAgent → 并行 Worker Agents → ReviewAgent → 保存。
    """
    from app.infra.database import session_scope
    from app.resource.agents import AGENT_REGISTRY
    from app.resource.schemas import WorkerState, LearningBlueprint, AgentInstruction

    async with session_scope() as session:
        usecases = ResourceUsecases(session)
        enabled_agents = request.enabled_agent_ids()
        await usecases.initialize_generation_progress(resource_id, enabled_agents)

        async def persist_event(event: ResourceGenerateEvent) -> None:
            await usecases.record_generation_event(resource_id, event)

        emitter = AgentEventEmitter(resource_id=resource_id, event_sink=persist_event)

        success = False
        start_time = time.perf_counter()
        try:
            logger.info("启动资源生成: user_id=%s, resource_id=%s, agents=%s", user_id, resource_id, enabled_agents)
            # 1. PlanningAgent
            planning_state = WorkerState(
                learning_need=request.learning_need,
                learning_scenario=request.learning_scenario,
                profile=profile,
                agent_config={"enabled_agents": enabled_agents},
            )
            planning_result = await AGENT_REGISTRY["planning"](emitter).run(planning_state)

            # Extract blueprint and instructions from planning result
            blueprint = None
            instruction_map: dict[str, AgentInstruction] = {}
            if planning_result.success and planning_result.metadata:
                blueprint_data = planning_result.metadata.get("blueprint")
                if blueprint_data:
                    blueprint = LearningBlueprint.model_validate(blueprint_data)
                instructions_data = planning_result.metadata.get("instructions", {})
                for aid, inst_data in instructions_data.items():
                    if isinstance(inst_data, dict):
                        instruction_map[aid] = AgentInstruction.model_validate(inst_data)

            planning_elapsed = time.perf_counter() - start_time
            if planning_result.success:
                logger.info("Planning 完成: %.2fs", planning_elapsed)
            else:
                logger.warning("Planning 失败: %.2fs, error=%s", planning_elapsed, planning_result.error)

            # 2. Parallel worker agents
            worker_start = time.perf_counter()
            await emitter.emit_workflow("generating", "并行生成资源", progress=20)
            results: dict[str, WorkerResult] = {}

            async def run_one(agent_id: str) -> None:
                agent_start = time.perf_counter()
                try:
                    logger.info("Agent[%s] 启动", agent_id)
                    state = WorkerState(
                        resource_id=resource_id,
                        learning_need=request.learning_need,
                        learning_scenario=request.learning_scenario,
                        agent_name=agent_id,
                        agent_config=request.agent_configs.get(agent_id, {}),
                        blueprint=blueprint,
                        instruction=instruction_map.get(agent_id),
                        profile=profile,
                    )
                    agent = AGENT_REGISTRY[agent_id](emitter)
                    result = await agent.run(state)
                    results[agent_id] = result
                    agent_elapsed = time.perf_counter() - agent_start
                    if result.success:
                        logger.info("Agent[%s] 完成: %.2fs", agent_id, agent_elapsed)
                    else:
                        logger.warning("Agent[%s] 失败: %.2fs, error=%s", agent_id, agent_elapsed, result.error)
                    if result.success and result.content:
                        await usecases.save_worker_result(
                            user_id=user_id,
                            resource_id=resource_id,
                            result=result,
                        )
                        await emitter.emit_resource(
                            agent_id=agent_id,
                            title=result.title,
                            file_type=result.file_type,
                            content=result.content,
                            summary=result.summary,
                            summary_data=result.summary_data,
                            metadata=result.metadata,
                        )
                except Exception as exc:
                    agent_elapsed = time.perf_counter() - agent_start
                    logger.error("Agent[%s] 异常: %.2fs", agent_id, agent_elapsed, exc_info=True)
                    results[agent_id] = WorkerResult(
                        success=False,
                        error=str(exc),
                        metadata={"agent_id": agent_id},
                    )

            worker_agents = [a for a in enabled_agents if a in AGENT_REGISTRY and a not in ("planning", "review")]
            logger.info("开始并行 Worker 生成: agents=%s", worker_agents)
            await asyncio.gather(*(run_one(agent_id) for agent_id in worker_agents))

            worker_elapsed = time.perf_counter() - worker_start
            success_count = sum(1 for r in results.values() if r.success)
            fail_count = sum(1 for r in results.values() if not r.success)
            logger.info("Worker 全部完成: 成功=%s, 失败=%s, 耗时=%.2fs", success_count, fail_count, worker_elapsed)

            # 3. ReviewAgent
            await emitter.emit_workflow("reviewing", "质量审查中", progress=85)
            if "review" in AGENT_REGISTRY:
                failed_results = {aid: r for aid, r in results.items() if not r.success}
                review_results = await usecases.results_for_review(user_id, resource_id, failed_results)
                review_state = WorkerState(
                    learning_need=request.learning_need,
                    profile=profile,
                    blueprint=blueprint,
                    agent_config={"worker_results": [r.model_dump(mode="json") for r in review_results.values()]},
                )
                review_worker_result = await AGENT_REGISTRY["review"](emitter).run(review_state)
                logger.info("Review 完成: success=%s", review_worker_result.success)
                review_result = ReviewResult(
                    passed=review_worker_result.success,
                    overall_score=100 if review_worker_result.success else 0,
                    suggestions=[review_worker_result.content] if review_worker_result.content else [],
                )
            else:
                review_result = ReviewResult(passed=True, overall_score=100)

            # 4. Save final results
            await usecases.save_generation_results(
                user_id=user_id,
                resource_id=resource_id,
                request=request,
                results=results,
                review_result=review_result,
                plan=ExecutionPlan(
                    blueprint=blueprint or LearningBlueprint(topic=request.learning_need),
                    agent_instructions=list(instruction_map.values()),
                ) if blueprint else ExecutionPlan(
                    blueprint=LearningBlueprint(topic=request.learning_need),
                    agent_instructions=[],
                ),
            )

            bundle = await usecases.get_resource_bundle(user_id, resource_id)
            if bundle:
                await emitter.emit_bundle(bundle, progress=99)
            await emitter.emit_done(bundle=bundle)

            saved_items = await usecases.list_resource_items(user_id, resource_id)
            resource = await usecases.get_resource(user_id, resource_id)
            current_status = resource.status if resource else "failed"
            success = current_status in ("completed", "partial_completed") and len(saved_items) > 0
            total_elapsed = time.perf_counter() - start_time
            logger.info("资源生成结束: resource_id=%s, success=%s, 耗时=%.2fs", resource_id, success, total_elapsed)
        except Exception:
            total_elapsed = time.perf_counter() - start_time
            logger.error("资源生成异常: resource_id=%s, 耗时=%.2fs", resource_id, total_elapsed, exc_info=True)

        if not success:
            await usecases.update_resource_status(resource_id, "failed")
        if node_id:
            await _update_node_resource_status(
                session, node_id, "ready" if success else "failed",
                resource_id if success else None, user_id,
            )


async def bg_single_gen_task(
    user_id: int,
    resource_id: int,
    agent_id: str,
    learning_need: str,
    profile: dict[str, Any],
    node_id: int | None = None,
) -> None:
    """在后台执行单智能体资源生成任务（路径规划 / 即调即用）。"""
    from app.infra.database import session_scope
    from app.resource.agents import AGENT_REGISTRY
    from app.resource.schemas import WorkerState

    async with session_scope() as session:
        usecases = ResourceUsecases(session)
        await usecases.initialize_generation_progress(resource_id, [agent_id])

        async def persist_event(event: ResourceGenerateEvent) -> None:
            await usecases.record_generation_event(resource_id, event)

        emitter = AgentEventEmitter(resource_id=resource_id, event_sink=persist_event)

        success = False
        start_time = time.perf_counter()
        try:
            logger.info("启动单智能体生成: user_id=%s, resource_id=%s, agent=%s", user_id, resource_id, agent_id)
            state = WorkerState(
                learning_need=learning_need,
                profile=profile,
            )
            result = await AGENT_REGISTRY[agent_id](emitter).run(state)

            agent_elapsed = time.perf_counter() - start_time
            if result.success:
                logger.info("Agent[%s] 完成: %.2fs", agent_id, agent_elapsed)
            else:
                logger.warning("Agent[%s] 失败: %.2fs, error=%s", agent_id, agent_elapsed, result.error)

            if result.success and result.content:
                await usecases.save_worker_result(
                    user_id=user_id,
                    resource_id=resource_id,
                    result=result,
                )
                await emitter.emit_resource(
                    agent_id=agent_id,
                    title=result.title,
                    file_type=result.file_type,
                    content=result.content,
                    summary=result.summary,
                    summary_data=result.summary_data,
                    metadata=result.metadata,
                )
                success = True

            await emitter.emit_done(bundle=None)
        except Exception:
            logger.error("单智能体生成异常: agent=%s, resource_id=%s", agent_id, resource_id, exc_info=True)

        if not success:
            await usecases.update_resource_status(resource_id, "failed")
        else:
            await usecases.update_resource_status(resource_id, "completed")
        total_elapsed = time.perf_counter() - start_time
        logger.info("单智能体生成结束: agent=%s, success=%s, 耗时=%.2fs", agent_id, success, total_elapsed)
        if node_id:
            await _update_node_resource_status(
                session, node_id, "ready" if success else "failed",
                resource_id if success else None, user_id,
            )


async def start_single_resource_task(
    *,
    user_id: int,
    agent_id: str,
    learning_need: str,
    profile: dict[str, Any],
    node_id: int | None = None,
) -> dict[str, Any]:
    """创建单智能体资源任务记录。

    实际后台任务调度由 API 层负责（需要 FastAPI BackgroundTasks）。
    """
    resource = GeneratedResource(
        user_id=user_id,
        learning_need=learning_need,
        personalization={},
        selected_agents=[agent_id],
        agent_configs={},
        status="pending",
    )
    session = None
    resource_id = 0

    from app.infra.database import session_scope
    async with session_scope() as s:
        session = s
        session.add(resource)
        await session.flush()
        resource_id = int(getattr(resource, "id", 0) or 0)

        if node_id is not None:
            from app.infra.models import CoursePathNode, CoursePathResourceBinding

            node = await session.get(CoursePathNode, node_id)
            if node is None or node.user_id != user_id:
                raise ValueError("路径节点不存在或不属于当前用户")
            node.resource_status = "generating"
            binding_stmt = (
                select(CoursePathResourceBinding)
                .where(
                    CoursePathResourceBinding.node_id == node_id,
                    CoursePathResourceBinding.user_id == user_id,
                )
                .order_by(col(CoursePathResourceBinding.created_at).desc())
            )
            binding = (await session.exec(binding_stmt)).first()
            if binding:
                binding.resource_id = resource_id
                binding.resource_item_id = None
            else:
                session.add(
                    CoursePathResourceBinding(
                        user_id=user_id,
                        node_id=node_id,
                        resource_id=resource_id,
                    )
                )
        await session.commit()

    return {
        "resource_id": resource_id,
        "status": "pending",
        "node_id": node_id,
        "source": "single_agent",
    }


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
