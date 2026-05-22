"""Memory request schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class OnboardingUpdate(BaseModel):
    """Onboarding data update request."""

    education_level: str | None = None
    grade: str | None = Field(default=None, max_length=50)
    major: str | None = None
    courses: list[str] = Field(default_factory=list)
    learning_goal: str | None = None
    school: str | None = Field(default=None, max_length=200)
    school_level: str | None = None
    preferred_language: str | None = None
