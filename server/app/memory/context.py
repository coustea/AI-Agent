"""构建 LLM 上下文（三层记忆 + 画像）。"""

from __future__ import annotations

from typing import Any

from app.memory.store import MemoryStore
from app.memory.types import (
    CHAT_BUDGET,
    LTM_BUDGET,
    MSG_LIMIT,
    PROFILE_BUDGET,
    SUMMARY_BUDGET,
    ModuleName,
    estimate_token_count,
    truncate_text,
)
from app.memory.profile import render_profile_markdown


class ContextBuilder:
    """组装三层记忆 + 画像为 LLM 系统提示上下文。"""

    def __init__(self, *, module: str = ModuleName.MENTOR, store: MemoryStore | None = None) -> None:
        self.module = module
        self.store = store or MemoryStore()

    async def build(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str = "",
    ) -> dict[str, Any]:
        profile_section = await self._build_profile(user_id)
        ltm_section = await self._build_long_term_memory(user_id)
        summary_section = await self._build_session_summaries(user_id, session_id)
        messages = await self._build_recent_messages(user_id, session_id)

        return {
            "profile": profile_section,
            "long_term_memory": ltm_section,
            "session_summaries": summary_section,
            "recent_messages": messages,
            "total_tokens": sum(
                estimate_token_count(str(v)) for v in [profile_section, ltm_section, summary_section] if v
            ),
        }

    async def _build_profile(self, user_id: int) -> str:
        profile = await self.store.get_profile(user_id=user_id, module=self.module)
        if not profile:
            return ""
        if profile.profile_markdown and profile.profile_markdown.strip():
            return truncate_text(profile.profile_markdown, PROFILE_BUDGET)
        if profile.profile_json:
            return truncate_text(render_profile_markdown(profile.profile_json), PROFILE_BUDGET)
        return ""

    async def _build_long_term_memory(self, user_id: int) -> str:
        memory = await self.store.get_long_term_memory(user_id=user_id, module=self.module)
        if not memory or not memory.memory_markdown:
            return ""
        return truncate_text(memory.memory_markdown, LTM_BUDGET)

    async def _build_session_summaries(self, user_id: int, session_id: str) -> str:
        summaries = await self.store.list_summaries(user_id=user_id, session_id=session_id, module=self.module, limit=3)
        if not summaries:
            return ""
        parts: list[str] = []
        for summary in summaries:
            if summary.summary_markdown and summary.summary_markdown.strip():
                parts.append(summary.summary_markdown)
        if not parts:
            return ""
        return truncate_text("\n\n---\n\n".join(parts), SUMMARY_BUDGET)

    async def _build_recent_messages(self, user_id: int, session_id: str) -> list[dict[str, Any]]:
        messages = await self.store.list_messages(
            user_id=user_id,
            session_id=session_id,
            module=self.module,
            limit=MSG_LIMIT,
        )
        result: list[dict[str, Any]] = []
        for msg in messages:
            content = str(msg.content or "").strip()
            if not content:
                continue
            entry: dict[str, Any] = {"role": msg.role, "content": content}
            if msg.attachments:
                entry["attachments"] = msg.attachments
            if msg.tool_calls:
                entry["tool_calls"] = msg.tool_calls
            result.append(entry)
        return result
