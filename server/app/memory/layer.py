"""记忆层公共 API — 外部模块唯一入口。

模块职责：
- 会话管理：创建/查询/列举/归档会话
- 短期记忆：消息的写入/读取
- 会话概要：上下文压缩
- 长期记忆：用户级单条记忆管理
- 用户画像：8 维度画像管理
- 上下文构建：为 TutorAgent 构建注入上下文
- 后处理流水线：对话后的记忆更新/画像更新/概要生成

设计原则：
- 外部模块只应依赖 MemoryLayer，不应直接导入 _store/_fact/_profile
- 一个用户一个 module 下只有一条长期记忆
- 一个用户一个 module 下只有一条当前画像
- 会话概要不写入长期记忆
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage

from app.config import PROFILE_GATE_EVERY_N_ASSISTANT_TURNS
from app.infra.logging import get_logger
from app.infra.models import ChatMessage, ChatSession, ChatSessionSummary, UserLongTermMemory, UserProfile, UserProfileHistory
from app.memory._fact import LongTermMemoryUpdateService
from app.memory._profile import ProfileBuildingService
from app.memory._store import MemoryStore, SESSION_SUMMARY_TOKEN_THRESHOLD
from app.memory.memory_types import render_profile_markdown, render_long_term_memory_markdown, render_session_summary_markdown

logger = get_logger(__name__)


class MemoryLayer:
    """记忆层公共 API — 外部模块应只依赖此类。"""

    def __init__(self, *, module_name: str = "mentor") -> None:
        self.module_name = module_name
        self.store = MemoryStore()
        self.memory_update_service = LongTermMemoryUpdateService(module_name=module_name, store=self.store)
        self.profile_builder = ProfileBuildingService(module_name=module_name, store=self.store)

    # ------------------------------------------------------------------
    # 会话管理
    # ------------------------------------------------------------------

    async def create_session(self, *, user_id: int, title: str = "新对话") -> ChatSession:
        return await self.store.create_chat_session(user_id=user_id, module=self.module_name, title=title)

    async def get_session(self, *, session_id: str) -> ChatSession | None:
        return await self.store.get_chat_session(session_id)

    async def list_sessions(self, *, user_id: int, limit: int = 20) -> list[ChatSession]:
        return await self.store.get_user_chat_sessions(user_id=user_id, module=self.module_name, limit=limit)

    async def archive_session(self, *, user_id: int, session_id: str) -> bool:
        return await self.store.archive_chat_session(session_id=session_id, user_id=user_id)

    # ------------------------------------------------------------------
    # 短期记忆（消息）
    # ------------------------------------------------------------------

    async def save_message(
        self,
        *,
        user_id: int,
        session_id: str,
        role: str,
        content: str,
        attachments: str | None = None,
        tool_calls: str | None = None,
        diagram: dict | None = None,
    ) -> int:
        return await self.store.save_message(
            user_id=user_id,
            session_id=session_id,
            module=self.module_name,
            role=role,
            content=content,
            attachments=attachments,
            tool_calls=tool_calls,
            diagram=diagram,
        )

    async def list_short_term_messages(
        self,
        *,
        user_id: int,
        session_id: str,
        limit: int | None = None,
        days: int = 7,
        only_unexpired: bool = True,
    ) -> list[ChatMessage]:
        return await self.store.get_recent_messages(
            user_id=user_id,
            session_id=session_id,
            module=self.module_name,
            limit=limit,
            days=days,
            only_unexpired=only_unexpired,
        )

    async def count_short_term_messages(self, *, user_id: int, session_id: str) -> int:
        return await self.store.get_message_count(user_id=user_id, session_id=session_id, module=self.module_name)

    # ------------------------------------------------------------------
    # 会话概要
    # ------------------------------------------------------------------

    async def get_session_summaries(
        self,
        *,
        user_id: int,
        session_id: str,
        limit: int = 3,
    ) -> list[ChatSessionSummary]:
        return await self.store.list_session_summaries(user_id, session_id, self.module_name, limit)

    async def get_latest_session_summary(
        self,
        *,
        user_id: int,
        session_id: str,
    ) -> ChatSessionSummary | None:
        return await self.store.get_latest_session_summary(user_id, session_id, self.module_name)

    # ------------------------------------------------------------------
    # 长期记忆（用户级单条）
    # ------------------------------------------------------------------

    async def get_long_term_memory(self, *, user_id: int) -> UserLongTermMemory | None:
        return await self.store.get_long_term_memory(user_id, self.module_name)

    async def get_or_create_long_term_memory(self, *, user_id: int) -> UserLongTermMemory:
        return await self.store.get_or_create_long_term_memory(user_id, self.module_name)

    # ------------------------------------------------------------------
    # 用户画像
    # ------------------------------------------------------------------

    async def get_profile(self, *, user_id: int) -> UserProfile | None:
        return await self.store.get_user_profile(user_id, self.module_name)

    async def get_or_create_profile(self, *, user_id: int) -> UserProfile:
        return await self.store.get_or_create_user_profile(user_id, self.module_name)

    async def list_profile_history(self, *, user_id: int, limit: int = 20) -> list[UserProfileHistory]:
        return await self.store.get_profile_history(user_id, self.module_name, limit)

    async def build_profile(self, *, user_id: int, session_id: str | None = None) -> bool:
        success, _ = await self.profile_builder.build_profile(user_id=user_id, session_id=session_id)
        return success

    # ------------------------------------------------------------------
    # 上下文构建
    # ------------------------------------------------------------------

    async def build_profile_context(self, user_id: int) -> str:
        profile = await self.get_profile(user_id=user_id)
        if not profile:
            return "暂无画像信息（新用户），请直接开始对话。"
        if profile.profile_markdown:
            return profile.profile_markdown
        if profile.profile_json and profile.profile_json.get("dimensions"):
            return render_profile_markdown(profile.profile_json)
        return "暂无画像信息（新用户），请直接开始对话。"

    async def build_long_term_memory_context(self, user_id: int) -> str:
        memory = await self.get_long_term_memory(user_id=user_id)
        if not memory:
            return "暂无长期记忆。"
        if memory.memory_json:
            return render_long_term_memory_markdown(memory.memory_json)
        return memory.memory_markdown or "暂无长期记忆。"

    def build_file_context(self, image_urls: list[str], file_urls: list[str]) -> str:
        """构建文件/图片附件上下文。

        Args:
            image_urls: 图片URL列表。
            file_urls: 文件URL列表。

        Returns:
            格式化的附件信息字符串。
        """
        if not image_urls and not file_urls:
            return "本次对话无上传文件。"

        lines = []
        if image_urls:
            lines.append(f"图片附件（{len(image_urls)}个）：")
            for url in image_urls:
                filename = url.split("/")[-1]
                lines.append(f"  - {filename}")

        if file_urls:
            lines.append(f"文档附件（{len(file_urls)}个）：")
            for url in file_urls:
                filename = url.split("/")[-1]
                lines.append(f"  - {filename}")

        return "\n".join(lines)

    async def build_session_summary_context(self, user_id: int, session_id: str) -> str:
        summaries = await self.get_session_summaries(user_id=user_id, session_id=session_id, limit=2)
        if not summaries:
            return "暂无会话概要。"
        chunks = []
        for summary in summaries:
            if summary.summary_json:
                chunks.append(render_session_summary_markdown(summary.summary_json))
            else:
                chunks.append(summary.summary_markdown)
        return "\n\n---\n\n".join(chunks)

    async def build_tutor_context(
        self,
        *,
        user_id: int,
        session_id: str,
        recent_limit: int = 10,
    ) -> str:
        profile_context = await self.build_profile_context(user_id)
        memory_context = await self.build_long_term_memory_context(user_id)
        summary_context = await self.build_session_summary_context(user_id, session_id)
        recent_msgs = await self.list_short_term_messages(user_id=user_id, session_id=session_id, limit=recent_limit)
        recent_lines = [
            f"- {msg.role}: {msg.content[:200]}..."
            if len(msg.content) > 200 else f"- {msg.role}: {msg.content}"
            for msg in recent_msgs
            if msg.role in {"user", "assistant"} and msg.content.strip()
        ]
        recent_context = "\n".join(recent_lines) if recent_lines else "暂无最近对话。"
        return "\n\n".join([
            f"# 用户画像\n{profile_context}",
            f"# 用户长期记忆\n{memory_context}",
            f"# 当前会话概要\n{summary_context}",
            f"# 最近对话\n{recent_context}",
        ])

    async def build_recent_chat_context(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str,
        image_urls: list[str] | None = None,
        file_urls: list[str] | None = None,
    ) -> tuple[list[AnyMessage], str]:
        initial_messages: list[AnyMessage] = []
        recent_lines: list[str] = []
        recent_msgs = await self.list_short_term_messages(user_id=user_id, session_id=session_id, limit=10)
        for msg in recent_msgs[:-1]:
            if msg.role == "user":
                initial_messages.append(HumanMessage(content=msg.content))
                recent_lines.append(f"- 用户: {msg.content}")
            elif msg.role == "assistant":
                initial_messages.append(AIMessage(content=msg.content))
                recent_lines.append(f"- 助手: {msg.content}")
        content = user_message
        if image_urls:
            content += f"\n[Attached Images: {', '.join(image_urls)}]"
        if file_urls:
            content += f"\n[Attached Files: {', '.join(file_urls)}]"
        initial_messages.append(HumanMessage(content=content))
        recent_context = "\n".join(recent_lines) if recent_lines else "最近 7 天暂无历史对话。"
        return initial_messages, recent_context

    async def build_context_preview(self, *, user_id: int, session_id: str, recent_limit: int = 10) -> str:
        return await self.build_tutor_context(user_id=user_id, session_id=session_id, recent_limit=recent_limit)

    # ------------------------------------------------------------------
    # 后处理流水线
    # ------------------------------------------------------------------

    async def post_turn_pipeline(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str,
        assistant_reply: str,
    ) -> None:
        await self.store.accumulate_session_tokens(
            user_id=user_id,
            session_id=session_id,
            module=self.module_name,
            content=f"{user_message}\n{assistant_reply}",
        )

        should_create_summary = await self.store.should_create_session_summary(
            user_id=user_id,
            session_id=session_id,
            module=self.module_name,
            threshold=SESSION_SUMMARY_TOKEN_THRESHOLD,
        )
        if should_create_summary:
            await self._create_session_summary(user_id, session_id)
            await self.store.reset_session_token_count(user_id, session_id, self.module_name)

        memory_updated = await self.memory_update_service.update_long_term_memory(
            user_id=user_id,
            session_id=session_id,
            user_message=user_message,
            assistant_reply=assistant_reply,
        )

        recent_msgs = await self.list_short_term_messages(user_id=user_id, session_id=session_id, limit=80)
        assistant_turns = sum(1 for msg in recent_msgs if msg.role == "assistant")
        if assistant_turns and assistant_turns % PROFILE_GATE_EVERY_N_ASSISTANT_TURNS == 0:
            success, updated = await self.profile_builder.build_profile(user_id=user_id, session_id=session_id)
            if success and updated:
                logger.info("[MemoryLayer] 画像已更新 user_id=%s session_id=%s", user_id, session_id)

    async def _create_session_summary(self, user_id: int, session_id: str) -> None:
        recent_msgs = await self.list_short_term_messages(user_id=user_id, session_id=session_id, limit=50)
        if not recent_msgs:
            return
        dialogue_msgs = [msg for msg in recent_msgs if msg.role in {"user", "assistant"} and msg.content.strip()]
        if not dialogue_msgs:
            return
        chat_text = "\n".join(
            f"[{msg.created_at.strftime('%m-%d %H:%M')}] {msg.role}: {msg.content[:500]}"
            for msg in dialogue_msgs
        )
        summary_markdown = f"# 会话概要\n\n## 最近对话\n\n{chat_text[:3000]}"
        await self.store.create_session_summary(
            user_id=user_id,
            session_id=session_id,
            module=self.module_name,
            summary_markdown=summary_markdown,
            summary_json=None,
            summarized_message_count=len(dialogue_msgs),
        )


class PostChatMemoryOrchestrator:
    """对话后处理流水线包装器 — 提供向后兼容的入口。"""

    def __init__(self, *, module_name: str = "mentor") -> None:
        self.layer = MemoryLayer(module_name=module_name)

    async def run(self, *, user_id: int, session_id: str, user_message: str, assistant_reply: str) -> None:
        await self.layer.post_turn_pipeline(
            user_id=user_id,
            session_id=session_id,
            user_message=user_message,
            assistant_reply=assistant_reply,
        )
