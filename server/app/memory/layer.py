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

import json
from typing import Any

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage

from app.config import PROFILE_GATE_EVERY_N_ASSISTANT_TURNS
from app.infra.logging import get_logger
from app.infra.models import ChatMessage, ChatSession, ChatSessionSummary, UserLongTermMemory, UserProfile, UserProfileHistory
from app.memory._fact import LongTermMemoryUpdateService
from app.memory._policy import (
    RECENT_CHAT_MESSAGE_LIMIT,
    SUMMARY_CHAR_BUDGET,
    render_priority_long_term_memory,
    render_recent_chat_context,
    select_recent_chat_messages,
    should_include_session_summary,
    truncate_text,
)
from app.memory._profile import (
    ProfileBuilder,
    build_onboarding_profile,
    build_score_json,
    is_onboarding_complete,
    normalize_onboarding,
)
from app.memory._store import MemoryStore, SESSION_SUMMARY_TOKEN_THRESHOLD
from app.memory.memory_types import render_session_summary_markdown

logger = get_logger(__name__)


class MemoryLayer:
    """记忆层公共 API — 外部模块应只依赖此类。"""

    def __init__(self, *, module: str = "mentor") -> None:
        self.module = module
        self.store = MemoryStore()
        self.memory_updater = LongTermMemoryUpdateService(module_name=module, store=self.store)
        self.profile_builder = ProfileBuilder(module=module, store=self.store)

    # ------------------------------------------------------------------
    # 会话管理
    # ------------------------------------------------------------------

    async def create_session(self, *, user_id: int, title: str = "新对话") -> ChatSession:
        return await self.store.create_chat_session(user_id=user_id, module=self.module, title=title)

    async def get_session(self, *, session_id: str) -> ChatSession | None:
        return await self.store.get_chat_session(session_id)

    async def list_sessions(self, *, user_id: int, limit: int = 20) -> list[ChatSession]:
        return await self.store.get_user_chat_sessions(user_id=user_id, module=self.module, limit=limit)

    async def archive_session(self, *, user_id: int, session_id: str) -> bool:
        return await self.store.archive_chat_session(session_id=session_id, user_id=user_id)

    async def update_session_title(self, *, user_id: int, session_id: str, title: str) -> bool:
        return await self.store.update_chat_session_title(session_id=session_id, user_id=user_id, title=title)

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
            module=self.module,
            role=role,
            content=content,
            attachments=attachments,
            tool_calls=tool_calls,
            diagram=diagram,
        )

    async def list_messages(
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
            module=self.module,
            limit=limit,
            days=days,
            only_unexpired=only_unexpired,
        )

    async def count_messages(self, *, user_id: int, session_id: str) -> int:
        return await self.store.get_message_count(user_id=user_id, session_id=session_id, module=self.module)

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
        return await self.store.list_session_summaries(user_id, session_id, self.module, limit)

    async def get_latest_session_summary(
        self,
        *,
        user_id: int,
        session_id: str,
    ) -> ChatSessionSummary | None:
        return await self.store.get_latest_session_summary(user_id, session_id, self.module)

    # ------------------------------------------------------------------
    # 长期记忆（用户级单条）
    # ------------------------------------------------------------------

    async def get_long_term_memory(self, *, user_id: int) -> UserLongTermMemory | None:
        return await self.store.get_long_term_memory(user_id, self.module)

    async def get_or_create_long_term_memory(self, *, user_id: int) -> UserLongTermMemory:
        return await self.store.get_or_create_long_term_memory(user_id, self.module)

    # ------------------------------------------------------------------
    # 用户画像
    # ------------------------------------------------------------------

    async def get_profile(self, *, user_id: int) -> UserProfile | None:
        return await self.store.get_user_profile(user_id, self.module)

    async def get_or_create_profile(self, *, user_id: int) -> UserProfile:
        return await self.store.get_or_create_user_profile(user_id, self.module)

    async def list_profile_history(self, *, user_id: int, limit: int = 20) -> list[UserProfileHistory]:
        return await self.store.get_profile_history(user_id, self.module, limit)

    async def build_profile(self, *, user_id: int, session_id: str | None = None) -> bool:
        success, _ = await self.profile_builder.build(user_id=user_id, session_id=session_id)
        return success

    async def get_onboarding(self, *, user_id: int) -> dict[str, Any]:
        """获取首次登录表单数据。"""
        profile = await self.get_profile(user_id=user_id)
        profile_json = profile.profile_json if profile and profile.profile_json else {}
        student = normalize_onboarding(profile_json.get("student_profile"))
        return {
            "student_profile": student,
            "profile_initialized": is_onboarding_complete(student),
        }

    async def update_onboarding(self, *, user_id: int, student_profile: dict[str, Any]) -> UserProfile:
        """更新首次登录表单数据。"""
        normalized = normalize_onboarding(student_profile)
        old = await self.get_profile(user_id=user_id)
        old_json = old.profile_json if old and old.profile_json else None
        profile_json = build_onboarding_profile(normalized, old_json)
        score_json = build_score_json(profile_json)
        return await self.store.update_user_profile(
            user_id=user_id,
            module=self.module,
            profile_json=profile_json,
            profile_score_json=score_json,
            updated_reason="基于首次登录学习资料初始化画像",
            confidence=score_json["confidence"],
        )

    # ------------------------------------------------------------------
    # 上下文构建
    # ------------------------------------------------------------------

    async def build_profile_context(self, user_id: int) -> str:
        """构建画像上下文，用于 Agent 系统提示词。"""
        profile = await self.get_profile(user_id=user_id)
        if not profile:
            return "暂无画像信息（新用户），请直接开始对话。"
        if profile.profile_json and profile.profile_json.get("dimensions"):
            return json.dumps(profile.profile_json, ensure_ascii=False, indent=2)
        return "暂无画像信息（新用户），请直接开始对话。"

    async def build_memory_context(self, user_id: int) -> str:
        """构建长期记忆上下文。"""
        memory = await self.get_long_term_memory(user_id=user_id)
        if not memory:
            return "暂无长期记忆。"
        if memory.memory_json:
            return render_priority_long_term_memory(memory.memory_json)
        if memory.memory_markdown:
            return truncate_text(memory.memory_markdown, 1600)
        return "暂无长期记忆。"

    def build_file_context(self, image_urls: list[str], file_urls: list[str]) -> str:
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

    async def build_session_summary_context(self, user_id: int, session_id: str) -> str:
        """构建会话概要上下文。"""
        summaries = await self.get_session_summaries(user_id=user_id, session_id=session_id, limit=2)
        if not summaries:
            return "暂无会话概要。"
        chunks = []
        for s in summaries:
            chunks.append(render_session_summary_markdown(s.summary_json) if s.summary_json else s.summary_markdown)
        return "\n\n---\n\n".join(chunks)

    async def build_tutor_context(
        self,
        *,
        user_id: int,
        session_id: str,
        recent_limit: int = 10,
    ) -> str:
        """构建完整辅导上下文（画像 + 长期记忆 + 最近对话）。"""
        profile_ctx = await self.build_profile_context(user_id)
        memory_ctx = await self.build_memory_context(user_id)
        msgs = await self.list_messages(user_id=user_id, session_id=session_id, limit=recent_limit)
        recent_lines = [
            f"- {m.role}: {m.content[:200]}..." if len(m.content) > 200 else f"- {m.role}: {m.content}"
            for m in msgs
            if m.role in {"user", "assistant"} and m.content.strip()
        ]
        recent_ctx = "\n".join(recent_lines) or "暂无最近对话。"
        return f"# 用户画像\n{profile_ctx}\n\n# 用户长期记忆\n{memory_ctx}\n\n# 最近对话\n{recent_ctx}"

    async def build_recent_chat_context(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str,
        image_urls: list[str] | None = None,
        file_urls: list[str] | None = None,
    ) -> tuple[list[AnyMessage], str]:
        """构建近期对话上下文，返回消息列表和文本描述。"""
        messages: list[AnyMessage] = []
        msgs = await self.list_messages(user_id=user_id, session_id=session_id, limit=RECENT_CHAT_MESSAGE_LIMIT)
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
                recent_ctx = f"# 会话概要\n{truncate_text(summary_ctx, SUMMARY_CHAR_BUDGET)}\n\n# 最近对话\n{recent_ctx}"
        return messages, recent_ctx

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
        enable_long_term_memory: bool = True,
    ) -> None:
        """对话后处理：累加 token、生成概要、更新长期记忆、构建画像。"""
        # 累加 token
        await self.store.accumulate_session_tokens(
            user_id=user_id,
            session_id=session_id,
            module=self.module,
            content=f"{user_message}\n{assistant_reply}",
        )

        # 生成会话概要
        if await self.store.should_create_session_summary(user_id, session_id, self.module, SESSION_SUMMARY_TOKEN_THRESHOLD):
            await self._create_session_summary(user_id, session_id)
            await self.store.reset_session_token_count(user_id, session_id, self.module)

        # 更新长期记忆
        if enable_long_term_memory:
            await self.memory_updater.update_long_term_memory(
                user_id=user_id,
                session_id=session_id,
                user_message=user_message,
                assistant_reply=assistant_reply,
            )

        # 构建画像（每 N 轮触发）
        msgs = await self.list_messages(user_id=user_id, session_id=session_id, limit=80)
        assistant_turns = sum(1 for m in msgs if m.role == "assistant")
        logger.info(
            "[MemoryLayer] 画像检查 user=%s session=%s turns=%s gate=%s",
            user_id, session_id, assistant_turns, PROFILE_GATE_EVERY_N_ASSISTANT_TURNS,
        )
        if assistant_turns and assistant_turns % PROFILE_GATE_EVERY_N_ASSISTANT_TURNS == 0:
            logger.info("[MemoryLayer] 触发画像构建 user=%s session=%s", user_id, session_id)
            success, updated = await self.profile_builder.build(user_id=user_id, session_id=session_id)
            if success and updated:
                logger.info("[MemoryLayer] 画像已更新 user=%s", user_id)
            elif success:
                logger.info("[MemoryLayer] 画像无变化 user=%s", user_id)
            else:
                logger.warning("[MemoryLayer] 画像构建失败 user=%s", user_id)

    async def _create_session_summary(self, user_id: int, session_id: str) -> None:
        """创建会话概要。"""
        msgs = await self.list_messages(user_id=user_id, session_id=session_id, limit=50)
        dialogue = [m for m in msgs if m.role in {"user", "assistant"} and m.content.strip()]
        if not dialogue:
            return
        chat_text = "\n".join(f"[{m.created_at.strftime('%m-%d %H:%M')}] {m.role}: {m.content[:500]}" for m in dialogue)
        await self.store.create_session_summary(
            user_id=user_id,
            session_id=session_id,
            module=self.module,
            summary_markdown=f"# 会话概要\n\n## 最近对话\n\n{chat_text[:3000]}",
            summary_json=None,
            summarized_message_count=len(dialogue),
        )


class PostChatPipeline:
    """对话后处理流水线入口。"""

    def __init__(self, *, module: str = "mentor") -> None:
        self.layer = MemoryLayer(module=module)

    async def run(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str,
        assistant_reply: str,
        enable_long_term_memory: bool = True,
    ) -> None:
        await self.layer.post_turn_pipeline(
            user_id=user_id,
            session_id=session_id,
            user_message=user_message,
            assistant_reply=assistant_reply,
            enable_long_term_memory=enable_long_term_memory,
        )


# 向后兼容别名
PostChatMemoryOrchestrator = PostChatPipeline
