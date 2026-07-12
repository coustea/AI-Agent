"""Deterministic semantic layout for the teaching-video stage."""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.shared.cartoon.schemas import (
    TeachingScene,
    VisualModel,
    stage_visual_model,
)


@dataclass(frozen=True)
class PositionedNode:
    id: str
    x: float
    y: float
    width: float = 17.0
    height: float = 14.0


def layout_scene(
    scene: TeachingScene,
) -> dict[str, PositionedNode]:
    """Lay out every node that can appear, including nodes later removed."""

    model = stage_visual_model(
        scene
    )

    handlers = {
        "structure": _structure_layout,
        "sequence": _sequence_layout,
        "state_transition": _state_layout,
        "data_flow": _sequence_layout,
        "message_exchange": (
            _message_exchange_layout
        ),
        "container_operation": (
            _container_layout
        ),
        "tree_growth": _tree_layout,
        "graph_traversal": _graph_layout,
        "timeline": _timeline_layout,
        "memory_change": _memory_layout,
        "pipeline": _pipeline_layout,
        "comparison": _comparison_layout,
    }

    positions = handlers.get(
        scene.mechanism,
        _layout_from_visual_kind,
    )(
        model
    )

    missing = {
        node.id
        for node in model.nodes
    } - set(
        positions
    )

    if missing:
        raise ValueError(
            f"scene {scene.id} layout "
            f"omitted nodes: {sorted(missing)}"
        )

    return positions


def _layout_from_visual_kind(
    model: VisualModel,
) -> dict[str, PositionedNode]:
    if model.kind == "tree":
        return _tree_layout(
            model
        )

    if model.kind == "array":
        return _container_layout(
            model
        )

    if model.kind == "comparison":
        return _comparison_layout(
            model
        )

    if model.kind == "memory":
        return _memory_layout(
            model
        )

    if model.kind == "state-machine":
        return _state_layout(
            model
        )

    if model.kind == "network":
        return _message_exchange_layout(
            model
        )

    if model.kind == "flow":
        return _sequence_layout(
            model
        )

    return _graph_layout(
        model
    )


def _single(
    model: VisualModel,
    *,
    width: float = 22,
    height: float = 16,
) -> dict[str, PositionedNode]:
    node = model.nodes[0]

    return {
        node.id: PositionedNode(
            node.id,
            50,
            49,
            width,
            height,
        )
    }


def _tree_layout(
    model: VisualModel,
) -> dict[str, PositionedNode]:
    if len(model.nodes) == 1:
        return _single(
            model
        )

    children: dict[
        str | None,
        list[str],
    ] = {}

    for node in model.nodes:
        children.setdefault(
            node.parent_id,
            [],
        ).append(
            node.id
        )

    known = {
        node.id
        for node in model.nodes
    }

    roots = [
        node.id
        for node in model.nodes
        if (
            not node.parent_id
            or node.parent_id
            not in known
        )
    ]

    if not roots:
        roots = [
            model.nodes[0].id
        ]

    levels: dict[
        int,
        list[str],
    ] = {}

    visited: set[str] = set()

    queue = [
        (
            root,
            0,
        )
        for root in roots
    ]

    while queue:
        node_id, depth = (
            queue.pop(0)
        )

        if node_id in visited:
            continue

        visited.add(
            node_id
        )

        levels.setdefault(
            depth,
            [],
        ).append(
            node_id
        )

        queue.extend(
            (
                child,
                depth + 1,
            )
            for child
            in children.get(
                node_id,
                [],
            )
        )

    next_depth = (
        max(
            levels,
            default=0,
        )
        + 1
    )

    disconnected = [
        node.id
        for node in model.nodes
        if node.id not in visited
    ]

    if disconnected:
        levels[next_depth] = (
            disconnected
        )

    result: dict[
        str,
        PositionedNode,
    ] = {}

    max_depth = max(
        levels,
        default=0,
    )

    for depth, ids in levels.items():
        spacing = (
            82
            / (
                len(ids)
                + 1
            )
        )

        y = (
            17
            + 65
            * depth
            / max(
                1,
                max_depth,
            )
        )

        width = min(
            19.0,
            max(
                11.0,
                65.0
                / len(ids),
            ),
        )

        for index, node_id in enumerate(
            ids,
            1,
        ):
            result[node_id] = (
                PositionedNode(
                    node_id,
                    9
                    + spacing
                    * index,
                    y,
                    width,
                    13,
                )
            )

    return result


def _container_layout(
    model: VisualModel,
) -> dict[str, PositionedNode]:
    count = len(
        model.nodes
    )

    if count == 1:
        return _single(
            model,
            width=18,
            height=14,
        )

    columns = min(
        8,
        count,
    )

    rows = math.ceil(
        count
        / columns
    )

    cell_width = min(
        13.5,
        78
        / columns,
    )

    result: dict[
        str,
        PositionedNode,
    ] = {}

    for index, node in enumerate(
        model.nodes
    ):
        row, column = divmod(
            index,
            columns,
        )

        row_count = min(
            columns,
            count
            - row
            * columns,
        )

        x = (
            50
            if row_count == 1
            else (
                11
                + column
                * 78
                / (
                    row_count
                    - 1
                )
            )
        )

        y = (
            49
            if rows == 1
            else (
                27
                + row
                * 45
                / (
                    rows
                    - 1
                )
            )
        )

        result[node.id] = (
            PositionedNode(
                node.id,
                x,
                y,
                cell_width,
                13,
            )
        )

    return result


def _sequence_layout(
    model: VisualModel,
) -> dict[str, PositionedNode]:
    count = len(
        model.nodes
    )

    if count == 1:
        return _single(
            model
        )

    if count == 2:
        return {
            node.id: PositionedNode(
                node.id,
                32
                + index
                * 36,
                50,
                22,
                16,
            )
            for index, node in enumerate(
                model.nodes
            )
        }

    if count == 3:
        return {
            node.id: PositionedNode(
                node.id,
                22
                + index
                * 28,
                50,
                20,
                16,
            )
            for index, node in enumerate(
                model.nodes
            )
        }

    columns = min(
        6,
        count,
    )

    rows = math.ceil(
        count
        / columns
    )

    width = min(
        16.0,
        68
        / columns,
    )

    result: dict[
        str,
        PositionedNode,
    ] = {}

    for index, node in enumerate(
        model.nodes
    ):
        row, raw_column = divmod(
            index,
            columns,
        )

        row_count = min(
            columns,
            count
            - row
            * columns,
        )

        column = (
            raw_column
            if row % 2 == 0
            else (
                row_count
                - raw_column
                - 1
            )
        )

        x = (
            50
            if row_count == 1
            else (
                16
                + column
                * 68
                / (
                    row_count
                    - 1
                )
            )
        )

        y = (
            49
            if rows == 1
            else (
                26
                + row
                * 48
                / (
                    rows
                    - 1
                )
            )
        )

        result[node.id] = (
            PositionedNode(
                node.id,
                x,
                y,
                width,
                14,
            )
        )

    return result


def _message_exchange_layout(
    model: VisualModel,
) -> dict[str, PositionedNode]:
    if len(model.nodes) == 1:
        return _single(
            model
        )

    endpoint_kinds = {
        "process",
        "state",
        "concept",
        "register",
        "pipeline_stage",
        "window",
    }

    endpoints = [
        node
        for node in model.nodes
        if node.kind
        in endpoint_kinds
    ]

    if len(endpoints) < 2:
        endpoints = [
            model.nodes[0],
            model.nodes[-1],
        ]

    left, right = (
        endpoints[0],
        endpoints[-1],
    )

    result = {
        left.id: PositionedNode(
            left.id,
            22,
            49,
            20,
            17,
        ),
        right.id: PositionedNode(
            right.id,
            78,
            49,
            20,
            17,
        ),
    }

    middle = [
        node
        for node in model.nodes
        if node.id
        not in {
            left.id,
            right.id,
        }
    ]

    for index, node in enumerate(
        middle
    ):
        y = (
            49
            if len(middle) == 1
            else (
                20
                + index
                * 58
                / (
                    len(middle)
                    - 1
                )
            )
        )

        result[node.id] = (
            PositionedNode(
                node.id,
                50,
                y,
                17,
                11,
            )
        )

    return result


def _comparison_layout(
    model: VisualModel,
) -> dict[str, PositionedNode]:
    if len(model.nodes) == 1:
        return _single(
            model,
            width=30,
            height=16,
        )

    count = len(
        model.nodes
    )

    rows = math.ceil(
        count
        / 2
    )

    result: dict[
        str,
        PositionedNode,
    ] = {}

    for index, node in enumerate(
        model.nodes
    ):
        row, column = divmod(
            index,
            2,
        )

        x = (
            27
            if column == 0
            else 73
        )

        y = (
            49
            if rows == 1
            else (
                18
                + row
                * 62
                / (
                    rows
                    - 1
                )
            )
        )

        result[node.id] = (
            PositionedNode(
                node.id,
                x,
                y,
                31,
                min(
                    15,
                    58
                    / rows,
                ),
            )
        )

    return result


def _state_layout(
    model: VisualModel,
) -> dict[str, PositionedNode]:
    count = len(
        model.nodes
    )

    if count == 1:
        return _single(
            model,
            width=20,
            height=15,
        )

    if count == 2:
        return {
            node.id: PositionedNode(
                node.id,
                30
                + index
                * 40,
                49,
                20,
                15,
            )
            for index, node in enumerate(
                model.nodes
            )
        }

    result: dict[
        str,
        PositionedNode,
    ] = {}

    for index, node in enumerate(
        model.nodes
    ):
        angle = (
            -math.pi
            / 2
            + 2
            * math.pi
            * index
            / count
        )

        result[node.id] = (
            PositionedNode(
                node.id,
                50
                + 32
                * math.cos(
                    angle
                ),
                49
                + 29
                * math.sin(
                    angle
                ),
                17,
                13,
            )
        )

    return result


def _timeline_layout(
    model: VisualModel,
) -> dict[str, PositionedNode]:
    count = len(
        model.nodes
    )

    if count == 1:
        return _single(
            model,
            width=18,
            height=12,
        )

    width = min(
        16,
        76
        / count,
    )

    return {
        node.id: PositionedNode(
            node.id,
            12
            + index
            * 76
            / (
                count
                - 1
            ),
            52
            + (
                8
                if index % 2
                else -8
            ),
            width,
            12,
        )
        for index, node in enumerate(
            model.nodes
        )
    }


def _memory_layout(
    model: VisualModel,
) -> dict[str, PositionedNode]:
    count = len(
        model.nodes
    )

    if count == 1:
        return _single(
            model,
            width=20,
            height=17,
        )

    columns = min(
        5,
        max(
            2,
            math.ceil(
                math.sqrt(
                    count
                )
            ),
        ),
    )

    rows = math.ceil(
        count
        / columns
    )

    result: dict[
        str,
        PositionedNode,
    ] = {}

    for index, node in enumerate(
        model.nodes
    ):
        row, column = divmod(
            index,
            columns,
        )

        row_count = min(
            columns,
            count
            - row
            * columns,
        )

        x = (
            50
            if row_count == 1
            else (
                16
                + column
                * 68
                / (
                    row_count
                    - 1
                )
            )
        )

        y = (
            49
            if rows == 1
            else (
                20
                + row
                * 60
                / (
                    rows
                    - 1
                )
            )
        )

        result[node.id] = (
            PositionedNode(
                node.id,
                x,
                y,
                min(
                    17,
                    62
                    / columns,
                ),
                min(
                    17,
                    54
                    / rows,
                ),
            )
        )

    return result


def _pipeline_layout(
    model: VisualModel,
) -> dict[str, PositionedNode]:
    stages = [
        node
        for node in model.nodes
        if node.kind
        in {
            "pipeline_stage",
            "process",
            "concept",
        }
    ]

    stage_ids = {
        node.id
        for node in stages
    }

    ordered = (
        stages
        + [
            node
            for node in model.nodes
            if node.id
            not in stage_ids
        ]
    )

    count = len(
        ordered
    )

    if count == 1:
        return _single(
            model,
            width=20,
            height=17,
        )

    width = min(
        16,
        68
        / count,
    )

    return {
        node.id: PositionedNode(
            node.id,
            16
            + index
            * 68
            / (
                count
                - 1
            ),
            49,
            width,
            (
                17
                if node.id
                in stage_ids
                else 11
            ),
        )
        for index, node in enumerate(
            ordered
        )
    }


def _structure_layout(
    model: VisualModel,
) -> dict[str, PositionedNode]:
    if model.kind == "tree":
        return _tree_layout(
            model
        )

    if len(model.nodes) == 1:
        return _single(
            model
        )

    if len(model.nodes) <= 5:
        positions = [
            (
                50,
                20,
            ),
            (
                22,
                52,
            ),
            (
                78,
                52,
            ),
            (
                35,
                80,
            ),
            (
                65,
                80,
            ),
        ]

        return {
            node.id: PositionedNode(
                node.id,
                *positions[index],
                18,
                14,
            )
            for index, node in enumerate(
                model.nodes
            )
        }

    return _graph_layout(
        model
    )


def _graph_layout(
    model: VisualModel,
) -> dict[str, PositionedNode]:
    count = len(
        model.nodes
    )

    if count == 1:
        return _single(
            model
        )

    result: dict[
        str,
        PositionedNode,
    ] = {}

    for index, node in enumerate(
        model.nodes
    ):
        angle = (
            -math.pi
            / 2
            + 2
            * math.pi
            * index
            / count
        )

        result[node.id] = (
            PositionedNode(
                node.id,
                50
                + 34
                * math.cos(
                    angle
                ),
                49
                + 31
                * math.sin(
                    angle
                ),
                16,
                13,
            )
        )

    return result
