"""Shared profile domain types."""

from __future__ import annotations

from typing import Any, Final

from pydantic import BaseModel, Field


class ProfileDimension:
    """画像维度键常量。"""

    MAJOR_BACKGROUND: Final[str] = "major_background"
    STUDENT_STAGE: Final[str] = "student_stage"
    COURSE_CONTEXT: Final[str] = "course_context"
    KNOWLEDGE_LEVEL: Final[str] = "knowledge_level"
    LEARNING_GOAL_TYPE: Final[str] = "learning_goal_type"
    WEAK_KNOWLEDGE_POINTS: Final[str] = "weak_knowledge_points"
    COGNITIVE_STYLE: Final[str] = "cognitive_style"
    RESOURCE_PREFERENCE_WEIGHT: Final[str] = "resource_preference_weight"
    LEARNING_PACE: Final[str] = "learning_pace"
    PRACTICE_PROFILE: Final[str] = "practice_profile"


ALL_DIMENSIONS: Final[tuple[str, ...]] = (
    ProfileDimension.MAJOR_BACKGROUND,
    ProfileDimension.STUDENT_STAGE,
    ProfileDimension.COURSE_CONTEXT,
    ProfileDimension.KNOWLEDGE_LEVEL,
    ProfileDimension.LEARNING_GOAL_TYPE,
    ProfileDimension.WEAK_KNOWLEDGE_POINTS,
    ProfileDimension.COGNITIVE_STYLE,
    ProfileDimension.RESOURCE_PREFERENCE_WEIGHT,
    ProfileDimension.LEARNING_PACE,
    ProfileDimension.PRACTICE_PROFILE,
)


DIMENSION_NAMES: Final[dict[str, str]] = {
    ProfileDimension.MAJOR_BACKGROUND: "专业背景",
    ProfileDimension.STUDENT_STAGE: "学习阶段",
    ProfileDimension.COURSE_CONTEXT: "课程上下文",
    ProfileDimension.KNOWLEDGE_LEVEL: "知识基础",
    ProfileDimension.LEARNING_GOAL_TYPE: "学习目标",
    ProfileDimension.WEAK_KNOWLEDGE_POINTS: "薄弱知识点",
    ProfileDimension.COGNITIVE_STYLE: "认知风格",
    ProfileDimension.RESOURCE_PREFERENCE_WEIGHT: "资源偏好",
    ProfileDimension.LEARNING_PACE: "学习节奏",
    ProfileDimension.PRACTICE_PROFILE: "实践能力",
}


def make_default_profile_json() -> dict[str, Any]:
    """生成空白画像 JSON，含所有结构的默认值。"""

    return {
        "schema_version": 1,
        "base_info": {
            "school": None,
            "school_level": None,
            "major": None,
            "grade": None,
            "daily_study_time": None,
            "global_learning_goal": None,
            "programming_languages": [],
            "courses": [],
        },
        "learning_profile": {
            "global_profile": {},
            "course_profiles": [],
        },
        "knowledge_mastery": [],
        "initial_strategy": {},
        "evidence": [],
        "profile_meta": {
            "coverage": 0,
            "last_update_reason": "",
            "updated_at": None,
        },
    }


def make_default_score_json() -> dict[str, Any]:
    """生成空白画像评分 JSON。"""

    return {
        "overall_score": 0,
        "dimension_scores": {key: 0 for key in ALL_DIMENSIONS},
        "scored_at": None,
    }


class EvidenceRecord(BaseModel):
    """维度证据记录。"""

    source: str = Field(default="system")
    signal_type: str
    course: str | None = None
    knowledge_point: str | None = None
    summary: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class OnboardingInferenceOutput(BaseModel):
    """Onboarding 画像推理输出。"""

    global_profile_patch: dict[str, Any] = Field(default_factory=dict)


class ProfileScoreOutput(BaseModel):
    """画像评分推理输出。"""

    overall_score: float | None = None
    dimension_scores: dict[str, Any] = Field(default_factory=dict)
    scored_at: str | None = None


class TutoringInferenceOutput(BaseModel):
    """辅导推理输出，包含画像增量 patch。"""

    should_update: bool = False
    global_profile_patch: dict[str, Any] = Field(default_factory=dict)
    course_profile_patch: dict[str, Any] | None = None
    knowledge_mastery_patch: list[dict[str, Any]] = Field(default_factory=list)
    initial_strategy_patch: dict[str, Any] = Field(default_factory=dict)
    evidence: list[EvidenceRecord] = Field(default_factory=list)
    update_reason: str = ""
