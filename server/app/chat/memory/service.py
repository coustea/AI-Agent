"""Chat 私有记忆管线与持久化门面。

核心类 ChatMemoryService 是记忆操作的统一入口，提供独立的后处理接口：
  compress_session      — 会话压缩（短期消息摘要化）
  update_long_term_memory — 长期记忆更新（稳定学习特征增量写入）

画像更新由 TutorAgent 的 post-turn 调度边界触发，避免与压缩/长期记忆同时执行。

其余方法提供会话 CRUD、消息存取、摘要查询等基础能力。

单例管理：get_chat_memory_service() 返回全局单例。
"""

from __future__ import annotations

import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from sqlmodel import delete, func, select

from app.chat.memory.compression import ChatSessionCompressor
from app.chat.memory.long_term import ChatLongTermMemoryService
from app.chat.memory.types import (
    DEFAULT_SESSION_TITLE,
    LTM_CATEGORY_NAMES,
    TITLE_MAX_LENGTH,
    classify_turn_signals,
    extract_content_text,
    now,
)
from app.config import (
    COMPRESS_KEEP_RECENT_MESSAGES,
    COMPRESS_MIN_MESSAGES,
    COMPRESS_MIN_TOKENS,
    LTM_MIN_CONFIDENCE,
    UPDATE_MIN_MESSAGES,
    UPDATE_MIN_TOKENS,
    SUMMARY_CONTEXT_BLOCKS,
)
from app.infra.database import session_scope
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.models import (
    ChatActivity,
    ChatAttachmentAnalysis,
    ChatLongTermMemory,
    ChatMessage,
    ChatSession,
    ChatSessionSummaryBlock,
)

logger = get_logger(__name__)

# -----------------------------------------------------------------------
# 常量 — 已迁移至 config.yaml，由 app.config 导入
# -----------------------------------------------------------------------


class ChatMemoryService:
    """Chat-owned memory pipeline and persistence facade."""

    # -------------------------------------------------------------------
    # __init__: 初始化记忆管线的组件
    #
    # 组件职责：
    #   compressor        — 短期记忆压缩：消息过多时将旧消息摘要化
    #   long_term_memory  — 长期记忆更新：检测稳定信号（如重复出现的知识偏好）
    #                       并增量写入长期记忆 markdown
    #   llm               — LLM 实例，供标题生成等辅助功能使用
    # -------------------------------------------------------------------
    def __init__(self) -> None:
        self.compressor = ChatSessionCompressor(
            keep_recent=COMPRESS_KEEP_RECENT_MESSAGES,
            min_messages=COMPRESS_MIN_MESSAGES,
            min_tokens=COMPRESS_MIN_TOKENS,
        )
        self.long_term_memory = ChatLongTermMemoryService(
            min_confidence=LTM_MIN_CONFIDENCE,
        )
        self.llm = get_llm()

    # -------------------------------------------------------------------
    # create_session: 创建新的聊天会话
    #
    # 每个 session 属于一个用户和一个模块（如 mentor/quiz），
    # 初始标题为 DEFAULT_SESSION_TITLE，后续由 generate_session_title 自动更新。
    # 返回创建的 session 对象（含自动生成的 id 和时间戳）。
    # -------------------------------------------------------------------
    async def create_session(self, *, user_id: int, title: str = DEFAULT_SESSION_TITLE) -> Any:
        async with session_scope() as db:
            chat_session = ChatSession(user_id=user_id, title=title)
            db.add(chat_session)
            await db.commit()
            await db.refresh(chat_session)
            return chat_session

    # -------------------------------------------------------------------
    # get_or_create_session: 获取或创建会话
    #
    # 如果 session_id 存在且属于该用户，返回现有会话；
    # 否则创建一个新会话。
    # -------------------------------------------------------------------
    async def get_or_create_session(self, *, user_id: int, session_id: str) -> Any:
        async with session_scope() as db:
            chat_session = (
                await db.exec(
                    select(ChatSession).where(
                        ChatSession.id == session_id,
                        ChatSession.user_id == user_id,
                    )
                )
            ).first()
            if chat_session:
                return chat_session
            chat_session = ChatSession(id=session_id, user_id=user_id)
            db.add(chat_session)
            await db.commit()
            await db.refresh(chat_session)
            return chat_session

    # -------------------------------------------------------------------
    # list_sessions: 获取用户未归档的会话列表
    #
    # 按 updated_at 降序排列（最近活跃的在前），限制返回数量。
    # -------------------------------------------------------------------
    async def list_sessions(self, *, user_id: int, limit: int = 20) -> list[Any]:
        async with session_scope() as db:
            stmt = (
                select(ChatSession)
                .where(
                    ChatSession.user_id == user_id,
                    ChatSession.is_archived.is_(False),
                )
                .order_by(ChatSession.updated_at.desc())
                .limit(limit)
            )
            return list((await db.exec(stmt)).all())

    # -------------------------------------------------------------------
    # archive_session: 归档指定会话（软删除）
    #
    # 将 is_archived 设为 True，会话不再出现在 list_sessions 中，
    # 但数据仍保留在数据库中供审计和恢复使用。
    # 返回 True 表示归档成功，False 表示 session 不存在或无权限。
    # -------------------------------------------------------------------
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

    # -------------------------------------------------------------------
    # update_session_title: 更新会话标题
    #
    # 标题截断到 TITLE_MAX_LENGTH 字符，防止过长标题影响 UI 展示。
    # 返回 True 表示更新成功，False 表示 session 不存在或无权限。
    # -------------------------------------------------------------------
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

    async def generate_session_title(self, *, user_id: int, session_id: str, first_message: str) -> bool:
        """根据首条用户消息生成会话标题，失败时退回到截断后的用户输入。"""
        fallback = self._clean_session_title(first_message) or DEFAULT_SESSION_TITLE
        title = fallback
        try:
            resp = await self.llm.ainvoke(
                [
                    SystemMessage(content="你是会话标题生成器。只输出一个简短中文标题，不要标点、引号或解释。"),
                    HumanMessage(content=f"为这段学习辅导对话生成标题，最多12个中文字符：\n{first_message}"),
                ],
                max_tokens=32,
            )
            raw_title = str(getattr(resp, "content", resp) or "")
            title = self._clean_session_title(raw_title) or fallback
        except Exception as exc:
            logger.warning("[ChatMemoryService] generate title failed: user_id=%s session_id=%s err=%s", user_id, session_id, exc)
        return await self.update_session_title(user_id=user_id, session_id=session_id, title=title)

    @staticmethod
    def _clean_session_title(value: str) -> str:
        title = re.sub(r"[\r\n\t]+", " ", value or "").strip()
        title = title.strip("`'\"“”‘’《》[]（）()，。！？!?：:；;、 ")
        title = re.sub(r"\s+", " ", title)
        if len(title) > TITLE_MAX_LENGTH:
            title = title[:TITLE_MAX_LENGTH]
        return title

    # -------------------------------------------------------------------
    # save_message: 持久化单条聊天消息，并更新 token 计数器
    # -------------------------------------------------------------------
    async def save_message(
        self,
        *,
        user_id: int,
        session_id: str,
        role: str,
        content: list[dict[str, Any]],
        user_message_id: int | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        tool_call_id: str | None = None,
        usage_metadata: dict[str, Any] | None = None,
    ) -> ChatMessage:
        async with session_scope() as db:
            chat_session = (await db.exec(select(ChatSession).where(ChatSession.id == session_id))).first()
            if chat_session:
                if chat_session.user_id != user_id:
                    raise PermissionError("会话不属于当前用户")
                chat_session.updated_at = now()
            else:
                chat_session = ChatSession(id=session_id, user_id=user_id)
            db.add(chat_session)
            if user_message_id is not None:
                root_message = (
                    await db.exec(
                        select(ChatMessage).where(
                            ChatMessage.id == user_message_id,
                            ChatMessage.session_id == session_id,
                            ChatMessage.role == "user",
                        )
                    )
                ).first()
                if root_message is None:
                    raise ValueError("关联的用户消息不存在")

            normalized_content = content
            if not isinstance(normalized_content, list):
                normalized_content = [{"type": "text", "text": str(content or "")}]
            message = ChatMessage(
                session_id=session_id,
                user_message_id=user_message_id,
                role=role,
                content=normalized_content,
                tool_calls=tool_calls,
                tool_call_id=tool_call_id,
                usage_metadata=usage_metadata,
            )
            db.add(message)
            await db.flush()

            # 更新 token 计数器（用于触发压缩、长期记忆和画像更新）
            from app.chat.memory.types import estimate_token_count, extract_content_text
            text_content = extract_content_text(normalized_content)
            token_count = estimate_token_count(text_content)

            # 递增 summary_token_count（会话压缩触发）
            chat_session.summary_token_count = int(chat_session.summary_token_count or 0) + token_count
            # 递增 ltm_token_count 和 ltm_message_count（长期记忆触发）
            chat_session.ltm_token_count = int(chat_session.ltm_token_count or 0) + token_count
            chat_session.ltm_message_count = int(chat_session.ltm_message_count or 0) + 1
            # 递增 profile_token_count 和 profile_message_count（画像更新触发）
            chat_session.profile_token_count = int(chat_session.profile_token_count or 0) + token_count
            chat_session.profile_message_count = int(chat_session.profile_message_count or 0) + 1
            db.add(chat_session)

            await db.commit()
            await db.refresh(message)
            return message

    async def list_messages(
        self,
        *,
        user_id: int,
        session_id: str,
        limit: int = 50,
    ) -> list[ChatMessage]:
        async with session_scope() as db:
            stmt = (
                select(ChatMessage)
                .join(ChatSession, ChatSession.id == ChatMessage.session_id)
                .where(
                    ChatSession.user_id == user_id,
                    ChatMessage.session_id == session_id,
                )
                .order_by(ChatMessage.id.desc())
                .limit(limit)
            )
            return list(reversed((await db.exec(stmt)).all()))

    async def count_messages(self, *, user_id: int, session_id: str) -> int:
        async with session_scope() as db:
            result = (
                await db.exec(
                    select(func.count())
                    .select_from(ChatMessage)
                    .join(ChatSession, ChatSession.id == ChatMessage.session_id)
                    .where(
                        ChatSession.user_id == user_id,
                        ChatMessage.session_id == session_id,
                    )
                )
            ).one()
            return int(result)

    async def create_attachment_analysis(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message_id: int,
        analysis_type: str,
    ) -> ChatAttachmentAnalysis:
        async with session_scope() as db:
            user_message = (
                await db.exec(
                    select(ChatMessage).where(
                        ChatMessage.id == user_message_id,
                        ChatMessage.session_id == session_id,
                        ChatMessage.session_id.in_(
                            select(ChatSession.id).where(ChatSession.user_id == user_id)
                        ),
                        ChatMessage.role == "user",
                    )
                )
            ).first()
            if user_message is None:
                raise ValueError("用户消息不存在")
            analysis = ChatAttachmentAnalysis(
                user_message_id=user_message_id,
                analysis_type=analysis_type,
                status="running",
            )
            db.add(analysis)
            await db.commit()
            await db.refresh(analysis)
            return analysis

    async def finish_attachment_analysis(
        self,
        *,
        analysis_id: str,
        content: str,
        error_message: str | None = None,
    ) -> None:
        async with session_scope() as db:
            analysis = (
                await db.exec(
                    select(ChatAttachmentAnalysis).where(
                        ChatAttachmentAnalysis.id == analysis_id,
                    )
                )
            ).first()
            if analysis is None:
                return
            analysis.content = content
            analysis.error_message = error_message
            analysis.status = "failed" if error_message else "completed"
            analysis.completed_at = now()
            db.add(analysis)
            await db.commit()

    async def list_attachment_analyses(
        self,
        *,
        user_id: int,
        session_id: str,
        completed_only: bool = False,
    ) -> list[ChatAttachmentAnalysis]:
        async with session_scope() as db:
            stmt = (
                select(ChatAttachmentAnalysis)
                .join(
                    ChatMessage,
                    ChatMessage.id == ChatAttachmentAnalysis.user_message_id,
                )
                .join(ChatSession, ChatSession.id == ChatMessage.session_id)
                .where(
                    ChatSession.user_id == user_id,
                    ChatMessage.session_id == session_id,
                )
            )
            if completed_only:
                stmt = stmt.where(ChatAttachmentAnalysis.status == "completed")
            stmt = stmt.order_by(ChatAttachmentAnalysis.created_at.asc())
            return list((await db.exec(stmt)).all())

    async def upsert_activity(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message_id: int,
        payload: dict[str, Any],
    ) -> ChatActivity | None:
        """保存公开状态摘要；同一 activity_id 的生命周期原位更新。"""
        activity_id = str(payload.get("activity_id") or "").strip()
        if not activity_id:
            return None
        status = str(payload.get("status") or "running")
        if status in {"completed", "finished"}:
            status = "done"
        elif status == "error":
            status = "failed"
        if status not in {"running", "done", "failed"}:
            status = "running"

        async with session_scope() as db:
            activity = (
                await db.exec(
                    select(ChatActivity)
                    .join(ChatMessage, ChatMessage.id == ChatActivity.user_message_id)
                    .join(ChatSession, ChatSession.id == ChatMessage.session_id)
                    .where(
                        ChatSession.user_id == user_id,
                        ChatMessage.session_id == session_id,
                        ChatActivity.user_message_id == user_message_id,
                        ChatActivity.activity_id == activity_id,
                    )
                )
            ).first()
            if activity is None:
                user_message = (
                    await db.exec(
                        select(ChatMessage).where(
                            ChatMessage.id == user_message_id,
                            ChatMessage.session_id == session_id,
                            ChatMessage.session_id.in_(
                                select(ChatSession.id).where(ChatSession.user_id == user_id)
                            ),
                            ChatMessage.role == "user",
                        )
                    )
                ).first()
                if user_message is None:
                    return None
                activity = ChatActivity(
                    user_message_id=user_message_id,
                    activity_id=activity_id,
                )

            activity.kind = str(payload.get("kind") or activity.kind or "workflow")
            activity.stage = str(payload.get("stage") or "") or None
            activity.status = status
            activity.title = str(payload.get("title") or activity.title or "")
            activity.summary = str(payload.get("summary") or "")
            activity.message = str(payload.get("message") or "")
            detail = payload.get("detail")
            activity.detail = detail if isinstance(detail, dict) else None
            if status in {"done", "failed"}:
                activity.completed_at = now()
            db.add(activity)
            await db.commit()
            await db.refresh(activity)
            return activity

    async def list_activities(
        self,
        *,
        user_id: int,
        session_id: str,
    ) -> list[ChatActivity]:
        async with session_scope() as db:
            stmt = (
                select(ChatActivity)
                .join(ChatMessage, ChatMessage.id == ChatActivity.user_message_id)
                .join(ChatSession, ChatSession.id == ChatMessage.session_id)
                .where(
                    ChatSession.user_id == user_id,
                    ChatMessage.session_id == session_id,
                )
                .order_by(ChatActivity.started_at.asc(), ChatActivity.id.asc())
            )
            return list((await db.exec(stmt)).all())

    async def delete_short_term_messages(self, *, user_id: int, session_id: str) -> int:
        async with session_scope() as db:
            msgs = list(
                (
                    await db.exec(
                        select(ChatMessage).where(
                            ChatMessage.session_id == session_id,
                            ChatMessage.session_id.in_(
                                select(ChatSession.id).where(ChatSession.user_id == user_id)
                            ),
                        )
                    )
                ).all()
            )
            stale_ids = [m.id for m in msgs if m.id]
            if stale_ids:
                await db.exec(
                    delete(ChatMessage).where(ChatMessage.id.in_(stale_ids))
                )
                await db.commit()
            return len(stale_ids)

    async def reset_session_counters(self, *, user_id: int, session_id: str) -> None:
        async with session_scope() as db:
            s = (
                await db.exec(
                    select(ChatSession).where(
                        ChatSession.id == session_id,
                        ChatSession.user_id == user_id,
                    )
                )
            ).first()
            if s:
                s.summary_token_count = 0
                s.ltm_token_count = 0
                s.ltm_message_count = 0
                db.add(s)
                await db.commit()


    # -------------------------------------------------------------------
    # list_summary_blocks: 获取最近的会话摘要块列表
    #
    # 摘要块由压缩器（ChatSessionCompressor）在压缩旧消息时生成，
    # 每个块包含一段 markdown 格式的摘要文本。
    # 按 created_at 降序返回最新的 limit 个摘要块。
    # -------------------------------------------------------------------
    async def list_summary_blocks(self, *, user_id: int, session_id: str, limit: int = SUMMARY_CONTEXT_BLOCKS) -> list[Any]:
        async with session_scope() as db:
            stmt = (
                select(ChatSessionSummaryBlock)
                .join(ChatSession, ChatSession.id == ChatSessionSummaryBlock.session_id)
                .where(
                    ChatSession.user_id == user_id,
                    ChatSessionSummaryBlock.session_id == session_id,
                )
                .order_by(ChatSessionSummaryBlock.created_at.desc())
                .limit(limit)
            )
            return list((await db.exec(stmt)).all())

    # -------------------------------------------------------------------
    # get_session_summary_context: 获取会话的摘要上下文（供 LLM 拼接 prompt）
    #
    # 从数据库取最近 N 个（默认 3 个）ChatSessionSummaryBlock，
    # 按时间正序用分隔符拼接为 markdown 文本。
    #
    # reversed 的原因：查询按 created_at DESC 排序，拼接时需要
    # 从旧到新排列，所以取结果后反转。
    #
    # 返回的 markdown 会注入到 system prompt 中，让 LLM 了解
    # "之前聊过什么"，避免重复询问或遗忘上下文。
    # -------------------------------------------------------------------
    async def get_session_summary_context(self, *, user_id: int, session_id: str) -> str:
        # 获取最近的摘要块（降序）
        blocks = await self.list_summary_blocks(user_id=user_id, session_id=session_id, limit=SUMMARY_CONTEXT_BLOCKS)
        if not blocks:
            return "暂无会话概要。"
        # 反转为时间正序，用分隔符拼接各块的 markdown 内容
        return "\n\n---\n\n".join(
            block.summary_markdown
            for block in reversed(blocks)
            if block.summary_markdown
        ) or "暂无会话概要。"

    # -------------------------------------------------------------------
    # get_long_term_memory: 获取用户的长期记忆记录对象
    #
    # 每个 user 对应一条 ChatLongTermMemory 记录，
    # 其中 memory_markdown 列存储完整的长期记忆 markdown。
    # 返回 ORM 对象（可能为 None），调用方可直接读取各字段。
    # -------------------------------------------------------------------
    async def get_long_term_memory(self, *, user_id: int) -> Any:
        async with session_scope() as db:
            return (
                await db.exec(
                    select(ChatLongTermMemory).where(
                        ChatLongTermMemory.user_id == user_id,
                    )
                )
            ).first()

    async def get_memory_markdown(self, user_id: int, category: str | None = None) -> str:
        """读取长期记忆 Markdown，按需返回指定分类小节。"""
        record = await self.get_long_term_memory(user_id=user_id)
        markdown = str(getattr(record, "memory_markdown", "") or "").strip()
        if not markdown:
            return "暂无长期学习记忆。"

        category_value = str(category or "").strip()
        if not category_value:
            return markdown

        heading = LTM_CATEGORY_NAMES.get(category_value)
        if not heading:
            return markdown

        match = re.search(
            rf"(^|\n)##\s+{re.escape(heading)}\s*\n(?P<body>.*?)(?=\n##\s+|\Z)",
            markdown,
            flags=re.S,
        )
        if not match:
            return f"## {heading}\n暂无信息。"
        return f"## {heading}\n{match.group('body').strip()}"

    # -------------------------------------------------------------------
    # compress_session: 会话压缩入口
    #
    # 当 session 中消息数 ≥ min_messages 或 token ≥ min_tokens 时，
    # 将旧消息通过 LLM 摘要化，保留最近 keep_recent 条原始消息。
    # 返回压缩后的 summary block（None 表示无需压缩）。
    # -------------------------------------------------------------------
    async def should_compress_session(
        self,
        *,
        user_id: int,
        session_id: str,
    ) -> bool:
        """Check whether session needs compression without actually compressing."""
        try:
            async with session_scope() as db:
                result = await self.compressor.needs_compression(
                    db=db,
                    user_id=user_id,
                    session_id=session_id,
                )
                logger.info("[ChatMemoryService] 压缩检查: user_id=%s session_id=%s needs_compression=%s", user_id, session_id, result)
                return result
        except Exception as exc:
            logger.error("[ChatMemoryService] compression need check failed: %s", exc)
            return False

    async def evaluate_post_turn_jobs(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str,
        assistant_reply: str,
    ) -> dict[str, Any]:
        """Combined LTM + compression + profile token threshold check in a single DB session."""
        signals = classify_turn_signals(user_message, assistant_reply)
        ltm_signal = signals["ltm"]
        profile_signal = signals["global_profile"] or signals["course_profile"]

        try:
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
                    should_ltm = ltm_signal
                    should_profile = profile_signal
                    ltm_schedule: dict[str, Any] = {
                        "signal_detected": ltm_signal,
                        "ltm_token_count": 0,
                        "ltm_message_count": 0,
                    }
                    profile_schedule: dict[str, Any] = {
                        "signal_detected": profile_signal,
                        "profile_token_count": 0,
                        "profile_message_count": 0,
                    }
                else:
                    # 画像/长期记忆更新阈值判断（统一阈值）
                    ltm_token = int(chat_session.ltm_token_count or 0)
                    ltm_msg = int(chat_session.ltm_message_count or 0)
                    ltm_threshold_due = ltm_token >= UPDATE_MIN_TOKENS or ltm_msg >= UPDATE_MIN_MESSAGES
                    should_ltm = (ltm_signal or ltm_threshold_due) and ltm_msg > 0
                    ltm_schedule = {
                        "signal_detected": ltm_signal,
                        "threshold_due": ltm_threshold_due,
                        "ltm_token_count": ltm_token,
                        "ltm_message_count": ltm_msg,
                        "last_ltm_message_id": int(chat_session.last_ltm_message_id or 0),
                    }

                    # 画像阈值判断（与 LTM 共用统一阈值）
                    profile_token = int(chat_session.profile_token_count or 0)
                    profile_msg = int(chat_session.profile_message_count or 0)
                    profile_threshold_due = profile_token >= UPDATE_MIN_TOKENS or profile_msg >= UPDATE_MIN_MESSAGES
                    should_profile = profile_signal or profile_threshold_due
                    profile_schedule = {
                        "signal_detected": profile_signal,
                        "threshold_due": profile_threshold_due,
                        "profile_token_count": profile_token,
                        "profile_message_count": profile_msg,
                    }

                should_compress = await self.compressor.needs_compression(
                    db=db,
                    user_id=user_id,
                    session_id=session_id,
                )

                logger.info(
                    "[ChatMemoryService] evaluate_post_turn_jobs: should_ltm=%s should_profile=%s should_compress=%s",
                    should_ltm, should_profile, should_compress,
                )
                return {
                    "should_ltm": should_ltm,
                    "ltm_schedule": ltm_schedule,
                    "should_profile": should_profile,
                    "profile_schedule": profile_schedule,
                    "should_compress": should_compress,
                    "signals": signals,
                }
        except Exception as exc:
            logger.error("[ChatMemoryService] evaluate_post_turn_jobs failed: %s", exc)
            return {
                "should_ltm": False,
                "ltm_schedule": {"signal_detected": signal_detected},
                "should_compress": False,
                "signals": signals,
            }

    async def compress_session(
        self,
        *,
        user_id: int,
        session_id: str,
        reason: str = "compress_session",
    ):
        logger.info("[ChatMemoryService] 开始会话压缩: user_id=%s session_id=%s reason=%s", user_id, session_id, reason)
        try:
            async with session_scope() as db:
                result = await self.compressor.maybe_compress(
                    db=db,
                    user_id=user_id,
                    session_id=session_id,
                    reason=reason,
                )
                if result:
                    logger.info("[ChatMemoryService] 会话压缩完成: user_id=%s session_id=%s block_index=%s", user_id, session_id, result.block_index)
                else:
                    logger.info("[ChatMemoryService] 会话压缩跳过: user_id=%s session_id=%s", user_id, session_id)
                return result
        except Exception as exc:
            logger.error("[ChatMemoryService] compression failed: %s", exc)
            return None

    # -------------------------------------------------------------------
    # update_long_term_memory: 长期记忆更新入口
    #
    # 根据信号触发（正则匹配偏好/纠正/背景）或新增消息/token 阈值触发
    # 判断是否需要更新。LLM 判断 need_update 且 confidence ≥ 阈值
    # 才实际写入。返回 True 表示已更新。
    # -------------------------------------------------------------------
    async def update_long_term_memory(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str,
        assistant_reply: str,
        signal_detected: bool = False,
    ) -> dict[str, Any]:
        logger.info(
            "[ChatMemoryService] 开始长期记忆更新: user_id=%s session_id=%s signal_detected=%s",
            user_id, session_id, signal_detected,
        )
        try:
            async with session_scope() as db:
                chat_session = (
                    await db.exec(
                        select(ChatSession).where(
                            ChatSession.id == session_id,
                            ChatSession.user_id == user_id,
                        )
                    )
                ).first()
                after_message_id = int(chat_session.last_ltm_message_id or 0) if chat_session else 0
                new_dialogue, message_count, latest_message_id = await self._build_dialogue_since(
                    db=db,
                    user_id=user_id,
                    session_id=session_id,
                    after_message_id=after_message_id,
                    limit=60,
                )
                logger.info(
                    "[ChatMemoryService] 构建对话: after_message_id=%s latest_message_id=%s message_count=%s dialogue_length=%s",
                    after_message_id, latest_message_id, message_count, len(new_dialogue),
                )
                if not new_dialogue or latest_message_id <= after_message_id:
                    logger.info("[ChatMemoryService] 无新对话，跳过长期记忆更新")
                    return {"updated": False, "analyzed": False, "latest_message_id": after_message_id}

                result = await self.long_term_memory.maybe_update(
                    db=db,
                    user_id=user_id,
                    session_id=session_id,
                    user_message=user_message,
                    assistant_reply=assistant_reply,
                    new_dialogue=new_dialogue,
                    turn_count=message_count,
                    signal_detected=signal_detected,
                )
                analyzed = bool(result.get("analyzed"))
                if analyzed and chat_session:
                    chat_session.ltm_token_count = 0
                    chat_session.ltm_message_count = 0
                    chat_session.last_ltm_message_id = latest_message_id
                    chat_session.last_ltm_updated_at = now()
                    chat_session.updated_at = now()
                    db.add(chat_session)
                logger.info(
                    "[ChatMemoryService] 长期记忆更新完成: updated=%s analyzed=%s",
                    result.get("updated"), result.get("analyzed"),
                )
                return {**result, "latest_message_id": latest_message_id}
        except Exception as exc:
            logger.error("[ChatMemoryService] long-term update failed: %s", exc)
            return {"updated": False, "analyzed": False, "error": str(exc)}

    # -------------------------------------------------------------------
    # reset_profile_counters: 重置画像更新计数器
    # -------------------------------------------------------------------
    async def reset_profile_counters(
        self,
        *,
        user_id: int,
        session_id: str,
    ) -> bool:
        """画像更新完成后重置 profile_token_count 和 profile_message_count。"""
        try:
            async with session_scope() as db:
                chat_session = (
                    await db.exec(
                        select(ChatSession).where(
                            ChatSession.id == session_id,
                            ChatSession.user_id == user_id,
                        )
                    )
                ).first()
                if chat_session:
                    chat_session.profile_token_count = 0
                    chat_session.profile_message_count = 0
                    chat_session.last_profile_updated_at = now()
                    chat_session.updated_at = now()
                    db.add(chat_session)
                    logger.info(
                        "[ChatMemoryService] 画像计数器已重置: user_id=%s session_id=%s",
                        user_id, session_id,
                    )
                    return True
                return False
        except Exception as exc:
            logger.error("[ChatMemoryService] reset_profile_counters failed: %s", exc)
            return False

    async def _build_dialogue_since(
        self,
        *,
        db: Any,
        user_id: int,
        session_id: str,
        after_message_id: int,
        limit: int,
    ) -> tuple[str, int, int]:
        stmt = (
            select(ChatMessage)
            .join(ChatSession, ChatSession.id == ChatMessage.session_id)
            .where(
                ChatSession.user_id == user_id,
                ChatMessage.session_id == session_id,
                ChatMessage.role.in_(["user", "assistant"]),
                ChatMessage.id > after_message_id,
            )
            .order_by(ChatMessage.id.desc())
            .limit(limit)
        )
        messages = list((await db.exec(stmt)).all())
        if not messages:
            return "", 0, after_message_id

        lines: list[str] = []
        latest_message_id = after_message_id
        for message in reversed(messages):
            latest_message_id = max(latest_message_id, int(message.id or 0))
            content = extract_content_text(message.content)
            if not content:
                continue
            role_label = "学生" if message.role == "user" else "辅导老师"
            lines.append(f"{role_label}：{content[:700]}")
        return "\n".join(lines), len(messages), latest_message_id


_chat_memory_service: ChatMemoryService | None = None


def get_chat_memory_service() -> ChatMemoryService:
    global _chat_memory_service
    if _chat_memory_service is None:
        _chat_memory_service = ChatMemoryService()
    return _chat_memory_service
