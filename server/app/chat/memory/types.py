"""Chat-private memory types and helpers."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Final

from pydantic import BaseModel


DIALOGUE_ROLES: Final[frozenset[str]] = frozenset({"user", "assistant"})
MESSAGE_EXPIRE_DAYS: Final[int] = 7
DEFAULT_SESSION_TITLE: Final[str] = "新对话"
TITLE_MAX_LENGTH: Final[int] = 100

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
    """返回当前 UTC 时间。"""

    return datetime.now(timezone.utc)


def estimate_token_count(text: str) -> int:
    """粗略估算文本 token 数。"""

    stripped = (text or "").strip()
    if not stripped:
        return 0
    return max(max(1, len(stripped) // 4), len(stripped.split()))


def truncate_text(text: str, char_budget: int, suffix: str = "...") -> str:
    """按字符预算截断文本。"""

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


def make_default_memory_markdown() -> str:
    """生成空白长期记忆 Markdown 模板。"""

    lines = ["# 长期记忆", "", "## 学习背景", "暂无学习背景信息。"]
    for key in LTM_CATEGORIES[1:]:
        lines.extend(["", f"## {LTM_CATEGORY_NAMES[key]}", "暂无信息。"])
    return "\n".join(lines)


class MemoryUpdateOutput(BaseModel):
    """长期记忆更新结果。"""

    need_update: bool = False
    memory_markdown: str | None = None
    confidence: float = 0.75
    update_reason: str = ""


STABLE_SIGNAL_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"(总是|经常|一直|老是|反复).*(出错|不会|卡住|记不住|搞不清|混淆|薄弱|边界)"),
    re.compile(r"(以后|下次|后续).*(希望|想|请|先|多|少|给|讲|不要|必须|应该|保持|沿用|避免|记住)"),
    re.compile(r"(喜欢|不喜欢|更喜欢|偏好|习惯)"),
    re.compile(r"(在学|正在学|学过|准备|打算|想要).*(考研|提高|练习|项目)"),
    re.compile(r"(专业|年级|方向|课程|考试|证书|竞赛|实习|面试|项目)"),
)

NON_SIGNIFICANT_TEXTS: Final[frozenset[str]] = frozenset(
    {"谢谢", "好的", "收到", "明白了", "继续", "再来一道题", "ok", "OK"}
)


def has_stable_signal(text: str) -> bool:
    """检测文本是否包含稳定的学习特征信号。"""

    normalized = " ".join((text or "").strip().split())
    if not normalized or normalized in NON_SIGNIFICANT_TEXTS:
        return False
    return any(pattern.search(normalized) for pattern in STABLE_SIGNAL_PATTERNS)
