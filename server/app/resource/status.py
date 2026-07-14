"""Canonical lifecycle states for one standalone resource-generation task."""

from __future__ import annotations

from enum import StrEnum


class ResourceLifecycleStatus(StrEnum):
    """Values persisted on a resource and emitted by its global events.

    The lifecycle protocol uses concise state names. Agent-run states remain a
    separate vocabulary in ``GeneratedResourceAgentRun``.
    """

    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


SUCCESSFUL_RESOURCE_STATUSES = frozenset(
    {
        ResourceLifecycleStatus.COMPLETED,
        ResourceLifecycleStatus.PARTIAL,
    }
)
