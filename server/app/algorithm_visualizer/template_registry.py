"""官方算法可视化模板目录。

这里是前端目录、模板源码和运行时入口的唯一事实来源。官方模式只保留
高频、适合逐步展示的经典算法；自定义代码模式不受此目录限制。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_TEMPLATES_DIR = Path(__file__).with_name("templates")

LANGUAGES: list[dict[str, str]] = [
    {"key": "python", "label": "Python", "extension": "py"},
]


@dataclass(frozen=True, slots=True)
class TemplateSpec:
    """One complete, executable official-template contract."""

    key: str
    domain: str
    name: str
    visualizer_type: str
    difficulty: str
    entry_point: str
    default_input: dict[str, Any]
    input_schema: dict[str, Any]
    expected_events: tuple[str, ...]
    language: str = "python"

    @property
    def source_path(self) -> Path:
        return _TEMPLATES_DIR / self.domain / self.key / "python.py"

    @property
    def visual_path(self) -> Path:
        return _TEMPLATES_DIR / self.domain / self.key / "visual.py"

    @property
    def source_code(self) -> str:
        return self.source_path.read_text(encoding="utf-8")

    @property
    def version(self) -> str:
        normalized = self.source_code.replace("\r\n", "\n").rstrip() + "\n"
        return f"sha256:{hashlib.sha256(normalized.encode()).hexdigest()}"


def _infer_input_schema(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {
            "type": "object",
            "required": list(value),
            "properties": {key: _infer_input_schema(item) for key, item in value.items()},
        }
    if isinstance(value, list):
        schema: dict[str, Any] = {"type": "array"}
        if value:
            item_schemas = [_infer_input_schema(item) for item in value]
            first_schema = item_schemas[0]
            schema["items"] = first_schema if all(item == first_schema for item in item_schemas) else {}
        return schema
    if isinstance(value, bool):
        return {"type": "boolean"}
    if isinstance(value, int):
        return {"type": "integer"}
    if isinstance(value, float):
        return {"type": "number"}
    if value is None:
        return {"type": "null"}
    return {"type": "string"}


def _template(
    *,
    key: str,
    domain: str,
    name: str,
    visualizer_type: str,
    difficulty: str,
    entry_point: str,
    default_input: dict[str, Any],
) -> TemplateSpec:
    initial_event = {
        "array": "init_array",
        "stack-queue": "init_stack",
        "linked-list": "init_list",
        "tree": "init_tree",
        "graph": "init_graph",
        "dp-table": "init_table",
    }[visualizer_type]
    return TemplateSpec(
        key=key,
        domain=domain,
        name=name,
        visualizer_type=visualizer_type,
        difficulty=difficulty,
        entry_point=entry_point,
        default_input=default_input,
        input_schema=_infer_input_schema(default_input),
        expected_events=(initial_event, "snapshot", "finish"),
    )


# Ordered teaching path: familiar fundamentals first, then core structures,
# traversal, shortest path and dynamic programming. Every entry is exercised
# by the official-runtime regression test.
_SPECS: tuple[TemplateSpec, ...] = (
    _template(
        key="bubble_sort", domain="sorting", name="冒泡排序", visualizer_type="array",
        difficulty="easy", entry_point="bubble_sort_with_bounds",
        default_input={"arr": [6, 1, 8, 3, 9, 2]},
    ),
    _template(
        key="selection_sort", domain="sorting", name="选择排序", visualizer_type="array",
        difficulty="easy", entry_point="selection_sort",
        default_input={"arr": [6, 1, 8, 3, 9, 2]},
    ),
    _template(
        key="insertion_sort", domain="sorting", name="插入排序", visualizer_type="array",
        difficulty="easy", entry_point="insertion_sort",
        default_input={"arr": [6, 1, 8, 3, 9, 2]},
    ),
    _template(
        key="quick_sort", domain="sorting", name="快速排序", visualizer_type="array",
        difficulty="medium", entry_point="quick_sort",
        default_input={"arr": [6, 1, 8, 3, 9, 2]},
    ),
    _template(
        key="merge_sort", domain="sorting", name="归并排序", visualizer_type="array",
        difficulty="medium", entry_point="merge_sort_wrapper",
        default_input={"arr": [6, 1, 8, 3, 9, 2]},
    ),
    _template(
        key="binary_search", domain="searching", name="二分查找", visualizer_type="array",
        difficulty="easy", entry_point="binary_search",
        default_input={"arr": [1, 2, 3, 5, 8], "target": 5},
    ),
    _template(
        key="linked_list_reverse", domain="base_data_structure", name="链表反转", visualizer_type="linked-list",
        difficulty="medium", entry_point="reverse_list",
        default_input={"arr": [1, 2, 3, 4, 5]},
    ),
    _template(
        key="bracket_match", domain="base_data_structure", name="括号匹配", visualizer_type="stack-queue",
        difficulty="easy", entry_point="is_valid_brackets",
        default_input={"s": "{[()]}"},
    ),
    _template(
        key="binary_tree_traverse", domain="tree_structure", name="二叉树前序遍历", visualizer_type="tree",
        difficulty="easy", entry_point="preorder_traversal",
        default_input={"arr": [1, 2, 3, 4, 5, 6, 7]},
    ),
    _template(
        key="graph_bfs", domain="graph_structure", name="广度优先搜索", visualizer_type="graph",
        difficulty="easy", entry_point="bfs_all_components",
        default_input={"num_nodes": 6, "edges": [[0, 1], [0, 2], [1, 3], [1, 4], [2, 5]], "start": 0},
    ),
    _template(
        key="graph_dfs", domain="graph_structure", name="深度优先搜索", visualizer_type="graph",
        difficulty="easy", entry_point="dfs_graph",
        default_input={"num_nodes": 6, "edges": [[0, 1], [0, 2], [1, 3], [1, 4], [2, 5]], "start": 0},
    ),
    _template(
        key="shortest_path", domain="graph_structure", name="Dijkstra 最短路径", visualizer_type="graph",
        difficulty="medium", entry_point="dijkstra",
        default_input={
            "num_nodes": 6,
            "edges": [[0, 1, 5], [0, 2, 1], [1, 2, 2], [1, 3, 3], [1, 4, 20], [2, 4, 12], [3, 4, 2], [3, 5, 6], [4, 5, 1]],
            "start": 0,
        },
    ),
    _template(
        key="knapsack_dp", domain="dynamic_programming", name="0/1 背包", visualizer_type="dp-table",
        difficulty="medium", entry_point="knapsack",
        default_input={"weights": [2, 3, 4, 5], "values": [3, 4, 5, 6], "capacity": 5},
    ),
)

_SPECS_BY_KEY = {spec.key: spec for spec in _SPECS}

# Kept as API-ready dictionaries because the response schema uses camelCase at
# its boundary. No duplicated, independent catalogue is maintained.
ALGORITHMS: dict[str, dict[str, Any]] = {
    spec.key: {
        "domain": spec.domain,
        "name": spec.name,
        "visualizer_type": spec.visualizer_type,
        "difficulty": spec.difficulty,
        "supported_languages": [spec.language],
        "required_events": list(spec.expected_events),
    }
    for spec in _SPECS
}


def get_all_template_specs() -> list[TemplateSpec]:
    return list(_SPECS)


def get_template_spec(algorithm_key: str) -> TemplateSpec:
    try:
        return _SPECS_BY_KEY[algorithm_key]
    except KeyError as exc:
        raise ValueError(f"不支持的算法模板: {algorithm_key}") from exc


def get_all_algorithms(domain: str = "all") -> list[dict[str, Any]]:
    return [
        {"key": spec.key, **ALGORITHMS[spec.key]}
        for spec in _SPECS
        if domain == "all" or spec.domain == domain
    ]


def get_algorithm_info(algorithm_key: str) -> dict[str, Any]:
    try:
        return {"key": algorithm_key, **ALGORITHMS[algorithm_key]}
    except KeyError as exc:
        raise ValueError(f"不支持的算法: {algorithm_key}") from exc


def get_template_code(algorithm_key: str, language: str) -> str:
    spec = get_template_spec(algorithm_key)
    if language != spec.language:
        raise ValueError(f"算法 {algorithm_key} 不支持语言 {language}")
    if not spec.source_path.is_file():
        raise ValueError(f"模板文件不存在: {algorithm_key}/{language}")
    return spec.source_code


def build_default_data(algorithm: str) -> dict[str, Any]:
    return get_template_spec(algorithm).default_input.copy()
