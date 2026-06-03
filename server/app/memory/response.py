"""Memory API response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CourseBaseInfoData(BaseModel):
    course: str | None = None
    foundation_level: str | None = None
    current_topic: str | None = None
    course_learning_goal: str | None = None
    weak_points: list[str] = Field(default_factory=list)


class BaseInfoData(BaseModel):
    school: str | None = None
    school_level: str | None = None
    major: str | None = None
    grade: str | None = None
    daily_study_time: str | None = None
    global_learning_goal: str | None = None
    resource_preference: list[str] = Field(default_factory=list)
    programming_languages: list[str] = Field(default_factory=list)
    self_description: str | None = None
    courses: list[CourseBaseInfoData] = Field(default_factory=list)


class StudentProfileData(BaseModel):
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
    base_info: BaseInfoData = Field(default_factory=BaseInfoData)
    student_profile: StudentProfileData = Field(default_factory=StudentProfileData)
    profile_initialized: bool = False


class ProfileEnvelopeResponse(BaseModel):
    base_info: dict[str, Any] = Field(default_factory=dict)
    learning_profile: dict[str, Any] = Field(default_factory=dict)
    knowledge_mastery: list[dict[str, Any]] = Field(default_factory=list)
    initial_strategy: dict[str, Any] = Field(default_factory=dict)
    profile_meta: dict[str, Any] = Field(default_factory=dict)


class TutoringProfileUpdateResponse(BaseModel):
    profile_updated: bool = False
    learning_profile: dict[str, Any] = Field(default_factory=dict)
    knowledge_mastery: list[dict[str, Any]] = Field(default_factory=list)
    profile_meta: dict[str, Any] = Field(default_factory=dict)
