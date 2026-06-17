"""LangGraph 工作流节点函数和辅助工具。

节点拓扑：
  START → planning → worker_node(×N, Send并行) → merge_workers
    → [ppt_node, video_node] (并行) → merge_aggregation → save_node
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.types import Send

from app.infra.database import session_scope
from app.resource.agents import AGENT_REGISTRY
from app.resource.events import AgentRunTracker
from app.resource.persistence import ResourceRepository, db_item_to_agent_result
from app.resource.schemas import (
    AgentResult,
    DownstreamContext,
    ResourceInput,
    TeachingPlan,
)
from app.resource.workflow.audit import (
    BUNDLE_AGENT_ID,
    COORDINATOR_AGENT_ID,
    PPT_AGENT_ID,
    VIDEO_AGENT_ID,
)
from app.resource.workflow.state import ParentState, WorkerInputState, CoverageReport

logger = logging.getLogger(__name__)

AGGREGATION_AGENT_IDS = (PPT_AGENT_ID, VIDEO_AGENT_ID)
BASE_RESOURCE_AGENT_IDS = {"content", "mindmap", "quiz", "code", "reading"}


def select_worker_agents(enabled_agents: list[str], registry: dict[str, Any]) -> list[str]:
    """筛选基础 worker agent（排除 planning、review 和聚合 agent）。"""
    return [
        agent_id
        for agent_id in enabled_agents
        if agent_id in registry
        and agent_id not in ("planning", "review")
        and agent_id not in AGGREGATION_AGENT_IDS
    ]


def build_agent_resource_input(
    *,
    request,
    resource_id: int,
    agent_id: str,
    teaching_plan: TeachingPlan | None,
    profile: dict[str, Any],
    upstream_handoffs: dict[str, DownstreamContext],
    agent_config_extra: dict[str, Any] | None,
):
    """为指定 agent 构建 ResourceInput 输入。"""
    agent_config = request.agent_configs.get(agent_id, {})
    if agent_config_extra:
        agent_config = {**agent_config, **agent_config_extra}
    agent_config["agent_id"] = agent_id
    return ResourceInput(
        resource_id=resource_id,
        learning_need=request.learning_need,
        learning_scenario=request.learning_scenario,
        agent_name=agent_id,
        agent_config=agent_config,
        teaching_plan=teaching_plan,
        profile=profile,
        upstream_handoffs=upstream_handoffs,
    )


def require_downstream_context_for_base_result(agent_id: str, result: AgentResult) -> AgentResult:
    """确保基础 agent 成功时一定有 downstream_context。

    如果基础 agent 成功但未输出 downstream_context，自动合成一个最小版本，
    避免下游聚合 agent 拿不到交接信息。
    """
    if agent_id not in BASE_RESOURCE_AGENT_IDS:
        return result
    if not result.success or result.downstream_context is not None:
        return result
    logger.warning("base agent %s succeeded but emitted no downstream_context; synthesizing", agent_id)
    ctx = DownstreamContext(
        source_agent=agent_id,
        title=result.title or f"{agent_id} 资源",
        one_sentence_summary=(result.summary or "")[:180],
        covered_outline_ids=[],
    )
    return result.model_copy(update={"downstream_context": ctx})


def collect_successful_handoffs(
    results: dict[str, AgentResult],
    teaching_plan: TeachingPlan | None = None,
) -> dict[str, DownstreamContext]:
    """收集所有基础 agent 的成功交接上下文，供聚合 agent 使用。"""
    handoffs: dict[str, DownstreamContext] = {}
    for agent_id, result in results.items():
        if agent_id not in BASE_RESOURCE_AGENT_IDS:
            continue
        if not result.success or result.downstream_context is None:
            continue
        handoffs[agent_id] = result.downstream_context
    if teaching_plan is not None:
        valid_ids = {item.id for item in teaching_plan.outline}
        if valid_ids:
            for agent_id, ctx in handoffs.items():
                filtered = [oid for oid in ctx.covered_outline_ids if oid in valid_ids]
                handoffs[agent_id] = ctx.model_copy(update={"covered_outline_ids": filtered})
    return handoffs


async def persist_result_and_emit_artifact(
    *,
    user_id: int,
    resource_id: int,
    result: AgentResult,
    emitter,
    depends_on_agents: list[str] | None = None,
) -> None:
    """将 Agent 结果持久化到数据库，并发送产物就绪事件。"""
    async with session_scope() as session:
        repository = ResourceRepository(session)
        resource_item = await repository.save_agent_result(
            user_id=user_id,
            resource_id=resource_id,
            result=result,
            depends_on_agents=depends_on_agents,
        )
    agent_id = str(result.metadata.get("agent_id") or "")
    await emitter.emit_artifact_ready(
        agent_id,
        message=f"{agent_id} 资源已保存，可在产物坞预览",
        artifact_id=str(resource_item.id),
        metrics=result.metrics,
    )


# ── Planning node ──────────────────────────────────────────────────────


async def planning_node(state: ParentState) -> dict[str, Any]:
    """规划节点 — 调用 PlanningAgent 生成教学方向与大纲（TeachingPlan）。"""
    planning_input = ResourceInput(
        resource_id=state["resource_id"],
        learning_need=state["request"].learning_need,
        learning_scenario=state["request"].learning_scenario,
        profile=state["profile"],
        agent_config={"enabled_agents": state["request"].enabled_agent_ids()},
    )
    async with AgentRunTracker(
        emitter=state["emitter"],
        agent_id="planning",
        phase="planning",
        message="正在规划教学方向与大纲",
        progress=5,
    ) as planning_tracker:
        planning_result = await AGENT_REGISTRY["planning"](state["emitter"]).generate_resource(planning_input)
        await planning_tracker.finish(
            "教学方向与大纲已生成" if planning_result.success else (planning_result.error or "规划失败"),
            success=planning_result.success,
            metrics={"enabled_agents": len(state["request"].enabled_agent_ids())},
        )

    teaching_plan = None
    if planning_result.success and planning_result.metadata:
        plan_data = planning_result.metadata.get("teaching_plan")
        if isinstance(plan_data, dict):
            teaching_plan = TeachingPlan.model_validate(plan_data)

    if not planning_result.success or teaching_plan is None:
        error_msg = planning_result.error or "规划阶段未返回教学计划"
        logger.error("规划阶段失败: resource_id=%s, error=%s", state["resource_id"], error_msg)
        raise ValueError(error_msg)

    return {"teaching_plan": teaching_plan}


# ── Worker nodes ───────────────────────────────────────────────────────


def base_worker_ids(state: ParentState) -> list[str]:
    enabled = state["request"].enabled_agent_ids()
    return [aid for aid in enabled if aid in BASE_RESOURCE_AGENT_IDS]


def route_workers_or_merge(state: ParentState) -> list[Send] | list[str]:
    """路由：有 worker agent → Send 并行分发，否则直接合并。"""
    worker_ids = base_worker_ids(state)
    if not worker_ids:
        return ["merge_workers"]
    return [
        Send("worker_node", {
            "agent_id": agent_id,
            "user_id": state["user_id"],
            "resource_id": state["resource_id"],
            "request": state["request"],
            "teaching_plan": state["teaching_plan"],
            "profile": state["profile"],
            "run_id": state["run_id"],
            "emitter": state["emitter"],
        })
        for agent_id in worker_ids
    ]


async def worker_node(state: WorkerInputState) -> dict[str, Any]:
    """Worker 节点 — 执行单个基础 agent 的资源生成并持久化结果。"""
    agent_id = state["agent_id"]
    resource_input = build_agent_resource_input(
        request=state["request"],
        resource_id=state["resource_id"],
        agent_id=agent_id,
        teaching_plan=state["teaching_plan"],
        profile=state["profile"],
        upstream_handoffs={},
        agent_config_extra=None,
    )

    agent = AGENT_REGISTRY[agent_id](state["emitter"])
    try:
        async with AgentRunTracker(
            emitter=state["emitter"],
            agent_id=agent_id,
            phase="llm_generating",
            message=f"{agent_id} 模型生成中",
            progress=25,
        ) as tracker:
            result = await agent.generate_resource(resource_input)
            await tracker.step(
                "validating",
                f"{agent_id} 已返回，正在校验与整理结果",
                progress=86,
            )
            await tracker.finish(
                result.summary if result.success else (result.error or f"{agent_id} 生成失败"),
                success=result.success,
                metrics=result.metrics,
            )
    except Exception as exc:
        logger.error("worker_node %s 异常: %s", agent_id, exc, exc_info=True)
        result = AgentResult(
            success=False,
            error=str(exc),
            title=f"{agent_id} 资源",
            summary=f"{agent_id} 生成异常: {exc}",
            metadata={"agent_id": agent_id},
        )
        await state["emitter"].emit_agent(
            agent_id,
            status="failed",
            message=f"{agent_id} 生成异常",
            progress=0,
        )

    if result.success and result.content:
        try:
            await persist_result_and_emit_artifact(
                user_id=state["user_id"],
                resource_id=state["resource_id"],
                result=result,
                emitter=state["emitter"],
            )
        except Exception as exc:
            logger.error("worker_node %s 入库异常: %s", agent_id, exc, exc_info=True)
            # 保留原始成功的 result，仅在 metadata 中标记入库失败
            updated_metadata = {**result.metadata, "persist_error": str(exc)}
            result = result.model_copy(update={"metadata": updated_metadata})

    result = require_downstream_context_for_base_result(agent_id, result)
    return {"results": {agent_id: result}}


# ── Merge workers node ─────────────────────────────────────────────────


async def merge_workers_node(state: ParentState) -> dict[str, Any]:
    """合并 Worker 结果 — 汇总成功/失败计数，检查大纲覆盖情况。"""
    results = state.get("results") or {}
    success_count = sum(1 for r in results.values() if r.success)
    fail_count = sum(1 for r in results.values() if not r.success)
    worker_agents = select_worker_agents(state["request"].enabled_agent_ids(), AGENT_REGISTRY)
    coordinator_status = "failed" if worker_agents and success_count == 0 else "finished"
    message = (
        f"基础资源并行生成完成：成功 {success_count} 个，失败 {fail_count} 个"
        if worker_agents
        else "未选择基础资源，聚合资源将基于教学计划生成"
    )
    await state["emitter"].emit_agent(
        COORDINATOR_AGENT_ID,
        status=coordinator_status,
        message=message,
        progress=70,
    )

    coverage_report = _compute_coverage_report(state)
    if coverage_report.get("critical_missing_ids"):
        critical_titles = []
        plan = state.get("teaching_plan")
        if plan:
            for item in plan.outline:
                if item.id in coverage_report["critical_missing_ids"]:
                    critical_titles.append(item.title)
        await state["emitter"].emit_agent(
            COORDINATOR_AGENT_ID,
            status="running",
            message=f"大纲覆盖警告：核心大纲项未覆盖 — {', '.join(critical_titles)}",
            progress=70,
            phase="coverage_gap_warning",
        )
    elif coverage_report.get("missing_outline_ids"):
        missing_ids = coverage_report["missing_outline_ids"]
        if plan := state.get("teaching_plan"):
            missing_titles = [item.title for item in plan.outline if item.id in missing_ids]
            await state["emitter"].emit_agent(
                COORDINATOR_AGENT_ID,
                status="running",
                message=f"非核心大纲项未覆盖：{', '.join(missing_titles)}",
                progress=70,
            )

    return {"coverage_report": coverage_report}


def _compute_coverage_report(state: ParentState) -> CoverageReport:
    """计算大纲覆盖报告 — 哪些大纲项被覆盖，哪些核心项缺失。"""
    plan = state.get("teaching_plan")
    results = state.get("results") or {}
    if not plan or not plan.outline:
        return CoverageReport(
            covered_outline_ids=[],
            missing_outline_ids=[],
            critical_missing_ids=[],
        )

    all_outline_ids = {item.id for item in plan.outline}
    must_not_miss_ids = {item.id for item in plan.outline if item.must_not_miss}

    covered: set[str] = set()
    for agent_id, result in results.items():
        if not result.success or result.downstream_context is None:
            continue
        for oid in result.downstream_context.covered_outline_ids:
            if oid in all_outline_ids:
                covered.add(oid)

    missing = sorted(all_outline_ids - covered)
    critical_missing = sorted(must_not_miss_ids - covered)

    return CoverageReport(
        covered_outline_ids=sorted(covered),
        missing_outline_ids=missing,
        critical_missing_ids=critical_missing,
    )


# ── Routing after merge ────────────────────────────────────────────────


def route_after_merge(state: ParentState) -> list[str]:
    """路由到聚合 Agent（PPT/Video）或直接保存。

    PPT 和 Video 被选中时并行执行，通过 merge_aggregation barrier 同步后再进 save_node。
    """
    enabled = state["request"].enabled_agent_ids()
    destinations: list[str] = []
    if PPT_AGENT_ID in enabled:
        destinations.append("ppt_node")
    if VIDEO_AGENT_ID in enabled:
        destinations.append("video_node")
    return destinations or ["save_node"]


# ── Aggregation nodes (PPT, Video) ─────────────────────────────────────


async def _run_aggregation_agent(
    state: ParentState,
    *,
    agent_id: str,
    running_message: str,
    extra_input_builder: Any | None = None,
) -> dict[str, Any]:
    """运行聚合 Agent（PPT/Video），不含审核。"""
    emitter = state["emitter"]
    await emitter.emit_agent(
        agent_id,
        status="running",
        message=running_message,
        progress=80,
        phase=f"{agent_id}_generating",
    )

    base_handoffs = collect_successful_handoffs(state["results"], teaching_plan=state.get("teaching_plan"))

    agent_config_extra: dict[str, Any] = {"upstream_handoff_agent_ids": list(base_handoffs.keys())}
    if extra_input_builder:
        extra = extra_input_builder(ResourceInput(
            resource_id=state["resource_id"],
            learning_need=state["request"].learning_need,
            learning_scenario=state["request"].learning_scenario,
            agent_name=agent_id,
            agent_config=state["request"].agent_configs.get(agent_id, {}),
            teaching_plan=state["teaching_plan"],
            profile=state["profile"],
            upstream_handoffs=base_handoffs,
        ))
        if extra:
            agent_config_extra.update(extra)

    agent_input = build_agent_resource_input(
        request=state["request"],
        resource_id=state["resource_id"],
        agent_id=agent_id,
        teaching_plan=state["teaching_plan"],
        profile=state["profile"],
        upstream_handoffs=base_handoffs,
        agent_config_extra=agent_config_extra,
    )

    agent = AGENT_REGISTRY[agent_id](emitter)
    async with AgentRunTracker(
        emitter=emitter,
        agent_id=agent_id,
        phase="llm_generating",
        message=f"{agent_id} 模型生成中",
        progress=80,
    ) as tracker:
        result = await agent.generate_resource(agent_input)
        await tracker.finish(
            result.summary if result.success else (result.error or f"{agent_id} 生成失败"),
            success=result.success,
            metrics=result.metrics,
        )

    if result.success and result.content:
        try:
            await persist_result_and_emit_artifact(
                user_id=state["user_id"],
                resource_id=state["resource_id"],
                result=result,
                emitter=emitter,
                depends_on_agents=list(base_handoffs.keys()),
            )
        except Exception as exc:
            logger.error("聚合 Agent %s 入库异常: %s", agent_id, exc, exc_info=True)
            updated_metadata = {**result.metadata, "persist_error": str(exc)}
            result = result.model_copy(update={"metadata": updated_metadata})

    return {"results": {agent_id: result}}


async def ppt_node(state: ParentState) -> dict[str, Any]:
    """PPT 聚合节点 — 从上游交接构建素材，运行 PptAgent 内部流水线。"""
    from app.resource.agents.ppt import build_resource_material

    def ppt_extra_input(base_input: ResourceInput) -> dict[str, Any] | None:
        material_bundle = build_resource_material(base_input)
        return {"material_bundle": material_bundle.model_dump(mode="json")}

    return await _run_aggregation_agent(
        state,
        agent_id=PPT_AGENT_ID,
        running_message="正在生成 PPT",
        extra_input_builder=ppt_extra_input,
    )


async def video_node(state: ParentState) -> dict[str, Any]:
    """Video 聚合节点 — 运行 VideoAgent 内部流水线生成视频脚本。"""
    return await _run_aggregation_agent(
        state,
        agent_id=VIDEO_AGENT_ID,
        running_message="正在生成讲解视频配置与分镜",
    )


# ── Merge aggregation barrier ──────────────────────────────────────────


async def merge_aggregation_node(state: ParentState) -> dict[str, Any]:
    """聚合 Barrier 节点 — 等待所有聚合 Agent（PPT/Video）完成后再保存。"""
    results = state.get("results") or {}
    agg_results = {aid: r for aid, r in results.items() if aid in AGGREGATION_AGENT_IDS}
    success_count = sum(1 for r in agg_results.values() if r.success)
    fail_count = sum(1 for r in agg_results.values() if not r.success)
    await state["emitter"].emit_agent(
        BUNDLE_AGENT_ID,
        status="running",
        message=f"聚合资源生成完成：成功 {success_count} 个，失败 {fail_count} 个",
        progress=95,
        phase="aggregation_done",
    )
    return {}


# ── Save node ──────────────────────────────────────────────────────────


async def save_node(state: ParentState) -> dict[str, Any]:
    """保存节点 — 组装资源包，将最终结果持久化到数据库。"""
    await state["emitter"].emit_agent(
        BUNDLE_AGENT_ID,
        status="running",
        message="正在组装资源包并保存结果",
        progress=95,
        phase="bundling",
    )

    try:
        async with session_scope() as session:
            repository = ResourceRepository(session)
            await repository.save_generation_results(
                user_id=state["user_id"],
                resource_id=state["resource_id"],
                request=state["request"],
                results=state["results"],
                teaching_plan=state["teaching_plan"],
                coverage_report=state.get("coverage_report"),
            )
            saved_items = await repository.list_resource_items(state["user_id"], state["resource_id"])
            resource = await repository.get_resource(state["user_id"], state["resource_id"])
            current_status = resource.status if resource else "failed"
            success = current_status in ("completed", "partial_completed") and len(saved_items) > 0

            await state["emitter"].emit_agent(
                BUNDLE_AGENT_ID,
                status="finished" if success else "failed",
                message="资源包组装完成" if success else "资源包组装失败",
                progress=100,
            )
            return {"success": success}
    except Exception:
        await state["emitter"].emit_agent(BUNDLE_AGENT_ID, status="failed", message="资源包组装异常", progress=0)
        raise
