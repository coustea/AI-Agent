"""Memory API request models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CourseBaseInfoInput(BaseModel):
    """课程基础信息输入。"""
    course: str
    foundation_level: str
    current_topic: str | None = None
    course_learning_goal: str | None = None
    weak_points: list[str] = Field(default_factory=list)


class OnboardingUpdate(BaseModel):
    """入门信息更新请求。"""
    school: str
    school_level: str | None = None
    major: str
    grade: str
    daily_study_time: str
    global_learning_goal: str
    courses: list[CourseBaseInfoInput] = Field(default_factory=list, max_length=3)
    resource_preference: list[str] = Field(default_factory=list)
    programming_languages: list[str] = Field(default_factory=list)
    learning_style_tags: list[str] = Field(default_factory=list)
    self_description: str | None = None


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
    dialogue_excerpt: str | None = None
    evidence: list[EvidenceInput] = Field(default_factory=list)
    behavior_signals: dict[str, Any] = Field(default_factory=dict)
    update_reason: str = Field(default="tutoring_inference")
