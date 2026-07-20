"""The trusted, Python-only algorithm template catalogue."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import JsonValue

from app.algorithm_visualizer.schemas import OfficialVisualizerType
from app.algorithm_visualizer.template_inputs import (
    BinarySearchInput,
    BinaryTreeInput,
    BracketMatchInput,
    GraphTraversalInput,
    IntegerArrayInput,
    KnapsackInput,
    LinkedListInput,
    StrictTemplateInput,
    WeightedGraphInput,
)


__all__ = (
    "TemplateNotFoundError",
    "TemplateSpec",
    "get_all_template_specs",
    "get_template_spec",
)


_TEMPLATES_DIR = Path(__file__).with_name("templates")


class TemplateNotFoundError(KeyError):
    """Raised when a key is not present in the official catalogue."""

    def __init__(self, template_key: str) -> None:
        self.template_key = template_key
        super().__init__(f"未找到算法模板: {template_key}")


@dataclass(frozen=True, slots=True)
class TemplateSpec:
    key: str
    domain: str
    name: str
    visualizer_type: OfficialVisualizerType
    difficulty: Literal["easy", "medium", "hard"]
    entry_point: str
    input_model: type[StrictTemplateInput]
    default_input: dict[str, JsonValue]
    max_events: int = 600

    @property
    def input_schema(self) -> dict[str, JsonValue]:
        return self.input_model.model_json_schema()

    @property
    def source_path(self) -> Path:
        return _TEMPLATES_DIR / self.domain / self.key / "python.py"

    @property
    def source_code(self) -> str:
        return self.source_path.read_text(encoding="utf-8")

    @property
    def version(self) -> str:
        normalized = self.source_code.replace("\r\n", "\n").rstrip() + "\n"
        return f"sha256:{hashlib.sha256(normalized.encode()).hexdigest()}"


def _template(
    *,
    key: str,
    domain: str,
    name: str,
    visualizer_type: OfficialVisualizerType,
    difficulty: Literal["easy", "medium", "hard"],
    entry_point: str,
    input_model: type[StrictTemplateInput],
    default_input: dict[str, JsonValue],
) -> TemplateSpec:
    validated_default = input_model.model_validate(default_input).model_dump(mode="json")
    return TemplateSpec(
        key=key,
        domain=domain,
        name=name,
        visualizer_type=visualizer_type,
        difficulty=difficulty,
        entry_point=entry_point,
        input_model=input_model,
        default_input=validated_default,
    )


_SPECS: tuple[TemplateSpec, ...] = (
    _template(
        key="bubble_sort",
        domain="sorting",
        name="冒泡排序",
        visualizer_type="array",
        difficulty="easy",
        entry_point="bubble_sort_with_bounds",
        input_model=IntegerArrayInput,
        default_input={"arr": [6, 1, 8, 3, 9, 2]},
    ),
    _template(
        key="selection_sort",
        domain="sorting",
        name="选择排序",
        visualizer_type="array",
        difficulty="easy",
        entry_point="selection_sort",
        input_model=IntegerArrayInput,
        default_input={"arr": [6, 1, 8, 3, 9, 2]},
    ),
    _template(
        key="insertion_sort",
        domain="sorting",
        name="插入排序",
        visualizer_type="array",
        difficulty="easy",
        entry_point="insertion_sort",
        input_model=IntegerArrayInput,
        default_input={"arr": [6, 1, 8, 3, 9, 2]},
    ),
    _template(
        key="quick_sort",
        domain="sorting",
        name="快速排序",
        visualizer_type="array",
        difficulty="medium",
        entry_point="quick_sort",
        input_model=IntegerArrayInput,
        default_input={"arr": [6, 1, 8, 3, 9, 2]},
    ),
    _template(
        key="merge_sort",
        domain="sorting",
        name="归并排序",
        visualizer_type="array",
        difficulty="medium",
        entry_point="merge_sort_wrapper",
        input_model=IntegerArrayInput,
        default_input={"arr": [6, 1, 8, 3, 9, 2]},
    ),
    _template(
        key="binary_search",
        domain="searching",
        name="二分查找",
        visualizer_type="array",
        difficulty="easy",
        entry_point="binary_search",
        input_model=BinarySearchInput,
        default_input={"arr": [1, 2, 3, 5, 8], "target": 5},
    ),
    _template(
        key="linked_list_reverse",
        domain="base_data_structure",
        name="链表反转",
        visualizer_type="linked-list",
        difficulty="medium",
        entry_point="reverse_list",
        input_model=LinkedListInput,
        default_input={"arr": [1, 2, 3, 4, 5]},
    ),
    _template(
        key="bracket_match",
        domain="base_data_structure",
        name="括号匹配",
        visualizer_type="stack-queue",
        difficulty="easy",
        entry_point="is_valid_brackets",
        input_model=BracketMatchInput,
        default_input={"s": "{[()]}"},
    ),
    _template(
        key="binary_tree_traverse",
        domain="tree_structure",
        name="二叉树前序遍历",
        visualizer_type="tree",
        difficulty="easy",
        entry_point="preorder_traversal",
        input_model=BinaryTreeInput,
        default_input={"arr": [1, 2, 3, 4, 5, 6, 7]},
    ),
    _template(
        key="graph_bfs",
        domain="graph_structure",
        name="广度优先搜索",
        visualizer_type="graph",
        difficulty="easy",
        entry_point="bfs_all_components",
        input_model=GraphTraversalInput,
        default_input={
            "num_nodes": 6,
            "edges": [[0, 1], [0, 2], [1, 3], [1, 4], [2, 5]],
            "start": 0,
        },
    ),
    _template(
        key="graph_dfs",
        domain="graph_structure",
        name="深度优先搜索",
        visualizer_type="graph",
        difficulty="easy",
        entry_point="dfs_graph",
        input_model=GraphTraversalInput,
        default_input={
            "num_nodes": 6,
            "edges": [[0, 1], [0, 2], [1, 3], [1, 4], [2, 5]],
            "start": 0,
        },
    ),
    _template(
        key="shortest_path",
        domain="graph_structure",
        name="Dijkstra 最短路径",
        visualizer_type="graph",
        difficulty="medium",
        entry_point="dijkstra",
        input_model=WeightedGraphInput,
        default_input={
            "num_nodes": 6,
            "edges": [
                [0, 1, 5],
                [0, 2, 1],
                [1, 2, 2],
                [1, 3, 3],
                [1, 4, 20],
                [2, 4, 12],
                [3, 4, 2],
                [3, 5, 6],
                [4, 5, 1],
            ],
            "start": 0,
        },
    ),
    _template(
        key="knapsack_dp",
        domain="dynamic_programming",
        name="0/1 背包",
        visualizer_type="dp-table",
        difficulty="medium",
        entry_point="knapsack",
        input_model=KnapsackInput,
        default_input={"weights": [2, 3, 4, 5], "values": [3, 4, 5, 6], "capacity": 5},
    ),
)

_SPECS_BY_KEY = {spec.key: spec for spec in _SPECS}


def get_all_template_specs() -> list[TemplateSpec]:
    return list(_SPECS)


def get_template_spec(template_key: str) -> TemplateSpec:
    try:
        return _SPECS_BY_KEY[template_key]
    except KeyError as exc:
        raise TemplateNotFoundError(template_key) from exc
