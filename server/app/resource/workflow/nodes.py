"""LangGraph 工作流节点函数和辅助工具。

节点拓扑：
  START → planning → worker_node(×N, Send并行) → merge_workers
    → [ppt_node, video_node] (并行) → merge_aggregation → save_node

核心设计：
- 只传递 user_id 和 resource_id
- 所有数据（request, profile, teaching_plan）从数据库获取
- 事件发送通过 ResourceEvents(user_id, resource_id) 创建
"""

from __future__ import annotations

import logging
import time
from typing import Any

from langgraph.types import Send
from app.infra.database import session_scope
from app.resource.agents import AGENT_REGISTRY
from app.resource.service import ResourceService
from app.resource.workflow.execution import execute_resource_agent, AgentOutcome
from app.resource.workflow.validation import check_content_overlap
from sqlalchemy import select
from app.infra.models import GeneratedResource, GeneratedResourceItem
from app.resource.schemas import (
    AgentResult,
    DownstreamContext,
    ResourceInput,
    TeachingPlan,
)
from app.resource.workflow.state import ParentState, WorkerInputState, CoverageReport, AgentFailure
from app.resource.service import (
    AGGREGATION_AGENT_IDS,
    BUNDLE_AGENT_ID,
    COORDINATOR_AGENT_ID,
    PPT_AGENT_ID,
    VIDEO_AGENT_ID,
)
from app.resource.event import ResourceEvents

logger = logging.getLogger(__name__)

BASE_RESOURCE_AGENT_IDS = {"content", "mindmap", "quiz", "code", "reading"}


async def _get_resource_snapshot(user_id: int, resource_id: int) -> dict[str, Any]:
    """从数据库获取资源快照（request, profile, selected_agents, agent_configs）。"""
    async with session_scope() as session:
        service = ResourceService(session)
        resource = await service.get_resource(user_id, resource_id)
        if resource is None:
            raise ValueError(f"Resource {resource_id} not found")
        return {
            "learning_need": resource.learning_need or "",
            "selected_agents": resource.selected_agents or [],
            "agent_configs": resource.agent_configs or {},
            "request_snapshot": resource.request_snapshot or {},
            "profile_snapshot": resource.profile_snapshot or {},
        }


async def _get_teaching_plan(resource_id: int) -> TeachingPlan | None:
    """从数据库获取教学计划。"""
    async with session_scope() as session:
        stmt = select(GeneratedResource).where(GeneratedResource.id == resource_id)
        result = await session.exec(stmt)
        resource = result.scalar_one_or_none()
        if resource and resource.teaching_plan:
            return TeachingPlan.model_validate(resource.teaching_plan)
        return None


def build_agent_resource_input(
    *,
    resource_id: int,
    agent_id: str,
    learning_need: str,
    selected_agents: list[str],
    agent_configs: dict[str, Any],
    teaching_plan: TeachingPlan | None,
    profile: dict[str, Any],
    upstream_handoffs: dict[str, DownstreamContext],
    agent_config_extra: dict[str, Any] | None = None,
    covered_outline_ids: list[str] | None = None,
) -> ResourceInput:
    """为指定 agent 构建 ResourceInput 输入。

    Args:
        resource_id: 资源 ID
        agent_id: Agent 标识符
        learning_need: 用户学习需求
        selected_agents: 选中的 agent IDs
        agent_configs: agent 配置
        teaching_plan: 教学计划（包含策略和大纲）
        profile: 学习者画像
        upstream_handoffs: 上游 Agent 交接数据
        agent_config_extra: 额外配置
        covered_outline_ids: 已覆盖的大纲 ID（动态追踪）

    Returns:
        ResourceInput 实例
    """
    agent_config = agent_configs.get(agent_id, {})
    if agent_config_extra:
        agent_config = {**agent_config, **agent_config_extra}

    # 策略传递：从 teaching_plan 提取 teaching_strategy
    if teaching_plan and teaching_plan.teaching_strategy:
        agent_config["teaching_strategy"] = teaching_plan.teaching_strategy

    # 动态覆盖追踪：传递已覆盖的大纲项
    if covered_outline_ids:
        agent_config["already_covered_outline_ids"] = covered_outline_ids

    agent_config["agent_id"] = agent_id
    return ResourceInput(
        resource_id=resource_id,
        learning_need=learning_need,
        learning_scenario=agent_config.get("learning_scenario") or "self_study",
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


async def get_covered_outline_ids(
    resource_id: int,
) -> list[str]:
    """获取已覆盖的大纲 ID（用于动态追踪）。

    从数据库读取已完成 Agent 的 downstream_context，
   提取 covered_outline_ids 并合并。
    """
    async with session_scope() as session:
        stmt = (
            select(GeneratedResourceItem.downstream_context)
            .where(GeneratedResourceItem.resource_id == resource_id)
            .where(GeneratedResourceItem.status == "completed")
            .where(GeneratedResourceItem.agent_type.in_(BASE_RESOURCE_AGENT_IDS))
        )
        result = await session.exec(stmt)
        rows = result.all()

    covered: set[str] = set()
    for row in rows:
        if row and isinstance(row, dict):
            for oid in row.get("covered_outline_ids", []):
                covered.add(oid)

    return sorted(covered)


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

    all_outline_ids = {item.get("id") for item in teaching_plan.outline}
    must_not_miss_ids = {item.get("id") for item in teaching_plan.outline if item.get("must_not_miss")}

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
    返回 selected_agents 供路由函数使用。
    """
    user_id = state["user_id"]
    resource_id = state["resource_id"]

    # 从数据库获取快照数据
    snapshot = await _get_resource_snapshot(user_id, resource_id)
    learning_need = snapshot["learning_need"]
    selected_agents = snapshot["selected_agents"]
    agent_configs = snapshot["agent_configs"]
    profile = snapshot["profile_snapshot"]
    request_snapshot = snapshot["request_snapshot"]

    # 提取基础 Agent IDs
    enabled_base_agents = [
        agent_id
        for agent_id in selected_agents
        if agent_id in BASE_RESOURCE_AGENT_IDS
    ]

    planning_input = ResourceInput(
        resource_id=resource_id,
        learning_need=learning_need,
        learning_scenario=request_snapshot.get("learning_scenario"),
        profile=profile,
        agent_config={"enabled_agents": enabled_base_agents},
    )

    events = ResourceEvents(user_id=user_id, resource_id=resource_id)
    started = time.perf_counter()
    try:
        async with session_scope() as session:
            service = ResourceService(session)
            await service.start_agent_run(
                resource_id=resource_id,
                agent_id="planning",
                stage="planning",
            )

        await events.send(
            "planning",
            "running",
            "正在分析学习需求并构建大纲...",
            10,
            data={"phase": "planning"},
        )
        planning_result = await AGENT_REGISTRY["planning"](events).generate_resource(planning_input)
        if not planning_result.success:
            error_msg = planning_result.error or "规划阶段失败"
            raise ValueError(error_msg)

        teaching_plan = None
        if planning_result.metadata:
            plan_data = planning_result.metadata.get("teaching_plan")
            if isinstance(plan_data, dict):
                teaching_plan = TeachingPlan.model_validate(plan_data)
        if teaching_plan is None:
            raise ValueError("规划阶段未返回教学计划")

        assigned_agents = {
            assignment.get("agent_id")
            for assignment in teaching_plan.agent_assignments
        }
        expected_agents = set(enabled_base_agents)
        if assigned_agents != expected_agents:
            raise ValueError(
                "TeachingPlan assignments do not match selected base Agents: "
                f"missing={sorted(expected_agents - assigned_agents)} "
                f"unexpected={sorted(assigned_agents - expected_agents)}"
            )

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        async with session_scope() as session:
            service = ResourceService(session)
            await service.save_teaching_plan(
                user_id=user_id,
                resource_id=resource_id,
                teaching_plan=teaching_plan,
            )
        await events.send(
            "planning",
            "completed",
            "教学大纲已生成",
            100,
            data={"phase": "planning", "elapsed_ms": elapsed_ms},
        )
        # 返回 selected_agents 供同步路由函数使用
        return {"selected_agents": selected_agents}
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.error("规划阶段失败: resource_id=%s error=%s", resource_id, exc)
        async with session_scope() as session:
            service = ResourceService(session)
            await service.mark_agent_failed(
                resource_id=resource_id,
                agent_id="planning",
                stage="planning",
                error_type=type(exc).__name__,
                error_message=str(exc)[:500],
                elapsed_ms=elapsed_ms,
            )
        await events.send(
            "planning",
            "failed",
            str(exc) or "规划失败",
            0,
            data={"phase": "planning", "elapsed_ms": elapsed_ms},
        )
        raise


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
    resource_input: ResourceInput,
    _require_downstream_context: bool = False,
    depends_on_agents: list[str] | None = None,
) -> dict[str, Any]:
    """统一执行非 Planning Agent 的生命周期。

    委托给 execution.execute_resource_agent 完成生成、校验、持久化。
    失败不影响兄弟 Agent。

    Args:
        agent_id: Agent 标识符
        user_id: 用户 ID
        resource_id: 资源任务 ID
        resource_input: Agent 输入参数
        require_downstream_context: 基础 Agent 必须有 downstream_context（用于验证）
        depends_on_agents: 依赖的 Agent ID 列表（用于聚合 Agent 的 source_item_ids）

    Returns:
        包含 results 或 failures 的字典
    """
    events = ResourceEvents(user_id=user_id, resource_id=resource_id)
    agent = AGENT_REGISTRY[agent_id](events)
    timeout_seconds = AGENT_TIMEOUTS.get(agent_id, 300.0)

    # 从数据库查询依赖 Agent 的成功 item IDs
    source_item_ids: list[int] | None = None
    if depends_on_agents:
        async with session_scope() as session:

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
        agent_id=agent_id,
        agent=agent,
        input_data=resource_input,
        events=events,
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


async def base_worker_ids(user_id: int, resource_id: int) -> list[str]:
    """获取启用的基础 worker agent IDs（从数据库读取）。"""
    snapshot = await _get_resource_snapshot(user_id, resource_id)
    selected = snapshot["selected_agents"]
    return [aid for aid in selected if aid in BASE_RESOURCE_AGENT_IDS]


def route_workers_or_merge(state: ParentState) -> list[Send] | list[str]:
    """路由：有 worker agent → Send 并行分发，否则直接合并。

    同步函数，从 state 读取 planning_node 写入的 selected_agents。
    """
    selected_agents = state.get("selected_agents") or []
    worker_ids = [aid for aid in selected_agents if aid in BASE_RESOURCE_AGENT_IDS]
    if not worker_ids:
        return ["merge_workers"]
    return [
        Send("worker_node", {
            "agent_id": agent_id,
            "user_id": state["user_id"],
            "resource_id": state["resource_id"],
        })
        for agent_id in worker_ids
    ]


async def worker_node(state: ParentState) -> dict[str, Any]:
    """Worker 节点 — 执行单个基础 agent 的资源生成并持久化结果。

    使用 ParentState，从 state["agent_id"] 读取当前 worker 的 agent_id。
    LangGraph Send 传递的状态会合并到 ParentState 中。
    """
    agent_id = state["agent_id"]
    user_id = state["user_id"]
    resource_id = state["resource_id"]

    # 从数据库获取快照数据
    snapshot = await _get_resource_snapshot(user_id, resource_id)
    learning_need = snapshot["learning_need"]
    agent_configs = snapshot["agent_configs"]
    profile = snapshot["profile_snapshot"]

    # 从数据库获取教学计划
    teaching_plan = await _get_teaching_plan(resource_id)

    # 动态覆盖追踪：获取已覆盖的大纲 ID
    covered_ids = await get_covered_outline_ids(resource_id)

    resource_input = build_agent_resource_input(
        resource_id=resource_id,
        agent_id=agent_id,
        learning_need=learning_need,
        selected_agents=snapshot["selected_agents"],
        agent_configs=agent_configs,
        teaching_plan=teaching_plan,
        profile=profile,
        upstream_handoffs={},
        covered_outline_ids=covered_ids if covered_ids else None,
    )

    return await _execute_non_planning_agent(
        agent_id=agent_id,
        user_id=user_id,
        resource_id=resource_id,
        resource_input=resource_input,
        _require_downstream_context=True,
    )


# ── Merge workers node ─────────────────────────────────────────────────


async def merge_workers_node(state: ParentState) -> dict[str, Any]:
    """合并 Worker 结果 — 汇总成功/失败计数，检查大纲覆盖和内容重复。
    """
    user_id = state["user_id"]
    resource_id = state["resource_id"]
    events = ResourceEvents(user_id=user_id, resource_id=resource_id)

    started = time.perf_counter()
    async with session_scope() as session:
        service = ResourceService(session)
        await service.start_agent_run(
            resource_id=resource_id,
            agent_id=COORDINATOR_AGENT_ID,
            stage="coordination",
        )
    await events.send(
        COORDINATOR_AGENT_ID,
        "running",
        "正在汇总并校验基础资源",
        65,
        data={"phase": "coordination"},
    )

    results = state.get("results") or {}
    failures = state.get("failures") or {}
    success_count = len(results)
    fail_count = len(failures)
    worker_agents = await base_worker_ids(user_id, resource_id)

    coordinator_status = "failed" if worker_agents and success_count == 0 else "finished"
    message = (
        f"基础资源并行生成完成：成功 {success_count} 个，失败 {fail_count} 个"
        if worker_agents
        else "未选择基础资源，聚合资源将基于教学计划生成"
    )
    stat = "completed" if coordinator_status == "finished" else "failed"

    # 从数据库获取教学计划
    teaching_plan = await _get_teaching_plan(resource_id)

    # 内容去重检查：读取已完成 Agent 的内容并检查相似度
    if results and teaching_plan:
        async with session_scope() as session:
            service = ResourceService(session)
            items = await service.list_resource_items(user_id, resource_id)

        existing_results: dict[str, AgentResult] = {}
        for item in items:
            if item.agent_type in BASE_RESOURCE_AGENT_IDS and item.status == "completed":
                # 根据 content_format 选择正确的内容字段
                if item.content_format == "json" and item.content_json:
                    content = str(item.content_json)
                elif item.content_text:
                    content = item.content_text
                else:
                    content = ""

                existing_results[item.agent_type] = AgentResult(
                    success=True,
                    content=content,
                    title=item.title or "",
                    file_type=item.content_format or "markdown",
                )

        # 检查每个成功 Agent 的内容重叠
        for agent_id in results:
            if agent_id in existing_results:
                warnings = check_content_overlap(
                    agent_id,
                    existing_results[agent_id],
                    teaching_plan,
                    existing_results,
                )
                for warning in warnings:
                    await events.send(agent_id, "running", f"⚠️ {warning}", 70)

    # 从数据库读取覆盖情况
    coverage_report = await get_coverage(
        resource_id=resource_id,
        teaching_plan=teaching_plan,
    )

    if coverage_report.get("critical_missing_ids"):
        critical_titles = []
        if teaching_plan:
            for item in teaching_plan.outline:
                if item.get("id") in coverage_report["critical_missing_ids"]:
                    critical_titles.append(item.get("title", ""))
        await events.send(
            COORDINATOR_AGENT_ID,
            "running",
            f"大纲覆盖警告：核心大纲项未覆盖 — {', '.join(critical_titles)}",
            70,
        )
    elif coverage_report.get("missing_outline_ids"):
        missing_ids = coverage_report["missing_outline_ids"]
        if teaching_plan:
            missing_titles = [item.get("title", "") for item in teaching_plan.outline if item.get("id") in missing_ids]
            await events.send(
                COORDINATOR_AGENT_ID,
                "running",
                f"非核心大纲项未覆盖：{', '.join(missing_titles)}",
                70,
            )

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    async with session_scope() as session:
        service = ResourceService(session)
        if stat == "completed":
            await service.complete_agent_run(
                resource_id=resource_id,
                agent_id=COORDINATOR_AGENT_ID,
                elapsed_ms=elapsed_ms,
            )
        else:
            await service.mark_agent_failed(
                resource_id=resource_id,
                agent_id=COORDINATOR_AGENT_ID,
                stage="coordination",
                error_type="WorkerPoolFailed",
                error_message=message,
                elapsed_ms=elapsed_ms,
            )
    await events.send(
        COORDINATOR_AGENT_ID,
        stat,
        message,
        70,
        data={"phase": "coordination", "elapsed_ms": elapsed_ms},
    )
    return {}


# ── Routing after merge ────────────────────────────────────────────────


def route_after_merge(state: ParentState) -> list[str]:
    """路由到聚合 Agent（PPT/Video）或直接保存。

    同步函数，从 state 读取 selected_agents。
    """
    selected_agents = state.get("selected_agents") or []
    destinations: list[str] = []
    if PPT_AGENT_ID in selected_agents:
        destinations.append("ppt_node")
    if VIDEO_AGENT_ID in selected_agents:
        destinations.append("video_node")
    return destinations or ["save_node"]


# ── Aggregation nodes (PPT, Video) ─────────────────────────────────────


async def ppt_node(state: ParentState) -> dict[str, Any]:
    """PPT 聚合节点 — 运行两阶段教学课件生成。

    从数据库读取成功的基础 Agent handoffs，委托给 _execute_non_planning_agent。
    聚合 Agent 不需要 downstream_context。
    """
    user_id = state["user_id"]
    resource_id = state["resource_id"]
    events = ResourceEvents(user_id=user_id, resource_id=resource_id)

    await events.send(
        PPT_AGENT_ID,
        "running",
        "正在生成 PPT",
        80,
    )

    # 从数据库读取快照数据
    snapshot = await _get_resource_snapshot(user_id, resource_id)
    learning_need = snapshot["learning_need"]
    agent_configs = snapshot["agent_configs"]
    profile = snapshot["profile_snapshot"]
    request_snapshot = snapshot["request_snapshot"]

    # 从数据库获取教学计划
    teaching_plan = await _get_teaching_plan(resource_id)

    # 从数据库读取成功持久化的基础 Agent handoffs
    base_handoffs = await get_handoffs(
        resource_id=resource_id,
        user_id=user_id,
    )

    agent_config_extra: dict[str, Any] = {
        "upstream_handoff_agent_ids": list(base_handoffs.keys()),
        "programming_language": request_snapshot.get("agent_configs", {}).get("code", {}).get("programming_language"),
    }

    resource_input = build_agent_resource_input(
        resource_id=resource_id,
        agent_id=PPT_AGENT_ID,
        learning_need=learning_need,
        selected_agents=snapshot["selected_agents"],
        agent_configs=agent_configs,
        teaching_plan=teaching_plan,
        profile=profile,
        upstream_handoffs=base_handoffs,
        agent_config_extra=agent_config_extra,
    )

    return await _execute_non_planning_agent(
        agent_id=PPT_AGENT_ID,
        user_id=user_id,
        resource_id=resource_id,
        resource_input=resource_input,
        _require_downstream_context=False,
        depends_on_agents=list(base_handoffs.keys()),
    )


async def video_node(state: ParentState) -> dict[str, Any]:
    """Video 聚合节点 — 运行 VideoAgent 内部流水线生成视频脚本。

    从数据库读取成功的基础 Agent handoffs，委托给 _execute_non_planning_agent。
    聚合 Agent 不需要 downstream_context。
    """
    user_id = state["user_id"]
    resource_id = state["resource_id"]
    events = ResourceEvents(user_id=user_id, resource_id=resource_id)

    await events.send(
        VIDEO_AGENT_ID,
        "running",
        "正在生成讲解视频配置与分镜",
        80,
    )

    # 从数据库读取快照数据
    snapshot = await _get_resource_snapshot(user_id, resource_id)
    learning_need = snapshot["learning_need"]
    agent_configs = snapshot["agent_configs"]
    profile = snapshot["profile_snapshot"]

    # 从数据库获取教学计划
    teaching_plan = await _get_teaching_plan(resource_id)

    # 从数据库读取成功持久化的基础 Agent handoffs
    base_handoffs = await get_handoffs(
        resource_id=resource_id,
        user_id=user_id,
    )

    agent_config_extra: dict[str, Any] = {
        "upstream_handoff_agent_ids": list(base_handoffs.keys()),
    }

    resource_input = build_agent_resource_input(
        resource_id=resource_id,
        agent_id=VIDEO_AGENT_ID,
        learning_need=learning_need,
        selected_agents=snapshot["selected_agents"],
        agent_configs=agent_configs,
        teaching_plan=teaching_plan,
        profile=profile,
        upstream_handoffs=base_handoffs,
        agent_config_extra=agent_config_extra,
    )

    return await _execute_non_planning_agent(
        agent_id=VIDEO_AGENT_ID,
        user_id=user_id,
        resource_id=resource_id,
        resource_input=resource_input,
        _require_downstream_context=False,
        depends_on_agents=list(base_handoffs.keys()),
    )


# ── Merge aggregation barrier ──────────────────────────────────────────


async def merge_aggregation_node(state: ParentState) -> dict[str, Any]:
    """聚合 Barrier 节点 — 等待所有聚合 Agent（PPT/Video）完成后再保存。

    results 仅包含成功持久化的 Agent。
    failures 包含失败的 Agent 记录。
    """
    user_id = state["user_id"]
    resource_id = state["resource_id"]
    events = ResourceEvents(user_id=user_id, resource_id=resource_id)

    results = state.get("results") or {}
    failures = state.get("failures") or {}
    agg_results = {aid: r for aid, r in results.items() if aid in AGGREGATION_AGENT_IDS}
    agg_failures = {aid: f for aid, f in failures.items() if aid in AGGREGATION_AGENT_IDS}
    success_count = len(agg_results)
    fail_count = len(agg_failures)
    await events.send(
        BUNDLE_AGENT_ID,
        "running",
        f"聚合资源生成完成：成功 {success_count} 个，失败 {fail_count} 个",
        90,
    )
    return {}


# ── Save node ──────────────────────────────────────────────────────────


async def save_node(state: ParentState) -> dict[str, Any]:
    """保存节点 — 从数据库计算终态并完成资源生成。

    终端状态由数据库已持久化的 Agent 集合严格计算。
    只调用 finalize_generation，不接收调用者声称的成功集合。
    """
    user_id = state["user_id"]
    resource_id = state["resource_id"]
    events = ResourceEvents(user_id=user_id, resource_id=resource_id)

    started = time.perf_counter()
    async with session_scope() as session:
        service = ResourceService(session)
        await service.start_agent_run(
            resource_id=resource_id,
            agent_id=BUNDLE_AGENT_ID,
            stage="aggregation",
        )
    await events.send(
        BUNDLE_AGENT_ID,
        "running",
        "正在组装资源包并保存结果",
        95,
        data={"phase": "aggregation"},
    )

    # 从数据库获取选中的 agent IDs
    snapshot = await _get_resource_snapshot(user_id, resource_id)
    selected_agent_ids = set(snapshot["selected_agents"])

    try:
        async with session_scope() as session:
            service = ResourceService(session)
            status = await service.finalize_generation(
                user_id=user_id,
                resource_id=resource_id,
                expected_agent_ids=selected_agent_ids,
            )
            success = status in ("completed", "partial_completed")
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            if success:
                await service.complete_agent_run(
                    resource_id=resource_id,
                    agent_id=BUNDLE_AGENT_ID,
                    elapsed_ms=elapsed_ms,
                )
            else:
                await service.mark_agent_failed(
                    resource_id=resource_id,
                    agent_id=BUNDLE_AGENT_ID,
                    stage="aggregation",
                    error_type="BundleFailed",
                    error_message="资源包组装失败",
                    elapsed_ms=elapsed_ms,
                )

            await events.send(
                BUNDLE_AGENT_ID,
                "completed" if success else "failed",
                "资源包组装完成" if success else "资源包组装失败",
                100,
                data={"phase": "aggregation", "elapsed_ms": elapsed_ms},
            )
            return {"success": success}
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        async with session_scope() as session:
            service = ResourceService(session)
            await service.mark_agent_failed(
                resource_id=resource_id,
                agent_id=BUNDLE_AGENT_ID,
                stage="aggregation",
                error_type=type(exc).__name__,
                error_message=str(exc)[:500],
                elapsed_ms=elapsed_ms,
            )
        await events.send(
            BUNDLE_AGENT_ID,
            "failed",
            "资源包组装异常",
            0,
            data={"phase": "aggregation", "elapsed_ms": elapsed_ms},
        )
        raise
