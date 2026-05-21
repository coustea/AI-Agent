"""记忆系统 API schema。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ProfileResponse(BaseModel):
    user_id: int
    module: str
    profile_json: dict | None
    profile_score_json: dict | None
    version: int
    confidence: float
    updated_reason: str | None
    updated_at: datetime

    @classmethod
    def from_model(cls, profile: Any) -> "ProfileResponse":
        return cls(
            user_id=profile.user_id,
            module=profile.module,
            profile_json=profile.profile_json,
            profile_score_json=profile.profile_score_json,
            version=profile.version,
            confidence=profile.confidence,
            updated_reason=profile.updated_reason,
            updated_at=profile.updated_at,
        )


class OnboardingUpdate(BaseModel):
    education_level: str = Field(..., min_length=1, max_length=50)
    grade: str = Field(..., min_length=1, max_length=50)
    major: str = Field(..., min_length=1, max_length=100)
    courses: list[str] = Field(..., min_length=1, max_length=20)
    learning_goal: str = Field(..., min_length=1, max_length=500)
    school: str | None = Field(default=None, max_length=100)
    school_level: str | None = Field(default=None, max_length=100)
    preferred_language: str | None = Field(default=None, max_length=50)
    cognitive_style: str | None = Field(default=None, max_length=100)
    interaction_preference: str | None = Field(default=None, max_length=100)
    practice_ability: str | None = Field(default=None, max_length=100)
    weakness_points: list[str] | None = Field(default=None)

    @field_validator("education_level", "grade", "major", "learning_goal")
    @classmethod
    def required_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("字段不能为空")
        return value

    @field_validator("courses")
    @classmethod
    def courses_not_empty(cls, values: list[str]) -> list[str]:
        courses: list[str] = []
        seen: set[str] = set()
        for item in values:
            course = str(item or "").strip()
            if course and course not in seen:
                seen.add(course)
                courses.append(course)
        if not courses:
            raise ValueError("至少填写一门课程")
        return courses


class OnboardingResponse(BaseModel):
    student_profile: dict
    profile_initialized: bool
