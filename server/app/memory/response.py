"""Memory API response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CourseBaseInfoData(BaseModel):
    """课程基础信息响应数据。"""
    course: str | None = None
    foundation_level: str | None = None
    current_topic: str | None = None
    course_learning_goal: str | None = None
    weak_points: list[str] = Field(default_factory=list)


class BaseInfoData(BaseModel):
    """用户基础信息响应数据。"""
    school: str | None = None
    school_level: str | None = None
    major: str | None = None
    grade: str | None = None
    daily_study_time: str | None = None
    global_learning_goal: str | None = None
    resource_preference: list[str] = Field(default_factory=list)
    programming_languages: list[str] = Field(default_factory=list)
    learning_style_tags: list[str] = Field(default_factory=list)
    self_description: str | None = None
    courses: list[CourseBaseInfoData] = Field(default_factory=list)


class StudentProfileData(BaseModel):
    """学生画像摘要响应数据。"""
    education_level: str | None = None
    grade: str | None = None
    major: str | None = None
    courses: list[str] = Field(default_factory=list)
    learning_goal: str | None = None
    school: str | None = None
    school_level: str | None = None
    preferred_language: str | None = None
    weakness_points: list[str] = Field(default_factory=list)


class OnboardingResponse(BaseModel):
    """入门信息查询响应。"""
    base_info: BaseInfoData = Field(default_factory=BaseInfoData)
    student_profile: StudentProfileData = Field(default_factory=StudentProfileData)
    profile_initialized: bool = False


class ProfileEnvelopeResponse(BaseModel):
    """完整画像信封响应（含 base_info、learning_profile 等顶层结构）。"""
    base_info: dict[str, Any] = Field(default_factory=dict)
    learning_profile: dict[str, Any] = Field(default_factory=dict)
    knowledge_mastery: list[dict[str, Any]] = Field(default_factory=list)
    initial_strategy: dict[str, Any] = Field(default_factory=dict)
    profile_meta: dict[str, Any] = Field(default_factory=dict)


class TutoringProfileUpdateResponse(BaseModel):
    """辅导画像增量更新响应。"""
    profile_updated: bool = False
    learning_profile: dict[str, Any] = Field(default_factory=dict)
    knowledge_mastery: list[dict[str, Any]] = Field(default_factory=list)
    profile_meta: dict[str, Any] = Field(default_factory=dict)
