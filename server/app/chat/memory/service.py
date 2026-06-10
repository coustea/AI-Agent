"""Chat-private memory orchestration."""

from __future__ import annotations

import re
from datetime import timedelta
from typing import Any

from sqlmodel import func, select

from app.chat.memory.compression import ChatSessionCompressor
from app.chat.memory.long_term import ChatLongTermMemoryService
from app.chat.memory.types import (
    DEFAULT_SESSION_TITLE,
    LTM_CATEGORY_NAMES,
    MESSAGE_EXPIRE_DAYS,
    TITLE_MAX_LENGTH,
    estimate_token_count,
    now,
)
from app.infra.database import session_scope
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.models import ChatLongTermMemory, ChatMessage, ChatSession, ChatSessionSummaryBlock
from app.profile.service import get_profile_service

logger = get_logger(__name__)

RECENT_RAW_MESSAGES = 8
COMPRESS_MIN_MESSAGES = 14
COMPRESS_MIN_TOKENS = 3500
SUMMARY_CONTEXT_BLOCKS = 3
LTM_PERIODIC_TURNS = 8
LTM_MIN_CONFIDENCE = 0.75
LTM_UPDATE_COOLDOWN_MINUTES = 30


class ChatMemoryService:
    """Chat-owned memory pipeline and persistence facade."""

    def __init__(self, *, module: str = "mentor") -> None:
        self.module = module
        self.profile_service = get_profile_service(module=module)
        self.compressor = ChatSessionCompressor(
            module=module,
            keep_recent=RECENT_RAW_MESSAGES,
            min_messages=COMPRESS_MIN_MESSAGES,
            min_tokens=COMPRESS_MIN_TOKENS,
        )
        self.long_term_memory = ChatLongTermMemoryService(
            module=module,
            periodic_turns=LTM_PERIODIC_TURNS,
            min_confidence=LTM_MIN_CONFIDENCE,
            cooldown_minutes=LTM_UPDATE_COOLDOWN_MINUTES,
        )
        self.llm = get_llm()

    async def create_session(self, *, user_id: int, title: str = DEFAULT_SESSION_TITLE) -> Any:
        async with session_scope() as db:
            chat_session = ChatSession(user_id=user_id, module=self.module, title=title)
            db.add(chat_session)
            await db.commit()
            await db.refresh(chat_session)
            return chat_session

    async def list_sessions(self, *, user_id: int, limit: int = 20) -> list[Any]:
        async with session_scope() as db:
            stmt = (
                select(ChatSession)
                .where(
                    ChatSession.user_id == user_id,
                    ChatSession.is_archived.is_(False),
                    ChatSession.module == self.module,
                )
                .order_by(ChatSession.updated_at.desc())
                .limit(limit)
            )
            return list((await db.exec(stmt)).all())

    async def archive_session(self, *, user_id: int, session_id: str) -> bool:
        async with session_scope() as db:
            chat_session = (
                await db.exec(
                    select(ChatSession).where(
                        ChatSession.id == session_id,
                        ChatSession.user_id == user_id,
                    )
                )
            ).first()
            if not chat_session:
                return False
            chat_session.is_archived = True
            chat_session.updated_at = now()
            db.add(chat_session)
            await db.commit()
            return True

    async def update_session_title(self, *, user_id: int, session_id: str, title: str) -> bool:
        async with session_scope() as db:
            chat_session = (
                await db.exec(
                    select(ChatSession).where(
                        ChatSession.id == session_id,
                        ChatSession.user_id == user_id,
                    )
                )
            ).first()
            if not chat_session:
                return False
            chat_session.title = title[:TITLE_MAX_LENGTH]
            chat_session.updated_at = now()
            db.add(chat_session)
            await db.commit()
            return True

    async def save_message(
        self,
        *,
        user_id: int,
        session_id: str,
        role: str,
        content: str,
        attachments: list[dict[str, Any]] | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        teaching_diagram: dict[str, Any] | None = None,
        usage_metadata: dict[str, Any] | None = None,
    ) -> None:
        async with session_scope() as db:
            chat_session = (await db.exec(select(ChatSession).where(ChatSession.id == session_id))).first()
            if chat_session:
                if chat_session.user_id != user_id or chat_session.module != self.module:
                    raise PermissionError("会话不属于当前用户或模块")
                chat_session.updated_at = now()
            else:
                chat_session = ChatSession(id=session_id, user_id=user_id, module=self.module)
            db.add(chat_session)
            db.add(
                ChatMessage(
                    user_id=user_id,
                    session_id=session_id,
                    module=self.module,
                    role=role,
                    content=content,
                    attachments=attachments,
                    tool_calls=tool_calls,
                    teaching_diagram=teaching_diagram,
                    usage_metadata=usage_metadata,
                )
            )
            await db.commit()

    async def list_messages(
        self,
        *,
        user_id: int,
        session_id: str,
        limit: int | None = None,
        only_unexpired: bool = True,
    ) -> list[Any]:
        async with session_scope() as db:
            filters = [
                ChatMessage.user_id == user_id,
                ChatMessage.session_id == session_id,
                ChatMessage.module == self.module,
            ]
            if only_unexpired:
                filters.append(ChatMessage.created_at >= now() - timedelta(days=MESSAGE_EXPIRE_DAYS))
            total = (await db.exec(select(func.count()).where(*filters))).one()
            stmt = select(ChatMessage).where(*filters).order_by(ChatMessage.created_at.asc())
            if limit is not None and limit > 0 and total > limit:
                stmt = stmt.offset(total - limit)
            return list((await db.exec(stmt)).all())

    async def count_messages(self, *, user_id: int, session_id: str) -> int:
        async with session_scope() as db:
            return (
                await db.exec(
                    select(func.count()).where(
                        ChatMessage.user_id == user_id,
                        ChatMessage.session_id == session_id,
                        ChatMessage.module == self.module,
                    )
                )
            ).one()

    async def delete_short_term_messages(self, *, user_id: int, session_id: str) -> int:
        async with session_scope() as db:
            messages = (
                await db.exec(
                    select(ChatMessage).where(
                        ChatMessage.user_id == user_id,
                        ChatMessage.session_id == session_id,
                        ChatMessage.module == self.module,
                    )
                )
            ).all()
            for message in messages:
                await db.delete(message)
            await db.commit()
            return len(messages)

    async def reset_session_counters(self, *, user_id: int, session_id: str) -> None:
        async with session_scope() as db:
            chat_session = (await db.exec(select(ChatSession).where(ChatSession.id == session_id))).first()
            if chat_session:
                chat_session.summary_token_count = 0
                db.add(chat_session)
                await db.commit()

    async def list_summary_blocks(self, *, user_id: int, session_id: str, limit: int = SUMMARY_CONTEXT_BLOCKS) -> list[Any]:
        async with session_scope() as db:
            stmt = (
                select(ChatSessionSummaryBlock)
                .where(
                    ChatSessionSummaryBlock.user_id == user_id,
                    ChatSessionSummaryBlock.session_id == session_id,
                    ChatSessionSummaryBlock.module == self.module,
                )
                .order_by(ChatSessionSummaryBlock.created_at.desc())
                .limit(limit)
            )
            return list((await db.exec(stmt)).all())

    async def get_session_summary_context(self, *, user_id: int, session_id: str) -> str:
        blocks = await self.list_summary_blocks(user_id=user_id, session_id=session_id, limit=SUMMARY_CONTEXT_BLOCKS)
        if not blocks:
            return "暂无会话概要。"
        return "\n\n---\n\n".join(
            block.summary_markdown
            for block in reversed(blocks)
            if block.summary_markdown
        ) or "暂无会话概要。"

    async def get_long_term_memory(self, *, user_id: int) -> Any:
        async with session_scope() as db:
            return (
                await db.exec(
                    select(ChatLongTermMemory).where(
                        ChatLongTermMemory.user_id == user_id,
                        ChatLongTermMemory.module == self.module,
                    )
                )
            ).first()

    async def get_memory_markdown(self, user_id: int, category: str | None = None) -> str:
        async with session_scope() as db:
            memory = (
                await db.exec(
                    select(ChatLongTermMemory).where(
                        ChatLongTermMemory.user_id == user_id,
                        ChatLongTermMemory.module == self.module,
                    )
                )
            ).first()
            if not memory or not memory.memory_markdown:
                return "暂无长期记忆。"

            if category:
                target_title = LTM_CATEGORY_NAMES.get(category, category)
                pattern = re.compile(rf"## {re.escape(target_title)}\n(.*?)(?=\n## |\Z)", re.DOTALL)
                match = pattern.search(memory.memory_markdown)
                if match:
                    content = match.group(1).strip()
                    if content and content != "暂无信息。":
                        return f"## {target_title}\n{content}"
                return f"记忆中暂无指定的分类（{category}）信息。"

            return memory.memory_markdown

    async def generate_session_title(self, *, user_id: int, session_id: str, first_message: str) -> str | None:
        if not (first_message or "").strip():
            return None
        prompt = f"""请根据用户的第一条消息生成一个简短的会话标题（10字以内）。

用户消息：{first_message[:200]}

只输出标题，不要解释。"""
        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            response = await self.llm.ainvoke(
                [SystemMessage(content="你是一个会话标题生成助手。"), HumanMessage(content=prompt)],
                temperature=0.3,
                max_tokens=20,
            )
            title = str(response.content or "").strip().strip("`\"'""''")
            if not title:
                return None
            title = title[:15]
            await self.update_session_title(user_id=user_id, session_id=session_id, title=title)
            return title
        except Exception as exc:
            logger.warning("[ChatMemoryService] 生成会话标题失败 user=%s session=%s err=%s", user_id, session_id, exc)
            return None

    async def get_profile_markdown(self, user_id: int, dimension: str | None = None) -> str:
        return await self.profile_service.get_profile_markdown(user_id, dimension=dimension)

    async def after_turn(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str,
        assistant_reply: str,
        usage_metadata: dict[str, Any] | None = None,
        turn_count: int = 0,
    ) -> None:
        if usage_metadata and "total_tokens" in usage_metadata:
            delta = usage_metadata["total_tokens"]
        else:
            delta = estimate_token_count(user_message) + estimate_token_count(assistant_reply)

        try:
            async with session_scope() as db:
                chat_session = (
                    await db.exec(
                        select(ChatSession).where(
                            ChatSession.id == session_id,
                            ChatSession.user_id == user_id,
                            ChatSession.module == self.module,
                        )
                    )
                ).first()
                if not chat_session:
                    chat_session = ChatSession(
                        id=session_id,
                        user_id=user_id,
                        module=self.module,
                        title=DEFAULT_SESSION_TITLE,
                    )
                chat_session.summary_token_count = max(0, (chat_session.summary_token_count or 0) + delta)
                chat_session.updated_at = now()
                db.add(chat_session)
                await db.commit()
        except Exception as exc:
            logger.error("[ChatMemoryService] token 计数更新失败 user=%s session=%s err=%s", user_id, session_id, exc)

        await self.post_turn(
            user_id=user_id,
            session_id=session_id,
            user_message=user_message,
            assistant_reply=assistant_reply,
            turn_count=turn_count,
        )

    async def post_turn(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str,
        assistant_reply: str,
        turn_count: int = 0,
    ) -> dict[str, bool]:
        results = {
            "compressed": False,
            "ltm_updated": False,
            "profile_updated": False,
        }

        try:
            async with session_scope() as db:
                summary = await self.compressor.maybe_compress(
                    db=db,
                    user_id=user_id,
                    session_id=session_id,
                    reason="post_turn",
                )
                results["compressed"] = summary is not None
        except Exception as exc:
            logger.error("[ChatMemoryService] compression failed: %s", exc)

        try:
            async with session_scope() as db:
                updated = await self.long_term_memory.maybe_update(
                    db=db,
                    user_id=user_id,
                    session_id=session_id,
                    user_message=user_message,
                    assistant_reply=assistant_reply,
                    turn_count=turn_count,
                )
                results["ltm_updated"] = updated
        except Exception as exc:
            logger.error("[ChatMemoryService] long-term update failed: %s", exc)

        try:
            results["profile_updated"] = await self.profile_service.maybe_update_from_tutoring_turn(
                user_id=user_id,
                session_id=session_id,
            )
        except Exception as exc:
            logger.error("[ChatMemoryService] profile update failed: %s", exc)

        return results


_chat_memory_service_cache: dict[str, ChatMemoryService] = {}


def get_chat_memory_service(*, module: str = "mentor") -> ChatMemoryService:
    if module not in _chat_memory_service_cache:
        _chat_memory_service_cache[module] = ChatMemoryService(module=module)
    return _chat_memory_service_cache[module]
