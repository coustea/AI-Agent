"""Compiled LangGraph for standalone resource generation."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.resource.workflow.nodes import (
    merge_workers_node,
    planning_node,
    ppt_node,
    pre_audit_node,
    route_aggregation_after_audit,
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
    workflow.add_node("pre_audit_node", pre_audit_node)
    workflow.add_node("ppt_node", ppt_node)
    workflow.add_node("video_node", video_node)
    workflow.add_node("save_node", save_node)

    workflow.add_edge(START, "planning")
    workflow.add_conditional_edges(
        "planning",
        route_workers_or_merge,
        ["worker_node", "merge_workers"],
    )
    workflow.add_edge("worker_node", "merge_workers")
    workflow.add_edge("merge_workers", "pre_audit_node")
    workflow.add_conditional_edges(
        "pre_audit_node",
        route_aggregation_after_audit,
        ["ppt_node", "video_node", "save_node"],
    )
    workflow.add_edge("ppt_node", "save_node")
    workflow.add_edge("video_node", "save_node")
    workflow.add_edge("save_node", END)

    return workflow.compile()


def export_mermaid_topology() -> str:
    graph = build_parent_graph()
    return graph.get_graph().draw_mermaid()
