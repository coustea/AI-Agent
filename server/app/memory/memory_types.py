"""记忆与画像类型常量及默认结构定义。

模块职责：
- 定义画像 8 维度常量与默认 JSON 结构
- 定义长期记忆默认 JSON 结构
- 定义会话概要默认 JSON 结构
- 提供长期记忆和会话概要的 Markdown 渲染函数

设计原则：
- 画像维度固定为 8 个，每个文字维度包含 name/confidence/summary/evidence/updated_at
- 没有证据的画像维度使用 summary=None、evidence=[]
- profile_json 是文字画像权威来源，profile_score_json 是评分画像权威来源
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Final


# ---------------------------------------------------------------------------
# 画像维度常量（8 个固定维度）
# ---------------------------------------------------------------------------

PROFILE_DIMENSION_KNOWLEDGE_FOUNDATION: Final[str] = "knowledge_foundation"  # 知识基础
PROFILE_DIMENSION_LEARNING_GOAL: Final[str] = "learning_goal"  # 学习目标
PROFILE_DIMENSION_COGNITIVE_STYLE: Final[str] = "cognitive_style"  # 认知风格
PROFILE_DIMENSION_WEAKNESS_POINTS: Final[str] = "weakness_points"  # 薄弱点
PROFILE_DIMENSION_MISTAKE_PREFERENCE: Final[str] = "mistake_preference"  # 易错点偏好
PROFILE_DIMENSION_PRACTICE_ABILITY: Final[str] = "practice_ability"  # 实践能力
PROFILE_DIMENSION_INTERACTION_PREFERENCE: Final[str] = "interaction_preference"  # 交互偏好
PROFILE_DIMENSION_LEARNING_HISTORY: Final[str] = "learning_history"  # 学习历史

ALL_PROFILE_DIMENSIONS: Final[tuple[str, ...]] = (
    PROFILE_DIMENSION_KNOWLEDGE_FOUNDATION,
    PROFILE_DIMENSION_LEARNING_GOAL,
    PROFILE_DIMENSION_COGNITIVE_STYLE,
    PROFILE_DIMENSION_WEAKNESS_POINTS,
    PROFILE_DIMENSION_MISTAKE_PREFERENCE,
    PROFILE_DIMENSION_PRACTICE_ABILITY,
    PROFILE_DIMENSION_INTERACTION_PREFERENCE,
    PROFILE_DIMENSION_LEARNING_HISTORY,
)

PROFILE_DIMENSION_NAMES: Final[dict[str, str]] = {
    PROFILE_DIMENSION_KNOWLEDGE_FOUNDATION: "知识基础",
    PROFILE_DIMENSION_LEARNING_GOAL: "学习目标",
    PROFILE_DIMENSION_COGNITIVE_STYLE: "认知风格",
    PROFILE_DIMENSION_WEAKNESS_POINTS: "薄弱点",
    PROFILE_DIMENSION_MISTAKE_PREFERENCE: "易错点偏好",
    PROFILE_DIMENSION_PRACTICE_ABILITY: "实践能力",
    PROFILE_DIMENSION_INTERACTION_PREFERENCE: "交互偏好",
    PROFILE_DIMENSION_LEARNING_HISTORY: "学习历史",
}

PROFILE_MARKDOWN_SECTIONS: Final[tuple[str, ...]] = (
    "基础信息与专业背景",
    "学习目标",
    "学习历史",
    "知识基础",
    "认知风格",
    "学习偏好",
    "易错点与薄弱点",
    "交互偏好与禁忌",
    "AI 纠正记录",
    "当前学习状态",
    "推荐辅导策略",
    "最近变化",
    "不确定信息",
)


# ---------------------------------------------------------------------------
# 默认 JSON 结构
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_default_dimension_json(dimension_key: str) -> dict[str, Any]:
    """创建单个维度的默认 JSON 结构。"""
    return {
        "name": PROFILE_DIMENSION_NAMES.get(dimension_key, dimension_key),
        "confidence": 0.0,
        "summary": None,
        "evidence": [],
        "updated_at": None,
    }


def make_default_profile_json() -> dict[str, Any]:
    """创建画像的默认 JSON 结构（8 维度）。"""
    dimensions = {key: make_default_dimension_json(key) for key in ALL_PROFILE_DIMENSIONS}
    return {
        "profile_version": 3,
        "format": "json",
        "overall_confidence": 0.0,
        "student_profile": None,
        "dimensions": dimensions,
        "recommended_strategy": [],
        "last_update_reason": "",
    }


def make_default_profile_score_json() -> dict[str, Any]:
    """创建画像评分的默认 JSON 结构。"""
    return {
        "profile_score_version": 1,
        "format": "profile_score_json",
        "overall_score": None,
        "confidence": 0.0,
        "dimension_scores": {key: None for key in ALL_PROFILE_DIMENSIONS},
        "section_coverage": 0,
        "evidence_quality": 0,
        "missing_sections": list(ALL_PROFILE_DIMENSIONS),
        "scored_at": None,
    }


def make_default_long_term_memory_json() -> dict[str, Any]:
    """创建长期记忆的默认 JSON 结构。"""
    return {
        "learning_background": {
            "major": None,
            "grade": None,
            "description": "",
        },
        "long_term_goals": [],
        "learning_preferences": [],
        "stable_weaknesses": [],
        "project_context": [],
        "interaction_rules": [],
        "effective_strategies": [],
        "corrections": [],
        "recent_important_changes": [],
    }


def make_default_session_summary_json() -> dict[str, Any]:
    """创建会话概要的默认 JSON 结构。"""
    return {
        "current_learning_task": "",
        "original_user_questions": [],
        "explained_content": [],
        "current_understanding": [],
        "current_confusions": [],
        "teaching_methods_used": [],
        "conversation_position": "",
        "next_action": "",
        "references": [],
    }


def render_long_term_memory_markdown(memory_json: dict[str, Any]) -> str:
    """从 memory_json 渲染 Markdown 文本。"""
    if not memory_json:
        return "# 长期记忆\n\n暂无长期记忆信息。"

    lines = ["# 长期记忆"]

    background = memory_json.get("learning_background", {})
    if background.get("description"):
        lines.append("\n## 学习背景\n")
        lines.append(background.get("description", ""))
        if background.get("major"):
            lines.append(f"\n- 专业: {background.get('major')}")
        if background.get("grade"):
            lines.append(f"- 年级: {background.get('grade')}")

    long_term_goals = memory_json.get("long_term_goals", [])
    if long_term_goals:
        lines.append("\n## 长期目标\n")
        for goal in long_term_goals:
            lines.append(f"- {goal}")

    learning_preferences = memory_json.get("learning_preferences", [])
    if learning_preferences:
        lines.append("\n## 学习偏好\n")
        for pref in learning_preferences:
            lines.append(f"- {pref}")

    stable_weaknesses = memory_json.get("stable_weaknesses", [])
    if stable_weaknesses:
        lines.append("\n## 稳定薄弱点\n")
        for weakness in stable_weaknesses:
            lines.append(f"- {weakness}")

    project_context = memory_json.get("project_context", [])
    if project_context:
        lines.append("\n## 项目背景\n")
        for project in project_context:
            lines.append(f"- {project}")

    interaction_rules = memory_json.get("interaction_rules", [])
    if interaction_rules:
        lines.append("\n## 交互规则\n")
        for rule in interaction_rules:
            lines.append(f"- {rule}")

    effective_strategies = memory_json.get("effective_strategies", [])
    if effective_strategies:
        lines.append("\n## 有效辅导策略\n")
        for strategy in effective_strategies:
            lines.append(f"- {strategy}")

    corrections = memory_json.get("corrections", [])
    if corrections:
        lines.append("\n## 用户纠正记录\n")
        for correction in corrections:
            lines.append(f"- {correction}")

    recent_changes = memory_json.get("recent_important_changes", [])
    if recent_changes:
        lines.append("\n## 最近重要变化\n")
        for change in recent_changes:
            lines.append(f"- {change}")

    return "\n".join(lines)


def render_session_summary_markdown(summary_json: dict[str, Any]) -> str:
    """从 summary_json 渲染 Markdown 文本。"""
    if not summary_json:
        return "# 会话概要\n\n暂无概要信息。"

    lines = ["# 会话概要"]

    task = summary_json.get("current_learning_task", "")
    if task:
        lines.append(f"\n## 当前学习任务\n\n{task}")

    questions = summary_json.get("original_user_questions", [])
    if questions:
        lines.append("\n## 用户原始问题\n")
        for q in questions:
            lines.append(f"- {q}")

    explained = summary_json.get("explained_content", [])
    if explained:
        lines.append("\n## 已解释内容\n")
        for content in explained:
            lines.append(f"- {content}")

    understanding = summary_json.get("current_understanding", [])
    if understanding:
        lines.append("\n## 当前理解状态\n")
        for u in understanding:
            lines.append(f"- {u}")

    confusions = summary_json.get("current_confusions", [])
    if confusions:
        lines.append("\n## 当前困惑点\n")
        for c in confusions:
            lines.append(f"- {c}")

    methods = summary_json.get("teaching_methods_used", [])
    if methods:
        lines.append("\n## 已使用教学方法\n")
        for m in methods:
            lines.append(f"- {m}")

    position = summary_json.get("conversation_position", "")
    if position:
        lines.append(f"\n## 对话进度\n\n{position}")

    next_action = summary_json.get("next_action", "")
    if next_action:
        lines.append(f"\n## 下一步行动\n\n{next_action}")

    return "\n".join(lines)
