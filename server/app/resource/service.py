"""
资源生成服务层。

整合资源生成工作流、数据库资源记录和 SSE 输出。
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.models import GeneratedResource, GeneratedResourceItem as GeneratedResourceItemModel
from app.resource.events import AgentEventEmitter
from app.resource.schemas import (
    AgentSelection,
    ExecutionPlan,
    GeneratedResourceItem,
    ResourceBundle,
    ResourceGenerationRequest,
    ReviewResult,
    WorkerResult, WorkerState,
)
from app.infra.logging import get_module_logger

logger = get_module_logger("resource", sub="workflow")

SOURCE_AUDIT_AGENT_IDS = ("content", "reading")
COMPLETENESS_ONLY_AGENT_IDS = ("quiz", "mindmap", "code")
PPT_AGENT_ID = "ppt"
PRE_REVIEW_AGENT_ID = "pre_review"
PPT_REVIEW_AGENT_ID = "ppt_review"
REVIEW_CONTENT_LIMIT = 12_000


class ResourceService:
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

    async def get_generation_status(self, user_id: int, resource_id: int) -> dict[str, Any] | None:
        """读取任务总状态及已生成资源列表。"""
        resource = await self.get_resource(user_id, resource_id)
        if resource is None:
            return None
        db_items = await self.list_resource_items(user_id, resource_id)
        return {
            "resource_id": resource_id,
            "status": resource.status,
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

    async def _commit(self, obj: Any) -> None:
        """提交并刷新数据库对象。"""
        try:
            await self.session.commit()
        except Exception as exc:
            await self.session.rollback()
            raise exc
        await self.session.refresh(obj)

    
    @staticmethod
    def _has_generated_content(result: WorkerResult | None) -> bool:
        if result is None or not result.success:
            return False
        content = result.content
        if content is None:
            return False
        if isinstance(content, str):
            return bool(content.strip())
        return True

    @staticmethod
    def _bounded_content(content: Any) -> str:
        if isinstance(content, str):
            text = content
        else:
            text = json.dumps(content, ensure_ascii=False)
        if len(text) <= REVIEW_CONTENT_LIMIT:
            return text
        return f"{text[:REVIEW_CONTENT_LIMIT]}\n\n[内容已截断用于审核上下文控制]"

    @staticmethod
    def _profile_summary(profile: dict[str, Any]) -> str:
        for key in ("profile_markdown", "summary", "profile_summary"):
            value = profile.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        profile_data = profile.get("profile_data")
        if isinstance(profile_data, dict):
            return json.dumps(profile_data, ensure_ascii=False)
        return ""

    @staticmethod
    def build_pre_audit_envelope(
        *,
        request: ResourceGenerationRequest,
        results: dict[str, WorkerResult],
        profile: dict[str, Any],
        blueprint: Any | None,
    ) -> tuple[dict[str, Any], list[str]]:
        selected_agents = request.enabled_agent_ids()
        checked_agents = [
            agent_id
            for agent_id in selected_agents
            if agent_id in SOURCE_AUDIT_AGENT_IDS or agent_id in COMPLETENESS_ONLY_AGENT_IDS
        ]
        missing_resources = [
            agent_id
            for agent_id in checked_agents
            if not ResourceService._has_generated_content(results.get(agent_id))
        ]
        deep_audit_resources = [
            {
                "agent_id": agent_id,
                "title": results[agent_id].title,
                "summary": results[agent_id].summary,
                "audit_content": ResourceService._bounded_content(results[agent_id].content),
            }
            for agent_id in selected_agents
            if agent_id in SOURCE_AUDIT_AGENT_IDS and ResourceService._has_generated_content(results.get(agent_id))
        ]
        completeness_only = [
            {
                "agent_id": agent_id,
                "title": results.get(agent_id).title if results.get(agent_id) else "",
                "summary": results.get(agent_id).summary if results.get(agent_id) else "",
                "has_content": ResourceService._has_generated_content(results.get(agent_id)),
            }
            for agent_id in selected_agents
            if agent_id in COMPLETENESS_ONLY_AGENT_IDS
        ]
        return {
            "mode": "pre_audit",
            "request_context": {
                "learning_need": request.learning_need,
                "learning_scenario": request.learning_scenario,
                "profile_summary": ResourceService._profile_summary(profile),
                "blueprint": blueprint.model_dump(mode="json") if blueprint else {},
            },
            "deep_audit_resources": deep_audit_resources,
            "completeness_only": completeness_only,
        }, missing_resources

    @staticmethod
    def build_ppt_audit_envelope(
        *,
        request: ResourceGenerationRequest,
        results: dict[str, WorkerResult],
        profile: dict[str, Any],
        blueprint: Any | None,
    ) -> tuple[dict[str, Any], list[str]]:
        selected_agents = request.enabled_agent_ids()
        missing_resources: list[str] = []
        ppt_result = results.get(PPT_AGENT_ID)
        if PPT_AGENT_ID in selected_agents and not ResourceService._has_generated_content(ppt_result):
            missing_resources.append(PPT_AGENT_ID)
        approved_sources = [
            {
                "agent_id": agent_id,
                "title": results[agent_id].title,
                "summary": results[agent_id].summary,
                "source_content": ResourceService._bounded_content(results[agent_id].content),
            }
            for agent_id in selected_agents
            if agent_id in SOURCE_AUDIT_AGENT_IDS and ResourceService._has_generated_content(results.get(agent_id))
        ]
        ppt_resource = (
            {
                "agent_id": PPT_AGENT_ID,
                "title": ppt_result.title,
                "summary": ppt_result.summary,
                "audit_content": ResourceService._bounded_content(ppt_result.content),
            }
            if ResourceService._has_generated_content(ppt_result)
            else None
        )
        return {
            "mode": "ppt_audit",
            "request_context": {
                "learning_need": request.learning_need,
                "learning_scenario": request.learning_scenario,
                "profile_summary": ResourceService._profile_summary(profile),
                "blueprint": blueprint.model_dump(mode="json") if blueprint else {},
            },
            "approved_sources": approved_sources,
            "ppt_resource": ppt_resource,
        }, missing_resources

    @staticmethod
    def failed_review_result(
        *,
        status: str,
        message: str,
        revision_targets: list[str],
        review_mode: str,
    ) -> ReviewResult:
        payload = {
            "status": status,
            "checks": {
                "need_alignment": "not_checked",
                "content_completeness": "fail",
                "factuality": "not_checked",
                "hallucination": "not_checked",
                "safety": "not_checked",
                "grounding": "not_checked",
            },
            "violations": [{"type": "missing_or_failed_resource", "resources": revision_targets}],
            "revision_targets": revision_targets,
            "mode": review_mode,
        }
        return ReviewResult(
            passed=False,
            overall_score=0,
            consistency_score=0,
            personalization_score=0,
            issues=[message],
            suggestions=[json.dumps(payload, ensure_ascii=False)],
            failed_agents=revision_targets,
        )

    @staticmethod
    def review_result_from_worker(result: WorkerResult) -> ReviewResult:
        parsed = result.metadata.get("parsed_review")
        status = result.metadata.get("review_status") or ("pass" if result.success else "blocked")
        issues: list[str] = []
        failed_agents: list[str] = []
        if isinstance(parsed, dict):
            violations = parsed.get("violations")
            if isinstance(violations, list):
                issues = [
                    item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)
                    for item in violations
                ]
            revision_targets = parsed.get("revision_targets")
            if isinstance(revision_targets, list):
                failed_agents = [str(item) for item in revision_targets]
        if not result.success and not issues:
            issues = [result.error or f"review status: {status}"]
        return ReviewResult(
            passed=result.success,
            overall_score=100 if result.success else 0,
            consistency_score=100 if result.success else 0,
            personalization_score=100 if result.success else 0,
            issues=issues,
            suggestions=[result.content] if result.content else [],
            failed_agents=failed_agents,
        )

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
            status="finished",
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

    def _db_item_to_resource_item(self, item: GeneratedResourceItemModel) -> GeneratedResourceItem:
        envelope = dict(item.content_json) if isinstance(item.content_json, dict) else {}
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
        envelope = dict(item.content_json) if isinstance(item.content_json, dict) else {}
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


async def run_multi_agent_generation(
    user_id: int,
    request: ResourceGenerationRequest,
    profile: dict[str, Any],
    resource_id: int,
    node_id: int | None = None,
) -> None:
    """【核心编排引擎】在后台执行多智能体资源生成任务 (Multi-Agent DAG Workflow)。

    此函数是整个多智能体系统的“总导演”，它按以下 DAG (有向无环图) 流程调度各个智能体：
    
    [ 阶段 1 ] : PlanningAgent (规划智能体)
                 ↓
                 生成蓝图 (Blueprint) 和 指令分发表 (Instructions)
                 ↓
    [ 阶段 2 ] : 并行调度所有启用的 Worker Agents (如 PPT, Quiz, Code, Mindmap 等)
                 (各个 Worker 会拿着专属的 Instruction 并行干活)
                 ↓
                 收集所有 Worker 的生成结果
                 ↓
    [ 阶段 3 ] : ReviewAgent (审阅智能体)
                 (检查所有生成结果的一致性和质量)
                 ↓
    [ 阶段 4 ] : 组装并落库 (Assembler / Save)
    """
    from app.infra.database import session_scope
    from app.resource.agents import AGENT_REGISTRY
    from app.resource.schemas import WorkerState, LearningBlueprint, AgentInstruction

    async with session_scope() as session:
        usecases = ResourceService(session)
        enabled_agents = request.enabled_agent_ids()

        # 实例化事件发射器，贯穿所有 Agent 的生命周期
        emitter = AgentEventEmitter(resource_id=resource_id)

        success = False
        start_time = time.perf_counter()
        try:
            logger.info("启动资源生成: user_id=%s, resource_id=%s, agents=%s", user_id, resource_id, enabled_agents)
            
            # ==========================================
            # 阶段 1: 规划阶段 (Planning Agent)
            # 职责: 拆解用户需求，生成整体教学蓝图，并为每个下游 Agent 分发具体指令
            # ==========================================
            planning_state = WorkerState(
                learning_need=request.learning_need,
                learning_scenario=request.learning_scenario,
                profile=profile,
                agent_config={"enabled_agents": enabled_agents},
            )
            await emitter.emit_agent("planning", status="running", message="正在规划生成蓝图...")
            planning_result = await AGENT_REGISTRY["planning"](emitter).run(planning_state)

            blueprint = None
            instruction_map: dict[str, AgentInstruction] = {}
            if planning_result.success and planning_result.metadata:
                # 提取总蓝图
                blueprint_data = planning_result.metadata.get("blueprint")
                if blueprint_data:
                    blueprint = LearningBlueprint.model_validate(blueprint_data)
                # 提取下游 Agent 的“锦囊”指令
                instructions_data = planning_result.metadata.get("instructions", {})
                for aid, inst_data in instructions_data.items():
                    if isinstance(inst_data, dict):
                        instruction_map[aid] = AgentInstruction.model_validate(inst_data)

            planning_elapsed = time.perf_counter() - start_time
            if planning_result.success:
                logger.info("Planning 完成: %.2fs", planning_elapsed)
            else:
                logger.warning("Planning 失败: %.2fs, error=%s", planning_elapsed, planning_result.error)

            # ==========================================
            # 阶段 2: 基础资源并行生成阶段 (Parallel Worker Agents)
            # 职责: 先生成非 PPT 资源，PPT 必须等待 source pre-audit 通过后再生成
            # ==========================================
            worker_start = time.perf_counter()
            await emitter.emit_agent("coordinator", status="running", message="并行生成基础资源")
            results: dict[str, WorkerResult] = {}

            async def run_one(agent_id: str, agent_config_extra: dict[str, Any] | None = None) -> None:
                """独立运行单个 Worker Agent 的协程函数"""
                agent_start = time.perf_counter()
                try:
                    logger.info("Agent[%s] 启动", agent_id)
                    agent_config = request.agent_configs.get(agent_id, {})
                    if agent_config_extra:
                        agent_config = {**agent_config, **agent_config_extra}
                    # 组装属于该 Agent 的执行上下文
                    state = WorkerState(
                        resource_id=resource_id,
                        learning_need=request.learning_need,
                        learning_scenario=request.learning_scenario,
                        agent_name=agent_id,
                        agent_config=agent_config,
                        blueprint=blueprint,                         # 共享总蓝图
                        instruction=instruction_map.get(agent_id),   # 独享专属指令
                        profile=profile,                             # 共享用户画像
                    )
                    agent = AGENT_REGISTRY[agent_id](emitter)
                    result = await agent.run(state)
                    results[agent_id] = result
                    
                    agent_elapsed = time.perf_counter() - agent_start
                    if result.success:
                        logger.info("Agent[%s] 完成: %.2fs", agent_id, agent_elapsed)
                    else:
                        logger.warning("Agent[%s] 失败: %.2fs, error=%s", agent_id, agent_elapsed, result.error)
                        
                    # 如果该 Worker 成功，立刻将其成果独立保存入库，避免阻塞
                    if result.success and result.content:
                        await usecases.save_worker_result(
                            user_id=user_id,
                            resource_id=resource_id,
                            result=result,
                        )
                        # 发送资源就绪事件给前端
                        # resource saved to DB, frontend polls status
                except Exception as exc:
                    agent_elapsed = time.perf_counter() - agent_start
                    logger.error("Agent[%s] 异常: %.2fs", agent_id, agent_elapsed, exc_info=True)
                    results[agent_id] = WorkerResult(
                        success=False,
                        error=str(exc),
                        metadata={"agent_id": agent_id},
                    )

            # 筛选出基础 Worker：PPT 需要在 source pre-audit 后串行生成。
            worker_agents = [
                a
                for a in enabled_agents
                if a in AGENT_REGISTRY and a not in ("planning", "review", PPT_AGENT_ID)
            ]
            logger.info("开始并行基础 Worker 生成: agents=%s", worker_agents)
            
            # 使用 asyncio.gather 实现高并发执行
            await asyncio.gather(*(run_one(agent_id) for agent_id in worker_agents))

            worker_elapsed = time.perf_counter() - worker_start
            success_count = sum(1 for r in results.values() if r.success)
            fail_count = sum(1 for r in results.values() if not r.success)
            logger.info("基础 Worker 完成: 成功=%s, 失败=%s, 耗时=%.2fs", success_count, fail_count, worker_elapsed)

            # ==========================================
            # 阶段 3: 前置审核 + PPT 生成 + PPT 单独审核
            # 职责: source 先过安全/事实性审核，PPT 只在通过后生成并单独审核
            # ==========================================
            await emitter.emit_agent("pre_review", status="running", message="前置内容安全审核中")
            pre_review_result = ReviewResult(passed=True, overall_score=100)
            review_result = pre_review_result
            review_passed = True

            failed_results = {aid: r for aid, r in results.items() if not r.success}
            review_results = await usecases.results_for_review(user_id, resource_id, failed_results)
            pre_audit_envelope, missing_resources = ResourceService.build_pre_audit_envelope(
                request=request,
                results=review_results,
                profile=profile,
                blueprint=blueprint,
            )
            source_audit_required = bool(pre_audit_envelope["deep_audit_resources"])

            if missing_resources:
                review_result = ResourceService.failed_review_result(
                    status="needs_revision",
                    message=f"资源生成不完整: {', '.join(missing_resources)}",
                    revision_targets=missing_resources,
                    review_mode="pre_audit",
                )
                review_passed = False
                await emitter.emit_agent(
                    PRE_REVIEW_AGENT_ID,
                    status="failed",
                    message="前置审核未通过：资源生成不完整",
                )
                logger.warning("前置审核跳过: missing_resources=%s", missing_resources)
            elif source_audit_required and "review" in AGENT_REGISTRY:
                pre_review_state = WorkerState(
                    learning_need=request.learning_need,
                    learning_scenario=request.learning_scenario,
                    profile=profile,
                    blueprint=blueprint,
                    agent_config={
                        "review_envelope": pre_audit_envelope,
                        "progress_agent_id": PRE_REVIEW_AGENT_ID,
                    },
                )
                pre_review_worker_result = await AGENT_REGISTRY["review"](emitter).run(pre_review_state)
                pre_review_result = ResourceService.review_result_from_worker(pre_review_worker_result)
                review_result = pre_review_result
                review_passed = pre_review_result.passed
                logger.info(
                    "Pre Review 完成: success=%s, status=%s",
                    pre_review_worker_result.success,
                    pre_review_worker_result.metadata.get("review_status"),
                )
            elif source_audit_required:
                review_result = ResourceService.failed_review_result(
                    status="blocked",
                    message="审核智能体不可用，无法完成前置安全审核",
                    revision_targets=["review"],
                    review_mode="pre_audit",
                )
                review_passed = False
                await emitter.emit_agent(
                    PRE_REVIEW_AGENT_ID,
                    status="failed",
                    message="审核智能体不可用，前置安全审核已阻断",
                )
            else:
                await emitter.emit_agent(
                    PRE_REVIEW_AGENT_ID,
                    status="skipped",
                    message="无需深度审核，跳过前置审核",
                )
                logger.info("未选择 content/reading 或 review agent 不可用，跳过前置 LLM 审核")

            if review_passed and PPT_AGENT_ID in enabled_agents:
                await emitter.emit_agent("ppt", status="running", message="正在生成 PPT")
                approved_sources = [
                    {
                        "agent_id": item["agent_id"],
                        "title": item.get("title", ""),
                        "summary": item.get("summary", ""),
                        "source_content": item.get("audit_content", ""),
                    }
                    for item in pre_audit_envelope["deep_audit_resources"]
                ]
                if PPT_AGENT_ID in AGENT_REGISTRY:
                    await run_one(PPT_AGENT_ID, {"approved_sources": approved_sources})

                await emitter.emit_agent("ppt_review", status="running", message="PPT 内容审核中")
                failed_results = {aid: r for aid, r in results.items() if not r.success}
                review_results = await usecases.results_for_review(user_id, resource_id, failed_results)
                ppt_audit_envelope, ppt_missing_resources = ResourceService.build_ppt_audit_envelope(
                    request=request,
                    results=review_results,
                    profile=profile,
                    blueprint=blueprint,
                )
                if ppt_missing_resources:
                    review_result = ResourceService.failed_review_result(
                        status="needs_revision",
                        message=f"PPT 生成不完整: {', '.join(ppt_missing_resources)}",
                        revision_targets=ppt_missing_resources,
                        review_mode="ppt_audit",
                    )
                    review_passed = False
                    await emitter.emit_agent(
                        PPT_REVIEW_AGENT_ID,
                        status="failed",
                        message="PPT 审核未通过：PPT 生成不完整",
                    )
                    logger.warning("PPT 审核跳过: missing_resources=%s", ppt_missing_resources)
                elif "review" in AGENT_REGISTRY:
                    ppt_review_state = WorkerState(
                        learning_need=request.learning_need,
                        learning_scenario=request.learning_scenario,
                        profile=profile,
                        blueprint=blueprint,
                        agent_config={
                            "review_envelope": ppt_audit_envelope,
                            "progress_agent_id": PPT_REVIEW_AGENT_ID,
                        },
                    )
                    ppt_review_worker_result = await AGENT_REGISTRY["review"](emitter).run(ppt_review_state)
                    ppt_review_result = ResourceService.review_result_from_worker(ppt_review_worker_result)
                    if pre_review_result.suggestions:
                        ppt_review_result.suggestions = [
                            *pre_review_result.suggestions,
                            *ppt_review_result.suggestions,
                        ]
                    review_result = ppt_review_result
                    review_passed = ppt_review_result.passed
                    logger.info(
                        "PPT Review 完成: success=%s, status=%s",
                        ppt_review_worker_result.success,
                        ppt_review_worker_result.metadata.get("review_status"),
                    )
                else:
                    review_result = ResourceService.failed_review_result(
                        status="blocked",
                        message="审核智能体不可用，无法完成 PPT 安全审核",
                        revision_targets=["review"],
                        review_mode="ppt_audit",
                    )
                    review_passed = False
                    await emitter.emit_agent(
                        PPT_REVIEW_AGENT_ID,
                        status="failed",
                        message="审核智能体不可用，PPT 安全审核已阻断",
                    )
            elif PPT_AGENT_ID in enabled_agents:
                await emitter.emit_agent(
                    PPT_AGENT_ID,
                    status="skipped",
                    message="前置审核未通过，已跳过 PPT 生成",
                )
                await emitter.emit_agent(
                    PPT_REVIEW_AGENT_ID,
                    status="skipped",
                    message="PPT 未生成，已跳过 PPT 审核",
                )

            # ==========================================
            # 阶段 4: 持久化与打包 (Save Final Results)
            # 职责: 将整个生成周期的数据打包落库，并通知前端完成
            # ==========================================
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

            # 组装最终 Bundle 发送结束事件
            bundle = await usecases.get_resource_bundle(user_id, resource_id)
            await emitter.emit_done(success=True)

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


async def run_single_agent_generation(
    user_id: int,
    resource_id: int,
    agent_id: str,
    learning_need: str,
    profile: dict[str, Any],
    node_id: int | None = None,
) -> None:
    """【轻量级独立执行引擎】在后台执行单智能体资源生成任务。
    
    适用场景：
    - 路径规划中单独生成某个特定知识点的资源 (Course Path Node Generation)
    - 用户在界面上点击“即调即用”单独唤醒某一个领域的专家 (如：仅生成 PPT)

    工作流程：
    [ 准备 ] : 初始化 SSE 进度条和事件发射器
                 ↓
    [ 执行 ] : 实例化指定的 Agent (通过 AGENT_REGISTRY) 并直接运行
                 ↓
    [ 落库 ] : 成功后立刻将生成的资源内容持久化
                 ↓
    [ 结束 ] : 发送 done 事件，更新数据库最终状态
    """
    from app.infra.database import session_scope
    from app.resource.agents import AGENT_REGISTRY
    from app.resource.schemas import WorkerState

    async with session_scope() as session:
        usecases = ResourceService(session)

        emitter = AgentEventEmitter(resource_id=resource_id)

        success = False
        start_time = time.perf_counter()
        try:
            logger.info("启动单智能体生成: user_id=%s, resource_id=%s, agent=%s", user_id, resource_id, agent_id)
            
            # ==========================================
            # 执行阶段: 独立唤醒特定 Agent
            # 注意：单 Agent 模式下没有 PlanningAgent 派发的蓝图，全靠自身的 System Prompt
            # ==========================================
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

            # ==========================================
            # 持久化阶段: 保存并推送结果
            # ==========================================
            if result.success and result.content:
                # 1. 结果立刻落库
                await usecases.save_worker_result(
                    user_id=user_id,
                    resource_id=resource_id,
                    result=result,
                )
                # 2. 通过 SSE 推送给前端（触发前端界面的卡片渲染）
                # resource saved to DB, frontend polls status
                success = True

            # 发送全局结束信号
            await emitter.emit_done(success=True)
        except Exception:
            logger.error("单智能体生成异常: agent=%s, resource_id=%s", agent_id, resource_id, exc_info=True)

        # ==========================================
        # 善后阶段: 标记总状态并更新路径节点（如果是路径任务）
        # ==========================================
        if not success:
            await usecases.update_resource_status(resource_id, "failed")
        else:
            await usecases.update_resource_status(resource_id, "completed")
            
        total_elapsed = time.perf_counter() - start_time
        logger.info("单智能体生成结束: agent=%s, success=%s, 耗时=%.2fs", agent_id, success, total_elapsed)
        
        # 如果这个任务关联了某个具体的学习路径节点，通知该节点状态已就绪
        if node_id:
            await _update_node_resource_status(
                session, node_id, "ready" if success else "failed",
                resource_id if success else None, user_id,
            )




async def _update_node_resource_status(
    session: AsyncSession,
    node_id: int,
    status: str,
    resource_id: int | None,
    user_id: int,
) -> None:
    """更新路径节点的资源状态，可选绑定资源 ID。"""
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
