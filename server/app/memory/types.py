"""Shared profile and memory types."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Final

from pydantic import BaseModel, Field


class ConcurrentUpdateError(Exception):
    """Raised when optimistic profile updates conflict."""


class ModuleName:
    """模块名称常量。"""
    MENTOR: Final[str] = "mentor"
    RESOURCE: Final[str] = "resource"
    AVATAR: Final[str] = "avatar"


DIALOGUE_ROLES: Final[frozenset[str]] = frozenset({"user", "assistant"})  # 参与对话的角色集合
MESSAGE_EXPIRE_DAYS: Final[int] = 7  # 消息过期天数
DEFAULT_SESSION_TITLE: Final[str] = "新对话"  # 新会话默认标题
TITLE_MAX_LENGTH: Final[int] = 100  # 会话标题最大长度

SUMMARY_TOKEN_THRESHOLD: Final[int] = 150  # 触发压缩的 token 阈值
SUMMARY_MESSAGE_THRESHOLD: Final[int] = 30  # 触发压缩的消息数阈值
SUMMARY_KEEP_RECENT: Final[int] = 10  # 压缩时保留的最近消息数
PROFILE_MIN_COVERAGE: Final[int] = 60  # 画像最低覆盖率（百分比）
MEMORY_UPDATE_COOLDOWN_SECONDS: Final[float] = 300.0  # 长期记忆更新冷却时间（秒）
LTM_PERIODIC_THRESHOLD: Final[int] = 10  # 周期性长期记忆更新的轮次间隔
PROFILE_TOKEN_THRESHOLD: Final[int] = 1500  # 触发画像更新的累积 token 阈值


LTM_CATEGORIES: Final[tuple[str, ...]] = (  # 长期记忆分类键
    "learning_background",
    "long_term_goals",
    "learning_preferences",
    "stable_weaknesses",
    "interaction_rules",
    "effective_strategies",
    "corrections",
)

LTM_CATEGORY_NAMES: Final[dict[str, str]] = {  # 分类键到中文名的映射
    "learning_background": "学习背景",
    "long_term_goals": "长期目标",
    "learning_preferences": "学习偏好",
    "stable_weaknesses": "稳定薄弱点",
    "interaction_rules": "交互规则",
    "effective_strategies": "有效辅导策略",
    "corrections": "用户纠正记录",
}


def now() -> datetime:
    """返回当前 UTC 时间。"""
    return datetime.now(timezone.utc)


def days_ago(days: int) -> datetime:
    """返回 N 天前的 UTC 时间。"""
    return now() - timedelta(days=max(days, 0))


def estimate_token_count(text: str) -> int:
    """粗略估算文本 token 数（中文按 4 字符/token，英文按空格分词）。"""
    stripped = (text or "").strip()
    if not stripped:
        return 0
    return max(max(1, len(stripped) // 4), len(stripped.split()))


def truncate_text(text: str, char_budget: int, suffix: str = "...") -> str:
    """按字符预算截断文本，超出时追加后缀。"""
    if len(text) <= char_budget:
        return text
    return text[: max(char_budget - len(suffix), 0)].rstrip() + suffix


def extract_fallback_summary_markdown(chat_text: str, max_lines: int = 8, char_budget: int = 1200) -> str:
    """Build a compact fallback session summary when LLM compression is unavailable."""
    normalized_lines = [line.strip() for line in str(chat_text or "").splitlines() if line.strip()]
    if not normalized_lines:
        return "# 会话摘要\n\n- 暂无可压缩的历史对话。"

    selected = normalized_lines[:max_lines]
    bullets = [f"- {truncate_text(line, 140)}" for line in selected]
    if len(normalized_lines) > max_lines:
        bullets.append(f"- 其余 {len(normalized_lines) - max_lines} 条对话已省略。")
    body = "\n".join(bullets)
    return truncate_text(f"# 会话摘要\n\n{body}", char_budget)


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


ALL_DIMENSIONS: Final[tuple[str, ...]] = (  # 所有画像维度，用于覆盖率计算
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

DIMENSION_NAMES: Final[dict[str, str]] = {  # 维度键到中文名的映射
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

CONFIDENCE_HIGH: Final[float] = 0.7  # 高置信度阈值
CONFIDENCE_MEDIUM: Final[float] = 0.4  # 中置信度阈值
CONFIDENCE_LOW: Final[float] = 0.0  # 低置信度基线


def confidence_label(value: float) -> str:
    """将置信度数值转换为标签（high/medium/low/empty）。"""
    if value >= CONFIDENCE_HIGH:
        return "high"
    if value >= CONFIDENCE_MEDIUM:
        return "medium"
    if value > CONFIDENCE_LOW:
        return "low"
    return "empty"


ONBOARDING_REQUIRED_FIELDS: Final[tuple[str, ...]] = (  # 入门必填字段
    "school",
    "major",
    "grade",
    "daily_study_time",
    "global_learning_goal",
    "courses",
)

ONBOARDING_REQUIRED_COURSE_FIELDS: Final[tuple[str, ...]] = (  # 课程必填字段
    "course",
    "foundation_level",
)

ONBOARDING_OPTIONAL_FIELDS: Final[tuple[str, ...]] = (  # 入门选填字段
    "resource_preference",
    "programming_languages",
    "learning_style_tags",
    "self_description",
)

OPTIONAL_COURSE_FIELDS: Final[tuple[str, ...]] = (  # 课程选填字段
    "current_topic",
    "course_learning_goal",
    "weak_points",
)

DAILY_STUDY_TIME_TO_PACE: Final[dict[str, str]] = {  # 每日学习时长到节奏的映射
    "30min以下": "slow",
    "30-60min": "slow",
    "1-2h": "medium",
    "2-3h": "fast",
    "3h以上": "intensive",
}

FOUNDATION_LEVEL_TO_KNOWLEDGE_LEVEL: Final[dict[str, str]] = {  # 基础水平到知识等级的映射
    "薄弱": "weak",
    "一般": "medium_low",
    "较好": "good",
    "熟练": "advanced",
}

GOAL_TO_PROFILE_GOAL: Final[dict[str, str]] = {  # 学习目标到画像目标类型的映射
    "期末复习": "exam_oriented",
    "考研学习": "exam_oriented",
    "考研强化": "exam_oriented",
    "进阶学习": "advanced_learning",
    "项目实战": "project_oriented",
    "竞赛提升": "competition_oriented",
    "补基础": "foundation_repair",
}

RESOURCE_WEIGHT_DEFAULTS: Final[dict[str, float]] = {  # 各资源类型的默认权重
    "document": 0.55,
    "diagram": 0.55,
    "exercise": 0.55,
    "code_case": 0.55,
    "mind_map": 0.5,
    "ppt": 0.4,
    "video_animation": 0.4,
}

RESOURCE_PREFERENCE_TO_WEIGHT_KEY: Final[dict[str, str]] = {  # 中文资源偏好到权重键的映射
    "文档": "document",
    "图解": "diagram",
    "练习题": "exercise",
    "题目": "exercise",
    "代码": "code_case",
    "代码案例": "code_case",
    "思维导图": "mind_map",
    "PPT": "ppt",
    "视频动画": "video_animation",
    "视频": "video_animation",
}


def dedupe_strings(items: list[str] | None) -> list[str]:
    """去重并清理字符串列表。"""
    result: list[str] = []
    seen: set[str] = set()
    for item in items or []:
        text = str(item or "").strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def slugify(value: str | None) -> str | None:
    """\u5c06\u6587\u672c\u8f6c\u4e3a URL \u5b89\u5168\u7684 slug \u683c\u5f0f\uff0c\u4fdd\u7559\u4e2d\u82f1\u6587\u548c\u6570\u5b57\u3002"""
    text = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "_", str(value or "").strip()).strip("_").lower()
    return text or None


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
            "resource_preference": [],
            "programming_languages": [],
            "learning_style_tags": [],
            "self_description": None,
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
        "profile_score_version": 2,
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
    """生成空白长期记忆 Markdown 模板。"""
    lines = ["# 长期记忆", "", "## 学习背景", "暂无学习背景信息。"]
    for key in LTM_CATEGORIES[1:]:
        lines.extend(["", f"## {LTM_CATEGORY_NAMES[key]}", "暂无信息。"])
    return "\n".join(lines)


class EvidenceRecord(BaseModel):
    """维度证据记录。"""
    source: str = Field(default="system")
    signal_type: str
    course: str | None = None
    knowledge_point: str | None = None
    summary: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class MemoryUpdateOutput(BaseModel):
    """长期记忆更新结果。"""
    need_update: bool = False
    memory_markdown: str | None = None
    update_reason: str = ""


class TutoringInferenceOutput(BaseModel):
    """辅导推理输出，包含画像增量 patch。"""
    should_update: bool = False
    global_profile_patch: dict[str, Any] = Field(default_factory=dict)
    course_profile_patch: dict[str, Any] | None = None
    knowledge_mastery_patch: list[dict[str, Any]] = Field(default_factory=list)
    initial_strategy_patch: dict[str, Any] = Field(default_factory=dict)
    evidence: list[EvidenceRecord] = Field(default_factory=list)
    update_reason: str = ""


STABLE_SIGNAL_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (  # 匹配稳定学习特征的正则模式
    re.compile(r"(总是|经常|一直|老是|反复).*(出错|不会|卡住|记不住|搞不清|混淆|薄弱|边界)"),
    re.compile(r"(喜欢|不喜欢|更喜欢|偏好|习惯)"),
    re.compile(r"(在学|正在学|学过|准备|打算|想要).*(考研|提高|练习|项目)"),
    re.compile(r"(专业|年级|方向|课程|考试|证书|竞赛|实习|面试|项目)"),
)

NON_SIGNIFICANT_TEXTS: Final[frozenset[str]] = frozenset(  # 无意义的短文本，不作为信号
    {"谢谢", "好的", "收到", "明白了", "继续", "再来一道题", "ok", "OK"}
)


def has_stable_signal(text: str) -> bool:
    """检测文本是否包含稳定的学习特征信号。"""
    normalized = " ".join((text or "").strip().split())
    if not normalized or normalized in NON_SIGNIFICANT_TEXTS:
        return False
    return any(pattern.search(normalized) for pattern in STABLE_SIGNAL_PATTERNS)


PROFILE_SIGNAL_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"(以后|下次|后续).*(不要|必须|应该|保持|沿用|避免|记住)"),
    re.compile(r"(喜欢|不喜欢|更喜欢|偏好|习惯)"),
    re.compile(r"(总是|经常|一直|反复).*(出错|不会|卡住|记不住|混淆|薄弱)"),
    re.compile(r"(我不会|我懂了|我会了|讲慢一点|先举例|先给题)"),
)


def has_profile_signal(text: str) -> bool:
    """检测文本是否包含画像更新信号（偏好、困难、节奏等）。"""
    normalized = " ".join((text or "").strip().split())
    return bool(normalized) and any(pattern.search(normalized) for pattern in PROFILE_SIGNAL_PATTERNS)


NON_SIGNIFICANT_TEXTS
