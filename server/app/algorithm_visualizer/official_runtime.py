"""Deterministic execution and state observation for official templates.

The runtime compiles only the trusted template source, enables
``sys.settrace`` only for that filename, and collects semantic events
through per-visualizer-type observation adapters.  It replaces the legacy
``_bind_arguments``, ``_build_linked_list``, ``_build_tree``,
``_build_graph``, and ``_StateAdapter`` with a simple contract:
``entry(**validated_input)``.
"""

from __future__ import annotations

import copy
import io
import importlib.util
import json
import sys
from contextlib import redirect_stdout
from dataclasses import dataclass
from types import FrameType, ModuleType
from typing import Any

from pydantic import JsonValue

from app.algorithm_visualizer.official_adapters import get_adapter
from app.algorithm_visualizer.official_adapters.structures import LinkedListAdapter
from app.algorithm_visualizer.template_registry import TemplateSpec
from app.algorithm_visualizer.trace_builder import TraceBuilder, TraceEvent


class OfficialRuntimeError(RuntimeError):
    """Raised when an official template cannot satisfy its registry contract."""


@dataclass(frozen=True, slots=True)
class OfficialExecution:
    """Result of running one official template with validated input."""

    events: list[TraceEvent]
    result: JsonValue
    summary: str


def execute_official_template(
    spec: TemplateSpec,
    input_data: dict[str, Any],
) -> OfficialExecution:
    """Execute a registered template and return its semantic trace.

    Args:
        spec: The template specification from the registry.
        input_data: Validated input matching ``spec.input_model``.

    Returns:
        An OfficialExecution with events, result, and summary.

    Raises:
        OfficialRuntimeError: when the template cannot be loaded or its
            entry function is missing.
    """
    module = _load_source_module(spec)
    entry = getattr(module, spec.entry_point, None)
    if not callable(entry):
        raise OfficialRuntimeError(
            f"模板 {spec.key} 缺少入口函数 {spec.entry_point}"
        )

    adapter = get_adapter(spec.visualizer_type, copy.deepcopy(input_data))
    builder = TraceBuilder(
        visualizer_type=spec.visualizer_type,
        max_events=spec.max_events,
    )

    # Pre-register linked-list identities. Tree nodes are instead captured
    # from the executing frame, including their actual left/right references.
    _pre_register_structures(adapter, module, input_data)

    first_line = max(1, entry.__code__.co_firstlineno)
    initial_structure, initial_targets = adapter.initial()
    initial_event_type = _initial_event_type(spec, initial_structure)
    builder.add(
        initial_event_type,
        initial_structure,
        targets=initial_targets,
        message="初始化可视化状态",
        line=first_line,
    )

    last_fingerprint = _snapshot_fingerprint(initial_structure, initial_targets)
    last_structure = initial_structure
    last_targets = initial_targets
    snapshot_count = 0
    source_path = str(spec.source_path.resolve())
    line_event_count = 0
    max_line_events = 50_000

    def observe(frame: FrameType, event: str, arg: object):
        nonlocal last_fingerprint, last_structure, last_targets
        nonlocal snapshot_count, line_event_count

        if frame.f_code.co_filename != source_path:
            return observe
        if event == "line":
            line_event_count += 1
            if line_event_count > max_line_events:
                return None  # Stop tracing this file
        if event not in {"line", "return"}:
            return observe
        if frame.f_code.co_name == "__init__":
            return observe

        structure, targets = adapter.capture(
            frame.f_locals,
            arg if event == "return" else None,
            func_name=frame.f_code.co_name,
        )
        fingerprint = _snapshot_fingerprint(structure, targets)
        is_construction = frame.f_code.co_name in {
            "_build_tree",
            "_build_undirected_graph",
            "_build_weighted_graph",
        }
        if (is_construction or fingerprint != last_fingerprint) and snapshot_count < spec.max_events:
            event_type = _describe_step(
                spec, last_structure, structure, targets
            )
            builder.add(
                event_type,
                structure,
                targets=targets,
                message=_line_message(frame.f_locals),
                line=frame.f_lineno,
            )
            last_fingerprint = fingerprint
            last_structure = structure
            last_targets = targets
            snapshot_count += 1
        return observe

    previous_trace = sys.gettrace()
    try:
        sys.settrace(observe)
        with redirect_stdout(io.StringIO()):
            result = entry(**input_data)
    finally:
        sys.settrace(previous_trace)

    # Final snapshot from the return value.
    final_structure, final_targets = adapter.capture({}, result, func_name=spec.entry_point)
    final_fingerprint = _snapshot_fingerprint(final_structure, final_targets)
    if final_fingerprint != last_fingerprint:
        builder.add(
            "snapshot",
            final_structure,
            targets=final_targets,
            message="算法完成一次有效执行",
            line=first_line,
        )
        last_structure = final_structure
    elif snapshot_count == 0:
        builder.add(
            "snapshot",
            last_structure,
            targets=last_targets,
            message="算法完成一次有效执行",
            line=first_line,
        )

    builder.add(
        "finish",
        last_structure,
        message="算法执行完成",
        line=first_line,
    )

    jsonable_result = _to_jsonable(result)
    event_count = builder.step
    return OfficialExecution(
        events=builder.events,
        result=jsonable_result,
        summary=f"执行成功，共产生 {event_count} 步可视化操作。",
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_source_module(spec: TemplateSpec) -> ModuleType:
    """Compile the trusted template source as an isolated module."""
    module_name = f"_algorithm_template_{spec.key}_{spec.version[-12:]}"
    module_spec = importlib.util.spec_from_file_location(
        module_name, spec.source_path
    )
    if module_spec is None or module_spec.loader is None:
        raise OfficialRuntimeError(f"无法加载模板源码: {spec.source_path}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def _pre_register_structures(
    adapter: object,
    module: ModuleType,
    input_data: dict[str, Any],
) -> None:
    """Pre-build linked-list nodes for identity tracking.

    The entry function constructs ListNode objects internally. We build the
    same initial list so the first rendered state is visible before the first
    traced frame; the runtime list replaces it as soon as execution begins.
    """
    if isinstance(adapter, LinkedListAdapter):
        head = _build_linked_list_from_module(module, input_data.get("arr", []))
        if head is not None:
            adapter.set_head(head)


def _build_linked_list_from_module(
    module: ModuleType,
    values: object,
) -> object | None:
    """Build a linked list using the template's own ListNode class."""
    if not isinstance(values, list) or not values:
        return None
    # Use the template's _build_linked_list helper if available.
    builder = getattr(module, "_build_linked_list", None)
    if callable(builder):
        return builder(values)
    # Fallback: construct manually using the template's ListNode.
    node_class = getattr(module, "ListNode", None) or getattr(module, "Node", None)
    if node_class is None:
        return None
    head = node_class(values[0])
    current = head
    for value in values[1:]:
        current.next = node_class(value)
        current = current.next
    return head


def _initial_event_type(
    spec: TemplateSpec,
    structure: dict[str, object],
) -> str:
    """Return the correct init event type for a visualizer."""
    if spec.visualizer_type == "array":
        return "init_array"
    if spec.visualizer_type == "stack-queue":
        mode = structure.get("mode", "stack")
        return "init_queue" if mode == "queue" else "init_stack"
    return {
        "linked-list": "init_list",
        "tree": "init_tree",
        "graph": "init_graph",
        "dp-table": "init_table",
    }[spec.visualizer_type]


def _describe_step(
    spec: TemplateSpec,
    previous_structure: dict[str, object],
    current_structure: dict[str, object],
    current_targets: list[object],
) -> str:
    """Classify an array step as swap, write, compare, or snapshot."""
    if spec.visualizer_type != "array":
        return "snapshot"

    previous_array = previous_structure.get("array")
    current_array = current_structure.get("array")
    if not isinstance(previous_array, list) or not isinstance(current_array, list):
        return "snapshot"
    if len(previous_array) != len(current_array):
        return "write"

    changed = [
        index
        for index, (before, after) in enumerate(zip(previous_array, current_array))
        if before != after
    ]
    if changed:
        is_swap = (
            len(changed) == 2
            and previous_array[changed[0]] == current_array[changed[1]]
            and previous_array[changed[1]] == current_array[changed[0]]
        )
        return "swap" if is_swap else "write"

    if len(current_targets) == 2 and current_targets[0] != current_targets[1]:
        return "compare"
    return "snapshot"


def _snapshot_fingerprint(
    structure: dict[str, object],
    targets: list[object],
) -> str:
    """Produce a deterministic fingerprint for deduplication."""
    return json.dumps(
        {"structure": structure, "targets": targets},
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )


def _line_message(local_values: dict[str, object]) -> str:
    """Build a short human-readable message from active local variables."""
    names = [
        name
        for name in (
            "i", "j", "left", "right", "middle", "position", "minimum",
            "char", "node", "current", "current_capacity",
        )
        if name in local_values
    ]
    return "执行算法步骤" if not names else f"更新状态：{', '.join(names)}"


def _to_jsonable(value: object) -> object:
    """Recursively convert a value to a JSON-compatible representation."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(item) for item in value]
    if hasattr(value, "val"):
        return getattr(value, "val")
    return str(value)
