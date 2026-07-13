"""Validation for trace events consumed by the six frontend visualizers."""

from __future__ import annotations

from typing import Any


class TraceValidationError(ValueError):
    """Raised when a trace cannot be rendered by the selected visualizer."""


_INITIAL_EVENTS = {
    "array": {"init_array"},
    "stack-queue": {"init_stack", "init_queue"},
    "linked-list": {"init_list"},
    "tree": {"init_tree"},
    "graph": {"init_graph"},
    "dp-table": {"init_table"},
}


def validate_trace_events(
    events: list[dict[str, Any]],
    visualizer_type: str,
    *,
    source_line_count: int,
) -> None:
    if visualizer_type not in _INITIAL_EVENTS:
        raise TraceValidationError(f"不支持的 visualizerType: {visualizer_type}")
    if not events:
        raise TraceValidationError("事件流不能为空")
    if events[0].get("type") not in _INITIAL_EVENTS[visualizer_type]:
        raise TraceValidationError("第一条事件必须是对应可视化器的初始化事件")
    if events[-1].get("type") != "finish":
        raise TraceValidationError("最后一条事件必须是 finish")

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
            raise TraceValidationError(f"事件 id 重复: {event_id}")
        seen_ids.add(event_id)


def _validate_event(
    event: dict[str, Any],
    *,
    index: int,
    visualizer_type: str,
    source_line_count: int,
) -> None:
    if event.get("step") != index:
        raise TraceValidationError(
            f"事件 step 必须连续，位置 {index} 收到 {event.get('step')}"
        )
    if not isinstance(event.get("id"), str) or not event["id"]:
        raise TraceValidationError("事件 id 必须是非空字符串")
    if event.get("visualizerType") != visualizer_type:
        raise TraceValidationError("事件 visualizerType 与模板不一致")

    line = event.get("line")
    if line is not None and (
        isinstance(line, bool)
        or not isinstance(line, int)
        or line < 1
        or line > source_line_count
    ):
        raise TraceValidationError(
            f"事件 line 必须位于 1..{source_line_count}，收到 {line}"
        )

    targets = event.get("targets")
    if targets is not None and not isinstance(targets, list):
        raise TraceValidationError("事件 targets 必须是数组")

    state = event.get("state")
    if not isinstance(state, dict) or not isinstance(state.get("structure"), dict):
        raise TraceValidationError("事件 state.structure 必须是对象")
    _validate_structure(state["structure"], visualizer_type)


def _validate_structure(structure: dict[str, Any], visualizer_type: str) -> None:
    if visualizer_type == "array":
        _require_list(structure, "array", "array")
        return
    if visualizer_type == "stack-queue":
        if structure.get("mode") not in {"stack", "queue"}:
            raise TraceValidationError("stack-queue structure.mode 无效")
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
                raise TraceValidationError(
                    f"{visualizer_type} structure.nodes 项必须包含 id 和 label"
                )
        return
    if visualizer_type == "dp-table":
        _require_list(structure, "headers", "dp-table")
        values = _require_list(structure, "values", "dp-table")
        if any(not isinstance(row, list) for row in values):
            raise TraceValidationError("dp-table structure.values 必须是二维数组")
        _require_list(structure, "highlighted", "dp-table")


def _require_list(
    structure: dict[str, Any],
    key: str,
    visualizer_type: str,
) -> list[Any]:
    value = structure.get(key)
    if not isinstance(value, list):
        raise TraceValidationError(
            f"{visualizer_type} structure.{key} 必须是数组"
        )
    return value


def _require_optional_list(
    structure: dict[str, Any],
    key: str,
    visualizer_type: str,
) -> None:
    if key in structure:
        _require_list(structure, key, visualizer_type)
