"""Shared helpers for renderable knowledge graph payloads."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


RELATION_LABELS: dict[str, str] = {
    "prerequisite": "前置",
    "extends": "扩展",
    "includes": "包含",
    "related": "相关",
}

LAYOUT_MODES = {"force", "radial", "hierarchy"}


def normalize_render_graph(
    graph: dict[str, Any],
    *,
    layout_mode: str = "force",
    relation_depth: int = 2,
) -> dict[str, Any]:
    """Normalize a graph for Neo4j storage and frontend rendering.

    Adds top-to-bottom rank hints so the frontend can avoid a long horizontal
    graph when the user picks hierarchy layout.
    """
    mode = layout_mode if layout_mode in LAYOUT_MODES else "force"
    nodes = [_normalize_node(node) for node in graph.get("nodes") or [] if isinstance(node, dict)]
    node_ids = {node["id"] for node in nodes if node.get("id")}
    edges = [
        _normalize_edge(edge)
        for edge in graph.get("edges") or []
        if isinstance(edge, dict)
        and edge.get("source") in node_ids
        and edge.get("target") in node_ids
        and edge.get("source") != edge.get("target")
    ]

    levels = _calculate_levels(nodes, edges)
    for node in nodes:
        node["level"] = levels.get(node["id"], 0)

    normalized = dict(graph)
    normalized["nodes"] = nodes
    normalized["edges"] = edges
    normalized["layout_mode"] = mode
    normalized["relation_depth"] = max(1, int(relation_depth or 1))
    normalized["layout"] = {"mode": mode, "rank_direction": "TB"}
    return normalized


def _normalize_node(node: dict[str, Any]) -> dict[str, Any]:
    node_id = str(node.get("id") or node.get("name") or node.get("label") or "").strip()
    label = str(node.get("label") or node.get("name") or node_id or "知识点").strip()
    category = str(node.get("category") or node.get("importance") or "important").strip()
    if category not in {"core", "important", "supplementary", "weak"}:
        category = "important"
    return {
        **node,
        "id": node_id,
        "label": label,
        "description": str(node.get("description") or "").strip(),
        "category": category,
        "is_weak": bool(node.get("is_weak") or category == "weak"),
        "prerequisites": list(node.get("prerequisites") or []),
    }


def _normalize_edge(edge: dict[str, Any]) -> dict[str, Any]:
    relation_type = str(edge.get("relation_type") or "related")
    if relation_type not in RELATION_LABELS:
        relation_type = "related"
    return {
        "source": str(edge.get("source") or ""),
        "target": str(edge.get("target") or ""),
        "relation_type": relation_type,
        "label": str(edge.get("label") or RELATION_LABELS[relation_type]),
    }


def _calculate_levels(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, int]:
    node_ids = [node["id"] for node in nodes]
    levels = {node_id: 0 for node_id in node_ids}
    incoming: dict[str, int] = defaultdict(int)
    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for edge in edges:
        incoming[edge["target"]] += 1
        outgoing[edge["source"]].append(edge)

    for node in nodes:
        if node.get("category") == "core" or not incoming.get(node["id"]):
            levels[node["id"]] = 0

    for _ in range(max(1, len(nodes))):
        changed = False
        for source, source_edges in outgoing.items():
            source_level = levels.get(source, 0)
            for edge in source_edges:
                target = edge["target"]
                relation = edge.get("relation_type")
                step = 0 if relation == "related" else 1
                next_level = source_level + step
                if next_level > levels.get(target, 0):
                    levels[target] = next_level
                    changed = True
        if not changed:
            break

    return levels
