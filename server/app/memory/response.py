"""Memory response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class OnboardingResponse(BaseModel):
    """Onboarding data response."""

    grade: str = ""
    school: str = ""
    subjects: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    learning_style: str = "visual"
    school_level: str | None = None
    profile_initialized: bool = False


class ProfileResponse(BaseModel):
    """User profile response."""

    user_id: int
    module: str | None = None
    profile_json: dict | None = None
    profile_score_json: dict | None = None
    version: int = 0
    confidence: float = 0.0
    updated_reason: str | None = None
    updated_at: datetime | None = None


class ProfileHistoryItem(BaseModel):
    """Profile history item response."""

    id: int
    user_id: int
    module: str
    version: int
    profile_json: dict | None = None
    profile_score_json: dict | None = None
    change_reason: str | None = None
    source_session_ids: list[str] | None = None
    created_at: datetime | None = None
