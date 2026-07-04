"""LangGraph 工作流节点函数和辅助工具。

节点拓扑：
  START → planning → worker_node(×N, Send并行) → merge_workers
    → [ppt_node, video_node, cartoon_node] → merge_aggregation → save_node

核心设计：
- 传递 user_id, resource_id, selected_agents, request_data, profile, teaching_plan
- 所有数据从 LangGraph state 获取，不再从数据库读取快照
- 事件发送通过 ResourceEvents(user_id, resource_id) 创建
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from langgraph.types import Send
from app.infra.database import session_scope
from app.resource.agents import AGENT_REGISTRY
from app.resource.service import ResourceService
from app.resource.workflow.execution import execute_resource_agent
from app.resource.workflow.validation import check_content_overlap
from app.resource.schemas import (
    AgentResult,
    DownstreamContext,
    ResourceInput,
    TeachingPlan,
)
from app.resource.workflow.state import ParentState, WorkerInputState, AgentFailure
from app.resource.service import (
    AGGREGATION_AGENT_IDS,
    BUNDLE_AGENT_ID,
    CARTOON_AGENT_ID,
    COORDINATOR_AGENT_ID,
    PPT_AGENT_ID,
    VIDEO_AGENT_ID,
    _infer_content_format,
)
from app.resource.event import ResourceEvents

logger = logging.getLogger(__name__)

BASE_RESOURCE_AGENT_IDS = {"content", "mindmap", "quiz", "code", "reading"}


def _split_handoff_materials(content: str, *, limit: int = 12000) -> list[str]:
    """把已持久化正文切成适合 PPT 规划器消费的有界材料块。"""
    normalized = content.strip()[:limit]
    if not normalized:
        return []

    chunks: list[str] = []
    current = ""
    for paragraph in normalized.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        candidate = f"{current}\n\n{paragraph}".strip()
        if current and len(candidate) > 2400:
            chunks.append(current)
            current = paragraph
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks[:6]


def build_agent_resource_input(
    *,
    resource_id: int,
    user_id: int,
    agent_id: str,
    learning_need: str,
    learning_scenario: str,
    selected_agents: list[str],
    agent_configs: dict[str, Any],
    teaching_plan: TeachingPlan | None,
    profile: dict[str, Any],
    upstream_handoffs: dict[str, DownstreamContext],
    agent_config_extra: dict[str, Any] | None = None,
) -> ResourceInput:
    """为指定 agent 构建 ResourceInput 输入。

    Args:
        resource_id: 资源 ID
        agent_id: Agent 标识符
        learning_need: 用户学习需求
        learning_scenario: 用户选择的学习场景
        selected_agents: 选中的 agent IDs
        agent_configs: agent 配置
        teaching_plan: 教学计划（包含策略和大纲）
        profile: 学习者画像
        upstream_handoffs: 上游 Agent 交接数据
        agent_config_extra: 额外配置
    Returns:
        ResourceInput 实例
    """
    agent_config = dict(agent_configs.get(agent_id, {}))
    if agent_config_extra:
        agent_config = {**agent_config, **agent_config_extra}

    agent_config["agent_id"] = agent_id
    return ResourceInput(
        resource_id=resource_id,
        user_id=user_id,
        learning_need=learning_need,
        learning_scenario=learning_scenario,
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
    """从成功持久化的基础资源构建 PPT 所需的真实内容交接。"""
    async with session_scope() as session:
        service = ResourceService(session)
        items = await service.list_resource_items(user_id, resource_id)

    handoffs: dict[str, DownstreamContext] = {}
    for item in items:
        if item.agent_type not in BASE_RESOURCE_AGENT_IDS:
            continue
        if item.content_text:
            content = item.content_text
        elif item.content_json is not None:
            content = json.dumps(
                item.content_json,
                ensure_ascii=False,
                indent=2,
            )
        else:
            content = ""
        materials = _split_handoff_materials(content)
        summary = " ".join(content.split())[:300] or item.title or item.agent_type
        handoffs[item.agent_type] = DownstreamContext(
            source_agent=item.agent_type,
            title=item.title or "",
            one_sentence_summary=summary,
            materials=materials,
        )
    return handoffs


def _extract_state_data(state: ParentState) -> tuple[str, str, dict[str, Any], dict[str, Any], TeachingPlan | None]:
    """从 state 提取通用数据：learning_need, learning_scenario, agent_configs, profile, teaching_plan。"""
    request_data: dict[str, Any] = state.get("request_data") or {}
    profile: dict[str, Any] = state.get("profile") or {}
    teaching_plan_raw: dict[str, Any] = state.get("teaching_plan") or {}

    learning_need = request_data.get("learning_need", "")
    learning_scenario = request_data.get("learning_scenario", "self_study")
    agent_configs = request_data.get("agent_configs", {})

    teaching_plan = None
    if teaching_plan_raw:
        teaching_plan = TeachingPlan.model_validate(teaching_plan_raw)

    return learning_need, learning_scenario, agent_configs, profile, teaching_plan


# ── Planning node ──────────────────────────────────────────────────────


async def planning_node(state: ParentState) -> dict[str, Any]:
    """规划节点 — 调用 PlanningAgent 生成教学方向与大纲（TeachingPlan）。

    Planning 是唯一致命节点：失败直接抛出异常，不调度任何普通 Agent。
    成功后将 TeachingPlan 写入 state（不再写数据库）。
    返回 selected_agents 供路由函数使用。
    """
    user_id = state["user_id"]
    resource_id = state["resource_id"]

    selected_agents: list[str] = state.get("selected_agents") or []
    learning_need, learning_scenario, agent_configs, profile, _ = _extract_state_data(state)

    # 提取基础 Agent IDs
    enabled_base_agents = [
        agent_id
        for agent_id in selected_agents
        if agent_id in BASE_RESOURCE_AGENT_IDS
    ]

    planning_input = ResourceInput(
        resource_id=resource_id,
        learning_need=learning_need,
        learning_scenario=learning_scenario,
        profile=profile,
        agent_config={"enabled_agents": enabled_base_agents},
        username=str(state.get("request_data", {}).get("username", "")),
    )

    events = ResourceEvents(user_id=user_id, resource_id=resource_id)
    started = time.perf_counter()
    try:
        async with session_scope() as session:
            service = ResourceService(session)
            await service.upsert_agent_run(
                resource_id=resource_id,
                agent_id="planning",
                status="running",
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

        assigned_agents = set(teaching_plan.worker_tasks)
        expected_agents = set(enabled_base_agents)
        if assigned_agents != expected_agents:
            raise ValueError(
                "TeachingPlan worker tasks do not match selected base Agents: "
                f"missing={sorted(expected_agents - assigned_agents)} "
                f"unexpected={sorted(assigned_agents - expected_agents)}"
            )

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        async with session_scope() as session:
            service = ResourceService(session)
            await service.upsert_agent_run(
                resource_id=resource_id,
                agent_id="planning",
                status="completed",
                elapsed_ms=elapsed_ms,
            )
        await events.send(
            "planning",
            "completed",
            "教学大纲已生成",
            100,
            data={"phase": "planning", "elapsed_ms": elapsed_ms},
        )
        # 返回 selected_agents 和 teaching_plan 到 state
        return {
            "selected_agents": selected_agents,
            "teaching_plan": teaching_plan.model_dump(mode="json"),
        }
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.error("规划阶段失败: resource_id=%s error=%s", resource_id, exc)
        async with session_scope() as session:
            service = ResourceService(session)
            await service.upsert_agent_run(
                resource_id=resource_id,
                agent_id="planning",
                status="failed",
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


# ── Worker nodes ───────────────────────────────────────────────────────


def route_workers_or_merge(state: ParentState) -> list[Send] | list[str]:
    """路由：有 worker agent → Send 并行分发，否则直接合并。

    同步函数，从 state 读取 planning_node 写入 of selected_agents。
    """
    selected_agents = state.get("selected_agents") or []
    worker_ids = [aid for aid in selected_agents if aid in BASE_RESOURCE_AGENT_IDS]
    if not worker_ids:
        return ["merge_workers"]
    # Send 必须携带 worker_node 所需的全部数据，
    # 因为 LangGraph Send 创建独立 state，不继承父 state。
    return [
        Send("worker_node", {
            "agent_id": agent_id,
            "user_id": state["user_id"],
            "resource_id": state["resource_id"],
            "selected_agents": selected_agents,
            "request_data": state.get("request_data") or {},
            "profile": state.get("profile") or {},
            "teaching_plan": state.get("teaching_plan") or {},
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
    selected_agents = state.get("selected_agents") or []

    learning_need, learning_scenario, agent_configs, profile, teaching_plan = _extract_state_data(state)

    resource_input = build_agent_resource_input(
        resource_id=resource_id,
        user_id=user_id,
        agent_id=agent_id,
        learning_need=learning_need,
        learning_scenario=learning_scenario,
        selected_agents=selected_agents,
        agent_configs=agent_configs,
        teaching_plan=teaching_plan,
        profile=profile,
        upstream_handoffs={},
    )

    return await execute_resource_agent(
        user_id=user_id,
        resource_id=resource_id,
        agent_id=agent_id,
        input_data=resource_input,
    )


# ── Merge workers node ─────────────────────────────────────────────────


async def merge_workers_node(state: ParentState) -> dict[str, Any]:
    """合并 Worker 结果 — 汇总成功/失败计数，检查大纲覆盖和内容重复。
    """
    user_id = state["user_id"]
    resource_id = state["resource_id"]
    events = ResourceEvents(user_id=user_id, resource_id=resource_id)

    started = time.perf_counter()
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
    selected_agents: list[str] = state.get("selected_agents") or []
    worker_agents = [aid for aid in selected_agents if aid in BASE_RESOURCE_AGENT_IDS]

    coordinator_status = "failed" if worker_agents and success_count == 0 else "finished"
    message = (
        f"基础资源并行生成完成：成功 {success_count} 个，失败 {fail_count} 个"
        if worker_agents
        else "未选择基础资源，聚合资源将基于教学计划生成"
    )
    stat = "completed" if coordinator_status == "finished" else "failed"

    # 从 state 获取教学计划
    teaching_plan_raw: dict[str, Any] = state.get("teaching_plan") or {}
    teaching_plan = None
    if teaching_plan_raw:
        teaching_plan = TeachingPlan.model_validate(teaching_plan_raw)

    # 内容去重检查：读取已完成 Agent 的内容并检查相似度
    if results and teaching_plan:
        async with session_scope() as session:
            service = ResourceService(session)
            items = await service.list_resource_items(user_id, resource_id)

        existing_results: dict[str, AgentResult] = {}
        for item in items:
            if item.agent_type in BASE_RESOURCE_AGENT_IDS:
                # item 表只有成功记录，无需检查 status
                content_format = _infer_content_format(item.agent_type)
                if content_format == "json" and item.content_json:
                    content = str(item.content_json)
                elif item.content_text:
                    content = item.content_text
                else:
                    content = ""

                existing_results[item.agent_type] = AgentResult(
                    success=True,
                    content=content,
                    title=item.title or "",
                    file_type=content_format,
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

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    async with session_scope() as session:
        service = ResourceService(session)
        await service.upsert_agent_run(
            resource_id=resource_id,
            agent_id=COORDINATOR_AGENT_ID,
            status=stat,
            error_message=message if stat == "failed" else None,
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
    if CARTOON_AGENT_ID in selected_agents:
        destinations.append("cartoon_node")
    return destinations or ["save_node"]


# ── Aggregation nodes (PPT, Video) ────────────────────────────────────


async def ppt_node(state: ParentState) -> dict[str, Any]:
    """PPT 聚合节点 — 调用独立课件生成器并保存其发布引用。

    从 state 读取数据，从数据库读取成功的基础 Agent handoffs。
    模板选择、布局、渲染和 HTML 发布均由 PPT Agent 内部流水线负责。
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

    selected_agents = state.get("selected_agents") or []
    learning_need, learning_scenario, agent_configs, profile, teaching_plan = _extract_state_data(state)

    # 从数据库读取成功持久化的基础 Agent handoffs
    base_handoffs = await get_handoffs(
        resource_id=resource_id,
        user_id=user_id,
    )

    resource_input = build_agent_resource_input(
        resource_id=resource_id,
        user_id=user_id,
        agent_id=PPT_AGENT_ID,
        learning_need=learning_need,
        learning_scenario=learning_scenario,
        selected_agents=selected_agents,
        agent_configs=agent_configs,
        teaching_plan=teaching_plan,
        profile=profile,
        upstream_handoffs=base_handoffs,
    )

    return await execute_resource_agent(
        user_id=user_id,
        resource_id=resource_id,
        agent_id=PPT_AGENT_ID,
        input_data=resource_input,
    )


async def video_node(state: ParentState) -> dict[str, Any]:
    """Video 聚合节点 — 基于已保存的基础资源生成最终 MP4。"""
    user_id = state["user_id"]
    resource_id = state["resource_id"]
    events = ResourceEvents(user_id=user_id, resource_id=resource_id)

    await events.send(
        VIDEO_AGENT_ID,
        "running",
        "正在生成讲解视频",
        80,
    )

    selected_agents = state.get("selected_agents") or []
    learning_need, learning_scenario, agent_configs, profile, teaching_plan = _extract_state_data(state)

    base_handoffs = await get_handoffs(
        resource_id=resource_id,
        user_id=user_id,
    )
    resource_input = build_agent_resource_input(
        resource_id=resource_id,
        user_id=user_id,
        agent_id=VIDEO_AGENT_ID,
        learning_need=learning_need,
        learning_scenario=learning_scenario,
        selected_agents=selected_agents,
        agent_configs=agent_configs,
        teaching_plan=teaching_plan,
        profile=profile,
        upstream_handoffs=base_handoffs,
        agent_config_extra={
            "upstream_handoff_agent_ids": list(base_handoffs),
        },
    )

    return await execute_resource_agent(
        user_id=user_id,
        resource_id=resource_id,
        agent_id=VIDEO_AGENT_ID,
        input_data=resource_input,
    )


async def cartoon_node(state: ParentState) -> dict[str, Any]:
    """Cartoon 聚合节点 — 基于基础资源生成带配音与字幕的动画讲解 MP4。"""
    user_id = state["user_id"]
    resource_id = state["resource_id"]
    events = ResourceEvents(user_id=user_id, resource_id=resource_id)

    await events.send(
        CARTOON_AGENT_ID,
        "running",
        "正在规划动画分镜与讲解节奏",
        72,
    )

    request_data: dict[str, Any] = state.get("request_data") or {}
    selected_agents = state.get("selected_agents") or []
    learning_need, learning_scenario, agent_configs, profile, teaching_plan = _extract_state_data(state)

    base_handoffs = await get_handoffs(
        resource_id=resource_id,
        user_id=user_id,
    )
    resource_input = build_agent_resource_input(
        resource_id=resource_id,
        user_id=user_id,
        agent_id=CARTOON_AGENT_ID,
        learning_need=learning_need,
        learning_scenario=learning_scenario,
        selected_agents=selected_agents,
        agent_configs=agent_configs,
        teaching_plan=teaching_plan,
        profile=profile,
        upstream_handoffs=base_handoffs,
        agent_config_extra={
            "upstream_handoff_agent_ids": list(base_handoffs),
        },
    )
    resource_input.username = str(request_data.get("username", ""))

    return await execute_resource_agent(
        user_id=user_id,
        resource_id=resource_id,
        agent_id=CARTOON_AGENT_ID,
        input_data=resource_input,
    )


# ── Merge aggregation barrier ──────────────────────────────────────────


async def merge_aggregation_node(state: ParentState) -> dict[str, Any]:
    """聚合 Barrier 节点 — 等待 PPT/Video Agent 完成后再保存。

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
    await events.send(
        BUNDLE_AGENT_ID,
        "running",
        "正在组装资源包并保存结果",
        95,
        data={"phase": "aggregation"},
    )

    # 从 state 获取选中的 agent IDs
    selected_agents: list[str] = state.get("selected_agents") or []
    selected_agent_ids = set(selected_agents)

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
            await service.upsert_agent_run(
                resource_id=resource_id,
                agent_id=BUNDLE_AGENT_ID,
                status="completed" if success else "failed",
                error_message="资源包组装失败" if not success else None,
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
            await service.upsert_agent_run(
                resource_id=resource_id,
                agent_id=BUNDLE_AGENT_ID,
                status="failed",
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
