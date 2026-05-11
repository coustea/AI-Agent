"""长期记忆领域类型定义。

模块职责：
- 定义长期记忆默认 JSON 结构
- 定义稳定信号检测模式
- 提供 Markdown 渲染函数
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Final


# ---------------------------------------------------------------------------
# 稳定信号检测模式
# ---------------------------------------------------------------------------

STABLE_SIGNAL_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"我(?:总是|经常|一直|老是|反复).*(?:出错|不会|卡住|卡在|记不住|搞不清|混淆|薄弱|边界)"),
    re.compile(r"我(?:喜欢|不喜欢|更喜欢|偏好|习惯)"),
    re.compile(r"我(?:在学|正在学|学过|以前学过|已经学过|准备|打算|想(?:学|考|准备|提高|练习))"),
    re.compile(r"(?:专业|年级|方向|课程|考试|证书|竞赛|实习|面试|项目)"),
    re.compile(r"(?:你|ai|AI|助手).*(?:错了|理解错|误解|不对|遗漏|应该|不要|别|记住|以后)"),
    re.compile(r"(?:以后|下次|后续).*(?:不要|别|先|必须|应该|保持|沿用|避免)"),
)

NON_SIGNIFICANT_TEXTS: Final[frozenset[str]] = frozenset({
    "谢谢", "好的", "收到", "明白了", "继续", "再来一道题", "ok", "OK"
})


def has_stable_signal(text: str) -> bool:
    """检测文本是否包含稳定信号。"""
    normalized = " ".join((text or "").strip().lower().split())
    if not normalized:
        return False
    if normalized in NON_SIGNIFICANT_TEXTS:
        return False
    return any(pattern.search(normalized) for pattern in STABLE_SIGNAL_PATTERNS)


# ---------------------------------------------------------------------------
# 默认 JSON 结构
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_default_memory_json() -> dict[str, Any]:
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


# ---------------------------------------------------------------------------
# Markdown 渲染
# ---------------------------------------------------------------------------

def render_memory_markdown(memory_json: dict[str, Any]) -> str:
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
