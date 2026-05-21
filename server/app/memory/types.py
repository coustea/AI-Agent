"""记忆系统共享类型与纯函数。"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Final

from pydantic import BaseModel, Field

from app.config import (
    CHAT_BUDGET as _CFG_CHAT_BUDGET,
    LTM_BUDGET as _CFG_LTM_BUDGET,
    MSG_LIMIT as _CFG_MSG_LIMIT,
    SUMMARY_BUDGET as _CFG_SUMMARY_BUDGET,
)


class ModuleName:
    MENTOR: Final[str] = "mentor"
    RESOURCE: Final[str] = "resource"
    AVATAR: Final[str] = "avatar"


DIALOGUE_ROLES: Final[frozenset[str]] = frozenset({"user", "assistant"})
MESSAGE_EXPIRE_DAYS: Final[int] = 7
DEFAULT_SESSION_TITLE: Final[str] = "新对话"
TITLE_MAX_LENGTH: Final[int] = 100

SUMMARY_TOKEN_THRESHOLD: Final[int] = 150
SUMMARY_MESSAGE_THRESHOLD: Final[int] = 30
SUMMARY_KEEP_RECENT: Final[int] = 10
PROFILE_GATE_ASSISTANT_TURNS: Final[int] = 6
PROFILE_MIN_COVERAGE: Final[int] = 60
MEMORY_UPDATE_COOLDOWN_SECONDS: Final[float] = 300.0

MSG_LIMIT: int = _CFG_MSG_LIMIT
CHAT_BUDGET: int = _CFG_CHAT_BUDGET
LTM_BUDGET: int = _CFG_LTM_BUDGET
SUMMARY_BUDGET: int = _CFG_SUMMARY_BUDGET
PROFILE_BUDGET: int = 2000


def now() -> datetime:
    return datetime.now(timezone.utc)


def days_ago(days: int) -> datetime:
    return now() - timedelta(days=max(days, 0))


def estimate_token_count(text: str) -> int:
    stripped = (text or "").strip()
    if not stripped:
        return 0
    return max(max(1, len(stripped) // 4), len(stripped.split()))


def truncate_text(text: str, char_budget: int, suffix: str = "...") -> str:
    if len(text) <= char_budget:
        return text
    return text[: max(char_budget - len(suffix), 0)].rstrip() + suffix


class ProfileDimension:
    KNOWLEDGE_FOUNDATION: Final[str] = "knowledge_foundation"
    LEARNING_GOAL: Final[str] = "learning_goal"
    COGNITIVE_STYLE: Final[str] = "cognitive_style"
    WEAKNESS_POINTS: Final[str] = "weakness_points"
    MISTAKE_PREFERENCE: Final[str] = "mistake_preference"
    PRACTICE_ABILITY: Final[str] = "practice_ability"
    INTERACTION_PREFERENCE: Final[str] = "interaction_preference"
    LEARNING_HISTORY: Final[str] = "learning_history"


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

ONBOARDING_REQUIRED_FIELDS: Final[tuple[str, ...]] = (
    "education_level",
    "grade",
    "major",
    "courses",
    "learning_goal",
)
ONBOARDING_OPTIONAL_FIELDS: Final[tuple[str, ...]] = (
    "school",
    "school_level",
    "preferred_language",
    "cognitive_style",
    "interaction_preference",
    "practice_ability",
    "weakness_points",
)


def make_default_dimension(key: str) -> dict[str, Any]:
    return {
        "name": DIMENSION_NAMES.get(key, key),
        "confidence": 0.0,
        "summary": None,
        "evidence": [],
        "updated_at": None,
    }


def make_default_profile_json() -> dict[str, Any]:
    return {
        "profile_version": 3,
        "format": "json",
        "overall_confidence": 0.0,
        "student_profile": None,
        "dimensions": {key: make_default_dimension(key) for key in ALL_DIMENSIONS},
        "recommended_strategy": [],
        "last_update_reason": "",
    }


def make_default_score_json() -> dict[str, Any]:
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


def make_default_memory_json() -> dict[str, Any]:
    return {
        "learning_background": {"major": None, "grade": None, "description": ""},
        "long_term_goals": [],
        "learning_preferences": [],
        "stable_weaknesses": [],
        "project_context": [],
        "interaction_rules": [],
        "effective_strategies": [],
        "corrections": [],
        "recent_important_changes": [],
    }


def make_default_summary_json() -> dict[str, Any]:
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
        "profile_candidates": [],
        "memory_candidates": [],
    }


class SummaryLLMOutput(BaseModel):
    current_learning_task: str = Field(default="")
    original_user_questions: list[str] = Field(default_factory=list)
    explained_content: list[str] = Field(default_factory=list)
    current_understanding: list[str] = Field(default_factory=list)
    current_confusions: list[str] = Field(default_factory=list)
    teaching_methods_used: list[str] = Field(default_factory=list)
    conversation_position: str = Field(default="")
    next_action: str = Field(default="")
    references: list[str] = Field(default_factory=list)
    profile_candidates: list[str] = Field(default_factory=list)
    memory_candidates: list[str] = Field(default_factory=list)


class DimensionOutput(BaseModel):
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    summary: str | None = None
    evidence: list[str] = Field(default_factory=list)


class ProfileOutput(BaseModel):
    dimensions: dict[str, DimensionOutput] = Field(default_factory=dict)
    recommended_strategy: list[str] = Field(default_factory=list)
    last_update_reason: str = ""


class MemoryUpdateOutput(BaseModel):
    need_update: bool = Field(default=False)
    memory_json: dict[str, Any] | None = None


STABLE_SIGNAL_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"我(?:总是|经常|一直|老是|反复).*(?:出错|不会|卡住|卡在|记不住|搞不清|混淆|薄弱|边界)"),
    re.compile(r"我(?:喜欢|不喜欢|更喜欢|偏好|习惯)"),
    re.compile(r"我(?:在学|正在学|学过|以前学过|已经学过|准备|打算|想(?:学|考|准备|提高|练习))"),
    re.compile(r"(?:专业|年级|方向|课程|考试|证书|竞赛|实习|面试|项目)"),
    re.compile(r"(?:你|ai|AI|助手).*(?:错了|理解错|误解|不对|遗漏|应该|不要|别|记住|以后)"),
    re.compile(r"(?:以后|下次|后续).*(?:不要|别|先|必须|应该|保持|沿用|避免|给|讲)"),
)
NON_SIGNIFICANT_TEXTS: Final[frozenset[str]] = frozenset({"谢谢", "好的", "收到", "明白了", "继续", "再来一道题", "ok", "OK"})


def has_stable_signal(text: str) -> bool:
    normalized = " ".join((text or "").strip().split())
    if not normalized or normalized in NON_SIGNIFICANT_TEXTS:
        return False
    return any(pattern.search(normalized) for pattern in STABLE_SIGNAL_PATTERNS)


PROFILE_SIGNAL_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"(?:以后|下次|后续).*(?:先|不要|别|必须|应该|保持|沿用|避免|给|讲)"),
    re.compile(r"我(?:喜欢|不喜欢|更喜欢|偏好|习惯)"),
    re.compile(r"我(?:总是|经常|一直|老是|反复).*(?:出错|不会|卡住|记不住|混淆|薄弱)"),
)


def has_profile_signal(text: str) -> bool:
    normalized = " ".join((text or "").strip().split())
    return bool(normalized) and any(pattern.search(normalized) for pattern in PROFILE_SIGNAL_PATTERNS)


SUMMARY_RECALL_TRIGGERS: Final[tuple[str, ...]] = ("之前", "前面", "刚才", "上次", "继续", "那个方案", "前文", "我们刚")


def should_include_session_summary(user_message: str) -> bool:
    normalized = (user_message or "").strip()
    return bool(normalized) and any(trigger in normalized for trigger in SUMMARY_RECALL_TRIGGERS)


def render_summary_markdown(summary_json: dict[str, Any]) -> str:
    if not summary_json:
        return "# 会话概要\n\n暂无概要信息。"
    sections = [
        ("当前学习任务", summary_json.get("current_learning_task")),
        ("对话进度", summary_json.get("conversation_position")),
        ("下一步行动", summary_json.get("next_action")),
    ]
    list_sections = [
        ("用户原始问题", summary_json.get("original_user_questions") or []),
        ("已解释内容", summary_json.get("explained_content") or []),
        ("当前理解状态", summary_json.get("current_understanding") or []),
        ("当前困惑点", summary_json.get("current_confusions") or []),
        ("已使用教学方法", summary_json.get("teaching_methods_used") or []),
        ("画像候选", summary_json.get("profile_candidates") or []),
        ("长期记忆候选", summary_json.get("memory_candidates") or []),
    ]
    lines = ["# 会话概要"]
    for title, value in sections:
        if value:
            lines.append(f"\n## {title}\n\n{value}")
    for title, values in list_sections:
        if values:
            lines.append(f"\n## {title}")
            lines.extend(f"- {item}" for item in values if item)
    return "\n".join(lines)


def render_memory_markdown(memory_json: dict[str, Any]) -> str:
    if not memory_json:
        return "# 长期记忆\n\n暂无长期记忆信息。"
    titles = {
        "long_term_goals": "长期目标",
        "learning_preferences": "学习偏好",
        "stable_weaknesses": "稳定薄弱点",
        "project_context": "项目背景",
        "interaction_rules": "交互规则",
        "effective_strategies": "有效辅导策略",
        "corrections": "用户纠正记录",
        "recent_important_changes": "最近重要变化",
    }
    lines = ["# 长期记忆"]
    background = memory_json.get("learning_background") or {}
    if isinstance(background, dict) and (background.get("description") or background.get("major") or background.get("grade")):
        lines.append("\n## 学习背景")
        if background.get("description"):
            lines.append(str(background["description"]))
        if background.get("major"):
            lines.append(f"- 专业: {background['major']}")
        if background.get("grade"):
            lines.append(f"- 年级: {background['grade']}")
    for key, title in titles.items():
        values = memory_json.get(key) or []
        if values:
            lines.append(f"\n## {title}")
            lines.extend(f"- {item}" for item in values if item)
    return "\n".join(lines) if len(lines) > 1 else "# 长期记忆\n\n暂无长期记忆。"
