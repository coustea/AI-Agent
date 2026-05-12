# -*- coding: utf-8 -*-
"""DAG 调度器。

负责 Agent 任务的 DAG 调度，管理依赖关系和并发执行。
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from app.infra.logging import get_logger
from app.resource.registry import MAX_PARALLEL, agent_role, layer_name, layer_stage
from app.resource.schemas import AgentTask, ResourceGenerationRequest

logger = get_logger(__name__)


@dataclass
class DagResult:
    """DAG 执行结果。"""
    results: dict[str, dict[str, Any]] = field(default_factory=dict)
    resources: list[Any] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class WorkflowContext:
    """工作流执行上下文。"""
    task_id: str
    user_id: int
    resource_id: int
    profile: dict[str, Any]
    selected: list[str]
    timing: dict[str, Any] = field(default_factory=dict)


class DagScheduler:
    """DAG 调度器：管理 Agent 任务的依赖关系和并发执行。"""

    def __init__(self, emitter: Any) -> None:
        self.emitter = emitter

    async def run(
        self,
        tasks: list[AgentTask],
        ctx: WorkflowContext,
        request: ResourceGenerationRequest,
        execute_agent: Callable,
        handle_result: Callable,
    ) -> DagResult:
        """执行 DAG 调度。

        Args:
            tasks: 要执行的 Agent 任务列表
            ctx: 工作流上下文
            request: 资源生成请求
            execute_agent: 执行单个 Agent 的回调函数
            handle_result: 处理 Agent 结果的回调函数

        Returns:
            DagResult: DAG 执行结果
        """
        result = DagResult()
        pending: dict[str, AgentTask] = {t.agent_id: t for t in tasks if t.enabled}
        running: dict[asyncio.Task, AgentTask] = {}
        done: set[str] = set()
        failed_set: set[str] = set()
        skipped_set: set[str] = set()
        all_ids = set(pending)

        if not pending:
            await self._emit_empty_dag()
            return result

        total = len(pending)
        layer_started: set[int] = set()
        layer_terminal: dict[int, set[str]] = {}

        def progress() -> int:
            ratio = (len(done) + len(failed_set) + len(skipped_set)) / total if total else 1
            return min(90, 15 + int(ratio * 75))

        async def start_ready() -> None:
            """调度就绪的 Agent。"""
            while len(running) < MAX_PARALLEL:
                scheduled = False
                for task in list(pending.values()):
                    ready, degraded, missing, failed_deps = self._check_deps(
                        task, all_ids, done, failed_set, skipped_set
                    )
                    if not ready:
                        if (missing or failed_deps) and task.failure_policy == "skip_on_dependency_failed":
                            pending.pop(task.agent_id, None)
                            await self._skip_agent(
                                task, missing, failed_deps, skipped_set, result, layer_terminal
                            )
                        continue

                    pending.pop(task.agent_id)
                    await self._emit_layer_start(task, layer_started, tasks, progress)

                    running_task = asyncio.create_task(execute_agent(
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
                start_time = getattr(task, "_start_time", None)

                try:
                    agent_id, agent_result, is_explicit, agent_task = finished_task.result()
                except Exception as exc:
                    agent_id = task.agent_id
                    agent_result = {"success": False, "error": str(exc)}
                    is_explicit = task.is_explicit
                    agent_task = task

                await handle_result(
                    agent_id=agent_id,
                    agent_result=agent_result,
                    is_explicit=is_explicit,
                    task=agent_task,
                    ctx=ctx,
                    result=result,
                    done=done,
                    failed_set=failed_set,
                    layer_terminal=layer_terminal,
                    start_time=start_time,
                )

        return result

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
        unfinished = [
            d for d in deps
            if d in all_ids and d not in done and d not in failed_set and d not in skipped_set
        ]

        if missing or failed_deps:
            if task.failure_policy == "skip_on_dependency_failed":
                return False, False, missing, failed_deps
            if task.failure_policy == "degraded_run" and not unfinished:
                return True, bool(missing or failed_deps), missing, failed_deps
            if task.failure_policy == "ignore_dependency" and not unfinished:
                return True, False, missing, failed_deps
            return False, False, missing, failed_deps

        return not unfinished, False, [], []

    def _pick_deps(
        self,
        task: AgentTask,
        results: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
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

    async def _emit_empty_dag(self) -> None:
        """发送空 DAG 事件。"""
        await self.emitter.emit_workflow(
            stage="layer_0",
            status="skipped",
            message="没有可执行的资源生成 Agent",
            payload={"completed_agents": [], "failed_agents": [], "skipped_agents": []},
            progress=15,
        )

    async def _emit_layer_start(
        self,
        task: AgentTask,
        layer_started: set[int],
        tasks: list[AgentTask],
        progress: Callable,
    ) -> None:
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
            payload={
                "layer": layer,
                "layer_name": layer_name(layer),
                "agents": [self._serialize_task(t) for t in layer_tasks],
                "schedule_mode": "dag_dependency_ready",
            },
            progress=progress(),
        )

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

    def _serialize_task(self, task: AgentTask) -> dict[str, Any]:
        """序列化 AgentTask。"""
        payload = task.model_dump(mode="json")
        payload["agent_role"] = agent_role(task.agent_id)
        return payload