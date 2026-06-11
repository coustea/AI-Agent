"""Chat 会话压缩 — 将旧消息压缩为时序摘要块。

触发条件：token 数 ≥ min_tokens 或消息数 ≥ min_messages（满足其一即可）。
压缩策略：保留最近 keep_recent 条原始消息，其余通过 LLM 生成 Markdown 摘要。
LLM 失败时降级为 extract_fallback_summary_markdown（取前 N 行拼接）。
压缩后物理删除已摘要的旧消息，重置 summary_token_count 计数器。
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.prompts import prompts
from app.chat.memory.types import DIALOGUE_ROLES, extract_fallback_summary_markdown
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.models import ChatMessage, ChatSession, ChatSessionSummaryBlock

logger = get_logger(__name__)


class ChatSessionCompressor:
    """Compress old raw messages into chronological summary blocks."""

    def __init__(
        self,
        *,
        module: str = "mentor",
        keep_recent: int = 8,
        min_messages: int = 14,
        min_tokens: int = 3500,
    ) -> None:
        self.module = module
        self.keep_recent = keep_recent
        self.min_messages = min_messages
        self.min_tokens = min_tokens
        self.llm = get_llm()

    async def maybe_compress(
        self,
        *,
        db: AsyncSession,
        user_id: int,
        session_id: str,
        force: bool = False,
        reason: str = "post_turn",
    ):
        should_compress = force or await self._should_compress(
            db=db,
            user_id=user_id,
            session_id=session_id,
        )
        if not should_compress:
            return None
        return await self._compress(
            db=db,
            user_id=user_id,
            session_id=session_id,
            reason=reason,
        )

    async def _should_compress(self, *, db: AsyncSession, user_id: int, session_id: str) -> bool:
        chat_session = (await db.exec(select(ChatSession).where(ChatSession.id == session_id))).first()
        token_count = chat_session.summary_token_count if chat_session else 0
        if token_count >= self.min_tokens:
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
        return count_result >= self.min_messages

    async def _compress(
        self,
        *,
        db: AsyncSession,
        user_id: int,
        session_id: str,
        reason: str = "manual",
    ):
        filters = [
            ChatMessage.user_id == user_id,
            ChatMessage.session_id == session_id,
            ChatMessage.module == self.module,
        ]
        messages = list((await db.exec(select(ChatMessage).where(*filters).order_by(ChatMessage.created_at.asc()))).all())
        dialogue = [msg for msg in messages if msg.role in DIALOGUE_ROLES and str(msg.content or "").strip()]
        if len(dialogue) <= self.keep_recent:
            return None

        target = dialogue[:-self.keep_recent] if self.keep_recent > 0 else dialogue
        if not target:
            return None

        chat_text = "\n".join(
            f"[{msg.created_at:%m-%d %H:%M}] {msg.role}: {msg.content[:500]}"
            for msg in target
        )

        summary_markdown = None
        try:
            prompt = prompts.get("chat_memory").render("compression", dialogue_text=chat_text[:5000])

            resp = await self.llm.ainvoke(
                [
                    SystemMessage(content=prompt),
                    HumanMessage(content="请根据以上对话记录输出会话摘要 Markdown。"),
                ],
                temperature=0.1,
            )
            summary_markdown = str(resp.content or "").strip()
        except Exception as exc:
            logger.warning("[ChatMemoryCompression] LLM compression failed: %s", exc)

        if not summary_markdown or not summary_markdown.strip():
            summary_markdown = extract_fallback_summary_markdown(chat_text)

        latest_block = (
            await db.exec(
                select(ChatSessionSummaryBlock)
                .where(
                    ChatSessionSummaryBlock.user_id == user_id,
                    ChatSessionSummaryBlock.session_id == session_id,
                    ChatSessionSummaryBlock.module == self.module,
                )
                .order_by(ChatSessionSummaryBlock.block_index.desc())
                .limit(1)
            )
        ).first()
        next_block_index = (latest_block.block_index if latest_block else 0) + 1

        summary_block = ChatSessionSummaryBlock(
            user_id=user_id,
            session_id=session_id,
            module=self.module,
            block_index=next_block_index,
            summary_markdown=summary_markdown,
            start_message_id=target[0].id,
            end_message_id=target[-1].id,
            start_at=target[0].created_at,
            end_at=target[-1].created_at,
            summarized_message_count=len(target),
            topics=[],
            keywords=[],
        )
        db.add(summary_block)
        await db.flush()

        first_kept = dialogue[-self.keep_recent].id if self.keep_recent > 0 else None
        if first_kept:
            stale_messages = list(
                (
                    await db.exec(
                        select(ChatMessage).where(
                            ChatMessage.user_id == user_id,
                            ChatMessage.session_id == session_id,
                            ChatMessage.module == self.module,
                            ChatMessage.id < first_kept,
                        )
                    )
                ).all()
            )
            for msg in stale_messages:
                await db.delete(msg)

        chat_session = (await db.exec(select(ChatSession).where(ChatSession.id == session_id))).first()
        if chat_session:
            chat_session.summary_token_count = 0
            db.add(chat_session)
        return summary_block
