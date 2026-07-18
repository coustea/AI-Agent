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
        head = _find_linked_head(local_values, result)
        if head is not None and id(head) not in self._object_ids:
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
        self._root_node: object | None = None
        self._object_ids: dict[int, str] = {}
        self._discovered: bool = False
        self._execution_started: bool = False

    def set_root(self, root: object) -> None:
        """Register the tree root for identity tracking."""
        self._root_node = root
        _, self._object_ids = _tree_nodes(root)
        self._discovered = True

    def _build_initial_structure(self) -> dict[str, object]:
        nodes = _fallback_tree_nodes(self._input_data)
        for node in nodes:
            node["left_constructed"] = False
            node["right_constructed"] = False
        return {"nodes": nodes, "phase": "construction"}

    def _do_capture(
        self,
        local_values: dict[str, object],
        result: object | None,
    ) -> tuple[dict[str, object], list[object]]:
        # Always use the fallback tree layout to keep positions stable and prevent jumping
        nodes = _fallback_tree_nodes(self._input_data)

        is_building = self.current_func_name in {"_build_tree", "__init__"}
        phase = "construction" if is_building else "traversal"

        if is_building:
            self._execution_started = False
            # During construction: build a map of all node objects by their
            # position-index (from the local `nodes` list in _build_tree).
            # Start all edges as unconstructed, then set True for each node
            # whose .left / .right attribute is already non-None.
            nodes_list = local_values.get("nodes")
            node_objects: dict[str, object] = {}
            if isinstance(nodes_list, list):
                for index, obj in enumerate(nodes_list):
                    if obj is not None:
                        nid = f"node-{index}"
                        self._object_ids[id(obj)] = nid
                        node_objects[nid] = obj

            for node in nodes:
                nid = node["id"]
                obj = node_objects.get(nid)
                if obj is not None:
                    node["left_constructed"] = (
                        hasattr(obj, "left") and getattr(obj, "left") is not None
                    )
                    node["right_constructed"] = (
                        hasattr(obj, "right") and getattr(obj, "right") is not None
                    )
                else:
                    # Object not yet in nodes list → definitely not constructed
                    node["left_constructed"] = False
                    node["right_constructed"] = False

            targets: list[str] = []
            # Highlight the parent node currently being wired (loop variable `node`)
            loop_node = local_values.get("node")
            loop_id = self._object_ids.get(id(loop_node))
            if loop_id is not None:
                targets.append(loop_id)

            # Highlight the child node currently being connected
            child_index = local_values.get("child_index")
            if isinstance(child_index, int) and isinstance(nodes_list, list) and 0 <= child_index < len(nodes_list):
                child_node = nodes_list[child_index]
                child_id = self._object_ids.get(id(child_node))
                if child_id is not None:
                    targets.append(child_id)

        else:
            # Traversal phase: all links are fully constructed.
            # Auto-discover root on first traversal frame.
            if not self._execution_started:
                root = _find_tree_root(local_values)
                if root is not None:
                    self.set_root(root)
                    self._execution_started = True

            for node in nodes:
                node["left_constructed"] = "left" in node
                node["right_constructed"] = "right" in node

            # Highlight the active node being visited
            targets = []
            for name in ("node", "root", "current"):
                value = local_values.get(name)
                nid = self._object_ids.get(id(value))
                if nid is not None:
                    targets.append(nid)

        return {"nodes": nodes, "phase": phase}, targets


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
