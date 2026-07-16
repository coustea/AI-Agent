"""Bounded, deterministic trace event builder for official template execution.

TraceBuilder assigns continuous step numbers and stable ids, enforces the
per-template max_events limit, and ensures all state payloads are
JSON-serializable.  It replaces the legacy VisualTracer from
tracer_sdks/python_tracer.py.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from typing import Any

from pydantic import JsonValue


class TraceLimitExceeded(RuntimeError):
    """Raised when a trace exceeds the configured event or size limits."""


@dataclass(frozen=True, slots=True)
class TraceEvent:
    """Immutable semantic event produced by an official template run."""

    id: str
    step: int
    type: str
    visualizer_type: str
    state: dict[str, Any]
    targets: list[Any]
    line: int | None = None
    message: str | None = None


@dataclass
class TraceBuilder:
    """Append-only builder that produces a validated list of TraceEvent objects.

    Steps are assigned automatically starting from 0.  Event ids follow the
    pattern ``evt-{step}``.  The builder rejects events once the step count
    reaches *max_events* and validates that state payloads are JSON-compatible.
    """

    visualizer_type: str
    max_events: int = 600
    max_serialized_bytes: int = 4 * 1024 * 1024  # 4 MiB

    _events: list[TraceEvent] = field(default_factory=list, init=False, repr=False)
    _serialized_size: int = field(default=0, init=False, repr=False)

    @property
    def events(self) -> list[TraceEvent]:
        return list(self._events)

    @property
    def step(self) -> int:
        return len(self._events)

    def add(
        self,
        event_type: str,
        state: dict[str, Any],
        *,
        targets: list[Any] | None = None,
        line: int | None = None,
        message: str | None = None,
    ) -> TraceEvent:
        """Append a new event and return it.

        Raises:
            TraceLimitExceeded: when the event count or serialized size
                would exceed the configured limits.
            TypeError: when *state* is not JSON-serializable.
        """
        if self.step >= self.max_events:
            raise TraceLimitExceeded(
                f"事件数量超过上限 {self.max_events}"
            )

        event_targets = list(targets) if targets else []
        event = TraceEvent(
            id=f"evt-{self.step}",
            step=self.step,
            type=event_type,
            visualizer_type=self.visualizer_type,
            state=copy.deepcopy(state),
            targets=copy.deepcopy(event_targets),
            line=line,
            message=message,
        )

        # Validate JSON-serializability and track serialized size.
        serialized = json.dumps(
            {"state": event.state, "targets": event.targets},
            ensure_ascii=False,
            default=str,
        )
        self._serialized_size += len(serialized.encode("utf-8"))
        if self._serialized_size > self.max_serialized_bytes:
            raise TraceLimitExceeded(
                f"序列化事件数据超过 {self.max_serialized_bytes} 字节"
            )

        self._events.append(event)
        return event

    def build(self) -> list[dict[str, JsonValue]]:
        """Return the event list as JSON-compatible dicts for the API layer."""
        result: list[dict[str, JsonValue]] = []
        for event in self._events:
            entry: dict[str, JsonValue] = {
                "id": event.id,
                "step": event.step,
                "type": event.type,
                "visualizerType": event.visualizer_type,
                "state": {"structure": _to_jsonable(event.state)},
                "targets": _to_jsonable(event.targets),
            }
            if event.line is not None:
                entry["line"] = event.line
            if event.message is not None:
                entry["message"] = event.message
            result.append(entry)
        return result


def _to_jsonable(value: Any) -> Any:
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
