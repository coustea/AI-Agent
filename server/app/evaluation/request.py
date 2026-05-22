"""Evaluation request schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

LearningEventType = Literal[
    "resource_viewed",
    "resource_completed",
    "quiz_submitted",
    "path_feedback",
    "tutor_helpful",
    "resource_feedback",
    "learning_heartbeat",
]


class LearningEventCreate(BaseModel):
    """Learning event creation request."""

    event_type: LearningEventType
    session_id: str | None = None
    resource_id: int | None = Field(default=None, ge=1)
    course: str | None = Field(default=None, max_length=200)
    topic: str | None = Field(default=None, max_length=200)
    score: float | None = Field(default=None, ge=0, le=100)
    duration_seconds: int | None = Field(default=None, ge=0)
    feedback: str | None = Field(default=None, max_length=2000)
    metadata: dict[str, Any] = Field(default_factory=dict)
