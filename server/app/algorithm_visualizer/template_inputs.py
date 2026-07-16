"""Strict input contracts for the trusted algorithm template catalogue."""

from __future__ import annotations

import math
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictFloat,
    StrictInt,
    StrictStr,
    model_validator,
)


MIN_INTEGER = -1_000_000
MAX_INTEGER = 1_000_000
MAX_ARRAY_LENGTH = 64
MAX_GRAPH_EDGES = 256

BoundedInteger = Annotated[
    StrictInt,
    Field(ge=MIN_INTEGER, le=MAX_INTEGER),
]
PositiveWeight = Annotated[StrictInt, Field(gt=0, le=64)]
Capacity = Annotated[StrictInt, Field(ge=0, le=64)]


class StrictTemplateInput(BaseModel):
    """Base behavior shared by every registered template input."""

    model_config = ConfigDict(extra="forbid", strict=True)


class IntegerArrayInput(StrictTemplateInput):
    arr: list[BoundedInteger] = Field(min_length=1, max_length=MAX_ARRAY_LENGTH)


class BinarySearchInput(IntegerArrayInput):
    target: BoundedInteger

    @model_validator(mode="after")
    def require_sorted_array(self) -> Self:
        if self.arr != sorted(self.arr):
            raise ValueError("arr 必须按升序排列")
        return self


class BracketMatchInput(StrictTemplateInput):
    s: Annotated[StrictStr, Field(min_length=1, max_length=512)]


class LinkedListInput(StrictTemplateInput):
    arr: list[BoundedInteger] = Field(min_length=1, max_length=MAX_ARRAY_LENGTH)


class BinaryTreeInput(StrictTemplateInput):
    arr: list[BoundedInteger | None] = Field(min_length=1, max_length=63)

    @model_validator(mode="after")
    def require_non_null_root(self) -> Self:
        if self.arr[0] is None:
            raise ValueError("二叉树根节点不能为空")
        return self


class GraphTraversalInput(StrictTemplateInput):
    num_nodes: Annotated[StrictInt, Field(ge=1, le=64)]
    edges: list[
        Annotated[list[StrictInt], Field(min_length=2, max_length=2)]
    ] = Field(max_length=MAX_GRAPH_EDGES)
    start: Annotated[StrictInt, Field(ge=0)]

    @model_validator(mode="after")
    def require_nodes_in_range(self) -> Self:
        if self.start >= self.num_nodes:
            raise ValueError("start 必须位于节点范围内")
        if any(
            endpoint < 0 or endpoint >= self.num_nodes
            for edge in self.edges
            for endpoint in edge
        ):
            raise ValueError("边端点必须位于节点范围内")
        return self


class WeightedGraphInput(StrictTemplateInput):
    num_nodes: Annotated[StrictInt, Field(ge=1, le=64)]
    edges: list[
        Annotated[
            list[StrictInt | StrictFloat],
            Field(min_length=3, max_length=3),
        ]
    ] = Field(max_length=MAX_GRAPH_EDGES)
    start: Annotated[StrictInt, Field(ge=0)]

    @model_validator(mode="after")
    def require_valid_weighted_edges(self) -> Self:
        if self.start >= self.num_nodes:
            raise ValueError("start 必须位于节点范围内")
        for edge in self.edges:
            if len(edge) != 3:
                raise ValueError("加权边必须包含起点、终点和权重")
            source, target, weight = edge
            if type(source) is not int or type(target) is not int:
                raise ValueError("边端点必须为整数")
            if not 0 <= source < self.num_nodes or not 0 <= target < self.num_nodes:
                raise ValueError("边端点必须位于节点范围内")
            if (
                isinstance(weight, float) and not math.isfinite(weight)
            ) or not 0 <= weight <= 1_000_000:
                raise ValueError("边权重必须是 0..1000000 的有限数")
        return self


class KnapsackInput(StrictTemplateInput):
    weights: list[PositiveWeight] = Field(min_length=1, max_length=24)
    values: list[BoundedInteger] = Field(min_length=1, max_length=24)
    capacity: Capacity

    @model_validator(mode="after")
    def require_equal_item_counts(self) -> Self:
        if len(self.weights) != len(self.values):
            raise ValueError("weights 与 values 长度必须一致")
        return self
