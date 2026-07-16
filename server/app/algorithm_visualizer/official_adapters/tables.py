"""Adapter for the DP-table visualizer type.

DP templates expose rectangular ``dp``, active ``index``/``current_capacity``,
and dependency cells.  The adapter validates rectangular shape and tracks
highlighted cells and their dependencies.
"""

from __future__ import annotations

import copy
from typing import Any

from app.algorithm_visualizer.official_adapters._base import BaseAdapter


class DpTableAdapter(BaseAdapter):
    """Observes DP-table templates (0/1 knapsack, etc.)."""

    def _build_initial_structure(self) -> dict[str, object]:
        return _initial_table(self._input_data)

    def _do_capture(
        self,
        local_values: dict[str, object],
        result: object | None,
    ) -> tuple[dict[str, object], list[object]]:
        table = _find_table(local_values)
        if table is None and isinstance(result, list):
            table = result
        if table is None:
            return copy.deepcopy(self._last_structure), []

        values = table if table and isinstance(table[0], list) else [table]
        width = max((len(row) for row in values), default=1)
        highlighted = _table_highlights(local_values, values)
        targets = _table_targets(local_values, values)
        return {
            "headers": [str(index) for index in range(width)],
            "values": _to_jsonable(values),
            "highlighted": highlighted,
        }, targets


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _initial_table(data: dict[str, object]) -> dict[str, object]:
    """Build the initial DP table structure from input data."""
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
        "values": _to_jsonable(values),
        "highlighted": [],
    }


def _find_table(local_values: dict[str, object]) -> list[object] | None:
    """Find the DP table in local variables."""
    for key in ("dp", "table", "grid", "matrix", "board", "visited"):
        value = local_values.get(key)
        if isinstance(value, list):
            return copy.deepcopy(value)
    return None


def _table_targets(
    local_values: dict[str, object],
    values: list[list[object]],
) -> list[dict[str, object]]:
    """Extract active cell coordinates from local variables."""
    if not values:
        return []
    row = next(
        (
            local_values.get(name)
            for name in ("i", "r", "row", "index")
            if isinstance(local_values.get(name), int)
        ),
        None,
    )
    col = next(
        (
            local_values.get(name)
            for name in ("j", "c", "col", "current_capacity")
            if isinstance(local_values.get(name), int)
        ),
        None,
    )
    if row is None or col is None:
        return []
    return [{"row": row, "col": col}]


def _table_highlights(
    local_values: dict[str, object],
    values: list[list[object]],
) -> list[dict[str, object]]:
    """Compute highlighted cells including dependency arrows."""
    targets = _table_targets(local_values, values)
    if not targets:
        return []
    row = targets[0]["row"]
    col = targets[0]["col"]
    highlighted: list[dict[str, object]] = [{"row": row, "col": col, "tone": "active"}]
    if row <= 0:
        return highlighted
    highlighted.append({"row": row - 1, "col": col, "tone": "dependency"})
    weight = local_values.get("weight")
    if isinstance(weight, int) and col >= weight:
        highlighted.append(
            {"row": row - 1, "col": col - weight, "tone": "dependency"}
        )
    return highlighted


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
