"""Memory request schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class OnboardingUpdate(BaseModel):
    """Onboarding data update request."""

    grade: str = Field(..., min_length=1, max_length=50)
    school: str = Field(default="", max_length=200)
    subjects: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    learning_style: str = Field(default="visual", max_length=50)
