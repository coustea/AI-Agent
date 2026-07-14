"""Deterministic execution and state observation for official templates."""

from __future__ import annotations

import copy
import io
import importlib.util
import inspect
import json
import sys
from contextlib import redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from types import FrameType, ModuleType
from typing import Any, Callable

from app.algorithm_visualizer.template_registry import TemplateSpec, get_template_spec
from app.algorithm_visualizer.tracer_sdks.python_tracer import VisualTracer


class OfficialRuntimeError(RuntimeError):
    """Raised when an official template cannot satisfy its registry contract."""


@dataclass(frozen=True, slots=True)
class OfficialExecution:
    result: Any
    events: list[dict[str, Any]]


@dataclass(frozen=True, slots=True)
class _Snapshot:
    structure: dict[str, Any]
    targets: list[Any]
    message: str


def run_official_template(
    algorithm_key: str,
    input_data: dict[str, Any],
) -> OfficialExecution:
    spec = get_template_spec(algorithm_key)
    tracer = VisualTracer(spec.visualizer_type)
    result = run_registered_template(algorithm_key, input_data, tracer)
    return OfficialExecution(result=result, events=tracer.events)


def run_registered_template(
    algorithm_key: str,
    input_data: dict[str, Any],
    tracer: VisualTracer,
) -> Any:
    spec = get_template_spec(algorithm_key)
    module = _load_source_module(spec)
    entry = getattr(module, spec.entry_point, None)
    if not callable(entry):
        raise OfficialRuntimeError(
            f"模板 {algorithm_key} 缺少入口函数 {spec.entry_point}"
        )

    args, kwargs = _bind_arguments(spec, module, entry, copy.deepcopy(input_data))
    adapter = _StateAdapter(spec, module, input_data, args, kwargs)
    first_line = max(1, entry.__code__.co_firstlineno)
    initial = adapter.initial()
    tracer.snapshot(
        _initial_event_type(spec, initial),
        initial.structure,
        targets=initial.targets,
        message=initial.message,
        line=first_line,
    )

    last_fingerprint = _snapshot_fingerprint(initial)
    last_snapshot = initial
    snapshot_count = 0
    source_path = str(spec.source_path.resolve())

    def observe(frame: FrameType, event: str, arg: object):
        nonlocal last_fingerprint, last_snapshot, snapshot_count
        if frame.f_code.co_filename != source_path or event not in {"line", "return"}:
            return observe
        snapshot = adapter.capture(frame.f_locals, arg if event == "return" else None)
        fingerprint = _snapshot_fingerprint(snapshot)
        if fingerprint != last_fingerprint and snapshot_count < 600:
            tracer.snapshot(
                "snapshot",
                snapshot.structure,
                targets=snapshot.targets,
                message=snapshot.message,
                line=frame.f_lineno,
            )
            last_fingerprint = fingerprint
            last_snapshot = snapshot
            snapshot_count += 1
        return observe

    previous_trace = sys.gettrace()
    try:
        sys.settrace(observe)
        with redirect_stdout(io.StringIO()):
            result = entry(*args, **kwargs)
    finally:
        sys.settrace(previous_trace)

    final_snapshot = adapter.capture({}, result)
    final_fingerprint = _snapshot_fingerprint(final_snapshot)
    if final_fingerprint != last_fingerprint:
        tracer.snapshot(
            "snapshot",
            final_snapshot.structure,
            targets=final_snapshot.targets,
            message=final_snapshot.message,
            line=first_line,
        )
        last_snapshot = final_snapshot
    elif snapshot_count == 0:
        tracer.snapshot(
            "snapshot",
            last_snapshot.structure,
            targets=last_snapshot.targets,
            message="算法完成一次有效执行",
            line=first_line,
        )

    tracer.snapshot(
        "finish",
        last_snapshot.structure,
        message="算法执行完成",
        line=first_line,
    )
    return _to_jsonable(result)


def _load_source_module(spec: TemplateSpec) -> ModuleType:
    module_name = f"_algorithm_template_{spec.key}_{spec.version[-12:]}"
    module_spec = importlib.util.spec_from_file_location(module_name, spec.source_path)
    if module_spec is None or module_spec.loader is None:
        raise OfficialRuntimeError(f"无法加载模板源码: {spec.source_path}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def _bind_arguments(
    spec: TemplateSpec,
    module: ModuleType,
    entry: Callable[..., Any],
    data: dict[str, Any],
) -> tuple[list[Any], dict[str, Any]]:
    signature = inspect.signature(entry)
    kwargs: dict[str, Any] = {}
    graph = _build_graph(data) if "edges" in data else None
    root = _build_tree(module, data.get("arr", []))
    head = _build_linked_list(module, data.get("arr", []))

    aliases = {
        "nums": ("arr",),
        "prices": ("arr",),
        "s": ("text", "string"),
        "source": ("start",),
        "node": ("start",),
        "perm_list": ("arr",),
        "candidates": ("arr",),
    }

    for name, parameter in signature.parameters.items():
        if name in data:
            kwargs[name] = data[name]
            continue
        if name in {"root", "tree"} and root is not None:
            kwargs[name] = root
            continue
        if name == "head" and head is not None:
            kwargs[name] = head
            continue
        if name == "node" and spec.visualizer_type == "linked-list" and head is not None:
            kwargs[name] = head
            continue
        if name == "graph" and graph is not None:
            kwargs[name] = graph
            continue
        matched = next((data[key] for key in aliases.get(name, ()) if key in data), None)
        if matched is not None:
            kwargs[name] = matched
            continue
        if name in {"lo", "left"} and "arr" in data:
            kwargs[name] = 0
            continue
        if name in {"hi", "right"} and "arr" in data:
            kwargs[name] = len(data["arr"]) - 1
            continue
        if name == "n" and "arr" in data:
            kwargs[name] = len(data["arr"])
            continue
        if parameter.default is not inspect.Parameter.empty:
            continue
        raise OfficialRuntimeError(
            f"模板 {spec.key} 的输入缺少入口参数: {name}"
        )
    return [], kwargs


def _build_linked_list(module: ModuleType, values: Any) -> Any:
    if not isinstance(values, list) or not values:
        return None
    node_class = getattr(module, "ListNode", None) or getattr(module, "Node", None)
    if node_class is None:
        return None
    head = node_class(values[0])
    current = head
    for value in values[1:]:
        current.next = node_class(value)
        current = current.next
    return head


def _build_tree(module: ModuleType, values: Any) -> Any:
    if not isinstance(values, list) or not values:
        return None
    node_class = getattr(module, "TreeNode", None) or getattr(module, "Node", None)
    if node_class is None:
        return None
    nodes = [node_class(value) if value is not None else None for value in values]
    child_index = 1
    for node in nodes:
        if node is None:
            continue
        if child_index < len(nodes):
            node.left = nodes[child_index]
            child_index += 1
        if child_index < len(nodes):
            node.right = nodes[child_index]
            child_index += 1
    return nodes[0]


def _build_graph(data: dict[str, Any]) -> dict[int, list[Any]]:
    num_nodes = int(data.get("num_nodes", 0))
    edges = data.get("edges", [])
    if not num_nodes and edges:
        num_nodes = max(max(int(edge[0]), int(edge[1])) for edge in edges) + 1
    graph: dict[int, list[Any]] = {index: [] for index in range(num_nodes)}
    weighted = any(isinstance(edge, list) and len(edge) > 2 for edge in edges)
    for edge in edges:
        source, target = int(edge[0]), int(edge[1])
        value: Any = (target, edge[2]) if weighted else target
        graph[source].append(value)
        if data.get("directed") is not True:
            reverse: Any = (source, edge[2]) if weighted else source
            graph[target].append(reverse)
    return graph


class _StateAdapter:
    def __init__(
        self,
        spec: TemplateSpec,
        module: ModuleType,
        input_data: dict[str, Any],
        args: list[Any],
        kwargs: dict[str, Any],
    ) -> None:
        self.spec = spec
        self.module = module
        self.input_data = copy.deepcopy(input_data)
        self.bound_values = [*args, *kwargs.values()]
        self._object_ids: dict[int, str] = {}
        self._last_structure = self._initial_structure()

    def initial(self) -> _Snapshot:
        return _Snapshot(
            structure=copy.deepcopy(self._last_structure),
            targets=[],
            message="初始化可视化状态",
        )

    def capture(self, local_values: dict[str, Any], result: Any = None) -> _Snapshot:
        capture_method = getattr(self, f"_capture_{self.spec.visualizer_type.replace('-', '_')}")
        structure, targets = capture_method(local_values, result)
        self._last_structure = structure
        return _Snapshot(
            structure=copy.deepcopy(structure),
            targets=targets,
            message=_line_message(local_values),
        )

    def _initial_structure(self) -> dict[str, Any]:
        visualizer_type = self.spec.visualizer_type
        if visualizer_type == "array":
            return {"array": _initial_array(self.input_data)}
        if visualizer_type == "stack-queue":
            mode = "queue" if "queue" in self.spec.key else "stack"
            return {"mode": mode, "items": [], "pointers": []}
        if visualizer_type == "linked-list":
            return {
                "nodes": _nodes_from_values(self.input_data.get("arr", [])),
                "pointers": [],
            }
        if visualizer_type == "tree":
            root = next(
                (value for value in self.bound_values if hasattr(value, "left") or hasattr(value, "right")),
                None,
            )
            nodes, self._object_ids = _tree_nodes(root)
            if not nodes:
                nodes = _fallback_tree_nodes(self.input_data)
            return {"nodes": nodes}
        if visualizer_type == "graph":
            return {"nodes": _graph_nodes(self.input_data)}
        return _initial_table(self.input_data)

    def _capture_array(self, local_values: dict[str, Any], result: Any):
        values = _find_scalar_list(local_values)
        if values is None and isinstance(result, (list, tuple)):
            values = list(result)
        array = _numeric_array(values) if values is not None else self._last_structure["array"]
        return {"array": array}, _integer_targets(local_values, len(array))

    def _capture_stack_queue(self, local_values: dict[str, Any], result: Any):
        mode = self._last_structure["mode"]
        values = _find_sequence(local_values, ("stack", "queue", "deque", "dq", "q"))
        if values is None:
            values = [item.get("label") for item in self._last_structure["items"]]
        items = [
            {"id": f"item-{index}", "label": str(value), "tone": "default"}
            for index, value in enumerate(values)
        ]
        return {"mode": mode, "items": items, "pointers": []}, []

    def _capture_linked_list(self, local_values: dict[str, Any], result: Any):
        candidates = [result, local_values.get("prev"), local_values.get("head")]
        root = next((item for item in candidates if hasattr(item, "next")), None)
        values, object_indexes = _linked_values(root)
        if not values:
            values = [node["label"] for node in self._last_structure["nodes"]]
        pointers = []
        for label in ("prev", "current", "curr", "head", "next_node"):
            node = local_values.get(label)
            if id(node) in object_indexes:
                pointers.append(
                    {"label": label, "nodeIndex": object_indexes[id(node)], "tone": "accent"}
                )
        return {"nodes": _nodes_from_values(values), "pointers": pointers}, list(object_indexes.values())[:1]

    def _capture_tree(self, local_values: dict[str, Any], result: Any):
        nodes = copy.deepcopy(self._last_structure["nodes"])
        targets = []
        for name in ("node", "root", "current"):
            value = local_values.get(name)
            node_id = self._object_ids.get(id(value))
            if node_id is not None:
                targets.append(node_id)
                for node in nodes:
                    if node["id"] == node_id:
                        node["tone"] = "visited"
        return {"nodes": nodes}, targets

    def _capture_graph(self, local_values: dict[str, Any], result: Any):
        nodes = copy.deepcopy(self._last_structure["nodes"])
        visited = local_values.get("visited")
        visited_values = set()
        if isinstance(visited, set):
            visited_values = visited
        elif isinstance(visited, list):
            visited_values = {index for index, value in enumerate(visited) if value}
        targets = _integer_targets(local_values, len(nodes))
        for node in nodes:
            if int(node["id"]) in visited_values or int(node["id"]) in targets:
                node["tone"] = "visited"
        return {"nodes": nodes}, [str(target) for target in targets]

    def _capture_dp_table(self, local_values: dict[str, Any], result: Any):
        table = _find_table(local_values)
        if table is None and isinstance(result, list):
            table = result
        if table is None:
            return copy.deepcopy(self._last_structure), []
        values = table if table and isinstance(table[0], list) else [table]
        width = max((len(row) for row in values), default=1)
        return {
            "headers": [str(index) for index in range(width)],
            "values": _to_jsonable(values),
            "highlighted": [],
        }, _table_targets(local_values, values)


def _initial_event_type(spec: TemplateSpec, snapshot: _Snapshot) -> str:
    if spec.visualizer_type == "array":
        return "init_array"
    if spec.visualizer_type == "stack-queue":
        return "init_queue" if snapshot.structure["mode"] == "queue" else "init_stack"
    return {
        "linked-list": "init_list",
        "tree": "init_tree",
        "graph": "init_graph",
        "dp-table": "init_table",
    }[spec.visualizer_type]


def _initial_array(data: dict[str, Any]) -> list[Any]:
    for key in ("arr", "nums", "prices", "points", "intervals"):
        if isinstance(data.get(key), list):
            return _numeric_array(data[key])
    for key in ("text", "s", "pattern"):
        if isinstance(data.get(key), str):
            return [ord(char) for char in data[key]]
    numeric = [value for value in data.values() if isinstance(value, (int, float))]
    return numeric or [0]


def _numeric_array(values: list[Any]) -> list[Any]:
    numeric: list[Any] = []
    for value in values:
        if isinstance(value, bool):
            numeric.append(int(value))
        elif isinstance(value, (int, float)):
            numeric.append(value)
        elif isinstance(value, str) and len(value) == 1:
            numeric.append(ord(value))
        elif isinstance(value, (list, tuple)):
            numeric.append(len(value))
    return numeric or [0]


def _find_scalar_list(local_values: dict[str, Any]) -> list[Any] | None:
    for key in ("arr", "nums", "prices", "result", "output", "dp"):
        value = local_values.get(key)
        if isinstance(value, list) and (not value or not isinstance(value[0], list)):
            return list(value)
    return None


def _find_sequence(local_values: dict[str, Any], names: tuple[str, ...]) -> list[Any] | None:
    for name in names:
        value = local_values.get(name)
        if isinstance(value, (list, tuple)):
            return list(value)
        if value is not None and value.__class__.__name__ == "deque":
            return list(value)
    return None


def _integer_targets(local_values: dict[str, Any], length: int) -> list[int]:
    targets = []
    for name in ("i", "j", "left", "right", "lo", "hi", "mid", "index", "start", "end"):
        value = local_values.get(name)
        if isinstance(value, int) and not isinstance(value, bool) and 0 <= value < length:
            if value not in targets:
                targets.append(value)
    return targets[:4]


def _nodes_from_values(values: Any) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        values = list(values) if isinstance(values, tuple) else []
    return [
        {"id": f"node-{index}", "label": str(value), "tone": "default"}
        for index, value in enumerate(values)
    ]


def _linked_values(root: Any) -> tuple[list[Any], dict[int, int]]:
    values = []
    indexes: dict[int, int] = {}
    current = root
    while current is not None and hasattr(current, "next") and id(current) not in indexes and len(values) < 100:
        indexes[id(current)] = len(values)
        values.append(getattr(current, "val", getattr(current, "value", "?")))
        current = current.next
    return values, indexes


def _tree_nodes(root: Any) -> tuple[list[dict[str, Any]], dict[int, str]]:
    nodes: list[dict[str, Any]] = []
    object_ids: dict[int, str] = {}

    def visit(node: Any) -> str | None:
        if node is None or id(node) in object_ids:
            return object_ids.get(id(node))
        node_id = f"node-{len(object_ids)}"
        object_ids[id(node)] = node_id
        item = {
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


def _heap_nodes(values: Any) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        return []
    nodes = _nodes_from_values([value for value in values if value is not None])
    for index, node in enumerate(nodes):
        children = []
        for child_index in (2 * index + 1, 2 * index + 2):
            if child_index < len(nodes):
                children.append(nodes[child_index]["id"])
        if children:
            node["children"] = children
    return nodes


def _fallback_tree_nodes(data: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(data.get("arr"), list):
        return _heap_nodes(data["arr"])
    if isinstance(data.get("candidates"), list):
        return _heap_nodes(["root", *data["candidates"]])
    if isinstance(data.get("words"), list):
        return _trie_nodes(data["words"])
    if isinstance(data.get("char_freq"), list):
        values = [f"{item[0]}:{item[1]}" for item in data["char_freq"] if len(item) >= 2]
        return _heap_nodes(values)
    if isinstance(data.get("n"), int):
        return _recursion_nodes(data["n"])
    return []


def _trie_nodes(words: list[Any]) -> list[dict[str, Any]]:
    nodes = [{"id": "node-0", "label": "root", "tone": "default", "children": []}]
    prefixes = {"": "node-0"}
    for raw_word in words:
        word = str(raw_word)
        prefix = ""
        for char in word:
            parent_prefix = prefix
            prefix += char
            if prefix in prefixes:
                continue
            node_id = f"node-{len(nodes)}"
            prefixes[prefix] = node_id
            nodes.append(
                {
                    "id": node_id,
                    "label": char,
                    "tone": "default",
                    "children": [],
                }
            )
            parent_id = prefixes[parent_prefix]
            parent = next(node for node in nodes if node["id"] == parent_id)
            parent["children"].append(node_id)
    return nodes


def _recursion_nodes(n: int) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []

    def build(value: int, depth: int) -> str:
        node_id = f"node-{len(nodes)}"
        node = {
            "id": node_id,
            "label": str(value),
            "tone": "default",
            "children": [],
        }
        nodes.append(node)
        if value > 1 and depth < 5:
            node["children"].append(build(value - 1, depth + 1))
            if value > 2:
                node["children"].append(build(value - 2, depth + 1))
        return node_id

    build(max(0, n), 0)
    return nodes


def _graph_nodes(data: dict[str, Any]) -> list[dict[str, Any]]:
    graph = _build_graph(data)
    nodes = []
    for node_id, adjacent in graph.items():
        edges = []
        for item in adjacent:
            if isinstance(item, tuple):
                edges.append({"to": str(item[0]), "weight": item[1]})
            else:
                edges.append({"to": str(item)})
        nodes.append(
            {"id": str(node_id), "label": str(node_id), "tone": "default", "edges": edges}
        )
    return nodes


def _initial_table(data: dict[str, Any]) -> dict[str, Any]:
    if isinstance(data.get("grid"), list):
        values = copy.deepcopy(data["grid"])
    elif isinstance(data.get("maze"), list):
        values = copy.deepcopy(data["maze"])
    else:
        size = int(data.get("n", data.get("capacity", 5))) + 1
        values = [[0 for _ in range(max(1, min(size, 100)))]]
    width = max((len(row) for row in values), default=1)
    return {
        "headers": [str(index) for index in range(width)],
        "values": values,
        "highlighted": [],
    }


def _find_table(local_values: dict[str, Any]) -> list[Any] | None:
    for key in ("dp", "table", "grid", "matrix", "board", "visited"):
        value = local_values.get(key)
        if isinstance(value, list):
            return copy.deepcopy(value)
    return None


def _table_targets(local_values: dict[str, Any], values: list[list[Any]]) -> list[Any]:
    if not values:
        return []
    row = next((local_values.get(name) for name in ("i", "r", "row") if isinstance(local_values.get(name), int)), None)
    col = next((local_values.get(name) for name in ("j", "c", "col") if isinstance(local_values.get(name), int)), None)
    if row is None or col is None:
        return []
    return [{"row": row, "col": col}]


def _line_message(local_values: dict[str, Any]) -> str:
    names = [name for name in ("i", "j", "left", "right", "node", "current") if name in local_values]
    return "执行算法步骤" if not names else f"更新状态：{', '.join(names)}"


def _snapshot_fingerprint(snapshot: _Snapshot) -> str:
    return json.dumps(
        {"structure": snapshot.structure, "targets": snapshot.targets},
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )


def _to_jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(item) for item in value]
    if hasattr(value, "val"):
        return getattr(value, "val")
    return str(value)
