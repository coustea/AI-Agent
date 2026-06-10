"""Chat-private long-term memory extraction."""

from __future__ import annotations

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.chat.memory.prompt_manager import chat_memory_prompts
from app.chat.memory.types import (
    MemoryUpdateOutput,
    has_stable_signal,
    make_default_memory_markdown,
    now,
)
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.models import ChatLongTermMemory, ChatSessionSummaryBlock

logger = get_logger(__name__)


class ChatLongTermMemoryService:
    """Extract and update stable cross-session chat memory."""

    def __init__(
        self,
        *,
        module: str = "mentor",
        periodic_turns: int = 8,
        min_confidence: float = 0.75,
        cooldown_minutes: int = 30,
    ) -> None:
        self.module = module
        self.periodic_turns = periodic_turns
        self.min_confidence = min_confidence
        self.cooldown_seconds = cooldown_minutes * 60
        self.llm = get_llm()

    def should_consider_update(
        self,
        *,
        user_message: str,
        assistant_reply: str,
    ) -> bool:
        if has_stable_signal(user_message):
            return True
        return has_stable_signal(assistant_reply) and any(
            keyword in assistant_reply for keyword in ("以后", "下次", "记住", "偏好", "纠正")
        )

    async def maybe_update(
        self,
        *,
        db: AsyncSession,
        user_id: int,
        session_id: str,
        user_message: str,
        assistant_reply: str,
        turn_count: int = 0,
    ) -> bool:
        signal_detected = self.should_consider_update(
            user_message=user_message,
            assistant_reply=assistant_reply,
        )
        periodic_trigger = turn_count > 0 and turn_count % self.periodic_turns == 0
        if not signal_detected and not periodic_trigger:
            return False

        existing = (
            await db.exec(
                select(ChatLongTermMemory).where(
                    ChatLongTermMemory.user_id == user_id,
                    ChatLongTermMemory.module == self.module,
                )
            )
        ).first()

        if existing:
            old_memory = existing
        else:
            old_memory = ChatLongTermMemory(
                user_id=user_id,
                module=self.module,
                memory_markdown=make_default_memory_markdown(),
                category="general",
            )
            db.add(old_memory)
            await db.flush()

        if (
            not signal_detected
            and periodic_trigger
            and old_memory.updated_at
            and (now() - old_memory.updated_at).total_seconds() < self.cooldown_seconds
        ):
            return False

        latest_summary_block = (
            await db.exec(
                select(ChatSessionSummaryBlock)
                .where(
                    ChatSessionSummaryBlock.user_id == user_id,
                    ChatSessionSummaryBlock.session_id == session_id,
                    ChatSessionSummaryBlock.module == self.module,
                )
                .order_by(ChatSessionSummaryBlock.created_at.desc())
                .limit(1)
            )
        ).first()

        prompt = chat_memory_prompts.render_ltm_update(
            user_message=user_message[:1000],
            assistant_reply=assistant_reply[:1000],
            session_summary=latest_summary_block.summary_markdown if latest_summary_block else "暂无会话概要。",
            old_memory=old_memory.memory_markdown if old_memory else "暂无长期记忆。",
        )

        resp = await self.llm.ainvoke_json(
            MemoryUpdateOutput,
            prompt,
            function_name="update_chat_long_term_memory",
            function_description="判断是否需要更新 chat 长期记忆，如需更新返回新的记忆 Markdown。",
            temperature=0.1,
        )

        if not resp.need_update or not resp.memory_markdown:
            return False
        if getattr(resp, "confidence", self.min_confidence) < self.min_confidence:
            return False

        memory = existing or old_memory
        memory.version = (memory.version or 1) + (1 if existing else 0)
        memory.memory_markdown = resp.memory_markdown
        memory.category = "general"
        memory.updated_reason = "signal" if signal_detected else "periodic"
        memory.source_session_ids = [session_id]
        memory.source_summary_block_ids = [latest_summary_block.id] if latest_summary_block and latest_summary_block.id else None
        memory.updated_at = now()
        db.add(memory)
        return True
