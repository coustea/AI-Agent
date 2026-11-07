"""学习者画像数据模型（请求与响应 Schema）。"""

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


class ProfileUpdate(BaseModel):
    """个人中心可编辑的基础资料。"""

    school: str
    major: str
    grade: str
    daily_study_time: str
    global_learning_goal: str
    programming_languages: list[str] = Field(default_factory=list)
    courses: list[str] = Field(default_factory=list)


class BaseInfoData(BaseModel):
    """用户基础信息响应数据。"""

    school: str | None = None
    school_level: str | None = None
    major: str | None = None
    grade: str | None = None
    daily_study_time: str | None = None
    global_learning_goal: str | None = None
    programming_languages: list[str] = Field(default_factory=list)
    courses: list[str] = Field(default_factory=list)
    foundational_level: str | None = None
    learning_style: str | None = None
    content_depth: str | None = None
    weak_points: list[str] = Field(default_factory=list)


class StudentProfileData(BaseModel):
    """学生画像摘要响应数据。"""

    school: str | None = None
    school_level: str | None = None
    major: str | None = None
    grade: str | None = None
    courses: list[str] = Field(default_factory=list)
    learning_goal: str | None = None
    preferred_language: str | None = None

    @classmethod
    def from_base_info(cls, base_info: dict[str, Any]) -> StudentProfileData:
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
    """入门信息查询响应。"""

    base_info: BaseInfoData = Field(default_factory=BaseInfoData)
    student_profile: StudentProfileData = Field(default_factory=StudentProfileData)
    profile_initialized: bool = False


__all__ = [
    "BaseInfoData",
    "OnboardingResponse",
    "OnboardingUpdate",
    "ProfileUpdate",
    "StudentProfileData",
]
