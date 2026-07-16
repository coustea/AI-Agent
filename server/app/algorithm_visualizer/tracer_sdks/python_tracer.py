"""Trace event writer used exclusively by the official runtime."""

from __future__ import annotations

import copy
from typing import Any


class VisualTracer:
    """Append immutable, frontend-compatible state snapshots."""

    def __init__(self, visualizer_type: str) -> None:
        self._events: list[dict[str, Any]] = []
        self._visualizer_type = visualizer_type

    @property
    def events(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self._events)

    def snapshot(
        self,
        event_type: str,
        state_structure: dict[str, Any],
        *,
        targets: list[Any] | None = None,
        message: str | None = None,
        line: int | None = None,
        formula: str | None = None,
    ) -> None:
        step = len(self._events)
        self._events.append(
            {
                "id": f"evt-{step}",
                "step": step,
                "domain": "algorithm",
                "visualizerType": self._visualizer_type,
                "type": event_type,
                "state": {"structure": copy.deepcopy(state_structure)},
                "targets": copy.deepcopy(targets) if targets else [],
                "message": message,
                "line": line,
                "formula": formula,
            }
        )
