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
]


class LearningEventCreate(BaseModel):
    """Learning event creation request."""

    event_type: LearningEventType
    session_id: str | None = None
    resource_id: int | None = Field(default=None, ge=1)
    resource_item_id: int | None = Field(default=None, ge=1)
    path_id: int | None = Field(default=None, ge=1)
    path_node_id: int | None = Field(default=None, ge=1)
    node_id: str | None = Field(default=None, max_length=50)
    course: str | None = Field(default=None, max_length=200)
    topic: str | None = Field(default=None, max_length=200)
    score: float | None = Field(default=None, ge=0, le=100)
    feedback: str | None = Field(default=None, max_length=2000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LearningSessionCreate(BaseModel):
    """学习会话上报请求 — 前端离开学习页面时一次性发送。"""

    source_page: str = Field(description="来源页面标识，如 resource/tutor/path/question-bank")
    started_at: str = Field(description="会话开始时间 ISO8601")
    ended_at: str = Field(description="会话结束时间 ISO8601")
    duration_seconds: int = Field(ge=1, le=86400, description="实际活跃时长(秒)")
    resource_id: int | None = Field(default=None, ge=1)
    path_id: int | None = Field(default=None, ge=1)
    path_node_id: int | None = Field(default=None, ge=1)
    node_id: str | None = Field(default=None, max_length=50)
    course: str | None = Field(default=None, max_length=200)
    topic: str | None = Field(default=None, max_length=200)
    metadata: dict[str, Any] = Field(default_factory=dict)
