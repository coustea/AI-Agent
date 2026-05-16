"""画像 API Schema。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ProfileResponse(BaseModel):
    """画像响应。"""
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


class ProfileScoreResponse(BaseModel):
    """画像评分响应。"""
    user_id: int
    module: str
    version: int
    score: int | None
    confidence: float
    dimension_scores: dict
    section_coverage: int
    missing_sections: list

    @classmethod
    def from_model(cls, profile: Any) -> "ProfileScoreResponse":
        score_json = profile.profile_score_json or {}
        return cls(
            user_id=profile.user_id,
            module=profile.module,
            version=profile.version,
            score=score_json.get("overall_score"),
            confidence=score_json.get("confidence", profile.confidence),
            dimension_scores=score_json.get("dimension_scores") or {},
            section_coverage=score_json.get("section_coverage", 0),
            missing_sections=score_json.get("missing_sections") or [],
        )


class OnboardingUpdate(BaseModel):
    """首次登录更新请求。"""
    education_level: str = Field(..., min_length=1, max_length=50)
    grade: str = Field(..., min_length=1, max_length=50)
    major: str = Field(..., min_length=1, max_length=100)
    courses: list[str] = Field(..., min_length=1, max_length=20)
    learning_goal: str = Field(..., min_length=1, max_length=500)
    school: str | None = Field(default=None, max_length=100)
    school_level: str | None = Field(default=None, max_length=100)
    preferred_language: str | None = Field(default=None, max_length=50)
    
    # 补充学习偏好维度
    cognitive_style: str | None = Field(default=None, max_length=100)
    interaction_preference: str | None = Field(default=None, max_length=100)
    practice_ability: str | None = Field(default=None, max_length=100)
    weakness_points: list[str] | None = Field(default=None)

    @field_validator("education_level", "grade", "major", "learning_goal")
    @classmethod
    def required_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("字段不能为空")
        return v

    @field_validator("courses")
    @classmethod
    def courses_not_empty(cls, v: list[str]) -> list[str]:
        courses = []
        seen = set()
        for item in v:
            course = str(item or "").strip()
            if course and course not in seen:
                seen.add(course)
                courses.append(course)
        if not courses:
            raise ValueError("至少填写一门课程")
        return courses


class OnboardingResponse(BaseModel):
    """首次登录状态响应。"""
    student_profile: dict
    profile_initialized: bool
