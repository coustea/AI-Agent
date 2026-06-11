"""Chat 私有记忆管线与持久化门面。

核心类 ChatMemoryService 是记忆操作的统一入口，编排三阶段后处理管线：
  after_turn → post_turn:
    1. 压缩(compressor.maybe_compress) — 短期消息过多时生成摘要块
    2. 长期记忆(long_term_memory.maybe_update) — 检测稳定信号并增量更新
    3. 画像(profile_service.maybe_update_from_tutoring_turn) — 同步画像维度

其余方法提供会话 CRUD、消息存取、摘要查询等基础能力。

内联模块（原 persistence.py 合并）：
  - TranscriptEvent / TurnTranscript — transcript 事件模型
  - ChatPersistenceAdapter — transcript 持久化适配器（追加事件 + 终态落盘）

单例管理：get_chat_memory_service(module=) 按 module 缓存实例。
"""

from __future__ import annotations

import re
from datetime import timedelta
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
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
from app.infra.models import (
    ChatAttachmentAnalysis,
    ChatLongTermMemory,
    ChatMessageAttachment,
    ChatMessage,
    ChatSession,
    ChatSessionSummaryBlock,
    ChatToolInvocation,
    ChatTurn,
    ChatTurnTranscript,
    ChatUploadedFile,
)

logger = get_logger(__name__)

RECENT_RAW_MESSAGES = 8
COMPRESS_MIN_MESSAGES = 14
COMPRESS_MIN_TOKENS = 3500
SUMMARY_CONTEXT_BLOCKS = 3
LTM_PERIODIC_TURNS = 8
LTM_MIN_CONFIDENCE = 0.75
LTM_UPDATE_COOLDOWN_MINUTES = 30


# -----------------------------------------------------------------------
# Transcript 模型（原 persistence.py 内联）
# -----------------------------------------------------------------------

class TranscriptEvent(BaseModel):
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)


class TurnTranscript(BaseModel):
    turn_id: int | None = None
    events: list[TranscriptEvent] = Field(default_factory=list)
    final_answer: str = ""
    constraint_report: dict[str, Any] | None = None

    def append(self, event_type: str, **payload: Any) -> None:
        self.events.append(TranscriptEvent(event_type=event_type, payload=payload))


class ChatPersistenceAdapter:
    async def append_transcript_event(
        self,
        *,
        turn_id: int,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        async with session_scope() as db:
            row = (
                await db.exec(
                    select(ChatTurnTranscript).where(ChatTurnTranscript.turn_id == turn_id)
                )
            ).first()
            transcript = TurnTranscript()
            if row is not None and isinstance(row.transcript_json, dict):
                transcript = TurnTranscript.model_validate(row.transcript_json)
            transcript.turn_id = turn_id
            transcript.append(event_type, **(payload or {}))
            if row is None:
                row = ChatTurnTranscript(
                    turn_id=turn_id,
                    transcript_json=transcript.model_dump(),
                    final_answer=transcript.final_answer,
                )
            else:
                row.transcript_json = transcript.model_dump()
                row.final_answer = transcript.final_answer
            db.add(row)
            await db.commit()

    async def finalize_turn(
        self,
        *,
        turn_id: int,
        final_answer: str,
        constraint_report: dict[str, Any] | None = None,
    ) -> None:
        async with session_scope() as db:
            row = (
                await db.exec(
                    select(ChatTurnTranscript).where(ChatTurnTranscript.turn_id == turn_id)
                )
            ).first()
            transcript = TurnTranscript(turn_id=turn_id, final_answer=final_answer)
            if row is not None and isinstance(row.transcript_json, dict):
                transcript = TurnTranscript.model_validate(row.transcript_json)
                transcript.turn_id = turn_id
                transcript.final_answer = final_answer
            transcript.constraint_report = constraint_report
            if row is None:
                row = ChatTurnTranscript(
                    turn_id=turn_id,
                    transcript_json=transcript.model_dump(),
                    final_answer=final_answer,
                    constraint_report_json=constraint_report,
                )
            else:
                row.transcript_json = transcript.model_dump()
                row.final_answer = final_answer
                row.constraint_report_json = constraint_report
            db.add(row)
            await db.commit()


class ChatMemoryService:
    """Chat-owned memory pipeline and persistence facade."""

    def __init__(self, *, module: str = "mentor") -> None:
        self.module = module
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
        self.persistence = ChatPersistenceAdapter()
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
        tool_call_id: str | None = None,
        knowledge_sources: list[dict[str, Any]] | None = None,
        attachment_analyses: list[dict[str, Any]] | None = None,
        teaching_diagram: dict[str, Any] | None = None,
        usage_metadata: dict[str, Any] | None = None,
        turn_id: int | None = None,
        message_kind: str | None = None,
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
            message = ChatMessage(
                user_id=user_id,
                session_id=session_id,
                turn_id=turn_id,
                module=self.module,
                role=role,
                message_kind=message_kind,
                content=content,
                attachments=attachments,
                tool_calls=tool_calls,
                tool_call_id=tool_call_id,
                knowledge_sources=knowledge_sources,
                teaching_diagram=teaching_diagram,
                usage_metadata=usage_metadata,
            )
            db.add(message)
            await db.flush()

            for analysis in attachment_analyses or []:
                summary_text = str(analysis.get("summary_text") or "").strip()
                if not summary_text:
                    continue
                db.add(
                    ChatAttachmentAnalysis(
                        user_id=user_id,
                        session_id=session_id,
                        message_id=message.id,
                        file_id=analysis.get("file_id"),
                        file_name=analysis.get("file_name"),
                        file_url=analysis.get("file_url"),
                        turn_id=turn_id,
                        module=self.module,
                        analysis_type=str(analysis.get("analysis_type") or "general"),
                        summary_text=summary_text,
                        extracted_text=analysis.get("extracted_text"),
                        structured_json=analysis.get("structured_json"),
                    )
                )

            await db.commit()

    async def save_tool_invocations(
        self,
        *,
        user_id: int,
        session_id: str,
        invocations: list[dict[str, Any]],
        turn_id: int | None = None,
    ) -> None:
        if not invocations:
            return
        async with session_scope() as db:
            for invocation in invocations:
                tool_call_id = str(invocation.get("tool_call_id") or "").strip()
                tool_name = str(invocation.get("tool_name") or "").strip()
                if not tool_call_id or not tool_name:
                    continue
                db.add(
                    ChatToolInvocation(
                        user_id=user_id,
                        session_id=session_id,
                        turn_id=turn_id,
                        module=self.module,
                        assistant_message_id=invocation.get("assistant_message_id"),
                        tool_message_id=invocation.get("tool_message_id"),
                        tool_call_id=tool_call_id,
                        tool_name=tool_name,
                        arguments_json=invocation.get("arguments_json"),
                        result_text=invocation.get("result_text"),
                        result_json=invocation.get("result_json"),
                        status=str(invocation.get("status") or "success"),
                    )
                )
            await db.commit()

    async def create_turn(
        self,
        *,
        user_id: int,
        session_id: str,
        route: str = "default",
        execution_mode: str = "default",
        has_attachments: bool = False,
        used_web_search: bool = False,
        used_teaching_diagram: bool = False,
        status: str = "running",
    ) -> Any:
        async with session_scope() as db:
            chat_session = (await db.exec(select(ChatSession).where(ChatSession.id == session_id))).first()
            if chat_session:
                if chat_session.user_id != user_id or chat_session.module != self.module:
                    raise PermissionError("会话不属于当前用户或模块")
                chat_session.updated_at = now()
            else:
                chat_session = ChatSession(id=session_id, user_id=user_id, module=self.module)
            db.add(chat_session)
            await db.flush()

            latest = (
                await db.exec(
                    select(ChatTurn)
                    .where(
                        ChatTurn.user_id == user_id,
                        ChatTurn.session_id == session_id,
                        ChatTurn.module == self.module,
                    )
                    .order_by(ChatTurn.turn_index.desc())
                    .limit(1)
                )
            ).first()
            next_index = int(getattr(latest, "turn_index", 0) or 0) + 1
            turn = ChatTurn(
                user_id=user_id,
                session_id=session_id,
                module=self.module,
                turn_index=next_index,
                route=route,
                execution_mode=execution_mode,
                has_attachments=has_attachments,
                used_web_search=used_web_search,
                used_teaching_diagram=used_teaching_diagram,
                status=status,
            )
            db.add(turn)
            await db.commit()
            await db.refresh(turn)
            return turn

    async def update_turn(
        self,
        *,
        user_id: int,
        session_id: str,
        turn_id: int,
        status: str,
        route: str = "default",
        execution_mode: str = "default",
        used_web_search: bool = False,
        used_teaching_diagram: bool = False,
        error_message: str | None = None,
    ) -> None:
        async with session_scope() as db:
            turn = (
                await db.exec(
                    select(ChatTurn).where(
                        ChatTurn.id == turn_id,
                        ChatTurn.user_id == user_id,
                        ChatTurn.session_id == session_id,
                        ChatTurn.module == self.module,
                    )
                )
            ).first()
            if turn is None:
                return
            turn.status = status
            turn.route = route
            turn.execution_mode = execution_mode
            turn.used_web_search = used_web_search
            turn.used_teaching_diagram = used_teaching_diagram
            turn.error_message = error_message
            if status == "completed":
                turn.completed_at = now()
            db.add(turn)
            await db.commit()

    async def append_turn_event(
        self,
        *,
        user_id: int,
        session_id: str,
        turn_id: int,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        await self.persistence.append_transcript_event(
            turn_id=turn_id,
            event_type=event_type,
            payload=payload,
        )

    async def finalize_turn_transcript(
        self,
        *,
        user_id: int,
        session_id: str,
        turn_id: int,
        status: str,
        final_answer: str,
        constraint_report: dict[str, Any] | None = None,
    ) -> None:
        report = dict(constraint_report or {})
        report.setdefault("status", status)
        await self.persistence.finalize_turn(
            turn_id=turn_id,
            final_answer=final_answer,
            constraint_report=report,
        )

    async def save_uploaded_file(
        self,
        *,
        user_id: int,
        session_id: str,
        payload: dict[str, Any],
    ) -> Any:
        async with session_scope() as db:
            record = ChatUploadedFile(
                user_id=user_id,
                session_id=session_id,
                module=self.module,
                storage_url=str(payload.get("url") or ""),
                storage_key=payload.get("storage_key"),
                original_name=str(payload.get("original_name") or ""),
                file_kind=str(payload.get("file_type") or "document"),
                mime_type=payload.get("mime_type"),
                extension=payload.get("extension"),
                size_bytes=int(payload.get("size_bytes") or 0),
            )
            db.add(record)
            await db.commit()
            await db.refresh(record)
            return record

    async def bind_message_attachments(
        self,
        *,
        user_id: int,
        session_id: str,
        message_id: int,
        turn_id: int | None,
        attachments: list[dict[str, Any]],
    ) -> None:
        if not attachments:
            return
        async with session_scope() as db:
            urls = [str(item.get("url") or "").strip() for item in attachments if str(item.get("url") or "").strip()]
            if not urls:
                return
            uploaded_files = list(
                (
                    await db.exec(
                        select(ChatUploadedFile).where(
                            ChatUploadedFile.user_id == user_id,
                            ChatUploadedFile.session_id == session_id,
                            ChatUploadedFile.module == self.module,
                            ChatUploadedFile.storage_url.in_(urls),
                        )
                    )
                ).all()
            )
            file_by_url = {item.storage_url: item for item in uploaded_files}
            for index, attachment in enumerate(attachments):
                url = str(attachment.get("url") or "").strip()
                file_record = file_by_url.get(url)
                if file_record is None:
                    continue
                db.add(
                    ChatMessageAttachment(
                        user_id=user_id,
                        session_id=session_id,
                        message_id=message_id,
                        file_id=file_record.id,
                        turn_id=turn_id,
                        module=self.module,
                        attachment_order=index,
                        attachment_role="input",
                    )
                )
            await db.commit()

    async def list_message_attachments(
        self,
        *,
        user_id: int,
        session_id: str,
        message_ids: list[int],
    ) -> dict[int, list[dict[str, Any]]]:
        if not message_ids:
            return {}
        async with session_scope() as db:
            stmt = (
                select(ChatMessageAttachment, ChatUploadedFile)
                .join(ChatUploadedFile, ChatUploadedFile.id == ChatMessageAttachment.file_id)
                .where(
                    ChatMessageAttachment.user_id == user_id,
                    ChatMessageAttachment.session_id == session_id,
                    ChatMessageAttachment.module == self.module,
                    ChatMessageAttachment.message_id.in_(message_ids),
                )
                .order_by(ChatMessageAttachment.message_id.asc(), ChatMessageAttachment.attachment_order.asc())
            )
            rows = (await db.exec(stmt)).all()
            result: dict[int, list[dict[str, Any]]] = {}
            for relation, uploaded in rows:
                result.setdefault(relation.message_id, []).append(
                    {
                        "file_id": uploaded.id,
                        "url": uploaded.storage_url,
                        "type": uploaded.file_kind,
                        "name": uploaded.original_name,
                        "mime_type": uploaded.mime_type,
                        "extension": uploaded.extension,
                        "storage_key": uploaded.storage_key,
                        "size_bytes": uploaded.size_bytes,
                    }
                )
            return result

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

    async def list_attachment_analyses(
        self,
        *,
        user_id: int,
        session_id: str,
        limit: int = 20,
    ) -> list[Any]:
        async with session_scope() as db:
            stmt = (
                select(ChatAttachmentAnalysis)
                .where(
                    ChatAttachmentAnalysis.user_id == user_id,
                    ChatAttachmentAnalysis.session_id == session_id,
                    ChatAttachmentAnalysis.module == self.module,
                )
                .order_by(ChatAttachmentAnalysis.created_at.desc())
                .limit(limit)
            )
            return list((await db.exec(stmt)).all())

    async def list_tool_invocations(
        self,
        *,
        user_id: int,
        session_id: str,
        limit: int = 20,
    ) -> list[Any]:
        async with session_scope() as db:
            stmt = (
                select(ChatToolInvocation)
                .where(
                    ChatToolInvocation.user_id == user_id,
                    ChatToolInvocation.session_id == session_id,
                    ChatToolInvocation.module == self.module,
                )
                .order_by(ChatToolInvocation.created_at.desc())
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
        from app.profile.service import get_profile_service
        return await get_profile_service().get_profile_markdown(user_id, dimension=dimension)

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

        
        return results


_chat_memory_service_cache: dict[str, ChatMemoryService] = {}


def get_chat_memory_service(*, module: str = "mentor") -> ChatMemoryService:
    if module not in _chat_memory_service_cache:
        _chat_memory_service_cache[module] = ChatMemoryService(module=module)
    return _chat_memory_service_cache[module]
