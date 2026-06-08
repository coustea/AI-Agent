"""会话压缩。"""

from __future__ import annotations

from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.models import ChatMessage, ChatSession, ChatSessionSummary
from app.memory.prompt_manager import memory_prompts
from app.memory.types import (
    DIALOGUE_ROLES,
    SUMMARY_KEEP_RECENT,
    SUMMARY_MESSAGE_THRESHOLD,
    SUMMARY_TOKEN_THRESHOLD,
    extract_fallback_summary_markdown,
)

logger = get_logger(__name__)


class SessionCompressor:
    """会话压缩器：将短期对话历史压缩为摘要。"""

    def __init__(self, *, module: str = "mentor") -> None:
        """初始化压缩器，指定模块名。"""
        self.module = module
        self.llm = get_llm()

    async def maybe_compress(
        self,
        *,
        db: AsyncSession,
        user_id: int,
        session_id: str,
        keep_recent: int = SUMMARY_KEEP_RECENT,
        force: bool = False,
        reason: str = "post_turn",
    ):
        """按条件触发压缩，force=True 时强制执行。"""
        should_compress = force or await self._should_compress(db=db, user_id=user_id, session_id=session_id)
        if not should_compress:
            return None
        return await self._compress(db=db, user_id=user_id, session_id=session_id, keep_recent=keep_recent, reason=reason)

    async def _should_compress(self, *, db: AsyncSession, user_id: int, session_id: str) -> bool:
        """判断是否需要压缩：token 数或消息数超过阈值。"""
        chat_session = (await db.exec(select(ChatSession).where(ChatSession.id == session_id))).first()
        token_count = chat_session.summary_token_count if chat_session else 0
        if token_count >= SUMMARY_TOKEN_THRESHOLD:
            return True
        count_result = (
            await db.exec(
                select(func.count()).where(
                    ChatMessage.user_id == user_id,
                    ChatMessage.session_id == session_id,
                    ChatMessage.module == self.module,
                )
            )
        ).one()
        return count_result > SUMMARY_MESSAGE_THRESHOLD

    async def _compress(self, *, db: AsyncSession, user_id: int, session_id: str, keep_recent: int = SUMMARY_KEEP_RECENT, reason: str = "manual"):
        """执行压缩：LLM 生成摘要 → 保存 → 删除已压缩的旧消息。"""
        filters = [
            ChatMessage.user_id == user_id,
            ChatMessage.session_id == session_id,
            ChatMessage.module == self.module,
        ]
        messages = list((await db.exec(select(ChatMessage).where(*filters).order_by(ChatMessage.created_at.asc()))).all())
        dialogue = [msg for msg in messages if msg.role in DIALOGUE_ROLES and str(msg.content or "").strip()]
        if len(dialogue) <= keep_recent:
            return None

        target = dialogue[:-keep_recent] if keep_recent > 0 else dialogue
        if not target:
            return None

        chat_text = "\n".join(f"[{msg.created_at:%m-%d %H:%M}] {msg.role}: {msg.content[:500]}" for msg in target)
        summary_markdown = None
        try:
            prompt = memory_prompts.render_compression(dialogue_text=chat_text[:5000])
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

        summary = ChatSessionSummary(
            user_id=user_id,
            session_id=session_id,
            module=self.module,
            summary_markdown=summary_markdown,
            summarized_message_count=len(target),
            start_message_id=target[0].id,
            end_message_id=target[-1].id,
        )
        db.add(summary)
        await db.flush()

        first_kept = dialogue[-keep_recent].id if keep_recent > 0 else (target[-1].id + 1 if target[-1].id else 0)
        if first_kept:
            stale_messages = list(
                (await db.exec(
                    select(ChatMessage).where(
                        ChatMessage.user_id == user_id,
                        ChatMessage.session_id == session_id,
                        ChatMessage.module == self.module,
                        ChatMessage.id < first_kept,
                    )
                )).all()
            )
            for msg in stale_messages:
                await db.delete(msg)

        chat_session = (await db.exec(select(ChatSession).where(ChatSession.id == session_id))).first()
        if chat_session:
            chat_session.summary_token_count = 0
            db.add(chat_session)
        return summary
