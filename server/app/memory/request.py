"""记忆系统 API 请求模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class OnboardingUpdate(BaseModel):
    education_level: str | None = None
    grade: str | None = None
    major: str | None = None
    school: str | None = None
    school_level: str | None = None
    courses: list[str] | None = None
    learning_goal: str | None = None
    preferred_language: str | None = None
    cognitive_style: str | None = None
    interaction_preference: str | None = None
    practice_ability: str | None = None
    weakness_points: list[str] | None = None
