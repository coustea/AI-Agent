"""记忆系统共享类型与纯函数。"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Final

from pydantic import BaseModel, Field


class ConcurrentUpdateError(Exception):
    """画像并发更新冲突。"""

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
PROFILE_MIN_COVERAGE: Final[int] = 60
MEMORY_UPDATE_COOLDOWN_SECONDS: Final[float] = 300.0

# 长期记忆周期触发阈值（每 N 轮 LLM 判断一次）
LTM_PERIODIC_THRESHOLD: Final[int] = 10

# 画像更新周期触发配置（coverage 分段 → 轮次间隔）
PROFILE_UPDATE_INTERVALS: Final[dict[str, dict[str, Any]]] = {
    "low": {"max_coverage": 0.4, "interval": 3},
    "medium": {"max_coverage": 0.8, "interval": 8},
    "high": {"max_coverage": 1.0, "interval": 15},
}

# 长期记忆分类（7 分类，去掉 recent_important_changes，合并 project_context 到 learning_background）
LTM_CATEGORIES: Final[tuple[str, ...]] = (
    "learning_background",
    "long_term_goals",
    "learning_preferences",
    "stable_weaknesses",
    "interaction_rules",
    "effective_strategies",
    "corrections",
)

LTM_CATEGORY_NAMES: Final[dict[str, str]] = {
    "learning_background": "学习背景",
    "long_term_goals": "长期目标",
    "learning_preferences": "学习偏好",
    "stable_weaknesses": "稳定薄弱点",
    "interaction_rules": "交互规则",
    "effective_strategies": "有效辅导策略",
    "corrections": "用户纠正记录",
}


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

# 置信度分档阈值
CONFIDENCE_HIGH: Final[float] = 0.7
CONFIDENCE_MEDIUM: Final[float] = 0.4
CONFIDENCE_LOW: Final[float] = 0.0

CONFIDENCE_LABELS: Final[dict[str, str]] = {
    "high": "确定",
    "medium": "推测",
    "low": "初步",
    "empty": "待探索",
}


def confidence_label(value: float) -> str:
    """将 confidence 数值映射为文字标签。"""
    if value >= CONFIDENCE_HIGH:
        return "high"
    if value >= CONFIDENCE_MEDIUM:
        return "medium"
    if value > CONFIDENCE_LOW:
        return "low"
    return "empty"


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


def make_default_memory_markdown() -> str:
    """长期记忆默认 Markdown（7 分类）。"""
    lines = ["# 长期记忆", "\n## 学习背景", "暂无学习背景信息。"]
    for key in LTM_CATEGORIES[1:]:
        lines.append(f"\n## {LTM_CATEGORY_NAMES[key]}")
        lines.append("暂无信息。")
    return "\n".join(lines)


class DimensionOutput(BaseModel):
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    summary: str | None = None
    evidence: list[str] = Field(default_factory=list)


class ProfileOutput(BaseModel):
    dimensions: dict[str, DimensionOutput] = Field(default_factory=dict)
    recommended_strategy: list[str] = Field(default_factory=list)
    last_update_reason: str = ""


class MemoryUpdateOutput(BaseModel):
    """长期记忆更新 LLM 输出（Markdown 格式）。"""

    need_update: bool = Field(description="是否需要更新长期记忆")
    memory_markdown: str | None = Field(
        default=None,
        description="更新后的长期记忆 Markdown，用 ## 分类名 分节",
    )


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


# 压缩降级启发式提取正则
COMPRESSION_FALLBACK_TASK_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"(?:学|理解|搞清楚|弄明白|想知道|想了解|想掌握|想学会|研究|探索).+"),
)
COMPRESSION_FALLBACK_CONFUSION_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"(?:不懂|不明白|困惑|为什么|怎么会|搞不清|搞不懂|不理解|没搞懂|不太懂|有点懵|一头雾水).+"),
)
COMPRESSION_FALLBACK_TOPIC_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"[A-Z][a-zA-Z]+(?:\.js|\.py|\.ts|\.java|\.go|\.rs|\.cpp)?"),
    re.compile(r"(?:算法|数据结构|排序|搜索|递归|动态规划|图|树|链表|栈|队列|哈希|数据库|网络|操作系统|编译|机器学习|深度学习|Python|Java|Go|Rust|C\+\+|JavaScript|TypeScript|React|Vue|Spring|Docker|Kubernetes|SQL|REST|API|HTTP|TCP|UDP|OS|CPU|GPU|内存|线程|进程|锁|并发|异步|微服务|设计模式|测试|CI|CD)"),
)


def extract_fallback_summary_markdown(dialogue_text: str) -> str:
    """LLM 失败时用启发式正则提取任务状态 Markdown（降级）。"""
    task_matches = [m.group().strip() for p in COMPRESSION_FALLBACK_TASK_PATTERNS if (m := p.search(dialogue_text))]
    confusion_matches = [m.group().strip() for p in COMPRESSION_FALLBACK_CONFUSION_PATTERNS if (m := p.search(dialogue_text))]
    topic_matches = [m.group().strip() for p in COMPRESSION_FALLBACK_TOPIC_PATTERNS if (m := p.search(dialogue_text))]

    lines = ["# 当前会话摘要（降级提取）"]
    lines.append("\n## 当前任务")
    if task_matches:
        lines.extend(f"- {t}" for t in task_matches[:5])
    else:
        lines.append("暂无。")
    lines.append("\n## 当前阶段")
    lines.append("未能自动提取。")
    lines.append("\n## 用户最新意图")
    if confusion_matches:
        lines.extend(f"- {c}" for c in confusion_matches[:3])
    else:
        lines.append("暂无。")
    lines.append("\n## 已确认结论")
    if topic_matches:
        lines.extend(f"- {t}" for t in topic_matches[:5])
    else:
        lines.append("暂无。")
    lines.append("\n## 用户纠正与约束")
    lines.append("暂无。")
    lines.append("\n## 下一步")
    lines.append("继续对话以明确任务方向。")
    return "\n".join(lines)