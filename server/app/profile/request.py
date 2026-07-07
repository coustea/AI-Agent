"""画像 API 请求模型 — 入门信息更新、全局辅导更新。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class OnboardingUpdate(BaseModel):
    """入门信息更新请求 — 用户首次填写的基本信息。"""

    school: str
    major: str
    grade: str
    daily_study_time: str
    global_learning_goal: str
    programming_languages: list[str] = Field(default_factory=list)
    courses: list[str] = Field(default_factory=list)


class GlobalTutoringProfileUpdate(BaseModel):
    """全局画像辅导增量更新请求。"""

    session_id: str
    update_reason: str = "tutoring_inference"
