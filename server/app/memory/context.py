"""上下文构建。"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage

from app.infra.logging import get_logger
from app.memory.store import MemoryStore
from app.memory.types import (
    CHAT_BUDGET,
    LTM_BUDGET,
    MSG_LIMIT,
    SUMMARY_BUDGET,
    should_include_session_summary,
    truncate_text,
)

logger = get_logger(__name__)

def _message_line(role: str, content: str) -> str:
    return f"- {'用户' if role == 'user' else '助手'}: {content}"


def select_recent_chat_messages(messages: list[Any], *, user_message: str, char_budget: int = CHAT_BUDGET) -> list[Any]:
    dialogue = [
        message
        for message in messages
        if getattr(message, "role", None) in {"user", "assistant"} and (getattr(message, "content", "") or "").strip()
    ]
    if dialogue and getattr(dialogue[-1], "role", None) == "user" and (getattr(dialogue[-1], "content", "") or "").strip() == (user_message or "").strip():
        dialogue = dialogue[:-1]
    selected: list[Any] = []
    used_chars = 0
    for message in reversed(dialogue):
        line = _message_line(getattr(message, "role", ""), (getattr(message, "content", "") or "").strip())
        next_size = len(line) + 1
        if selected and used_chars + next_size > char_budget:
            continue
        if not selected and next_size > char_budget:
            selected.append(message)
            break
        selected.append(message)
        used_chars += next_size
    return list(reversed(selected))


def render_recent_chat_context(messages: list[Any], *, char_budget: int = CHAT_BUDGET) -> str:
    context = "\n".join(
        _message_line(getattr(message, "role", ""), truncate_text((getattr(message, "content", "") or "").strip(), char_budget))
        for message in messages
    )
    return truncate_text(context, char_budget) if context else "最近 7 天暂无历史对话。"


def render_priority_long_term_memory(memory_json: dict[str, Any], *, char_budget: int = LTM_BUDGET) -> str:
    if not memory_json:
        return "# 长期记忆\n\n暂无长期记忆信息。"
    order = (
        ("corrections", "用户纠正记录"),
        ("interaction_rules", "交互规则"),
        ("learning_preferences", "学习偏好"),
        ("long_term_goals", "长期目标"),
        ("project_context", "项目背景"),
        ("effective_strategies", "有效辅导策略"),
        ("stable_weaknesses", "稳定薄弱点"),
        ("recent_important_changes", "最近重要变化"),
    )
    lines = ["# 长期记忆"]
    background = memory_json.get("learning_background") or {}
    if isinstance(background, dict) and any(background.values()):
        lines.append("\n## 学习背景")
        if background.get("description"):
            lines.append(str(background["description"]))
        if background.get("major"):
            lines.append(f"- 专业: {background['major']}")
        if background.get("grade"):
            lines.append(f"- 年级: {background['grade']}")
    for key, title in order:
        values = memory_json.get(key) or []
        if values:
            lines.append(f"\n## {title}")
            lines.extend(f"- {value}" for value in values if value)
    return truncate_text("\n".join(lines), char_budget) if len(lines) > 1 else "# 长期记忆\n\n暂无长期记忆。"


class MemoryContextBuilder:
    def __init__(self, *, module: str = "mentor", store: MemoryStore | None = None) -> None:
        self.module = module
        self.store = store or MemoryStore()

    async def build_profile_context(self, user_id: int) -> str:
        profile = await self.store.get_profile(user_id=user_id, module=self.module)
        logger.info("[MemoryContextBuilder] 开始获取用户画像。")
        if not profile or not profile.profile_json:
            return "暂无画像信息（新用户），请直接开始对话。"
        return json.dumps(profile.profile_json, ensure_ascii=False, indent=2)

    async def build_memory_context(self, user_id: int) -> str:
        memory = await self.store.get_long_term_memory(user_id=user_id, module=self.module)
        logger.info("[MemoryContextBuilder] 开始获取长期记忆。")
        if not memory:
            return "暂无长期记忆。"
        if memory.memory_json:
            return render_priority_long_term_memory(memory.memory_json)
        return truncate_text(memory.memory_markdown or "暂无长期记忆。", LTM_BUDGET)

    def build_file_context(self, image_urls: list[str], file_urls: list[str]) -> str:
        if not image_urls and not file_urls:
            return "本次对话无上传文件。"
        lines: list[str] = []
        if image_urls:
            lines.append(f"图片附件（{len(image_urls)}个）：")
            lines.extend(f"  - {url.split('/')[-1]}" for url in image_urls)
        if file_urls:
            lines.append(f"文档附件（{len(file_urls)}个）：")
            lines.extend(f"  - {url.split('/')[-1]}" for url in file_urls)
        return "\n".join(lines)

    async def build_session_summary_context(self, user_id: int, session_id: str) -> str:
        summaries = await self.store.list_summaries(user_id=user_id, session_id=session_id, module=self.module, limit=2)
        logger.info("[MemoryContextBuilder] 开始获取用户会话概要。")
        if not summaries:
            return "暂无会话概要。"
        return "\n\n---\n\n".join(summary.summary_markdown for summary in summaries if summary.summary_markdown)

    async def build_cross_session_context(self, user_id: int, current_session_id: str, char_budget: int = 800) -> str:
        summaries = await self.store.list_cross_session_summaries(
            user_id=user_id,
            module=self.module,
            exclude_session_id=current_session_id,
            limit=5,
        )
        chunks: list[str] = []
        for summary in summaries:
            data = summary.summary_json or {}
            if data.get("current_learning_task"):
                chunks.append(f"- {data['current_learning_task']}")
            for confusion in (data.get("current_confusions") or [])[:2]:
                chunks.append(f"  - 困惑: {confusion}")
        return truncate_text("# 其他会话概要\n" + "\n".join(chunks), char_budget) if chunks else ""

    async def build_recent_chat_context(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str,
        image_urls: list[str] | None = None,
        file_urls: list[str] | None = None,
    ) -> tuple[list[AnyMessage], str]:
        raw_messages = await self.store.list_messages(user_id=user_id, session_id=session_id, module=self.module, limit=MSG_LIMIT)
        logger.info("[MemoryContextBuilder] 开始获取用户近 %d messages。", MSG_LIMIT)
        selected = select_recent_chat_messages(raw_messages, user_message=user_message)
        messages: list[AnyMessage] = []
        for message in selected:
            if message.role == "user":
                messages.append(HumanMessage(content=message.content))
            elif message.role == "assistant":
                messages.append(AIMessage(content=message.content))
        content = user_message
        if image_urls:
            content += f"\n[Attached Images: {', '.join(image_urls)}]"
        if file_urls:
            content += f"\n[Attached Files: {', '.join(file_urls)}]"
        messages.append(HumanMessage(content=content))

        recent_ctx = render_recent_chat_context(selected)
        if should_include_session_summary(user_message):
            summary_ctx = await self.build_session_summary_context(user_id, session_id)
            if summary_ctx != "暂无会话概要。":
                recent_ctx = f"# 会话概要\n{truncate_text(summary_ctx, SUMMARY_BUDGET)}\n\n# 最近对话\n{recent_ctx}"
            cross_ctx = await self.build_cross_session_context(user_id, session_id)
            if cross_ctx:
                recent_ctx = f"{cross_ctx}\n\n{recent_ctx}"
        return messages, recent_ctx

    async def build_tutor_context(self, *, user_id: int, session_id: str, recent_limit: int = 10) -> str:
        profile_ctx = await self.build_profile_context(user_id)
        memory_ctx = await self.build_memory_context(user_id)
        messages = await self.store.list_messages(user_id=user_id, session_id=session_id, module=self.module, limit=recent_limit)
        recent_lines = [
            _message_line(message.role, truncate_text(message.content, 200))
            for message in messages
            if message.role in {"user", "assistant"} and message.content.strip()
        ]
        return f"# 用户画像\n{profile_ctx}\n\n# 用户长期记忆\n{memory_ctx}\n\n# 最近对话\n{chr(10).join(recent_lines) or '暂无最近对话。'}"

    async def build_context_preview(self, *, user_id: int, session_id: str, recent_limit: int = 10) -> str:
        return await self.build_tutor_context(user_id=user_id, session_id=session_id, recent_limit=recent_limit)
