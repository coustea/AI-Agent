"""Validation for trace events consumed by the six frontend visualizers.

Validates both structural shape and semantic invariants:
- Continuous steps and unique ids
- Valid positive source lines
- JSON size limits (4 MiB serialized)
- List/node uniqueness
- Named-pointer targets
- Linked-list: dangling ``next`` references
- Tree: dangling ``left``/``right``/``children`` references
- Graph: edges pointing to non-existent nodes, duplicate directed edges
- DP table: rectangular shape, header width consistency, target coordinates
"""

from __future__ import annotations

import json
from typing import Any


class InvalidTraceError(ValueError):
    """Raised when a trace cannot be rendered by the selected visualizer."""


_INITIAL_EVENTS = {
    "array": {"init_array"},
    "stack-queue": {"init_stack", "init_queue"},
    "linked-list": {"init_list"},
    "tree": {"init_tree"},
    "graph": {"init_graph"},
    "dp-table": {"init_table"},
}

_MAX_SERIALIZED_BYTES = 4 * 1024 * 1024  # 4 MiB


def validate_trace_events(
    events: list[dict[str, Any]],
    visualizer_type: str,
    *,
    source_line_count: int,
) -> None:
    """Validate core trace structure and visualizer-specific invariants."""
    _validate_core(events, visualizer_type, source_line_count=source_line_count)
    _validate_semantic_invariants(events, visualizer_type)


# ---------------------------------------------------------------------------
# Core structural validation
# ---------------------------------------------------------------------------

def _validate_core(
    events: list[dict[str, Any]],
    visualizer_type: str,
    *,
    source_line_count: int | None,
) -> None:
    """Validate basic structural shape of a trace event list."""
    if visualizer_type not in _INITIAL_EVENTS:
        raise InvalidTraceError(f"不支持的 visualizerType: {visualizer_type}")
    if not events:
        raise InvalidTraceError("事件流不能为空")
    if events[0].get("type") not in _INITIAL_EVENTS[visualizer_type]:
        raise InvalidTraceError("第一条事件必须是对应可视化器的初始化事件")
    if events[-1].get("type") != "finish":
        raise InvalidTraceError("最后一条事件必须是 finish")

    seen_ids: set[str] = set()
    for index, event in enumerate(events):
        _validate_event(
            event,
            index=index,
            visualizer_type=visualizer_type,
            source_line_count=source_line_count,
        )
        event_id = event.get("id")
        if event_id in seen_ids:
            raise InvalidTraceError(f"事件 id 重复: {event_id}")
        seen_ids.add(event_id)

    if not any(
        _has_renderable_content(event["state"]["structure"], visualizer_type)
        for event in events
    ):
        raise InvalidTraceError(f"{visualizer_type} 事件流没有可渲染内容")

    # Check serialized size.
    try:
        serialized = json.dumps(events, ensure_ascii=False, default=str)
        if len(serialized.encode("utf-8")) > _MAX_SERIALIZED_BYTES:
            raise InvalidTraceError(
                f"序列化事件数据超过 {_MAX_SERIALIZED_BYTES} 字节"
            )
    except (TypeError, ValueError) as exc:
        raise InvalidTraceError(f"事件数据无法序列化: {exc}") from exc


def _validate_event(
    event: dict[str, Any],
    *,
    index: int,
    visualizer_type: str,
    source_line_count: int | None,
) -> None:
    """Validate a single event's structural shape."""
    if event.get("step") != index:
        raise InvalidTraceError(
            f"事件 step 必须连续，位置 {index} 收到 {event.get('step')}"
        )
    if not isinstance(event.get("id"), str) or not event["id"]:
        raise InvalidTraceError("事件 id 必须是非空字符串")
    if event.get("visualizerType") != visualizer_type:
        raise InvalidTraceError("事件 visualizerType 与模板不一致")

    line = event.get("line")
    if line is not None:
        if isinstance(line, bool) or not isinstance(line, int) or line < 1:
            raise InvalidTraceError(
                f"事件 line 必须是正整数，收到 {line}"
            )
        if source_line_count is not None and line > source_line_count:
            raise InvalidTraceError(
                f"事件 line 必须位于 1..{source_line_count}，收到 {line}"
            )

    targets = event.get("targets")
    if targets is not None and not isinstance(targets, list):
        raise InvalidTraceError("事件 targets 必须是数组")

    state = event.get("state")
    if not isinstance(state, dict) or not isinstance(state.get("structure"), dict):
        raise InvalidTraceError("事件 state.structure 必须是对象")
    _validate_structure(state["structure"], visualizer_type)


def _validate_structure(structure: dict[str, Any], visualizer_type: str) -> None:
    """Validate the structure field shape for a visualizer type."""
    if visualizer_type == "array":
        _require_list(structure, "array", "array")
        return
    if visualizer_type == "stack-queue":
        if structure.get("mode") not in {"stack", "queue"}:
            raise InvalidTraceError("stack-queue structure.mode 无效")
        _require_list(structure, "items", "stack-queue")
        _require_optional_list(structure, "pointers", "stack-queue")
        return
    if visualizer_type == "linked-list":
        _require_list(structure, "nodes", "linked-list")
        _require_list(structure, "pointers", "linked-list")
        return
    if visualizer_type in {"tree", "graph"}:
        nodes = _require_list(structure, "nodes", visualizer_type)
        for node in nodes:
            if not isinstance(node, dict) or "id" not in node or "label" not in node:
                raise InvalidTraceError(
                    f"{visualizer_type} structure.nodes 项必须包含 id 和 label"
                )
        return
    if visualizer_type == "dp-table":
        _require_list(structure, "headers", "dp-table")
        values = _require_list(structure, "values", "dp-table")
        if any(not isinstance(row, list) for row in values):
            raise InvalidTraceError("dp-table structure.values 必须是二维数组")
        _require_list(structure, "highlighted", "dp-table")
        return


# ---------------------------------------------------------------------------
# Semantic invariant validation
# ---------------------------------------------------------------------------

def _validate_semantic_invariants(
    events: list[dict[str, Any]],
    visualizer_type: str,
) -> None:
    """Check semantic invariants that go beyond structural shape."""
    for event in events:
        structure = event.get("state", {}).get("structure", {})
        if not isinstance(structure, dict):
            continue

        if visualizer_type == "linked-list":
            _validate_linked_list_invariants(structure)
        elif visualizer_type == "tree":
            _validate_tree_invariants(structure)
        elif visualizer_type == "graph":
            _validate_graph_invariants(structure)
        elif visualizer_type == "dp-table":
            _validate_dp_table_invariants(structure, event.get("targets"))


def _validate_linked_list_invariants(structure: dict[str, Any]) -> None:
    """Check that linked-list node references are not dangling."""
    nodes = structure.get("nodes", [])
    if not isinstance(nodes, list):
        return
    node_ids = {node.get("id") for node in nodes if isinstance(node, dict)}
    for node in nodes:
        if not isinstance(node, dict):
            continue
        next_id = node.get("next")
        if next_id is not None and next_id not in node_ids:
            raise InvalidTraceError(
                f"链表节点 {node.get('id')} 的 next 指向不存在的节点: {next_id}"
            )


def _validate_tree_invariants(structure: dict[str, Any]) -> None:
    """Check that tree node left/right/children references are not dangling."""
    nodes = structure.get("nodes", [])
    if not isinstance(nodes, list):
        return
    node_ids = {node.get("id") for node in nodes if isinstance(node, dict)}
    for node in nodes:
        if not isinstance(node, dict):
            continue
        for ref_key in ("left", "right", "children"):
            ref_value = node.get(ref_key)
            if ref_value is None:
                continue
            if isinstance(ref_value, list):
                for child_id in ref_value:
                    if child_id not in node_ids:
                        raise InvalidTraceError(
                            f"树节点 {node.get('id')} 的 {ref_key} 指向不存在的节点: {child_id}"
                        )
            elif ref_value not in node_ids:
                raise InvalidTraceError(
                    f"树节点 {node.get('id')} 的 {ref_key} 指向不存在的节点: {ref_value}"
                )


def _validate_graph_invariants(structure: dict[str, Any]) -> None:
    """Check graph edge endpoints and duplicate directed edges."""
    nodes = structure.get("nodes", [])
    if not isinstance(nodes, list):
        return
    node_ids = {node.get("id") for node in nodes if isinstance(node, dict)}
    directed = structure.get("directed", False)

    for node in nodes:
        if not isinstance(node, dict):
            continue
        edges = node.get("edges", [])
        if not isinstance(edges, list):
            continue
        seen_targets: set[str] = set()
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            target = edge.get("to")
            if target is not None and target not in node_ids:
                raise InvalidTraceError(
                    f"图节点 {node.get('id')} 的边指向不存在的节点: {target}"
                )
            if directed:
                edge_key = target
                if edge_key in seen_targets:
                    raise InvalidTraceError(
                        f"有向图节点 {node.get('id')} 存在重复的指向 {target} 的边"
                    )
                seen_targets.add(edge_key)


def _validate_dp_table_invariants(
    structure: dict[str, Any],
    targets: list[Any] | None,
) -> None:
    """Check DP table rectangularity, header width, and target coordinates."""
    values = structure.get("values")
    headers = structure.get("headers")

    if not isinstance(values, list):
        return

    # Check rectangularity.
    if values:
        first_width = len(values[0]) if isinstance(values[0], list) else 1
        for row_index, row in enumerate(values):
            if not isinstance(row, list):
                raise InvalidTraceError(
                    f"DP 表第 {row_index} 行不是数组"
                )
            if len(row) != first_width:
                raise InvalidTraceError(
                    f"DP 表不是矩形：第 0 行宽度 {first_width}，"
                    f"第 {row_index} 行宽度 {len(row)}"
                )

        # Check header width consistency.
        if isinstance(headers, list) and len(headers) != first_width:
            raise InvalidTraceError(
                f"DP 表 headers 宽度 {len(headers)} 与数据宽度 {first_width} 不一致"
            )

    # Check target coordinates are within bounds.
    if isinstance(targets, list) and isinstance(values, list) and values:
        row_count = len(values)
        col_count = len(values[0]) if isinstance(values[0], list) else 0
        for target in targets:
            if not isinstance(target, dict):
                continue
            row = target.get("row")
            col = target.get("col")
            if isinstance(row, int) and (row < 0 or row >= row_count):
                raise InvalidTraceError(
                    f"DP 表 target row={row} 超出范围 0..{row_count - 1}"
                )
            if isinstance(col, int) and (col < 0 or col >= col_count):
                raise InvalidTraceError(
                    f"DP 表 target col={col} 超出范围 0..{col_count - 1}"
                )


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _require_list(
    structure: dict[str, Any],
    key: str,
    visualizer_type: str,
) -> list[Any]:
    value = structure.get(key)
    if not isinstance(value, list):
        raise InvalidTraceError(f"{visualizer_type} structure.{key} 必须是数组")
    return value


def _require_optional_list(
    structure: dict[str, Any],
    key: str,
    visualizer_type: str,
) -> None:
    if key in structure:
        _require_list(structure, key, visualizer_type)


def _has_renderable_content(
    structure: dict[str, Any],
    visualizer_type: str,
) -> bool:
    if visualizer_type == "array":
        return bool(structure.get("array"))
    if visualizer_type == "stack-queue":
        return bool(structure.get("items")) or bool(structure.get("currentValue"))
    if visualizer_type in {"linked-list", "tree", "graph"}:
        return bool(structure.get("nodes"))
    if visualizer_type == "dp-table":
        values = structure.get("values")
        return bool(values) and any(bool(row) for row in values)
    return False
