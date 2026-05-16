"""画像领域类型定义。

模块职责：
- 定义 8 维度常量
- 定义画像默认结构
- 定义评分结构
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Final


class ProfileDimension:
    """画像维度常量。"""

    KNOWLEDGE_FOUNDATION: Final[str] = "knowledge_foundation"
    """知识基础"""

    LEARNING_GOAL: Final[str] = "learning_goal"
    """学习目标"""

    COGNITIVE_STYLE: Final[str] = "cognitive_style"
    """认知风格"""

    WEAKNESS_POINTS: Final[str] = "weakness_points"
    """薄弱点"""

    MISTAKE_PREFERENCE: Final[str] = "mistake_preference"
    """易错点偏好"""

    PRACTICE_ABILITY: Final[str] = "practice_ability"
    """实践能力"""

    INTERACTION_PREFERENCE: Final[str] = "interaction_preference"
    """交互偏好"""

    LEARNING_HISTORY: Final[str] = "learning_history"
    """学习历史"""


# 所有维度列表
ALL_DIMENSIONS: Final[tuple[str, ...]] = (
    ProfileDimension.KNOWLEDGE_FOUNDATION,
    ProfileDimension.LEARNING_GOAL,
    ProfileDimension.COGNITIVE_STYLE,
    ProfileDimension.WEAKNESS_POINTS,
    ProfileDimension.MISTAKE_PREFERENCE,
    ProfileDimension.PRACTICE_ABILITY,
    ProfileDimension.INTERACTION_PREFERENCE,
    ProfileDimension.LEARNING_HISTORY,
)

# 维度中文名称
DIMENSION_NAMES: Final[dict[str, str]] = {
    ProfileDimension.KNOWLEDGE_FOUNDATION: "知识基础",
    ProfileDimension.LEARNING_GOAL: "学习目标",
    ProfileDimension.COGNITIVE_STYLE: "认知风格",
    ProfileDimension.WEAKNESS_POINTS: "薄弱点",
    ProfileDimension.MISTAKE_PREFERENCE: "易错点偏好",
    ProfileDimension.PRACTICE_ABILITY: "实践能力",
    ProfileDimension.INTERACTION_PREFERENCE: "交互偏好",
    ProfileDimension.LEARNING_HISTORY: "学习历史",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_default_dimension(key: str) -> dict[str, Any]:
    """创建默认维度结构。"""
    return {
        "name": DIMENSION_NAMES.get(key, key),
        "confidence": 0.0,
        "summary": None,
        "evidence": [],
        "updated_at": None,
    }


def make_default_profile_json() -> dict[str, Any]:
    """创建默认画像 JSON 结构。"""
    dimensions = {key: make_default_dimension(key) for key in ALL_DIMENSIONS}
    return {
        "profile_version": 3,
        "format": "json",
        "overall_confidence": 0.0,
        "student_profile": None,
        "dimensions": dimensions,
        "recommended_strategy": [],
        "last_update_reason": "",
    }


def make_default_score_json() -> dict[str, Any]:
    """创建默认评分 JSON 结构。"""
    return {
        "profile_score_version": 1,
        "format": "profile_score_json",
        "overall_score": None,
        "confidence": 0.0,
        "dimension_scores": {key: None for key in ALL_DIMENSIONS},
        "section_coverage": 0,
        "evidence_quality": 0,
        "missing_sections": list(ALL_DIMENSIONS),
        "scored_at": None,
    }


# 首次登录必填字段
ONBOARDING_REQUIRED_FIELDS = ("education_level", "grade", "major", "courses", "learning_goal")
ONBOARDING_OPTIONAL_FIELDS = (
    "school", 
    "school_level", 
    "preferred_language",
    "cognitive_style",
    "interaction_preference",
    "practice_ability",
    "weakness_points"
)
