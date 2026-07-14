"""画像 API 请求模型。"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class OnboardingUpdate(BaseModel):
    """入门信息更新请求。"""

    school: str
    major: str
    grade: str
    daily_study_time: str
    global_learning_goal: str
    programming_languages: list[str] = Field(default_factory=list)
    courses: list[str] = Field(default_factory=list)
    foundational_level: str = ""  # beginner/entry/proficient/master
    learning_style: str = ""  # theory_first/practice_first/case_driven
    content_depth: str = ""  # quick_overview/systematic_deep
    weak_points: list[str] = Field(default_factory=list)


class GlobalTutoringProfileUpdate(BaseModel):
    """全局画像辅导增量更新请求。"""

    session_id: str
    update_reason: str = "tutoring_inference"
