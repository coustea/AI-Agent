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

import json
import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.infra.logging import get_logger
from app.resource.registry import (
    AGENT_CLASSES,
    AGENT_META,
    DEPENDS,
    ESTIMATED_MINUTES,
    LAYER_AGENTS,
    MAX_PARALLEL,
    RESOURCE_ORDER,
    ensure_initialized,
    agent_difficulty,
    agent_format,
    agent_layer,
    agent_name,
    agent_objectives,
    agent_output,
    agent_priority,
    agent_role,
    agent_stage,
    agent_time,
    layer_name,
    layer_stage,
)
from app.resource.events import AgentEventEmitter
from app.resource.worker_agents.master_agent import MasterAgent
from app.resource.utils import load_profile_snapshot
from app.resource.schemas import (
    AgentTask,
    GeneratedResourceItem,
    ResourceBundle,
    ResourceGenerationRequest,
    ResourceAgentId,
    ReviewIssue,
    ReviewResult,
    StudyPathStep,
    WorkerState,
)

logger = get_logger(__name__)

# 兼容测试和历史扩展点；实际注册中心中的 AGENT_CLASSES 是唯一类映射来源。
AGENT_CLASS_MAP = AGENT_CLASSES


# =============================================================================
# 数据类
# =============================================================================

@dataclass
class WorkflowContext:
    """工作流执行上下文。"""
    task_id: str    # 任务 ID
    resource_id: int    # 资源ID
    profile: dict[str, Any] # 画像
    selected: list[str]
    timing: dict[str, Any] = field(default_factory=dict)


@dataclass
class DagResult:
    """DAG 执行结果。"""
    results: dict[str, dict[str, Any]] = field(default_factory=dict)
    resources: list[GeneratedResourceItem] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# =============================================================================
# RulePlanner - 规则规划
# =============================================================================

class RulePlanner:
    """规则规划器：根据用户选择的 Agent 和依赖关系，一次性生成完整 DAG。"""

    def plan(self, request: ResourceGenerationRequest) -> list[AgentTask]:
        """根据用户选择和依赖关系生成 AgentTask 列表。"""
        enabled_ids = request.enabled_agent_ids()
        agent_configs = request.agent_configs.model_dump()
        learning_need = request.learning_need

        tasks: list[AgentTask] = []
        for i, agent_id in enumerate(enabled_ids):
            if agent_id not in AGENT_CLASSES:
                continue

            deps = [dep for dep in DEPENDS.get(agent_id, []) if dep in enabled_ids]
            layer = agent_layer(agent_id)

            tasks.append(AgentTask(
                agent_id=agent_id,
                layer=layer,
                layer_name=layer_name(layer),
                task_description=f"根据用户需求「{learning_need[:80]}」生成{agent_name(agent_id)}。",
                depends_on=deps,
                is_explicit=True,
                priority=i,
                config=agent_configs.get(agent_id, {}),
                resource_type=agent_id,
                input_params={"topic": learning_need},
                output_requirements=agent_output(agent_id),
                personalized_constraints=["结合学习者画像"],
                planning_reason=AGENT_META.get(agent_id, {}).get("planning_reason", ""),
                failure_policy="skip_on_dependency_failed",
            ))

        return tasks


# =============================================================================
# 资源审查函数
# =============================================================================

def check_resources(
    resources: list[GeneratedResourceItem],
    selected: list[str],
    failed: list[str],
    skipped: list[str],
) -> tuple[bool, list[str]]:
    """检查每个 Agent 是否有生成内容。返回 (passed, issues)。"""
    issues: list[str] = []

    if not resources:
        return False, ["没有生成任何资源"]

    # 检查每个启用的 Agent 是否有产出
    resource_map = {res.type.value: res for res in resources}
    for agent_id in selected:
        if agent_id in failed:
            issues.append(f"{agent_id} 生成失败")
        elif agent_id in skipped:
            issues.append(f"{agent_id} 被跳过")
        elif agent_id not in resource_map:
            issues.append(f"{agent_id} 未产出结果")

    return len(resources) > 0, issues


class ReviewerAgent:
    """ReviewerAgent：审查资源完整性，不生成资源正文。"""

    def review(
        self,
        *,
        request: ResourceGenerationRequest,
        resources: list[GeneratedResourceItem],
        failed_agents: list[str],
        skipped_agents: list[str] | None = None,
        errors: list[str],
    ) -> ReviewResult:
        """审查已生成资源，并区分失败与跳过 Agent。"""
        skipped_agents = skipped_agents or []
        _, missing_issues = check_resources(
            resources=resources,
            selected=request.enabled_agent_ids(),
            failed=failed_agents,
            skipped=skipped_agents,
        )

        issues: list[ReviewIssue] = []
        suggestions: list[str] = []
        for message in missing_issues:
            level = "error" if "失败" in message else "warning"
            issues.append(ReviewIssue(level=level, message=message, suggestion="可重新生成对应资源"))

        for error in errors:
            issues.append(ReviewIssue(level="error", message=str(error), suggestion="检查对应 Agent 日志后重试"))

        if skipped_agents:
            suggestions.append("部分 Agent 因依赖未满足被跳过，可先修复上游资源后重试。")
        if failed_agents:
            suggestions.append("部分 Agent 生成失败，已保留成功生成的资源。")

        score = 100
        score -= min(len(failed_agents) * 20, 60)
        score -= min(len(skipped_agents) * 10, 30)
        score -= min(len(errors) * 10, 30)
        score = max(0, score)

        return ReviewResult(
            passed=bool(resources),
            score=score,
            issues=issues,
            suggestions=suggestions,
            failed_agents=failed_agents,
            skipped_agents=skipped_agents,
        )


class AssemblerAgent:
    """AssemblerAgent：组装最终 ResourceBundle，不负责首次发送单个资源。"""

    def assemble(
        self,
        *,
        task_id: str,
        resource_id: str,
        request: ResourceGenerationRequest,
        resources: list[GeneratedResourceItem],
        review_result: ReviewResult,
        failed_agents: list[str],
        skipped_agents: list[str] | None = None,
        timing: dict[str, Any] | None = None,
    ) -> ResourceBundle:
        """根据审查结果组装最终资源包。"""
        skipped_agents = skipped_agents or []
        title = request.output_options.final_bundle_title or "个性化学习资源包"
        study_path = _build_study_path(resources) if request.output_options.include_study_path else []

        if not resources:
            status = "failed"
        elif failed_agents:
            status = "partial_completed"
        elif review_result.issues:
            status = "completed_with_warnings"
        else:
            status = "completed"

        metadata: dict[str, Any] = {
            "agent_count": len(resources),
            "failed_agents": failed_agents,
            "skipped_agents": skipped_agents,
        }
        if timing:
            metadata["timing"] = timing

        return ResourceBundle(
            id=str(resource_id),
            task_id=task_id,
            title=title,
            learning_need=request.learning_need,
            selected_agents=[selection for selection in request.selected_agents if selection.enabled],
            resources=resources,
            study_path=study_path,
            review_result=review_result,
            status=status,
            metadata=metadata,
        )


# =============================================================================
# 资源包组装函数
# =============================================================================

def build_bundle(
    *,
    task_id: str,
    resource_id: int,
    request: ResourceGenerationRequest,
    resources: list[GeneratedResourceItem],
    failed: list[str],
    skipped: list[str],
    review_result: ReviewResult | None = None,
    timing: dict[str, Any] | None = None,
) -> ResourceBundle:
    """组装资源包。"""
    review_result = review_result or ReviewerAgent().review(
        request=request,
        resources=resources,
        failed_agents=failed,
        skipped_agents=skipped,
        errors=[],
    )
    return AssemblerAgent().assemble(
        task_id=task_id,
        resource_id=str(resource_id),
        request=request,
        resources=resources,
        review_result=review_result,
        failed_agents=failed,
        skipped_agents=skipped,
        timing=timing,
    )


def _build_study_path(resources: list[GeneratedResourceItem]) -> list[StudyPathStep]:
    """构建学习路径。"""
    resource_types = {res.type for res in resources}
    path: list[StudyPathStep] = []

    step_titles = {
        "content": "先阅读课程讲解文档",
        "diagram": "查看知识图解",
        "mindmap": "浏览思维导图",
        "code": "学习代码实操案例",
        "quiz": "完成练习题",
        "reading": "阅读拓展材料",
    }

    step_reasons = {
        "content": "建立对主题的整体理解",
        "diagram": "通过可视化加深理解",
        "mindmap": "梳理知识结构",
        "code": "通过实践加深理解",
        "quiz": "检验学习效果",
        "reading": "扩展知识面",
    }

    order = 1
    for resource_type in RESOURCE_ORDER:
        if resource_type in resource_types:
            path.append(StudyPathStep(
                order=order,
                resource_type=ResourceAgentId(resource_type),
                title=step_titles.get(resource_type, f"学习 {resource_type}"),
                reason=step_reasons.get(resource_type, "巩固学习"),
                estimated_time=ESTIMATED_MINUTES.get(resource_type),
            ))
            order += 1

    return path


# =============================================================================
# ResourceWorkflow - 主编排器
# =============================================================================

class ResourceWorkflow:
    """资源生成工作流。协调 MasterAgent、WorkerAgents。"""

    def __init__(self, emitter: AgentEventEmitter, resource_store: Any):
        self.emitter = emitter
        self.store = resource_store
        self.master = MasterAgent()
        self.master_agent = self.master
        self.rule_planner = RulePlanner()

    async def run(self, user_id: int, request: ResourceGenerationRequest) -> dict[str, Any]:
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

            return {"success": bundle.status != "failed", "results": result.results, "bundle": bundle.model_dump(mode="json")}

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
        await self.emitter.emit_workflow(stage="profile", status="running", message="正在加载学习者画像", progress=5)
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
            )
            layer_plan = await self.master_agent.plan(context)
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
                candidates = [a for a in LAYER_AGENTS.get(layer, []) if a in selected and a in AGENT_CLASSES]
                upstream_summaries = self._build_upstream_summaries(tasks, {})
                upstream_reports = self._build_reports(upstream_summaries)

                await self.emitter.emit_event(
                    event_type="planning",
                    stage="planning",
                    agent="master",
                    status="running",
                    message=f"MasterAgent 正在规划 {layer_name(layer)}",
                    progress=8 + layer * 3,
                    payload={"layer": layer, "layer_name": layer_name(layer), "candidate_agents": candidates, "planning_mode": "layer_llm"},
                )

                context = PlanningContext(
                    layer=layer,
                    question=request,
                    user_explicit_selection=selected,
                    implicit_dependencies=[],
                    upstream_results=upstream_summaries,
                    upstream_reports=upstream_reports,
                )
                layer_plan = await self.master_agent.plan(context)

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

    async def _run_dag(
        self,
        tasks: list[AgentTask],
        ctx: WorkflowContext,
        request: ResourceGenerationRequest,
    ) -> DagResult:
        """执行 DAG 调度。"""
        result = DagResult()
        pending: dict[str, AgentTask] = {t.agent_id: t for t in tasks if t.enabled}
        running: dict[asyncio.Task, AgentTask] = {}
        done: set[str] = set()
        failed_set: set[str] = set()
        skipped_set: set[str] = set()
        all_ids = set(pending)

        if not pending:
            await self.emitter.emit_workflow(
                stage="layer_0",
                status="skipped",
                message="没有可执行的资源生成 Agent",
                payload={"completed_agents": [], "failed_agents": [], "skipped_agents": []},
                progress=15,
            )
            return result

        total = len(pending)
        layer_started: set[int] = set()
        layer_terminal: dict[int, set[str]] = {}

        def progress() -> int:
            ratio = len(done) + len(failed_set) + len(skipped_set) / total if total else 1
            return min(90, 15 + int(ratio * 75))

        async def start_ready() -> None:
            """调度就绪的 Agent。"""
            while len(running) < MAX_PARALLEL:
                scheduled = False
                for task in list(pending.values()):
                    ready, degraded, missing, failed_deps = self._check_deps(task, all_ids, done, failed_set, skipped_set)
                    if not ready:
                        if (missing or failed_deps) and task.failure_policy == "skip_on_dependency_failed":
                            pending.pop(task.agent_id, None)
                            await self._skip_agent(task, missing, failed_deps, skipped_set, result, layer_terminal)
                        continue

                    pending.pop(task.agent_id)
                    await self._emit_layer_start(task, layer_started, tasks, progress)

                    running_task = asyncio.create_task(self._execute_agent_task(
                        agent_task=task,
                        ctx=ctx,
                        request=request,
                        upstream=self._pick_deps(task, result.results),
                        degraded=degraded,
                        missing=missing,
                        failed_deps=failed_deps,
                    ))
                    running[running_task] = task
                    task._start_time = time.time()
                    scheduled = True
                    break
                if not scheduled:
                    break

        # 主循环
        while pending or running:
            await start_ready()
            if not running:
                for task in list(pending.values()):
                    pending.pop(task.agent_id, None)
                    await self._skip_agent(
                        task,
                        [d for d in task.depends_on if d not in all_ids],
                        [d for d in task.depends_on if d in failed_set or d in skipped_set],
                        skipped_set,
                        result,
                        layer_terminal,
                    )
                continue

            finished, _ = await asyncio.wait(running.keys(), return_when=asyncio.FIRST_COMPLETED)
            for finished_task in finished:
                task = running.pop(finished_task)
                await self._handle_agent_result(
                    finished_task, task, ctx, result, done, failed_set, layer_terminal, progress
                )

        return result

    async def _execute_planned_tasks_dag(
        self,
        *,
        planned_tasks: list[AgentTask],
        user_id: int,
        resource_id: int,
        request: ResourceGenerationRequest,
        agent_context: dict[str, Any],
        raw_results: dict[str, dict[str, Any]],
        all_resources: list[GeneratedResourceItem],
        failed_agents: list[str],
        skipped_agents: list[str],
        errors: list[str],
        user_explicit_selection: list[str],
    ) -> None:
        """兼容旧测试入口：执行已规划任务并回填可变结果容器。"""
        _ = user_id, user_explicit_selection
        ctx = WorkflowContext(
            task_id=str(uuid4()),
            resource_id=resource_id,
            profile=agent_context.get("learner_profile", {}),
            selected=request.enabled_agent_ids(),
            timing={"agents": {}},
        )
        result = await self._run_dag(planned_tasks, ctx, request)
        raw_results.update(result.results)
        all_resources.extend(result.resources)
        failed_agents.extend(result.failed)
        skipped_agents.extend(result.skipped)
        errors.extend(result.errors)

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
                user_id=ctx.resource_id,
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

        review_result = ReviewerAgent().review(
            request=request,
            resources=resources,
            failed_agents=result.failed,
            skipped_agents=result.skipped,
            errors=result.errors,
        )
        if review_result.issues:
            logger.warning("[ResourceWorkflow] 资源检查发现问题: %s", [issue.message for issue in review_result.issues])

        bundle = build_bundle(
            task_id=ctx.task_id,
            resource_id=ctx.resource_id,
            request=request,
            resources=resources,
            failed=result.failed,
            skipped=result.skipped,
            review_result=review_result,
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
    # Agent 执行
    # =========================================================================

    async def _run_agent(
        self,
        *,
        task: AgentTask,
        ctx: WorkflowContext,
        request: ResourceGenerationRequest,
        upstream: dict[str, dict[str, Any]],
        degraded: bool,
        missing: list[str],
        failed_deps: list[str],
    ) -> tuple[str, dict[str, Any], bool, AgentTask]:
        """执行单个 Agent。"""
        agent_id = task.agent_id
        agent_cls = AGENT_CLASSES.get(agent_id)
        if agent_cls is None:
            return agent_id, {"success": False, "error": f"Unknown agent: {agent_id}"}, task.is_explicit, task

        stage = layer_stage(task.layer)
        self.emitter.bind_agent_stage(agent_id, stage)

        await self.emitter.emit_agent_step(
            agent=agent_id,
            message=f"{agent_role(agent_id)}正在准备生成",
            stage=stage,
            status="running",
            action="prepare_generation",
            current_step=1,
            total_steps=3,
            step_label="准备生成",
            payload={
                "layer": task.layer,
                "layer_name": task.layer_name,
                "agent_id": agent_id,
                "agent_role": agent_role(agent_id),
                "task_description": task.task_description,
                "depends_on": task.depends_on,
                "resource_type": task.resource_type or agent_id,
                "upstream_agents": list(upstream.keys()),
                "has_profile": bool(ctx.profile),
                "learning_need_preview": request.learning_need[:120],
                "input_params": task.input_params,
                "output_requirements": task.output_requirements,
                "personalized_constraints": task.personalized_constraints,
                "planning_reason": task.planning_reason,
            },
        )

        worker = agent_cls(ctx.resource_id, ctx.resource_id, emitter=self.emitter)
        task_payload = {
            "learning_need": request.learning_need,
            "task_description": task.task_description,
            "planning_reason": task.planning_reason,
        }
        dep_reports = {dep: upstream[dep].get("summary", "") for dep in task.depends_on if dep in upstream}

        await self.emitter.emit_agent_step(
            agent=agent_id,
            stage=stage,
            status="running",
            message=f"{agent_role(agent_id)}正在调用模型生成内容",
            action="llm_generating",
            current_step=2,
            total_steps=3,
            step_label="模型生成",
            payload={"agent_id": agent_id, "depends_on": task.depends_on},
        )

        state = WorkerState(
            user_id=ctx.resource_id,
            resource_id=ctx.resource_id,
            agent_name=agent_id,
            task=task_payload,
            learner_profile=ctx.profile,
            agent_config=task.config,
            workflow_plan=[],
            layer_index=task.layer,
            upstream_results=upstream,
            dependency_reports=dep_reports,
            learning_scenario=request.learning_scenario.value,
            planner_input_params=task.input_params,
            output_requirements=task.output_requirements,
            personalized_constraints=task.personalized_constraints,
            degraded=degraded,
            missing_dependencies=missing,
            failed_dependencies=failed_deps,
        )

        result = await worker.run(state)
        return agent_id, result.model_dump() if hasattr(result, "model_dump") else dict(result), task.is_explicit, task

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
        """兼容旧测试入口：执行单个 Agent 任务。"""
        return await self._run_agent(
            task=agent_task,
            ctx=ctx,
            request=request,
            upstream=upstream,
            degraded=degraded,
            missing=missing,
            failed_deps=failed_deps,
        )

    async def _handle_agent_result(
        self,
        finished_task: asyncio.Task,
        task: AgentTask,
        ctx: WorkflowContext,
        result: DagResult,
        done: set[str],
        failed_set: set[str],
        layer_terminal: dict[int, set[str]],
        progress,
    ) -> None:
        """处理 Agent 执行结果。"""
        agent_elapsed_ms = 0
        if hasattr(task, "_start_time"):
            agent_elapsed_ms = int((time.time() - task._start_time) * 1000)

        try:
            agent_id, agent_result, is_explicit, agent_task = finished_task.result()
        except Exception as exc:
            agent_id = task.agent_id
            agent_result = {"success": False, "error": str(exc)}
            is_explicit = task.is_explicit
            agent_task = task

        if ctx.timing is not None and agent_id:
            ctx.timing["agents"][agent_id] = agent_elapsed_ms
            logger.info("[ResourceWorkflow] Agent %s 完成: %dms", agent_id, agent_elapsed_ms)

        result.results[agent_id] = agent_result
        stage = layer_stage(task.layer)

        if agent_result.get("success"):
            try:
                saved = await self._save_result(agent_id, agent_result, is_explicit, agent_task, ctx, stage)
                if saved:
                    done.add(agent_id)
                    result.resources.append(saved)
                    layer_terminal.setdefault(task.layer, set()).add(agent_id)
            except Exception as exc:
                agent_result = {"success": False, "error": str(exc)}
                result.results[agent_id] = agent_result
                failed_set.add(agent_id)
                result.failed.append(agent_id)
                result.errors.append(f"{agent_id} 生成失败: {exc}")
        else:
            failed_set.add(agent_id)
            result.failed.append(agent_id)
            result.errors.append(f"{agent_id} 生成失败: {agent_result.get('error', 'unknown')}")
            await self.emitter.emit_agent(
                agent=agent_id,
                status="failed",
                stage=stage,
                message=f"{agent_role(agent_id)}生成失败",
                payload={
                    "error": agent_result.get("error", "unknown"),
                    "layer": task.layer,
                    "layer_name": task.layer_name,
                    "task_description": task.task_description,
                    "elapsed_ms": agent_elapsed_ms,
                },
            )
            layer_terminal.setdefault(task.layer, set()).add(agent_id)

    async def _save_result(
        self,
        agent_id: str,
        result: dict[str, Any],
        is_explicit: bool,
        task: AgentTask,
        ctx: WorkflowContext,
        stage: str,
    ) -> GeneratedResourceItem | None:
        """保存成功 Agent 的产物。"""
        item = self._make_resource(agent_id, result, task.depends_on, task)
        try:
            saved = await self.store.save_resource_item(resource_id=ctx.resource_id, user_id=ctx.resource_id, item=item)
            if saved.id is not None:
                item.id = str(saved.id)
            await self.emitter.emit_agent(
                agent=agent_id,
                status="success",
                stage=stage,
                message=f"{agent_role(agent_id)}生成完成",
                payload={
                    "resource_id": item.id,
                    "resource_type": item.type.value,
                    "title": item.title,
                    "summary": item.summary,
                    "is_explicit": is_explicit,
                },
            )
            await self.emitter.emit_resource(agent=agent_id, resource=item, stage=stage, message=f"{agent_role(agent_id)}生成完成")
            return item
        except Exception as exc:
            await self.emitter.emit_agent(agent=agent_id, status="failed", stage=stage, message=f"{agent_role(agent_id)}数据库保存失败")
            raise RuntimeError(f"{agent_id} 保存失败: {exc}") from exc

    async def _skip_agent(
        self,
        task: AgentTask,
        missing: list[str],
        failed_deps: list[str],
        skipped_set: set[str],
        result: DagResult,
        layer_terminal: dict[int, set[str]],
    ) -> None:
        """跳过 Agent。"""
        skipped_set.add(task.agent_id)
        result.skipped.append(task.agent_id)
        stage = layer_stage(task.layer)

        await self.emitter.emit_agent(
            agent=task.agent_id,
            status="skipped",
            stage=stage,
            message=f"{agent_role(task.agent_id)}因依赖未满足已跳过",
            payload={
                "skipped_reason": "依赖 Agent 失败或缺失",
                "missing_dependencies": missing,
                "failed_dependencies": failed_deps,
                "layer": task.layer,
                "layer_name": task.layer_name,
                "agent_id": task.agent_id,
                "agent_role": agent_role(task.agent_id),
                "depends_on": task.depends_on,
                "task_description": task.task_description,
                "schedule_mode": "dependency_failed",
            },
        )
        layer_terminal.setdefault(task.layer, set()).add(task.agent_id)

    # =========================================================================
    # 辅助方法
    # =========================================================================

    def _check_deps(
        self,
        task: AgentTask,
        all_ids: set[str],
        done: set[str],
        failed_set: set[str],
        skipped_set: set[str],
    ) -> tuple[bool, bool, list[str], list[str]]:
        """检查依赖状态。"""
        deps = task.depends_on or []
        missing = [d for d in deps if d not in all_ids]
        failed_deps = [d for d in deps if d in failed_set or d in skipped_set]
        unfinished = [d for d in deps if d in all_ids and d not in done and d not in failed_set and d not in skipped_set]

        if missing or failed_deps:
            if task.failure_policy == "skip_on_dependency_failed":
                return False, False, missing, failed_deps
            if task.failure_policy == "degraded_run" and not unfinished:
                return True, bool(missing or failed_deps), missing, failed_deps
            if task.failure_policy == "ignore_dependency" and not unfinished:
                return True, False, missing, failed_deps
            return False, False, missing, failed_deps

        return not unfinished, False, [], []

    def _pick_deps(self, task: AgentTask, results: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        """提取显式依赖的上游摘要。"""
        upstream: dict[str, dict[str, Any]] = {}
        for dep_id in task.depends_on:
            result = results.get(dep_id)
            if isinstance(result, dict):
                upstream[dep_id] = {
                    "success": result.get("success", False),
                    "title": result.get("title") or "",
                    "summary": result.get("summary") or "",
                    "summary_data": result.get("summary_data") or {},
                    "file_type": result.get("file_type") or "",
                    "metadata": {"agent_id": dep_id, "resource_type": result.get("file_type") or ""},
                }
        return upstream

    def _build_upstream_summaries(self, tasks: list[AgentTask], results: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        """构建上游摘要。"""
        return {t.agent_id: self._pick_deps(t, results) for t in tasks}

    def _build_reports(self, summaries: dict[str, dict[str, Any]]) -> dict[str, str]:
        """构建交接报告。"""
        reports: dict[str, str] = {}
        for agent_id, summary in summaries.items():
            report = summary.get("summary") or summary.get("title") or ""
            reports[agent_id] = str(report)[:1000]
        return reports

    def _make_resource(
        self,
        agent_id: str,
        result: dict[str, Any],
        depends_on: list[str],
        task: AgentTask | None = None,
    ) -> GeneratedResourceItem:
        """构建资源项。"""
        raw = result.get("content", "")
        parsed: Any = raw
        fmt = agent_format(agent_id)

        if agent_id == "diagram":
            parsed = self._normalize_diagram(raw)
            fmt = "mermaid" if parsed.get("render_format") == "mermaid" else "json"
        elif agent_id == "code":
            parsed = self._normalize_code(raw)
            fmt = "json"
        elif agent_id == "reading":
            parsed = self._normalize_reading(raw)
            fmt = "json"
        elif fmt == "json":
            try:
                parsed = json.loads(raw) if isinstance(raw, str) else raw
            except Exception:
                parsed = {"raw": raw}

        summary_data = result.get("summary_data") or {}
        metadata = dict(result.get("metadata") or {})
        metadata["summary_data"] = summary_data
        metadata.update({
            "agent": f"{agent_id.capitalize()}Agent",
            "agent_role": agent_role(agent_id),
            "depends_on": depends_on,
            "knowledge_points": self._extract_knowledge_points(agent_id, result, task),
            "difficulty": metadata.get("difficulty") or agent_difficulty(agent_id),
            "suitable_stage": metadata.get("suitable_stage") or agent_stage(agent_id),
            "estimated_time": metadata.get("estimated_time") or agent_time(agent_id),
            "personalized_reason": (task.planning_reason if task else None) or metadata.get("personalized_reason") or "",
            "learning_objectives": metadata.get("learning_objectives") or agent_objectives(agent_id),
            "prerequisites": metadata.get("prerequisites") or depends_on,
            "resource_priority": metadata.get("resource_priority") or agent_priority(agent_id),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

        return GeneratedResourceItem(
            type=ResourceAgentId(agent_id),
            title=result.get("title") or f"学习资源 - {agent_id}",
            format=fmt,
            content=parsed,
            summary=result.get("summary") or f"{agent_id} 资源已生成",
            summary_data=summary_data,
            execution_report=result.get("execution_report"),
            metadata=metadata,
        )

    def _normalize_diagram(self, raw: Any) -> dict[str, Any]:
        """标准化 diagram 内容。"""
        if isinstance(raw, dict):
            if "source" in raw:
                return raw
            render = raw.get("render")
            if isinstance(render, dict) and render.get("source"):
                return {
                    "diagram_type": raw.get("diagram_type") or raw.get("type") or "hierarchy",
                    "render_format": render.get("engine", "mermaid"),
                    "source": render.get("source", ""),
                    "description": raw.get("description") or raw.get("summary", "知识图解"),
                }
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                return self._normalize_diagram(parsed)
            except Exception:
                return {"diagram_type": "hierarchy", "render_format": "mermaid", "source": raw, "description": "知识图解"}
        return {"diagram_type": "hierarchy", "render_format": "mermaid", "source": "", "description": "知识图解"}

    def _normalize_code(self, raw: Any) -> dict[str, Any]:
        """标准化 code 内容。"""
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
            return {
                "language": "python",
                "code": raw,
                "explanation": "代码实操案例",
                "input_example": "",
                "output_example": "",
                "complexity": {"time": "", "space": ""},
                "run_steps": [],
                "debug_tips": [],
                "exercises": [],
            }
        return {"language": "python", "code": "", "explanation": "", "input_example": "", "output_example": "", "complexity": {"time": "", "space": ""}, "run_steps": [], "debug_tips": [], "exercises": []}

    def _normalize_reading(self, raw: Any) -> dict[str, Any]:
        """标准化 reading 内容。"""
        if isinstance(raw, dict):
            if "items" in raw:
                return raw
            return {"items": [raw]}
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                return self._normalize_reading(parsed)
            except Exception:
                return {"items": [{"title": "拓展阅读", "type": "article", "description": raw, "reason": "", "difficulty": "medium", "url": ""}]}
        return {"items": []}

    def _extract_knowledge_points(self, agent_id: str, result: dict[str, Any], task: AgentTask | None) -> list[str]:
        """提取知识点。"""
        metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
        points = metadata.get("knowledge_points")
        if not points and task:
            points = task.input_params.get("knowledge_points")
        if isinstance(points, list):
            return [str(item) for item in points if item]
        return [agent_id]

    def _summarize_profile(self, profile: dict[str, Any]) -> dict[str, Any]:
        """压缩画像摘要。"""
        if not profile:
            return {}
        profile_json = profile.get("profile_json")
        if isinstance(profile_json, dict):
            dimensions = profile_json.get("dimensions")
            if isinstance(dimensions, dict):
                return {key: value.get("summary") for key, value in dimensions.items() if isinstance(value, dict) and value.get("summary")}
        return {key: profile.get(key) for key in ("username", "major", "grade", "confidence") if profile.get(key)}

    def _serialize_task(self, task: AgentTask) -> dict[str, Any]:
        """序列化 AgentTask。"""
        payload = task.model_dump(mode="json")
        payload["agent_role"] = agent_role(task.agent_id)
        return payload

    async def _emit_created(self, task_id: str, selected: list[str], request: ResourceGenerationRequest) -> None:
        """发送创建事件。"""
        await self.emitter.emit_workflow(
            stage="created",
            status="pending",
            message="资源生成任务已创建",
            payload={"task_id": task_id, "selected_agents": selected, "learning_need_preview": request.learning_need[:120], "planning_mode": request.planning_mode},
            progress=0,
        )

    async def _emit_layer_start(self, task: AgentTask, layer_started: set[int], tasks: list[AgentTask], progress) -> None:
        """发送层开始事件。"""
        layer = task.layer
        if layer in layer_started:
            return
        layer_started.add(layer)
        layer_tasks = [t for t in tasks if t.layer == layer and t.enabled]
        await self.emitter.emit_workflow(
            stage=layer_stage(layer),
            status="running",
            message=f"开始执行{layer_name(layer)}",
            payload={"layer": layer, "layer_name": layer_name(layer), "agents": [self._serialize_task(t) for t in layer_tasks], "schedule_mode": "dag_dependency_ready"},
            progress=progress(),
        )
