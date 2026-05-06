"""记忆上下文注入策略。

该模块只做上下文选择与裁剪，不访问数据库、不调用 LLM。
"""

from __future__ import annotations

from typing import Any

RECENT_CHAT_MESSAGE_LIMIT = 10
RECENT_CHAT_CONTEXT_CHAR_BUDGET = 700
LONG_TERM_MEMORY_CHAR_BUDGET = 1600
SUMMARY_CHAR_BUDGET = 900

SUMMARY_RECALL_TRIGGERS = (
    "之前",
    "前面",
    "刚才",
    "上次",
    "继续",
    "那个方案",
    "前文",
    "我们刚",
)

LONG_TERM_FIELD_TITLES = {
    "corrections": "用户纠正记录",
    "interaction_rules": "交互规则",
    "learning_preferences": "学习偏好",
    "long_term_goals": "长期目标",
    "project_context": "项目背景",
    "stable_weaknesses": "稳定薄弱点",
    "effective_strategies": "有效辅导策略",
    "learning_background": "学习背景",
    "recent_important_changes": "最近重要变化",
}

LONG_TERM_FIELD_ORDER = (
    "corrections",
    "interaction_rules",
    "learning_preferences",
    "long_term_goals",
    "project_context",
    "effective_strategies",
    "learning_background",
    "recent_important_changes",
    "stable_weaknesses",
)


def truncate_text(text: str, char_budget: int) -> str:
    if len(text) <= char_budget:
        return text
    return text[: max(char_budget - 3, 0)].rstrip() + "..."


def should_include_session_summary(user_message: str) -> bool:
    normalized = (user_message or "").strip()
    if not normalized:
        return False
    return any(trigger in normalized for trigger in SUMMARY_RECALL_TRIGGERS)


def _message_line(role: str, content: str) -> str:
    label = "用户" if role == "user" else "助手"
    return f"- {label}: {content}"


def _is_current_user_duplicate(message: Any, user_message: str) -> bool:
    return (
        getattr(message, "role", None) == "user"
        and (getattr(message, "content", "") or "").strip() == (user_message or "").strip()
    )


def select_recent_chat_messages(
    messages: list[Any],
    *,
    user_message: str,
    char_budget: int = RECENT_CHAT_CONTEXT_CHAR_BUDGET,
) -> list[Any]:
    """从最近消息中按预算保留最新上下文。

    传入列表通常已由 store 按时间正序返回；这里从后往前选，最后再恢复正序。
    """
    dialogue = [
        message
        for message in messages
        if getattr(message, "role", None) in {"user", "assistant"}
        and (getattr(message, "content", "") or "").strip()
    ]
    if dialogue and _is_current_user_duplicate(dialogue[-1], user_message):
        dialogue = dialogue[:-1]

    selected: list[Any] = []
    used_chars = 0
    for message in reversed(dialogue):
        role = getattr(message, "role", "")
        content = (getattr(message, "content", "") or "").strip()
        line = _message_line(role, content)
        next_size = len(line) + 1
        if selected and used_chars + next_size > char_budget:
            continue
        if not selected and next_size > char_budget:
            selected.append(message)
            break
        selected.append(message)
        used_chars += next_size
    return list(reversed(selected))


def render_recent_chat_context(messages: list[Any], *, char_budget: int = RECENT_CHAT_CONTEXT_CHAR_BUDGET) -> str:
    lines = []
    for message in messages:
        role = getattr(message, "role", "")
        content = truncate_text((getattr(message, "content", "") or "").strip(), char_budget)
        lines.append(_message_line(role, content))
    context = "\n".join(lines)
    return truncate_text(context, char_budget) if context else "最近 7 天暂无历史对话。"


def _append_with_budget(lines: list[str], addition: str, char_budget: int) -> bool:
    current = "\n".join(lines)
    separator = "\n" if current else ""
    if len(current) + len(separator) + len(addition) > char_budget:
        return False
    lines.append(addition)
    return True


def render_priority_long_term_memory(memory_json: dict[str, Any], *, char_budget: int = LONG_TERM_MEMORY_CHAR_BUDGET) -> str:
    if not memory_json:
        return "# 长期记忆\n\n暂无长期记忆信息。"

    lines = ["# 长期记忆"]
    for field in LONG_TERM_FIELD_ORDER:
        value = memory_json.get(field)
        if not value:
            continue

        section_lines = [f"\n## {LONG_TERM_FIELD_TITLES[field]}"]
        if field == "learning_background":
            description = value.get("description", "") if isinstance(value, dict) else ""
            if description:
                section_lines.append(description)
            major = value.get("major") if isinstance(value, dict) else None
            grade = value.get("grade") if isinstance(value, dict) else None
            if major:
                section_lines.append(f"- 专业: {major}")
            if grade:
                section_lines.append(f"- 年级: {grade}")
        elif isinstance(value, list):
            for item in value:
                if not item:
                    continue
                section_lines.append(f"- {item}")
        else:
            section_lines.append(str(value))

        section = "\n".join(section_lines)
        if not _append_with_budget(lines, section, char_budget):
            continue

    return "\n".join(lines) if len(lines) > 1 else "# 长期记忆\n\n暂无长期记忆。"
