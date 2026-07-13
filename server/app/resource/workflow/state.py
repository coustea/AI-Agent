"""资源工作流的共享 LangGraph 状态类型和归约器。

状态保存本次编排所需的冻结请求数据、计划，以及并行分支的归约结果。
"""

from __future__ import annotations

from typing import Any, Annotated, Literal, TypedDict

from app.resource.schemas.plan import DownstreamContext, ResourcePlan


def merge_results_dict(left: dict[str, Any] | None, right: dict[str, Any] | None) -> dict[str, Any]:
    """合并两个 Agent 结果字典（LangGraph Send 并行后的归约器）。"""
    # 以空字典兜底缺失分支
    if left is None:
        left = {}
    if right is None:
        right = {}
    # 检测到同一 agent 出现两次则违反不变量
    overlap = set(left.keys()) & set(right.keys())
    if overlap:
        raise RuntimeError(f"workflow invariant violated: duplicate agent results for {sorted(overlap)}")
    return {**left, **right}


def merge_failures_dict(left: dict[str, "AgentFailure"] | None, right: dict[str, "AgentFailure"] | None) -> dict[str, "AgentFailure"]:
    """合并两个 Agent 失败字典（LangGraph Send 并行后的归约器）。"""
    if left is None:
        left = {}
    if right is None:
        right = {}
    # 同一 agent 失败记录重复则违反不变量
    overlap = set(left.keys()) & set(right.keys())
    if overlap:
        raise RuntimeError(f"workflow invariant violated: duplicate agent failures for {sorted(overlap)}")
    return {**left, **right}


class AgentFailure(TypedDict):
    """Agent 执行失败记录。"""
    agent_id: str
    stage: Literal["generation", "validation", "persistence", "timeout"]
    error_type: str
    message: str


class ParentState(TypedDict, total=False):
    """全局编排状态。

    orchestrator 写入: user_id, resource_id, selected_agents, request_data, profile
    planning_node 写入: selected_agents, teaching_plan
    """
    user_id: int
    resource_id: int
    selected_agents: list[str]  # planning_node 写入，路由函数读取
    request_data: dict[str, Any]  # {agent_configs, learning_scenario} from request
    profile: dict[str, Any]  # learner profile
    teaching_plan: ResourcePlan
    handoffs: Annotated[dict[str, DownstreamContext], merge_results_dict]
    results: Annotated[dict[str, Any], merge_results_dict]  # worker 返回 {agent_id: True}
    failures: Annotated[dict[str, AgentFailure], merge_failures_dict]
    success: bool

