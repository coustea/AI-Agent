"""Base class for observation adapters.

Separated from __init__.py to avoid circular imports.
"""

from __future__ import annotations

from typing import Any


class BaseAdapter:
    """Base class for observation adapters."""

    def __init__(self, input_data: dict[str, object]) -> None:
        self._input_data = input_data
        self._last_structure: dict[str, object] = {}
        self._last_targets: list[object] = []

    def initial(self) -> tuple[dict[str, object], list[object]]:
        """Return the initial state and targets before execution begins."""
        structure = self._build_initial_structure()
        self._last_structure = structure
        self._last_targets = []
        return structure, []

    def capture(
        self,
        local_values: dict[str, object],
        result: object | None = None,
    ) -> tuple[dict[str, object], list[object]]:
        """Observe local variables and return (structure, targets)."""
        structure, targets = self._do_capture(local_values, result)
        self._last_structure = structure
        self._last_targets = targets
        return structure, targets

    def _build_initial_structure(self) -> dict[str, object]:
        raise NotImplementedError

    def _do_capture(
        self,
        local_values: dict[str, object],
        result: object | None,
    ) -> tuple[dict[str, object], list[object]]:
        raise NotImplementedError
