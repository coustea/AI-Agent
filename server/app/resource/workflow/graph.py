"""Compiled LangGraph for standalone resource generation.

拓扑：
  START → planning → worker_node(×N, Send并行) → merge_workers
    → aggregation_node(PPT/Cartoon按选择并发) → save_node
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.resource.workflow.nodes import (
    aggregation_node,
    merge_workers_node,
    planning_node,
    route_workers_or_merge,
    save_node,
    worker_node,
)
from app.resource.workflow.state import ParentState


@lru_cache(maxsize=1)
def build_parent_graph() -> Any:
    # 构建全局编排状态图（仅编译一次并缓存）
    workflow = StateGraph(ParentState)

    # 注册所有节点
    workflow.add_node("planning", planning_node)
    workflow.add_node("worker_node", worker_node)
    workflow.add_node("merge_workers", merge_workers_node)
    workflow.add_node("aggregation", aggregation_node)
    workflow.add_node("save_node", save_node)

    # 连边：START → 规划 → 基础 worker 并行 → 合并
    workflow.add_edge(START, "planning")
    workflow.add_conditional_edges(
        "planning",
        route_workers_or_merge,
    )
    workflow.add_edge("worker_node", "merge_workers")
    workflow.add_edge("merge_workers", "aggregation")
    workflow.add_edge("aggregation", "save_node")
    workflow.add_edge("save_node", END)

    return workflow.compile()
