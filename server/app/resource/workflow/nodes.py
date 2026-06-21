"""LangGraph 工作流节点函数和辅助工具。

节点拓扑：
  START → planning → worker_node(×N, Send并行) → merge_workers
    → [ppt_node, video_node] (并行) → merge_aggregation → save_node

重构说明（v2）：
- 普通 Agent 通过 execution.execute_resource_agent 执行
- 验证通过 validation.validate_agent_result 完成
- 持久化由 execution 层直接调用 service.save_agent_result
- 最终状态由 save_node 调用 service.finalize_generation 从数据库计算
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.types import Send
from sqlalchemy import select

from app.infra.database import session_scope
from app.infra.models import GeneratedResourceItem
from app.resource.agents import AGENT_REGISTRY
from app.infra.agent_events import AgentRunTracker
from app.resource.service import ResourceService
from app.resource.workflow.execution import execute_resource_agent, AgentOutcome
from app.resource.workflow.validation import validate_agent_result

from app.resource.schemas import (
    AgentResult,
    DownstreamContext,
    ResourceInput,
    TeachingPlan,
)
from app.resource.workflow.state import ParentState, WorkerInputState, CoverageReport, AgentFailure
from app.resource.constants import (
    BUNDLE_AGENT_ID,
    COORDINATOR_AGENT_ID,
    PPT_AGENT_ID,
    VIDEO_AGENT_ID,
    AGGREGATION_AGENT_IDS,
)

logger = logging.getLogger(__name__)

BASE_RESOURCE_AGENT_IDS = {"content", "mindmap", "quiz", "code", "reading"}


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


async def get_handoffs(
    resource_id: int,
    user_id: int,
) -> dict[str, DownstreamContext]:
    """获取成功持久化的基础 Agent handoffs。"""
    async with session_scope() as session:
        service = ResourceService(session)
        items = await service.list_resource_items(user_id, resource_id)

    handoffs: dict[str, DownstreamContext] = {}
    for item in items:
        if item.agent_type not in BASE_RESOURCE_AGENT_IDS:
            continue
        if item.status != "completed":
            continue
        if item.downstream_context and isinstance(item.downstream_context, dict):
            handoffs[item.agent_type] = DownstreamContext.model_validate(item.downstream_context)
    return handoffs


async def get_coverage(
    resource_id: int,
    teaching_plan: TeachingPlan | None,
) -> CoverageReport:
    """获取 Agent 覆盖情况。"""
    if not teaching_plan or not teaching_plan.outline:
        return CoverageReport(
            covered_outline_ids=[],
            missing_outline_ids=[],
            critical_missing_ids=[],
        )

    async with session_scope() as session:
        service = ResourceService(session)
        # 使用 user_id=0 因为我们只需要 resource_id 级别的数据
        # 实际上 list_resource_items 需要 user_id，这里用子查询
        stmt = (
            select(GeneratedResourceItem.downstream_context)
            .where(GeneratedResourceItem.resource_id == resource_id)
            .where(GeneratedResourceItem.status == "completed")
            .where(GeneratedResourceItem.agent_type.in_(BASE_RESOURCE_AGENT_IDS))
        )
        result = await session.exec(stmt)
        rows = result.all()

    all_outline_ids = {item.id for item in teaching_plan.outline}
    must_not_miss_ids = {item.id for item in teaching_plan.outline if item.must_not_miss}

    covered: set[str] = set()
    for row in rows:
        if row and isinstance(row, dict):
            for oid in row.get("covered_outline_ids", []):
                if oid in all_outline_ids:
                    covered.add(oid)

    missing = sorted(all_outline_ids - covered)
    critical_missing = sorted(must_not_miss_ids - covered)

    return CoverageReport(
        covered_outline_ids=sorted(covered),
        missing_outline_ids=missing,
        critical_missing_ids=critical_missing,
    )


# ── Planning node ──────────────────────────────────────────────────────


async def planning_node(state: ParentState) -> dict[str, Any]:
    """规划节点 — 调用 PlanningAgent 生成教学方向与大纲（TeachingPlan）。

    Planning 是唯一致命节点：失败直接抛出异常，不调度任何普通 Agent。
    成功后立即将 TeachingPlan 写入数据库。
    """
    enabled_base_agents = [
        agent_id
        for agent_id in state["request"].enabled_agent_ids()
        if agent_id in BASE_RESOURCE_AGENT_IDS
    ]
    planning_input = ResourceInput(
        resource_id=state["resource_id"],
        learning_need=state["request"].learning_need,
        learning_scenario=state["request"].learning_scenario,
        profile=state["profile"],
        agent_config={"enabled_agents": enabled_base_agents},
    )

    # 执行 Planning
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

    # Planning 失败直接抛出（致命）
    if not planning_result.success:
        error_msg = planning_result.error or "规划阶段失败"
        logger.error("规划阶段失败: resource_id=%s, error=%s", state["resource_id"], error_msg)
        raise ValueError(error_msg)

    # 解析 TeachingPlan
    teaching_plan = None
    if planning_result.metadata:
        plan_data = planning_result.metadata.get("teaching_plan")
        if isinstance(plan_data, dict):
            teaching_plan = TeachingPlan.model_validate(plan_data)

    if teaching_plan is None:
        raise ValueError("规划阶段未返回教学计划")

    # 校验 agent assignments
    assigned_agents = {assignment.agent_id for assignment in teaching_plan.agent_assignments}
    expected_agents = set(enabled_base_agents)
    if assigned_agents != expected_agents:
        raise ValueError(
            "TeachingPlan assignments do not match selected base Agents: "
            f"missing={sorted(expected_agents - assigned_agents)} "
            f"unexpected={sorted(assigned_agents - expected_agents)}"
        )

    # 立即将 TeachingPlan 写入数据库
    try:
        async with session_scope() as session:
            service = ResourceService(session)
            await service.save_teaching_plan(
                user_id=state["user_id"],
                resource_id=state["resource_id"],
                run_id=state["run_id"],
                teaching_plan=teaching_plan,
            )
    except Exception as exc:
        logger.error("TeachingPlan 持久化失败: %s", exc)
        raise

    return {"teaching_plan": teaching_plan}


# Agent 超时配置（秒）
AGENT_TIMEOUTS: dict[str, float] = {
    "content": 300.0,
    "mindmap": 300.0,
    "quiz": 300.0,
    "code": 300.0,
    "reading": 300.0,
    PPT_AGENT_ID: 600.0,
    VIDEO_AGENT_ID: 900.0,
}


# ── Unified non-Planning Agent lifecycle ─────────────────────────────────


async def _execute_non_planning_agent(
    *,
    agent_id: str,
    user_id: int,
    resource_id: int,
    run_id: str,
    resource_input: ResourceInput,
    emitter,
    require_downstream_context: bool,
    depends_on_agents: list[str] | None = None,
) -> dict[str, Any]:
    """统一执行非 Planning Agent 的生命周期。

    委托给 execution.execute_resource_agent 完成生成、校验、持久化。
    失败不影响兄弟 Agent。

    Args:
        agent_id: Agent 标识符
        user_id: 用户 ID
        resource_id: 资源任务 ID
        run_id: 运行 ID
        resource_input: Agent 输入参数
        emitter: 事件发射器
        require_downstream_context: 基础 Agent 必须有 downstream_context（用于验证）
        depends_on_agents: 依赖的 Agent ID 列表（用于聚合 Agent 的 source_item_ids）

    Returns:
        包含 results 或 failures 的字典
    """
    agent = AGENT_REGISTRY[agent_id](emitter)
    timeout_seconds = AGENT_TIMEOUTS.get(agent_id, 300.0)

    # 从数据库查询依赖 Agent 的成功 item IDs
    source_item_ids: list[int] | None = None
    if depends_on_agents:
        async with session_scope() as session:
            from sqlalchemy import select
            from app.infra.models import GeneratedResourceItem
            stmt = (
                select(GeneratedResourceItem.id)
                .where(GeneratedResourceItem.resource_id == resource_id)
                .where(GeneratedResourceItem.status == "completed")
                .where(GeneratedResourceItem.agent_type.in_(depends_on_agents))
            )
            result = await session.exec(stmt)
            source_item_ids = list(result.all())

    outcome = await execute_resource_agent(
        user_id=user_id,
        resource_id=resource_id,
        run_id=run_id,
        agent_id=agent_id,
        agent=agent,
        input_data=resource_input,
        emitter=emitter,
        timeout_seconds=timeout_seconds,
        source_item_ids=source_item_ids,
    )

    if outcome.status == "completed":
        # 成功 - 返回标记（execute_resource_agent 已持久化）
        return {"results": {agent_id: True}}
    else:
        # 失败 - 返回失败记录
        return {
            "results": {},
            "failures": {
                agent_id: AgentFailure(
                    agent_id=agent_id,
                    stage=outcome.failure_stage or "unknown",
                    error_type=outcome.failure_type or "UnknownError",
                    message=outcome.failure_message or "",
                )
            },
        }


# ── Worker nodes ───────────────────────────────────────────────────────


def base_worker_ids(state: ParentState) -> list[str]:
    """获取启用的基础 worker agent IDs。"""
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
    """Worker 节点 — 执行单个基础 agent 的资源生成并持久化结果。

    委托给 _execute_non_planning_agent，它调用 execute_resource_agent。
    基础 Agent 必须有 downstream_context。
    """
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

    return await _execute_non_planning_agent(
        agent_id=agent_id,
        user_id=state["user_id"],
        resource_id=state["resource_id"],
        run_id=state["run_id"],
        resource_input=resource_input,
        emitter=state["emitter"],
        require_downstream_context=True,
    )


# ── Merge workers node ─────────────────────────────────────────────────


async def merge_workers_node(state: ParentState) -> dict[str, Any]:
    """合并 Worker 结果 — 汇总成功/失败计数，检查大纲覆盖情况。

    从数据库读取成功持久化的 Agent 信息。
    """
    results = state.get("results") or {}
    failures = state.get("failures") or {}
    success_count = len(results)
    fail_count = len(failures)
    worker_agents = base_worker_ids(state)
    # 直接使用 request 的 enabled_agent_ids，前端已按要求传参
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

    # 从数据库读取覆盖情况
    coverage_report = await get_coverage(
        resource_id=state["resource_id"],
        teaching_plan=state.get("teaching_plan"),
    )

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


async def ppt_node(state: ParentState) -> dict[str, Any]:
    """PPT 聚合节点 — 运行两阶段教学课件生成。

    从数据库读取成功的基础 Agent handoffs，委托给 _execute_non_planning_agent。
    聚合 Agent 不需要 downstream_context。
    """
    await state["emitter"].emit_agent(
        PPT_AGENT_ID,
        status="running",
        message="正在生成 PPT",
        progress=80,
        phase="ppt_generating",
    )

    # 从数据库读取成功持久化的基础 Agent handoffs
    base_handoffs = await get_handoffs(
        resource_id=state["resource_id"],
        user_id=state["user_id"],
    )

    agent_config_extra: dict[str, Any] = {
        "upstream_handoff_agent_ids": list(base_handoffs.keys()),
        "programming_language": state["request"].agent_configs.code.programming_language,
    }

    resource_input = build_agent_resource_input(
        request=state["request"],
        resource_id=state["resource_id"],
        agent_id=PPT_AGENT_ID,
        teaching_plan=state["teaching_plan"],
        profile=state["profile"],
        upstream_handoffs=base_handoffs,
        agent_config_extra=agent_config_extra,
    )

    return await _execute_non_planning_agent(
        agent_id=PPT_AGENT_ID,
        user_id=state["user_id"],
        resource_id=state["resource_id"],
        run_id=state["run_id"],
        resource_input=resource_input,
        emitter=state["emitter"],
        require_downstream_context=False,
        depends_on_agents=list(base_handoffs.keys()),
    )


async def video_node(state: ParentState) -> dict[str, Any]:
    """Video 聚合节点 — 运行 VideoAgent 内部流水线生成视频脚本。

    从数据库读取成功的基础 Agent handoffs，委托给 _execute_non_planning_agent。
    聚合 Agent 不需要 downstream_context。
    """
    await state["emitter"].emit_agent(
        VIDEO_AGENT_ID,
        status="running",
        message="正在生成讲解视频配置与分镜",
        progress=80,
        phase="video_generating",
    )

    # 从数据库读取成功持久化的基础 Agent handoffs
    base_handoffs = await get_handoffs(
        resource_id=state["resource_id"],
        user_id=state["user_id"],
    )

    agent_config_extra: dict[str, Any] = {
        "upstream_handoff_agent_ids": list(base_handoffs.keys()),
    }

    resource_input = build_agent_resource_input(
        request=state["request"],
        resource_id=state["resource_id"],
        agent_id=VIDEO_AGENT_ID,
        teaching_plan=state["teaching_plan"],
        profile=state["profile"],
        upstream_handoffs=base_handoffs,
        agent_config_extra=agent_config_extra,
    )

    return await _execute_non_planning_agent(
        agent_id=VIDEO_AGENT_ID,
        user_id=state["user_id"],
        resource_id=state["resource_id"],
        run_id=state["run_id"],
        resource_input=resource_input,
        emitter=state["emitter"],
        require_downstream_context=False,
        depends_on_agents=list(base_handoffs.keys()),
    )


# ── Merge aggregation barrier ──────────────────────────────────────────


async def merge_aggregation_node(state: ParentState) -> dict[str, Any]:
    """聚合 Barrier 节点 — 等待所有聚合 Agent（PPT/Video）完成后再保存。

    results 仅包含成功持久化的 Agent。
    failures 包含失败的 Agent 记录。
    """
    results = state.get("results") or {}
    failures = state.get("failures") or {}
    agg_results = {aid: r for aid, r in results.items() if aid in AGGREGATION_AGENT_IDS}
    agg_failures = {aid: f for aid, f in failures.items() if aid in AGGREGATION_AGENT_IDS}
    success_count = len(agg_results)
    fail_count = len(agg_failures)
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
    """保存节点 — 从数据库计算终态并完成资源生成。

    终端状态由数据库已持久化的 Agent 集合严格计算。
    只调用 finalize_generation，不接收调用者声称的成功集合。
    """
    await state["emitter"].emit_agent(
        BUNDLE_AGENT_ID,
        status="running",
        message="正在组装资源包并保存结果",
        progress=95,
        phase="bundling",
    )

    selected_agent_ids = set(state["request"].enabled_agent_ids())

    try:
        async with session_scope() as session:
            service = ResourceService(session)
            status = await service.finalize_generation(
                user_id=state["user_id"],
                resource_id=state["resource_id"],
                expected_agent_ids=selected_agent_ids,
            )
            success = status in ("completed", "partial_completed")

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
