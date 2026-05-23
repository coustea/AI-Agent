"""Memory response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class StudentProfileData(BaseModel):
    education_level: str | None = None
    grade: str | None = None
    major: str | None = None
    courses: list[str] = Field(default_factory=list)
    learning_goal: str | None = None
    school: str | None = None
    school_level: str | None = None
    preferred_language: str | None = None
    cognitive_style: str | None = None
    interaction_preference: str | None = None
    practice_ability: str | None = None
    weakness_points: list[str] = Field(default_factory=list)


class OnboardingResponse(BaseModel):
    student_profile: StudentProfileData = Field(default_factory=StudentProfileData)
    profile_initialized: bool = False


class ProfileResponse(BaseModel):
    user_id: int
    module: str | None = None
    profile_markdown: str | None = None
    profile_json: dict | None = None
    profile_score_json: dict | None = None
    version: int = 0
    confidence: float = 0.0
    source_session_ids: list[str] | None = None
    source_summary_ids: list[int] | None = None
    source_event_ids: list[int] | None = None
    updated_reason: str | None = None
    updated_at: datetime | None = None


class ProfileHistoryItem(BaseModel):
    id: int
    user_id: int
    module: str
    version: int
    profile_json: dict | None = None
    profile_score_json: dict | None = None
    change_reason: str | None = None
    source_session_ids: list[str] | None = None
    source_summary_ids: list[int] | None = None
    source_event_ids: list[int] | None = None
    created_at: datetime | None = None
