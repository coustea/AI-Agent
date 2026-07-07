"""画像 API 响应模型 — 入门信息、全局画像及评分响应。"""

from __future__ import annotations

from typing import Any
from datetime import datetime

from pydantic import BaseModel, Field


class BaseInfoData(BaseModel):
    """用户基础信息响应数据 — 学校、专业、年级等。"""

    school: str | None = None
    school_level: str | None = None
    major: str | None = None
    grade: str | None = None
    daily_study_time: str | None = None
    global_learning_goal: str | None = None
    programming_languages: list[str] = Field(default_factory=list)
    courses: list[str] = Field(default_factory=list)


class StudentProfileData(BaseModel):
    """学生画像摘要响应数据 — 精简版画像用于前端展示。"""

    school: str | None = None
    school_level: str | None = None
    major: str | None = None
    grade: str | None = None
    courses: list[str] = Field(default_factory=list)
    learning_goal: str | None = None
    preferred_language: str | None = None

    @classmethod
    def from_base_info(cls, base_info: dict[str, Any]) -> "StudentProfileData":
        """从 base_info 字典构造 StudentProfileData。"""
        return cls(
            school=base_info.get("school"),
            school_level=base_info.get("school_level"),
            major=base_info.get("major"),
            grade=base_info.get("grade"),
            courses=base_info.get("courses", []),
            learning_goal=base_info.get("global_learning_goal"),
            preferred_language=", ".join(base_info.get("programming_languages", [])),
        )


class OnboardingResponse(BaseModel):
    """入门信息查询响应 — 包含基础信息和学生画像摘要。"""

    base_info: BaseInfoData = Field(default_factory=BaseInfoData)
    student_profile: StudentProfileData = Field(default_factory=StudentProfileData)
    profile_initialized: bool = False


class GlobalProfileResponse(BaseModel):
    """全局画像详情响应（GET /profile）。"""

    user_id: int
    module: str
    base_info: BaseInfoData = Field(default_factory=BaseInfoData)
    dimensions: dict[str, Any] = Field(default_factory=dict)
    profile_score_json: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime | str | None = None
