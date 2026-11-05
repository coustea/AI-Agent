"""Adapters for array and stack-queue visualizer types.

Sorting/search templates expose ``nums`` or ``arr`` plus index variables
(``index``, ``start``, ``end``, ``left``, ``right``, ``middle``, ``i``,
``j``, ``position``, ``minimum``).  Stack templates expose ``stack``,
current ``char``, and a top pointer.
"""

from __future__ import annotations

from app.algorithm_visualizer.official_adapters._base import BaseAdapter


class ArrayAdapter(BaseAdapter):
    """Observes array-state templates (sorting, searching)."""

    def _build_initial_structure(self) -> dict[str, object]:
        return {"array": _initial_array(self._input_data)}

    def _do_capture(
        self,
        local_values: dict[str, object],
        result: object | None,
    ) -> tuple[dict[str, object], list[object]]:
        values = _find_scalar_list(local_values)
        if values is None and isinstance(result, (list, tuple)):
            values = list(result)
        if values is not None:
            array = _numeric_array(values)
        else:
            array = self._last_structure.get("array", [0])
        targets = _array_targets(local_values, len(array))
        return {"array": array}, targets


class StackQueueAdapter(BaseAdapter):
    """Observes stack-queue templates (bracket matching, etc.)."""

    def __init__(self, input_data: dict[str, object]) -> None:
        super().__init__(input_data)
        self._mode: str = "stack"

    def _build_initial_structure(self) -> dict[str, object]:
        return {
            "mode": self._mode,
            "items": [],
            "pointers": [],
            "currentValue": "",
        }

    def _do_capture(
        self,
        local_values: dict[str, object],
        result: object | None,
    ) -> tuple[dict[str, object], list[object]]:
        mode = self._last_structure.get("mode", "stack")
        values = _find_sequence(local_values, ("stack", "queue", "deque", "dq", "q"))
        if values is None:
            values = [
                item.get("label", "")
                if isinstance(item, dict)
                else str(item)
                for item in self._last_structure.get("items", [])
            ]
        items = [
            {"id": f"item-{index}", "label": str(value), "tone": "default"}
            for index, value in enumerate(values)
        ]
        pointers: list[dict[str, object]] = []
        if items:
            pointers.append(
                {
                    "label": "top" if mode == "stack" else "front",
                    "itemIndex": len(items) - 1 if mode == "stack" else 0,
                    "tone": "accent",
                }
            )
        return {
            "mode": mode,
            "items": items,
            "pointers": pointers,
            "currentValue": str(local_values.get("char", "")),
        }, []


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _initial_array(data: dict[str, object]) -> list[object]:
    for key in ("arr", "nums", "prices", "points", "intervals"):
        if isinstance(data.get(key), list):
            return _numeric_array(data[key])
    for key in ("text", "s", "pattern"):
        if isinstance(data.get(key), str):
            return [ord(char) for char in data[key]]
    numeric = [value for value in data.values() if isinstance(value, (int, float))]
    return numeric or [0]


def _numeric_array(values: list[object]) -> list[object]:
    numeric: list[object] = []
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


def _find_scalar_list(local_values: dict[str, object]) -> list[object] | None:
    for key in ("nums", "arr", "prices", "result", "output", "dp"):
        value = local_values.get(key)
        if isinstance(value, list) and (not value or not isinstance(value[0], list)):
            return list(value)
    return None


def _find_sequence(
    local_values: dict[str, object],
    names: tuple[str, ...],
) -> list[object] | None:
    for name in names:
        value = local_values.get(name)
        if isinstance(value, (list, tuple)):
            return list(value)
        if value is not None and value.__class__.__name__ == "deque":
            return list(value)
    return None


def _array_targets(
    local_values: dict[str, object],
    length: int,
) -> list[int]:
    def valid_index(value: object) -> bool:
        return isinstance(value, int) and not isinstance(value, bool) and 0 <= value < length

    targets: list[int] = []
    for name in (
        "i", "j", "left", "right", "lo", "hi", "mid", "middle",
        "index", "position", "minimum", "start", "end",
    ):
        value = local_values.get(name)
        if valid_index(value) and value not in targets:
            targets.append(value)
    return targets[:4]
