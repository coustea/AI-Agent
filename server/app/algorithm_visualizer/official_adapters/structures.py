"""Adapters for linked-list and tree visualizer types.

Linked-list templates expose object identity plus actual ``next``,
``prev``/``current``/``next_node`` pointers.  Tree templates expose
actual ``left``/``right`` identities plus traversal focus.

No adapter may connect nodes by array position when the source object has
no explicit relation.
"""

from __future__ import annotations

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
        self._object_ids: dict[int, str] = {}

    def _build_initial_structure(self) -> dict[str, object]:
        # Node links must come from the executing `_build_tree` frame.  An
        # empty initial state is preferable to inferring links from input.
        return {"nodes": [], "phase": "construction"}

    def _do_capture(
        self,
        local_values: dict[str, object],
        result: object | None,
    ) -> tuple[dict[str, object], list[object]]:
        is_building = self.current_func_name in {"_build_tree", "__init__"}
        phase = "construction" if is_building else "traversal"

        if is_building:
            nodes_list = local_values.get("nodes")
            nodes = _tree_nodes_from_execution_list(nodes_list, self._object_ids)

            targets: list[str] = []
            loop_node = local_values.get("node")
            loop_id = self._object_ids.get(id(loop_node))
            if loop_id is not None:
                targets.append(loop_id)

            child_index = local_values.get("child_index")
            if isinstance(child_index, int) and isinstance(nodes_list, list) and 0 <= child_index < len(nodes_list):
                child_node = nodes_list[child_index]
                child_id = self._object_ids.get(id(child_node))
                if child_id is not None:
                    targets.append(child_id)

        else:
            root = _find_tree_root(local_values)
            if root is not None:
                nodes, self._object_ids = _tree_nodes(root, self._object_ids)
            else:
                nodes = list(self._last_structure.get("nodes", []))

            for node in nodes:
                node["left_constructed"] = node.get("left") is not None
                node["right_constructed"] = node.get("right") is not None

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


def _tree_nodes(
    root: object,
    object_ids: dict[int, str] | None = None,
) -> tuple[list[dict[str, object]], dict[int, str]]:
    """Walk a binary tree and collect nodes with actual left/right references."""
    nodes: list[dict[str, object]] = []
    object_ids = dict(object_ids or {})
    visited: set[int] = set()

    def visit(node: object) -> str | None:
        if node is None:
            return None
        if id(node) in visited:
            return object_ids.get(id(node))
        visited.add(id(node))
        node_id = object_ids.get(id(node), f"node-{len(object_ids)}")
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


def _tree_nodes_from_execution_list(
    nodes_list: object,
    object_ids: dict[int, str],
) -> list[dict[str, object]]:
    """Serialize the actual nodes created by the template's builder frame."""
    if not isinstance(nodes_list, list):
        return []

    runtime_nodes = [node for node in nodes_list if node is not None]
    for index, node in enumerate(nodes_list):
        if node is not None:
            object_ids[id(node)] = f"node-{index}"

    result: list[dict[str, object]] = []
    for node in runtime_nodes:
        item: dict[str, object] = {
            "id": object_ids[id(node)],
            "label": str(getattr(node, "val", getattr(node, "value", "?"))),
            "tone": "default",
            "left_constructed": getattr(node, "left", None) is not None,
            "right_constructed": getattr(node, "right", None) is not None,
        }
        left = getattr(node, "left", None)
        right = getattr(node, "right", None)
        if left is not None and id(left) in object_ids:
            item["left"] = object_ids[id(left)]
        if right is not None and id(right) in object_ids:
            item["right"] = object_ids[id(right)]
        result.append(item)
    return result
