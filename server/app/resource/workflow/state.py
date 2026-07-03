"""资源工作流的共享 LangGraph 状态类型和归约器。

简化后：只传递 user_id 和 resource_id，其他数据由节点内部获取。
"""

from __future__ import annotations

from typing import Any, Annotated, Literal, TypedDict

from app.resource.schemas import AgentResult


def merge_results_dict(left: dict[str, Any] | None, right: dict[str, Any] | None) -> dict[str, Any]:
    """合并两个 Agent 结果字典（LangGraph Send 并行后的归约器）。"""
    if left is None:
        left = {}
    if right is None:
        right = {}
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
    overlap = set(left.keys()) & set(right.keys())
    if overlap:
        raise RuntimeError(f"workflow invariant violated: duplicate agent failures for {sorted(overlap)}")
    return {**left, **right}


class AgentFailure(TypedDict):
    """Agent 执行失败记录。"""
    agent_id: str
    stage: Literal["generation", "validation", "persistence"]
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
    teaching_plan: dict[str, Any]  # planning_node writes, workers read
    results: Annotated[dict[str, Any], merge_results_dict]  # worker 返回 {agent_id: True}
    failures: Annotated[dict[str, AgentFailure], merge_failures_dict]
    success: bool


class WorkerInputState(TypedDict, total=False):
    """Worker 节点输入状态 — 每个并行 worker 的独立输入。

    Send payload 携带 worker_node 所需的全部数据，
    因为 LangGraph Send 创建独立 state，不继承父 state。
    """
    agent_id: str
    user_id: int
    resource_id: int
    selected_agents: list[str]
    request_data: dict[str, Any]
    profile: dict[str, Any]
    teaching_plan: dict[str, Any]
