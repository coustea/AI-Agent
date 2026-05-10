"""Learning evaluation schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


LearningEventType = Literal[
    "resource_viewed",
    "resource_completed",
    "quiz_submitted",
    "path_feedback",
    "tutor_helpful",
    "resource_feedback",
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


class LearningEventItem(BaseModel):
    """Learning event item for response."""

    id: int
    event_type: str
    course: str | None = None
    topic: str | None = None
    score: float | None = None
    duration_seconds: int | None = None
    feedback: str | None = None
    created_at: datetime


class EvaluationMetric(BaseModel):
    """Evaluation metric item."""

    label: str
    value: str
    trend: str = "stable"


class EvaluationSummary(BaseModel):
    """Evaluation summary response."""

    event_count: int
    average_score: float | None = None
    completed_resources: int = 0
    viewed_resources: int = 0
    active_minutes: int = 0
    weak_topics: list[str] = Field(default_factory=list)
    preferred_resources: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    metrics: list[EvaluationMetric] = Field(default_factory=list)
    recent_events: list[LearningEventItem] = Field(default_factory=list)

