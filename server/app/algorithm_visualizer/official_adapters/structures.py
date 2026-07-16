"""Adapters for linked-list and tree visualizer types.

Linked-list templates expose object identity plus actual ``next``,
``prev``/``current``/``next_node`` pointers.  Tree templates expose
actual ``left``/``right`` identities plus traversal focus.

No adapter may connect nodes by array position when the source object has
no explicit relation.
"""

from __future__ import annotations

import copy
from typing import Any

from app.algorithm_visualizer.official_adapters._base import BaseAdapter


class LinkedListAdapter(BaseAdapter):
    """Observes linked-list templates using object identity and named pointers.

    The adapter auto-discovers linked-list nodes from local variables on
    first capture, so it does not require pre-registration.
    """

    def __init__(self, input_data: dict[str, object]) -> None:
        super().__init__(input_data)
        self._node_objects: list[object] = []
        self._object_ids: dict[int, str] = {}
        self._discovered: bool = False

    def set_head(self, head: object) -> None:
        """Register the linked-list head object for identity tracking."""
        self._node_objects, self._object_ids = _collect_linked_nodes(head)
        self._discovered = True

    def _build_initial_structure(self) -> dict[str, object]:
        if self._discovered:
            nodes = _linked_nodes(self._node_objects, self._object_ids, set())
        else:
            nodes = _fallback_linked_nodes(self._input_data)
        return {
            "nodes": nodes,
            "pointers": [],
        }

    def _do_capture(
        self,
        local_values: dict[str, object],
        result: object | None,
    ) -> tuple[dict[str, object], list[object]]:
        # Auto-discover linked-list nodes from local variables.
        if not self._discovered:
            head = _find_linked_head(local_values, result)
            if head is not None:
                self.set_head(head)

        pointers: list[dict[str, object]] = []
        active_ids: set[str] = set()
        for label in ("prev", "current", "curr", "head", "next_node"):
            node = local_values.get(label)
            node_id = self._object_ids.get(id(node))
            if node_id is not None:
                pointers.append(
                    {
                        "label": label,
                        "nodeId": node_id,
                        "tone": "accent",
                    }
                )
                active_ids.add(node_id)
        if not pointers and result is not None:
            node_id = self._object_ids.get(id(result))
            if node_id is not None:
                active_ids.add(node_id)

        if self._discovered:
            nodes = _linked_nodes(self._node_objects, self._object_ids, active_ids)
        else:
            nodes = _fallback_linked_nodes(self._input_data)
        return {
            "nodes": nodes,
            "pointers": pointers,
        }, list(active_ids)


class TreeAdapter(BaseAdapter):
    """Observes tree templates using actual left/right object identity.

    The adapter auto-discovers tree nodes from local variables on first
    capture, so it does not require pre-registration.
    """

    def __init__(self, input_data: dict[str, object]) -> None:
        super().__init__(input_data)
        self._object_ids: dict[int, str] = {}
        self._discovered: bool = False

    def set_root(self, root: object) -> None:
        """Register the tree root for identity tracking."""
        _, self._object_ids = _tree_nodes(root)
        self._discovered = True

    def _build_initial_structure(self) -> dict[str, object]:
        if self._discovered:
            # We don't store the root, so we can't rebuild here.
            # Return fallback nodes; capture() will fix it.
            pass
        nodes = _fallback_tree_nodes(self._input_data)
        return {"nodes": nodes}

    def _do_capture(
        self,
        local_values: dict[str, object],
        result: object | None,
    ) -> tuple[dict[str, object], list[object]]:
        # Rebuild tree nodes from object identity each capture.
        root = _find_tree_root(local_values)
        if root is not None:
            nodes, self._object_ids = _tree_nodes(root)
            self._discovered = True
        elif self._discovered:
            nodes = copy.deepcopy(self._last_structure.get("nodes", []))
        else:
            nodes = _fallback_tree_nodes(self._input_data)

        targets: list[str] = []
        for name in ("node", "root", "current"):
            value = local_values.get(name)
            node_id = self._object_ids.get(id(value))
            if node_id is not None:
                targets.append(node_id)
                for node in nodes:
                    if isinstance(node, dict) and node.get("id") == node_id:
                        node["tone"] = "visited"
        return {"nodes": nodes}, targets


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _collect_linked_nodes(root: object) -> tuple[list[object], dict[int, str]]:
    """Walk a linked list and collect node objects with stable ids."""
    nodes: list[object] = []
    object_ids: dict[int, str] = {}
    current = root
    while (
        current is not None
        and hasattr(current, "next")
        and id(current) not in object_ids
        and len(nodes) < 100
    ):
        object_ids[id(current)] = f"node-{len(nodes)}"
        nodes.append(current)
        current = getattr(current, "next", None)
    return nodes, object_ids


def _linked_nodes(
    node_objects: list[object],
    object_ids: dict[int, str],
    active_ids: set[str],
) -> list[dict[str, object]]:
    """Serialize linked-list node objects into the frontend contract."""
    return [
        {
            "id": object_ids[id(node)],
            "label": str(getattr(node, "val", getattr(node, "value", "?"))),
            "next": object_ids.get(id(getattr(node, "next", None))),
            "tone": "visited" if object_ids[id(node)] in active_ids else "default",
        }
        for node in node_objects
    ]


def _find_linked_head(
    local_values: dict[str, object],
    result: object | None,
) -> object | None:
    """Find the linked-list head in local variables or return value."""
    for name in ("head", "current", "curr", "prev", "next_node"):
        value = local_values.get(name)
        if value is not None and hasattr(value, "next"):
            return value
    if result is not None and hasattr(result, "next"):
        return result
    return None


def _fallback_linked_nodes(data: dict[str, object]) -> list[dict[str, object]]:
    """Build linked-list nodes from input array when no head object is available."""
    arr = data.get("arr")
    if not isinstance(arr, list) or not arr:
        return []
    nodes: list[dict[str, object]] = []
    for index, value in enumerate(arr):
        node: dict[str, object] = {
            "id": f"node-{index}",
            "label": str(value),
            "next": f"node-{index + 1}" if index + 1 < len(arr) else None,
            "tone": "default",
        }
        nodes.append(node)
    return nodes


def _tree_nodes(root: object) -> tuple[list[dict[str, object]], dict[int, str]]:
    """Walk a binary tree and collect nodes with actual left/right references."""
    nodes: list[dict[str, object]] = []
    object_ids: dict[int, str] = {}

    def visit(node: object) -> str | None:
        if node is None or id(node) in object_ids:
            return object_ids.get(id(node))
        node_id = f"node-{len(object_ids)}"
        object_ids[id(node)] = node_id
        item: dict[str, object] = {
            "id": node_id,
            "label": str(getattr(node, "val", getattr(node, "value", "?"))),
            "tone": "default",
        }
        nodes.append(item)
        left_id = visit(getattr(node, "left", None))
        right_id = visit(getattr(node, "right", None))
        if left_id is not None:
            item["left"] = left_id
        if right_id is not None:
            item["right"] = right_id
        return node_id

    visit(root)
    return nodes, object_ids


def _find_tree_root(local_values: dict[str, object]) -> object | None:
    """Find the tree root in local variables by object identity."""
    for name in ("root", "node", "current"):
        value = local_values.get(name)
        if value is not None and (hasattr(value, "left") or hasattr(value, "right")):
            return value
    return None


def _fallback_tree_nodes(data: dict[str, object]) -> list[dict[str, object]]:
    """Build tree nodes from an input array when no root object is available."""
    arr = data.get("arr")
    if not isinstance(arr, list) or not arr:
        return []
    nodes: list[dict[str, object]] = []
    for index, value in enumerate(arr):
        if value is None:
            continue
        node: dict[str, object] = {
            "id": f"node-{index}",
            "label": str(value),
            "tone": "default",
        }
        left_index = 2 * index + 1
        right_index = 2 * index + 2
        if left_index < len(arr) and arr[left_index] is not None:
            node["left"] = f"node-{left_index}"
        if right_index < len(arr) and arr[right_index] is not None:
            node["right"] = f"node-{right_index}"
        nodes.append(node)
    return nodes
