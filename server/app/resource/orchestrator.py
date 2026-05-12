"""
资源生成编排器。

实现完整的资源生成工作流：
1. prepare - 创建任务、加载画像
2. plan - 规划任务
3. run_dag - 执行 Agent DAG
4. assemble - 组装资源包
5. finish - 完成
"""

from __future__ import annotations

import time
from uuid import uuid4

from app.infra.logging import get_logger
from app.resource.registry import (
    AGENT_CLASSES,
    LAYER_AGENTS,
    ensure_initialized,
    agent_role,
    layer_name,
    layer_stage,
)
from app.resource.events import AgentEventEmitter
from app.resource.planner import RulePlanner, LLMPlanner
from app.resource.assembler import BundleAssembler, QualityReviewAgent, Reviewer
from app.resource.executor import DagScheduler, AgentRunner
from app.resource.executor.dag_scheduler import WorkflowContext, DagResult
from app.resource.utils import load_profile_snapshot
from app.resource.schemas import (
    AgentTask,
    GeneratedResourceItem,
    ResourceBundle,
    ResourceGenerationRequest,
    ResourceAgentId,
    PlanningContext,
)

logger = get_logger(__name__)


class ResourceWorkflow:
    """资源生成工作流。协调 Planner、Executor、Assembler。"""

    def __init__(self, emitter: AgentEventEmitter, resource_store: object) -> None:
        self.emitter = emitter
        self.store = resource_store

        # 初始化各模块
        self.rule_planner = RulePlanner()
        self.llm_planner = LLMPlanner()
        self.assembler = BundleAssembler()
        self.quality_reviewer = QualityReviewAgent()
        self.scheduler = DagScheduler(emitter)
        self.runner = AgentRunner(emitter, resource_store)

    async def run(self, user_id: int, request: ResourceGenerationRequest) -> dict[str, object]:
        """执行资源生成工作流。"""
        ensure_initialized()
        selected = request.enabled_agent_ids()
        task_id = str(uuid4())
        self.emitter.bind_task(task_id)

        total_start = time.time()

        # 发送创建事件
        await self._emit_created(task_id, selected, request)

        try:
            ctx = await self._prepare(user_id, request, task_id, selected)
            tasks = await self._plan(request, ctx, selected)
            result = await self._run_dag(tasks, ctx, request)
            bundle = await self._assemble(ctx, request, result)
            await self._finish(ctx, bundle)

            timing = ctx.timing
            timing["total_ms"] = int((time.time() - total_start) * 1000)
            logger.info("[ResourceWorkflow] 完成: timing=%s", timing)

            return {
                "success": bundle.status != "failed",
                "results": result.results,
                "bundle": bundle.model_dump(mode="json"),
            }

        except Exception as exc:
            logger.exception("[ResourceWorkflow] 执行失败")
            await self.emitter.emit_error(message=str(exc))
            await self.emitter.close()
            return {"success": False, "results": {}, "error": str(exc)}

    # =========================================================================
    # 阶段方法
    # =========================================================================

    async def _prepare(
        self,
        user_id: int,
        request: ResourceGenerationRequest,
        task_id: str,
        selected: list[str],
    ) -> WorkflowContext:
        """创建任务、加载画像。"""
        resource_record = await self.store.create_resource(user_id=user_id, request=request)
        resource_id = resource_record.id

        profile_start = time.time()
        await self.emitter.emit_workflow(
            stage="profile",
            status="running",
            message="正在加载学习者画像",
            progress=5,
        )
        snapshot = await load_profile_snapshot(user_id)
        profile = snapshot.as_agent_profile()
        profile_ms = int((time.time() - profile_start) * 1000)

        await self.emitter.emit_workflow(
            stage="profile",
            status="success",
            message="学习者画像加载完成",
            progress=8,
            payload={"profile_summary": self._summarize_profile(profile), "has_profile": bool(profile)},
        )

        return WorkflowContext(
            task_id=task_id,
            user_id=user_id,
            resource_id=resource_id,
            profile=profile,
            selected=selected,
            timing={"profile_load_ms": profile_ms, "planning_ms": 0, "agents": {}, "review_ms": 0, "assemble_ms": 0},
        )

    async def _plan(
        self,
        request: ResourceGenerationRequest,
        ctx: WorkflowContext,
        selected: list[str],
    ) -> list[AgentTask]:
        """规划任务。"""
        planning_start = time.time()
        mode = request.planning_mode

        if mode == "rule":
            await self.emitter.emit_event(
                event_type="planning",
                stage="planning",
                agent="master",
                status="running",
                message="RulePlanner 正在规划资源生成任务",
                progress=10,
                payload={"planning_mode": "rule", "selected_agents": selected},
            )
            tasks = self.rule_planner.plan(request)
            await self.emitter.emit_event(
                event_type="planning",
                stage="planning",
                agent="master",
                status="success",
                message="规则规划完成",
                payload={"planning_mode": "rule", "agents": [self._serialize_task(t) for t in tasks]},
                progress=15,
            )
        else:
            tasks = await self._plan_with_llm(request, ctx, selected, mode)

        ctx.timing["planning_ms"] = int((time.time() - planning_start) * 1000)
        return tasks

    async def _plan_with_llm(
        self,
        request: ResourceGenerationRequest,
        ctx: WorkflowContext,
        selected: list[str],
        mode: str,
    ) -> list[AgentTask]:
        """LLM 规划。"""
        tasks: list[AgentTask] = []
        planned_ids: set[str] = set()

        if mode == "single_llm":
            await self.emitter.emit_event(
                event_type="planning",
                stage="planning",
                agent="master",
                status="running",
                message="MasterAgent 正在规划资源生成任务",
                progress=10,
                payload={"planning_mode": "single_llm"},
            )
            context = PlanningContext(
                layer=0,
                question=request,
                user_explicit_selection=selected,
                implicit_dependencies=[],
                upstream_results={},
                upstream_reports={},
                learner_profile=ctx.profile,
            )
            layer_plan = await self._safe_plan(context)
            tasks = layer_plan.agents
            await self.emitter.emit_event(
                event_type="planning",
                stage="planning",
                agent="master",
                status="success",
                message="LLM 规划完成",
                payload={"planning_mode": "single_llm", "agents": [self._serialize_task(t) for t in tasks]},
                progress=15,
            )
        else:
            # layer_llm
            for layer in range(3):
                candidates = [
                    a for a in LAYER_AGENTS.get(layer, [])
                    if a in selected and a in AGENT_CLASSES
                ]
                upstream_summaries = self._build_upstream_summaries(tasks, {})
                upstream_reports = self._build_reports(upstream_summaries)

                await self.emitter.emit_event(
                    event_type="planning",
                    stage="planning",
                    agent="master",
                    status="running",
                    message=f"MasterAgent 正在规划 {layer_name(layer)}",
                    progress=8 + layer * 3,
                    payload={
                        "layer": layer,
                        "layer_name": layer_name(layer),
                        "candidate_agents": candidates,
                        "planning_mode": "layer_llm",
                    },
                )

                context = PlanningContext(
                    layer=layer,
                    question=request,
                    user_explicit_selection=selected,
                    implicit_dependencies=[],
                    upstream_results=upstream_summaries,
                    upstream_reports=upstream_reports,
                    learner_profile=ctx.profile,
                )
                layer_plan = await self._safe_plan(context)

                await self.emitter.emit_event(
                    event_type="planning",
                    stage="planning",
                    agent="master",
                    status="success",
                    message=f"{layer_name(layer)} 规划完成",
                    payload={
                        "layer": layer,
                        "layer_name": layer_name(layer),
                        "reasoning": layer_plan.reasoning,
                        "agents": [self._serialize_task(t) for t in layer_plan.agents],
                        "fallback_used": layer_plan.fallback_used,
                    },
                    progress=10 + int((layer + 1) / 3 * 5),
                )

                for task in layer_plan.agents:
                    tasks.append(task)
                    planned_ids.add(task.agent_id)

        return tasks

    async def _safe_plan(self, context: PlanningContext):
        """调用 LLMPlanner，失败时自动降级为规则兜底规划。"""
        try:
            return await self.llm_planner.plan(context)
        except Exception as exc:
            logger.warning("[ResourceWorkflow] LLM 规划失败，降级为规则规划: %s", exc)
            return self.llm_planner.plan_fallback(context)

    async def _execute_agent_task(
        self,
        *,
        agent_task: AgentTask,
        ctx: WorkflowContext,
        request: ResourceGenerationRequest,
        upstream: dict[str, dict[str, Any]],
        degraded: bool,
        missing: list[str],
        failed_deps: list[str],
    ) -> tuple[str, dict[str, Any], bool, AgentTask]:
        """执行单个 Agent 任务。"""
        return await self.runner.run(
            agent_task=agent_task,
            ctx=ctx,
            request=request,
            upstream=upstream,
            degraded=degraded,
            missing=missing,
            failed_deps=failed_deps,
        )

    async def _run_dag(
        self,
        tasks: list[AgentTask],
        ctx: WorkflowContext,
        request: ResourceGenerationRequest,
    ) -> DagResult:
        """执行 DAG 调度。"""
        return await self.scheduler.run(
            tasks=tasks,
            ctx=ctx,
            request=request,
            execute_agent=self._execute_agent_task,
            handle_result=self._handle_agent_result,
        )

    async def _handle_agent_result(
        self,
        *,
        agent_id: str,
        agent_result: dict[str, object],
        is_explicit: bool,
        task: AgentTask,
        ctx: WorkflowContext,
        result: DagResult,
        done: set[str],
        failed_set: set[str],
        layer_terminal: dict[int, set[str]],
        start_time: float | None = None,
    ) -> None:
        """处理 Agent 执行结果。"""
        await self.runner.handle_result(
            agent_id=agent_id,
            agent_result=agent_result,
            is_explicit=is_explicit,
            task=task,
            ctx=ctx,
            result=result,
            done=done,
            failed_set=failed_set,
            layer_terminal=layer_terminal,
            start_time=start_time,
        )

    async def _assemble(
        self,
        ctx: WorkflowContext,
        request: ResourceGenerationRequest,
        result: DagResult,
    ) -> ResourceBundle:
        """组装资源包。从数据库获取已保存的资源。"""
        assemble_start = time.time()

        # 优先从数据库恢复；测试替身或轻量存储未实现时使用内存中的已保存资源。
        if not hasattr(self.store, "list_resource_items"):
            resources = list(result.resources)
        else:
            db_items = await self.store.list_resource_items(
                user_id=ctx.user_id,
                resource_id=ctx.resource_id,
            )

            # 转换数据库模型为 GeneratedResourceItem
            resources = []
            for item in db_items:
                content = item.content_json or {}
                if item.content_text:
                    content["raw_text"] = item.content_text

                resources.append(GeneratedResourceItem(
                    id=str(item.id),
                    type=ResourceAgentId(item.agent_type),
                    title=content.get("title") or f"{item.agent_type} 资源",
                    format=item.content_format,
                    content=content.get("content") or content,
                    summary=content.get("summary") or "",
                    summary_data=content.get("summary_data") or {},
                    metadata=content.get("metadata") or {},
                ))

        completeness_review = self.assembler.reviewer.review(
            request=request,
            resources=resources,
            failed_agents=result.failed,
            skipped_agents=result.skipped,
            errors=result.errors,
        )
        quality_review = await self.quality_reviewer.review(request=request, resources=resources)
        review_result = self._merge_review_results(completeness_review, quality_review)

        bundle = self.assembler.build_bundle(
            task_id=ctx.task_id,
            resource_id=ctx.resource_id,
            request=request,
            resources=resources,
            failed=result.failed,
            skipped=result.skipped,
            errors=result.errors,
            review_result=review_result,
            profile=ctx.profile,
            timing=ctx.timing,
        )

        ctx.timing["assemble_ms"] = int((time.time() - assemble_start) * 1000)
        return bundle

    async def _finish(self, ctx: WorkflowContext, bundle: ResourceBundle) -> None:
        """完成工作流。"""
        await self.store.update_resource_status(resource_id=ctx.resource_id, status=bundle.status)
        await self.emitter.emit_bundle(bundle=bundle, progress=99)
        await self.emitter.emit_done(bundle=bundle)

    # =========================================================================
    # 辅助方法
    # =========================================================================

    def _build_upstream_summaries(
        self,
        tasks: list[AgentTask],
        results: dict[str, dict[str, object]],
    ) -> dict[str, dict[str, object]]:
        """构建上游摘要。"""
        return {
            t.agent_id: self.scheduler._pick_deps(t, results)
            for t in tasks
        }

    def _build_reports(self, summaries: dict[str, dict[str, object]]) -> dict[str, str]:
        """构建交接报告。"""
        reports: dict[str, str] = {}
        for agent_id, summary in summaries.items():
            report = summary.get("summary") or summary.get("title") or ""
            reports[agent_id] = str(report)[:1000]
        return reports

    def _merge_review_results(self, completeness, quality):
        """合并完整性审查与质量审查结果。"""
        issues = [*completeness.issues, *quality.issues]
        suggestions = []
        for item in [*completeness.suggestions, *quality.suggestions]:
            if item and item not in suggestions:
                suggestions.append(item)
        return completeness.model_copy(update={
            "passed": completeness.passed and quality.passed,
            "score": min(completeness.score, quality.score),
            "issues": issues,
            "suggestions": suggestions,
        })

    def _summarize_profile(self, profile: dict[str, object]) -> dict[str, object]:
        """压缩画像摘要。"""
        if not profile:
            return {}
        profile_json = profile.get("profile_json")
        if isinstance(profile_json, dict):
            dimensions = profile_json.get("dimensions")
            if isinstance(dimensions, dict):
                return {
                    key: value.get("summary")
                    for key, value in dimensions.items()
                    if isinstance(value, dict) and value.get("summary")
                }
        return {
            key: profile.get(key)
            for key in ("username", "major", "grade", "confidence")
            if profile.get(key)
        }

    def _serialize_task(self, task: AgentTask) -> dict[str, object]:
        """序列化 AgentTask。"""
        payload = task.model_dump(mode="json")
        payload["agent_role"] = agent_role(task.agent_id)
        return payload

    async def _emit_created(
        self,
        task_id: str,
        selected: list[str],
        request: ResourceGenerationRequest,
    ) -> None:
        """发送创建事件。"""
        await self.emitter.emit_workflow(
            stage="created",
            status="pending",
            message="资源生成任务已创建",
            payload={
                "task_id": task_id,
                "selected_agents": selected,
                "learning_need_preview": request.learning_need[:120],
                "planning_mode": request.planning_mode,
            },
            progress=0,
        )
