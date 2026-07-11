"""Deterministic semantic layout for the teaching-video stage."""

from __future__ import annotations

from dataclasses import dataclass

from app.shared.cartoon.schemas import TeachingScene, VisualModel, replay_scene


@dataclass(frozen=True)
class PositionedNode:
    id: str
    x: float
    y: float


def layout_scene(scene: TeachingScene) -> dict[str, PositionedNode]:
    """Lay out the union of initial and future nodes so inserts keep stable space."""
    final_model = replay_scene(scene)
    initial = scene.visual_model
    model = VisualModel(kind=initial.kind, label=initial.label, nodes=final_model.nodes, edges=final_model.edges)
    if model.kind == "tree":
        return _tree_layout(model)
    if model.kind == "array":
        return _array_layout(model)
    if model.kind in {"flow", "network", "memory"}:
        return _flow_layout(model)
    if model.kind == "comparison":
        return _comparison_layout(model)
    return _graph_layout(model)


def _tree_layout(model: VisualModel) -> dict[str, PositionedNode]:
    children: dict[str | None, list[str]] = {}
    for node in model.nodes:
        children.setdefault(node.parent_id, []).append(node.id)
    roots = children.get(None) or [model.nodes[0].id]
    result: dict[str, PositionedNode] = {}
    queue = [(root, 0) for root in roots]
    levels: dict[int, list[str]] = {}
    while queue:
        node_id, depth = queue.pop(0)
        levels.setdefault(depth, []).append(node_id)
        queue.extend((child, depth + 1) for child in children.get(node_id, []))
    max_depth = max(levels, default=0)
    for depth, ids in levels.items():
        spacing = 100 / (len(ids) + 1)
        for index, node_id in enumerate(ids, 1):
            result[node_id] = PositionedNode(node_id, spacing * index, 16 + (68 * depth / max(1, max_depth)))
    return result


def _array_layout(model: VisualModel) -> dict[str, PositionedNode]:
    count = max(1, len(model.nodes))
    return {node.id: PositionedNode(node.id, (index + 1) * 100 / (count + 1), 48) for index, node in enumerate(model.nodes)}


def _flow_layout(model: VisualModel) -> dict[str, PositionedNode]:
    count = max(1, len(model.nodes))
    return {node.id: PositionedNode(node.id, 12 + index * 76 / max(1, count - 1), 48) for index, node in enumerate(model.nodes)}


def _comparison_layout(model: VisualModel) -> dict[str, PositionedNode]:
    count = max(1, len(model.nodes))
    return {node.id: PositionedNode(node.id, 24 + (index % 2) * 52, 28 + (index // 2) * 42) for index, node in enumerate(model.nodes)}


def _graph_layout(model: VisualModel) -> dict[str, PositionedNode]:
    positions = [(50, 17), (22, 45), (78, 45), (35, 78), (65, 78), (50, 51), (15, 75), (85, 75)]
    return {node.id: PositionedNode(node.id, *positions[index % len(positions)]) for index, node in enumerate(model.nodes)}
