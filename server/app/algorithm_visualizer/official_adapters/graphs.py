"""Adapter for the graph visualizer type.

Graph templates expose graph adjacency plus ``visited``, ``queue``,
``order``, ``distance``, and ``current node``.  The adapter tracks visited
nodes and distances using the actual graph structure from local variables.
"""

from __future__ import annotations

import copy
import math
from typing import Any

from app.algorithm_visualizer.official_adapters._base import BaseAdapter


class GraphAdapter(BaseAdapter):
    """Observes graph templates (BFS, DFS, Dijkstra)."""

    def _build_initial_structure(self) -> dict[str, object]:
        return {
            "nodes": _graph_nodes_from_input(self._input_data),
            "directed": _is_directed(self._input_data),
        }

    def _do_capture(
        self,
        local_values: dict[str, object],
        result: object | None,
    ) -> tuple[dict[str, object], list[object]]:
        nodes = copy.deepcopy(self._last_structure.get("nodes", []))
        directed = self._last_structure.get("directed", False)

        visited = local_values.get("visited")
        distance = local_values.get("distance")
        visited_values: set[int] = set()
        if isinstance(visited, set):
            visited_values = visited
        elif isinstance(visited, list):
            visited_values = {
                index for index, value in enumerate(visited) if value
            }

        targets = _integer_targets(local_values, len(nodes))
        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_index = int(node["id"])
            if node_index in visited_values or node_index in targets:
                node["tone"] = "visited"
            if isinstance(distance, list) and node_index < len(distance):
                value = distance[node_index]
                node["distance"] = (
                    "inf" if isinstance(value, float) and math.isinf(value) else value
                )
        return {"nodes": nodes, "directed": directed}, [str(t) for t in targets]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _graph_nodes_from_input(data: dict[str, object]) -> list[dict[str, object]]:
    """Build graph node list from validated input data."""
    num_nodes = int(data.get("num_nodes", 0))
    edges = data.get("edges", [])
    if not isinstance(edges, list):
        edges = []

    graph: dict[int, list[object]] = {index: [] for index in range(num_nodes)}
    weighted = any(isinstance(edge, list) and len(edge) > 2 for edge in edges)
    for edge in edges:
        if not isinstance(edge, (list, tuple)) or len(edge) < 2:
            continue
        source, target = int(edge[0]), int(edge[1])
        value: object = (target, edge[2]) if weighted and len(edge) > 2 else target
        graph[source].append(value)
        if data.get("directed") is not True:
            reverse: object = (
                (source, edge[2]) if weighted and len(edge) > 2 else source
            )
            graph[target].append(reverse)

    nodes: list[dict[str, object]] = []
    for node_id, adjacent in graph.items():
        edge_list: list[dict[str, object]] = []
        for item in adjacent:
            if isinstance(item, tuple):
                edge_list.append({"to": str(item[0]), "weight": item[1]})
            else:
                edge_list.append({"to": str(item)})
        nodes.append(
            {
                "id": str(node_id),
                "label": str(node_id),
                "tone": "default",
                "edges": edge_list,
            }
        )
    return nodes


def _is_directed(data: dict[str, object]) -> bool:
    """Determine if the graph is directed from input data."""
    return data.get("directed") is True


def _integer_targets(local_values: dict[str, object], length: int) -> list[int]:
    """Extract valid integer index targets from local variables."""
    targets: list[int] = []
    for name in ("i", "j", "node", "current", "start", "source"):
        value = local_values.get(name)
        if (
            isinstance(value, int)
            and not isinstance(value, bool)
            and 0 <= value < length
            and value not in targets
        ):
            targets.append(value)
    return targets[:4]
