"""会话压缩。"""

from __future__ import annotations

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.memory.store import MemoryStore
from app.memory.types import (
    DIALOGUE_ROLES,
    SUMMARY_KEEP_RECENT,
    SUMMARY_MESSAGE_THRESHOLD,
    SUMMARY_TOKEN_THRESHOLD,
    extract_fallback_summary_markdown,
)
from app.prompts import registry

logger = get_logger(__name__)


class SessionCompressor:
    """按触发条件把旧消息压缩为 Markdown 概要。"""

    def __init__(self, *, module: str = "mentor", store: MemoryStore | None = None) -> None:
        self.module = module
        self.store = store or MemoryStore()
        self.llm = get_llm()

    async def maybe_compress(
        self,
        *,
        user_id: int,
        session_id: str,
        keep_recent: int = SUMMARY_KEEP_RECENT,
        force: bool = False,
        reason: str = "post_turn",
    ):
        should_compress = force or await self.should_compress(user_id=user_id, session_id=session_id)
        if not should_compress:
            return None
        return await self.compress(user_id=user_id, session_id=session_id, keep_recent=keep_recent, reason=reason)

    async def should_compress(self, *, user_id: int, session_id: str) -> bool:
        token_count = await self.store.get_session_token_count(session_id)
        if token_count >= SUMMARY_TOKEN_THRESHOLD:
            return True
        message_count = await self.store.count_messages(user_id=user_id, session_id=session_id, module=self.module)
        return message_count > SUMMARY_MESSAGE_THRESHOLD

    async def compress(self, *, user_id: int, session_id: str, keep_recent: int = SUMMARY_KEEP_RECENT, reason: str = "manual"):
        messages = await self.store.list_messages(user_id=user_id, session_id=session_id, module=self.module, limit=None, only_unexpired=False)
        dialogue = [msg for msg in messages if msg.role in DIALOGUE_ROLES and str(msg.content or "").strip()]
        if len(dialogue) <= keep_recent:
            return None

        target = dialogue[:-keep_recent] if keep_recent > 0 else dialogue
        if not target:
            return None

        chat_text = "\n".join(f"[{msg.created_at:%m-%d %H:%M}] {msg.role}: {msg.content[:500]}" for msg in target)
        summary_markdown = None
        try:
            prompt = registry.render("memory/compression", dialogue_text=chat_text[:5000])
            logger.info("[MemoryCompression] LLM 开始会话压缩。")

            from langchain_core.messages import HumanMessage, SystemMessage

            resp = await self.llm.ainvoke(
                [SystemMessage(content=prompt), HumanMessage(content="请根据以上对话记录输出会话摘要 Markdown。")],
                temperature=0.1,
            )
            summary_markdown = str(resp.content or "").strip()
        except Exception as exc:
            logger.warning("[MemoryCompression] LLM 压缩失败，降级启发式提取: %s", exc)

        if not summary_markdown or not summary_markdown.strip():
            summary_markdown = extract_fallback_summary_markdown(chat_text)

        summary = await self.store.create_summary(
            user_id=user_id,
            session_id=session_id,
            module=self.module,
            summary_markdown=summary_markdown,
            summarized_message_count=len(target),
            start_message_id=target[0].id,
            end_message_id=target[-1].id,
        )
        first_kept = dialogue[-keep_recent].id if keep_recent > 0 else (target[-1].id + 1 if target[-1].id else 0)
        if first_kept:
            await self.store.delete_messages_before(user_id=user_id, session_id=session_id, module=self.module, before_message_id=first_kept)
        await self.store.reset_session_token_count(session_id)
        return summary
