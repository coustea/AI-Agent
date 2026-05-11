"""上下文构建服务。

模块职责：
- 构建画像上下文
- 构建长期记忆上下文
- 构建文件附件上下文
- 构建会话概要上下文
- 构建完整辅导上下文
- 构建近期对话上下文
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage

from app.memory.core.types import ModuleName
from app.memory.context.policy import (
    RECENT_CHAT_MESSAGE_LIMIT,
    SUMMARY_CHAR_BUDGET,
    render_priority_long_term_memory,
    render_recent_chat_context,
    select_recent_chat_messages,
    should_include_session_summary,
    truncate_text,
)
from app.memory.message.store import MessageStore
from app.memory.memory.store import LongTermMemoryStore
from app.memory.profile.store import ProfileStore
from app.memory.summary.store import SummaryStore
from app.memory.summary.types import render_summary_markdown


class ContextService:
    """上下文构建服务。"""

    def __init__(
        self,
        module: str = ModuleName.MENTOR,
        *,
        message_store: MessageStore | None = None,
        memory_store: LongTermMemoryStore | None = None,
        profile_store: ProfileStore | None = None,
        summary_store: SummaryStore | None = None,
    ) -> None:
        self.module = module
        self.message_store = message_store or MessageStore()
        self.memory_store = memory_store or LongTermMemoryStore()
        self.profile_store = profile_store or ProfileStore()
        self.summary_store = summary_store or SummaryStore()

    async def build_profile_context(self, user_id: int) -> str:
        """构建画像上下文，用于 Agent 系统提示词。"""
        profile = await self.profile_store.get(user_id, self.module)
        if not profile:
            return "暂无画像信息（新用户），请直接开始对话。"
        if profile.profile_json and profile.profile_json.get("dimensions"):
            return json.dumps(profile.profile_json, ensure_ascii=False, indent=2)
        return "暂无画像信息（新用户），请直接开始对话。"

    async def build_memory_context(self, user_id: int) -> str:
        """构建长期记忆上下文。"""
        memory = await self.memory_store.get(user_id, self.module)
        if not memory:
            return "暂无长期记忆。"
        if memory.memory_json:
            return render_priority_long_term_memory(memory.memory_json)
        if memory.memory_markdown:
            return truncate_text(memory.memory_markdown, 1600)
        return "暂无长期记忆。"

    def build_file_context(
        self,
        image_urls: list[str],
        file_urls: list[str],
    ) -> str:
        """构建附件上下文。"""
        if not image_urls and not file_urls:
            return "本次对话无上传文件。"
        lines = []
        if image_urls:
            lines.append(f"图片附件（{len(image_urls)}个）：")
            lines.extend(f"  - {url.split('/')[-1]}" for url in image_urls)
        if file_urls:
            lines.append(f"文档附件（{len(file_urls)}个）：")
            lines.extend(f"  - {url.split('/')[-1]}" for url in file_urls)
        return "\n".join(lines)

    async def build_session_summary_context(
        self,
        user_id: int,
        session_id: str,
    ) -> str:
        """构建会话概要上下文。"""
        summaries = await self.summary_store.list(
            user_id=user_id,
            session_id=session_id,
            module=self.module,
            limit=2,
        )
        if not summaries:
            return "暂无会话概要。"
        chunks = []
        for s in summaries:
            if s.summary_json:
                chunks.append(render_summary_markdown(s.summary_json))
            else:
                chunks.append(s.summary_markdown)
        return "\n\n---\n\n".join(chunks)

    async def build_tutor_context(
        self,
        user_id: int,
        session_id: str,
        recent_limit: int = 10,
    ) -> str:
        """构建完整辅导上下文（画像 + 长期记忆 + 最近对话）。"""
        profile_ctx = await self.build_profile_context(user_id)
        memory_ctx = await self.build_memory_context(user_id)
        msgs = await self.message_store.get_recent(
            user_id=user_id,
            session_id=session_id,
            module=self.module,
            limit=recent_limit,
        )
        recent_lines = [
            f"- {m.role}: {m.content[:200]}..."
            if len(m.content) > 200
            else f"- {m.role}: {m.content}"
            for m in msgs
            if m.role in {"user", "assistant"} and m.content.strip()
        ]
        recent_ctx = "\n".join(recent_lines) or "暂无最近对话。"
        return f"# 用户画像\n{profile_ctx}\n\n# 用户长期记忆\n{memory_ctx}\n\n# 最近对话\n{recent_ctx}"

    async def build_recent_chat_context(
        self,
        user_id: int,
        session_id: str,
        user_message: str,
        image_urls: list[str] | None = None,
        file_urls: list[str] | None = None,
    ) -> tuple[list[AnyMessage], str]:
        """构建近期对话上下文，返回消息列表和文本描述。"""
        messages: list[AnyMessage] = []
        msgs = await self.message_store.get_recent(
            user_id=user_id,
            session_id=session_id,
            module=self.module,
            limit=RECENT_CHAT_MESSAGE_LIMIT,
        )
        selected = select_recent_chat_messages(msgs, user_message=user_message)

        for m in selected:
            if m.role == "user":
                messages.append(HumanMessage(content=m.content))
            elif m.role == "assistant":
                messages.append(AIMessage(content=m.content))

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
                recent_ctx = (
                    f"# 会话概要\n{truncate_text(summary_ctx, SUMMARY_CHAR_BUDGET)}\n\n"
                    f"# 最近对话\n{recent_ctx}"
                )
        return messages, recent_ctx

    async def build_context_preview(
        self,
        user_id: int,
        session_id: str,
        recent_limit: int = 10,
    ) -> str:
        """构建上下文预览。"""
        return await self.build_tutor_context(
            user_id=user_id,
            session_id=session_id,
            recent_limit=recent_limit,
        )
