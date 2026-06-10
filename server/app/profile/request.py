"""Profile API request models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class OnboardingUpdate(BaseModel):
    """入门信息更新请求。"""

    school: str = ""
    major: str
    grade: str
    daily_study_time: str
    global_learning_goal: str
    programming_languages: list[str] = Field(default_factory=list)
    courses: list[str] = Field(default_factory=list)


class EvidenceInput(BaseModel):
    """单条维度证据输入。"""

    source: str = Field(default="tutoring")
    signal_type: str
    summary: str
    course: str | None = None
    knowledge_point: str | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class TutoringProfileUpdate(BaseModel):
    """辅导过程中画像增量更新请求。"""

    session_id: str | None = None
    active_course: str | None = None
    active_topic: str | None = None
    evidence: list[EvidenceInput] = Field(default_factory=list)
    behavior_signals: dict[str, Any] = Field(default_factory=dict)
    update_reason: str = Field(default="tutoring_inference")
