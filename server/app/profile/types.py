"""学习者画像领域类型 — 维度常量、默认值模板、推理输出模型。

画像维度（10个）：
  major_background — 专业背景
  student_stage — 学习阶段
  course_context — 课程上下文
  knowledge_level — 知识基础
  learning_goal_type — 学习目标
  weak_knowledge_points — 薄弱知识点
  cognitive_style — 认知风格
  resource_preference_weight — 资源偏好
  learning_pace — 学习节奏
  practice_profile — 实践能力
"""

from __future__ import annotations

from typing import Any, Final

from pydantic import BaseModel, Field


# ── 画像更新调度常量 ──────────────────────────────────────────────────────

# 画像 token 累积阈值 — 超过此值触发画像更新检查
PROFILE_TOKEN_THRESHOLD: Final[int] = 8000
# 画像消息累积阈值 — 超过此值触发画像更新检查
PROFILE_MESSAGE_THRESHOLD: Final[int] = 30
# 画像更新冷却时间（分钟）— 两次更新之间的最小间隔
PROFILE_UPDATE_COOLDOWN_MINUTES: Final[int] = 90
# 画像最小覆盖率 — 低于此值时优先更新画像
PROFILE_MIN_COVERAGE: Final[int] = 60


class ProfileDimension:
    """画像维度键常量 — 用于跨模块统一引用维度名称。"""

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


GLOBAL_DIMENSIONS: Final[tuple[str, ...]] = (
    ProfileDimension.MAJOR_BACKGROUND,
    ProfileDimension.STUDENT_STAGE,
    ProfileDimension.LEARNING_GOAL_TYPE,
    ProfileDimension.COGNITIVE_STYLE,
    ProfileDimension.RESOURCE_PREFERENCE_WEIGHT,
    ProfileDimension.LEARNING_PACE,
    ProfileDimension.PRACTICE_PROFILE,
)

SCORE_DIMENSIONS: Final[tuple[str, ...]] = (
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

# 所有维度键的有序元组 (为了向后兼容部分代码，保留 ALL_DIMENSIONS 指向 SCORE_DIMENSIONS)
ALL_DIMENSIONS: Final[tuple[str, ...]] = SCORE_DIMENSIONS


# 维度键 → 中文名称映射 — 用于 Markdown 渲染和前端展示
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
    """生成空白全局画像 JSON。"""
    return {
        "base_info": {
            "school": "",
            "school_level": "",
            "major": "",
            "grade": "",
            "daily_study_time": "",
            "global_learning_goal": "",
            "programming_languages": [],
            "courses": [],
        },
        "dimensions": {
            dim: {
                "value": "",
                "evidence": [],
            }
            for dim in GLOBAL_DIMENSIONS
        }
    }


def make_default_score_json() -> dict[str, Any]:
    """生成空白画像评分 JSON — 所有维度初始分为 0，证据列表为空。"""
    return {
        "overall_score": 0,
        "dimension_scores": {key: 0 for key in SCORE_DIMENSIONS},
        "dimension_evidence": {key: [] for key in SCORE_DIMENSIONS},
        "scored_at": "",
    }


class GlobalDimensionValue(BaseModel):
    """全局画像维度值结构。"""
    value: str = ""
    evidence: list[str] = Field(default_factory=list)


class OnboardingGlobalInferenceOutput(BaseModel):
    """全局 Onboarding 推理输出 Pydantic 模型。"""
    dimensions_patch: dict[str, GlobalDimensionValue] = Field(default_factory=dict)


class GlobalTutoringInferenceOutput(BaseModel):
    """全局辅导推理输出 Pydantic 模型。"""
    should_update: bool = False
    dimensions_patch: dict[str, GlobalDimensionValue] = Field(default_factory=dict)


class ProfileScoreOutput(BaseModel):
    """画像评分推理输出 Pydantic 模型。"""
    dimension_scores: dict[str, float | int | None] = Field(default_factory=dict)
    dimension_evidence: dict[str, list[str]] = Field(default_factory=dict)
