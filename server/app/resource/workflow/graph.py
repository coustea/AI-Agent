"""Compiled LangGraph for standalone resource generation.

拓扑：
  START → planning → worker_node(×N, Send并行) → merge_workers
    → [ppt_node, video_node, cartoon_node] → merge_aggregation → save_node
    → save_node (无聚合Agent时直接保存)
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.resource.workflow.nodes import (
    merge_aggregation_node,
    merge_workers_node,
    cartoon_node,
    planning_node,
    ppt_node,
    route_after_merge,
    route_workers_or_merge,
    save_node,
    video_node,
    worker_node,
)
from app.resource.workflow.state import ParentState


@lru_cache(maxsize=1)
def build_parent_graph() -> Any:
    workflow = StateGraph(ParentState)

    workflow.add_node("planning", planning_node)
    workflow.add_node("worker_node", worker_node)
    workflow.add_node("merge_workers", merge_workers_node)
    workflow.add_node("ppt_node", ppt_node)
    workflow.add_node("video_node", video_node)
    workflow.add_node("cartoon_node", cartoon_node)
    workflow.add_node("merge_aggregation", merge_aggregation_node)
    workflow.add_node("save_node", save_node)

    workflow.add_edge(START, "planning")
    workflow.add_conditional_edges(
        "planning",
        route_workers_or_merge,
    )
    workflow.add_edge("worker_node", "merge_workers")
    workflow.add_conditional_edges(
        "merge_workers",
        route_after_merge,
    )
    workflow.add_edge("ppt_node", "merge_aggregation")
    workflow.add_edge("video_node", "merge_aggregation")
    workflow.add_edge("cartoon_node", "merge_aggregation")
    workflow.add_edge("merge_aggregation", "save_node")
    workflow.add_edge("save_node", END)

    return workflow.compile()
