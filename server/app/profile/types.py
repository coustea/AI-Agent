"""学习者画像领域类型 — 7 维度画像体系。

维度设计原则：
  - 知识层（3个）：反映学生"学什么"的状态
  - 认知层（4个）：反映学生"怎么学"的特征

维度列表（7个）：
  knowledge_level — 知识基础（赛题要求）
  cognitive_style — 认知风格（赛题要求）
  weak_knowledge_points — 易错点偏好（赛题要求）
  knowledge_gap_pattern — 知识缺口模式
  learning_goal_type — 学习目标导向
  difficulty_tolerance — 难度耐受度
  self_correction_ability — 自纠能力水平

每个维度包含：
  - value: 文字描述（画像主体）
  - evidence: 推断依据列表
"""

# 定义 7 个画像维度的键、名称、默认值与 Pydantic 模型
from __future__ import annotations

from typing import Any, Final

from pydantic import BaseModel, Field


# ── 画像维度键常量 ──────────────────────────────────────────────────────

class ProfileDimension:
    """画像维度键常量 — 用于跨模块统一引用。"""

    # 赛题要求的维度（保留原名称）
    KNOWLEDGE_LEVEL: Final[str] = "knowledge_level"
    COGNITIVE_STYLE: Final[str] = "cognitive_style"
    WEAK_KNOWLEDGE_POINTS: Final[str] = "weak_knowledge_points"

    # 新增维度
    KNOWLEDGE_GAP_PATTERN: Final[str] = "knowledge_gap_pattern"
    LEARNING_GOAL_TYPE: Final[str] = "learning_goal_type"
    DIFFICULTY_TOLERANCE: Final[str] = "difficulty_tolerance"
    SELF_CORRECTION_ABILITY: Final[str] = "self_correction_ability"


# 所有维度键的有序元组（知识层 + 认知层）
ALL_DIMENSIONS: Final[tuple[str, ...]] = (
    ProfileDimension.KNOWLEDGE_LEVEL,
    ProfileDimension.COGNITIVE_STYLE,
    ProfileDimension.WEAK_KNOWLEDGE_POINTS,
    ProfileDimension.KNOWLEDGE_GAP_PATTERN,
    ProfileDimension.LEARNING_GOAL_TYPE,
    ProfileDimension.DIFFICULTY_TOLERANCE,
    ProfileDimension.SELF_CORRECTION_ABILITY,
)

# 维度键 → 中文名称映射（用于前端展示）
DIMENSION_NAMES: Final[dict[str, str]] = {
    ProfileDimension.KNOWLEDGE_LEVEL: "知识基础",
    ProfileDimension.COGNITIVE_STYLE: "认知风格",
    ProfileDimension.WEAK_KNOWLEDGE_POINTS: "易错点偏好",
    ProfileDimension.KNOWLEDGE_GAP_PATTERN: "知识缺口模式",
    ProfileDimension.LEARNING_GOAL_TYPE: "学习目标导向",
    ProfileDimension.DIFFICULTY_TOLERANCE: "难度耐受度",
    ProfileDimension.SELF_CORRECTION_ABILITY: "自纠能力水平",
}

# 维度分类：知识层维度（"学什么"）
KNOWLEDGE_DIMENSIONS: Final[tuple[str, ...]] = (
    ProfileDimension.KNOWLEDGE_LEVEL,
    ProfileDimension.WEAK_KNOWLEDGE_POINTS,
    ProfileDimension.KNOWLEDGE_GAP_PATTERN,
)

# 认知层维度（"怎么学"）
COGNITIVE_DIMENSIONS: Final[tuple[str, ...]] = (
    ProfileDimension.COGNITIVE_STYLE,
    ProfileDimension.LEARNING_GOAL_TYPE,
    ProfileDimension.DIFFICULTY_TOLERANCE,
    ProfileDimension.SELF_CORRECTION_ABILITY,
)


# ── 默认值 ──────────────────────────────────────────────────────────────

# 新建用户时的默认画像 JSON（各维度置空）
default_profile_json: dict[str, Any] = {
    "dimensions": {
        dim: {
            "value": "",
            "evidence": [],
        }
        for dim in ALL_DIMENSIONS
    },
}

# 新建用户时的默认评分 JSON（各维度 0 分）
default_score_json: dict[str, Any] = {
    "overall_score": 0,
    "dimension_scores": {key: 0 for key in ALL_DIMENSIONS},
    "scored_at": "",
}


# ── Pydantic 模型 ──────────────────────────────────────────────────────

# 单个画像维度的数据模型：文字描述 + 推断依据
class DimensionValue(BaseModel):
    """画像维度值结构 — 文字描述 + 推断依据。"""
    value: str = ""
    evidence: list[str] = Field(default_factory=list)


# 画像维度增量更新补丁模型
class ProfileDimensionsPatch(BaseModel):
    """画像维度更新补丁。"""
    dimensions_patch: dict[str, DimensionValue] = Field(default_factory=dict)


# 画像评分推理输出（仅维度分数，总分由后端均值计算）
class ProfileScoreOutput(BaseModel):
    """画像评分推理输出 — 仅输出 7 维度分数，overall_score 由后端按均值计算。"""
    dimension_scores: dict[str, int] = Field(default_factory=dict)
