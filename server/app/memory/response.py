"""记忆系统 API 响应模型。"""

from __future__ import annotations

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