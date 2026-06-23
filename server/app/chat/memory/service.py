"""Chat 私有记忆管线与持久化门面。

核心类 ChatMemoryService 是记忆操作的统一入口，提供独立的后处理接口：
  update_post_turn_counters — 累加本轮压缩/画像/长期记忆调度计数器
  compress_session      — 会话压缩（短期消息摘要化）
  update_long_term_memory — 长期记忆更新（稳定学习特征增量写入）

画像更新由 TutorAgent 的 post-turn 调度边界触发，避免与压缩/长期记忆同时执行。

其余方法提供会话 CRUD、消息存取、摘要查询等基础能力。

单例管理：get_chat_memory_service(module=) 按 module 缓存实例。
"""

from __future__ import annotations

import re
from datetime import timedelta
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from sqlmodel import func, select

from app.chat.memory.compression import ChatSessionCompressor
from app.chat.memory.long_term import ChatLongTermMemoryService
from app.chat.memory.types import (
    DEFAULT_SESSION_TITLE,
    LTM_CATEGORY_NAMES,
    MESSAGE_EXPIRE_DAYS,
    TITLE_MAX_LENGTH,
    estimate_token_count,
    has_stable_signal,
    now,
)
from app.config import (
    COMPRESS_KEEP_RECENT_MESSAGES,
    COMPRESS_MIN_MESSAGES,
    COMPRESS_MIN_TOKENS,
    LTM_MIN_CONFIDENCE,
    LTM_MIN_MESSAGES,
    LTM_MIN_TOKENS,
    LTM_COOLDOWN_MINUTES,
    SUMMARY_CONTEXT_BLOCKS,
)
from app.infra.database import session_scope
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.models import (
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
    #
    # module 参数区分不同业务模块（mentor/quiz 等），
    # 确保各模块记忆互不干扰。
    # -------------------------------------------------------------------
    def __init__(self, *, module: str = "mentor") -> None:
        # 业务模块标识，用于数据库行的 module 字段隔离
        self.module = module
        # 压缩器：保留最近 N 条原始消息，超过阈值时触发压缩
        self.compressor = ChatSessionCompressor(
            module=module,
            keep_recent=COMPRESS_KEEP_RECENT_MESSAGES,
            min_messages=COMPRESS_MIN_MESSAGES,
            min_tokens=COMPRESS_MIN_TOKENS,
        )
        # 长期记忆服务：按新增消息/token 调度，置信度 >= 0.75 才写入，冷却期 30 分钟
        self.long_term_memory = ChatLongTermMemoryService(
            module=module,
            periodic_turns=LTM_MIN_MESSAGES,
            min_confidence=LTM_MIN_CONFIDENCE,
            cooldown_minutes=LTM_COOLDOWN_MINUTES,
        )
        # LLM 实例，用于标题生成等需要语言模型的辅助功能
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
            chat_session = ChatSession(user_id=user_id, module=self.module, title=title)
            db.add(chat_session)
            await db.commit()
            await db.refresh(chat_session)
            return chat_session

    # -------------------------------------------------------------------
    # list_sessions: 获取用户未归档的会话列表
    #
    # 按 updated_at 降序排列（最近活跃的在前），限制返回数量。
    # 仅返回当前模块的会话，不同模块的会话互不可见。
    # -------------------------------------------------------------------
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
                temperature=0.2,
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
    # save_message: 持久化单条聊天消息
    # -------------------------------------------------------------------
    async def save_message(
        self,
        *,
        user_id: int,
        session_id: str,
        role: str,
        content: list[dict[str, Any]],
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
                chat_session = ChatSession(id=session_id, user_id=user_id, module=self.module)
            db.add(chat_session)
            message = ChatMessage(
                user_id=user_id,
                session_id=session_id,
                role=role,
                content=content,
                tool_calls=tool_calls,
                tool_call_id=tool_call_id,
                usage_metadata=usage_metadata,
            )
            db.add(message)
            await db.commit()
            return message


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
                .where(
                    ChatSessionSummaryBlock.user_id == user_id,
                    ChatSessionSummaryBlock.session_id == session_id,
                    ChatSessionSummaryBlock.module == self.module,
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
    # 每个 user + module 组合对应一条 ChatLongTermMemory 记录，
    # 其中 memory_markdown 列存储完整的长期记忆 markdown。
    # 返回 ORM 对象（可能为 None），调用方可直接读取各字段。
    # -------------------------------------------------------------------
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
    # update_post_turn_counters: 累加本轮后处理调度计数器
    #
    # summary_token_count 只用于压缩；画像和长期记忆各自维护 token/message 计数与处理游标。
    # -------------------------------------------------------------------
    async def update_post_turn_counters(
        self,
        *,
        user_id: int,
        session_id: str,
        turn_id: int | None = None,
        user_message: str,
        assistant_reply: str,
        usage_metadata: dict[str, Any] | None = None,
    ) -> dict[str, int]:
        try:
            async with session_scope() as db:
                token_delta, message_delta, max_message_id = await self._turn_message_stats(
                    db=db,
                    user_id=user_id,
                    session_id=session_id,
                    turn_id=turn_id,
                    user_message=user_message,
                    assistant_reply=assistant_reply,
                    usage_metadata=usage_metadata,
                )
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
                chat_session.summary_token_count = max(0, (chat_session.summary_token_count or 0) + token_delta)
                chat_session.profile_token_count = max(0, (chat_session.profile_token_count or 0) + token_delta)
                chat_session.profile_message_count = max(0, (chat_session.profile_message_count or 0) + message_delta)
                chat_session.ltm_token_count = max(0, (chat_session.ltm_token_count or 0) + token_delta)
                chat_session.ltm_message_count = max(0, (chat_session.ltm_message_count or 0) + message_delta)
                chat_session.updated_at = now()
                db.add(chat_session)
                await db.commit()
                return {
                    "token_delta": token_delta,
                    "message_delta": message_delta,
                    "max_message_id": max_message_id,
                    "summary_token_count": int(chat_session.summary_token_count or 0),
                    "profile_token_count": int(chat_session.profile_token_count or 0),
                    "profile_message_count": int(chat_session.profile_message_count or 0),
                    "ltm_token_count": int(chat_session.ltm_token_count or 0),
                    "ltm_message_count": int(chat_session.ltm_message_count or 0),
                }
        except Exception as exc:
            logger.error("[ChatMemoryService] post-turn 计数更新失败 user=%s session=%s err=%s", user_id, session_id, exc)
        token_delta = estimate_token_count(user_message) + estimate_token_count(assistant_reply)
        return {
            "token_delta": token_delta,
            "message_delta": int(bool(user_message)) + int(bool(assistant_reply)),
            "max_message_id": 0,
            "summary_token_count": 0,
            "profile_token_count": 0,
            "profile_message_count": 0,
            "ltm_token_count": 0,
            "ltm_message_count": 0,
        }

    async def _turn_message_stats(
        self,
        *,
        db: Any,
        user_id: int,
        session_id: str,
        turn_id: int | None,
        user_message: str,
        assistant_reply: str,
        usage_metadata: dict[str, Any] | None = None,
    ) -> tuple[int, int, int]:
        if turn_id is not None:
            messages = list(
                (
                    await db.exec(
                        select(ChatMessage)
                        .where(
                            ChatMessage.user_id == user_id,
                            ChatMessage.session_id == session_id,
                            ChatMessage.module == self.module,
                            ChatMessage.turn_id == turn_id,
                            ChatMessage.role.in_(["user", "assistant"]),
                        )
                        .order_by(ChatMessage.id.asc())
                    )
                ).all()
            )
            if messages:
                stored_tokens = sum(estimate_token_count(message.content or "") for message in messages)
                token_delta = int(usage_metadata.get("total_tokens") or stored_tokens) if usage_metadata else stored_tokens
                return token_delta, len(messages), int(messages[-1].id or 0)

        fallback_messages = [text for text in (user_message, assistant_reply) if str(text or "").strip()]
        if usage_metadata and "total_tokens" in usage_metadata:
            token_delta = int(usage_metadata["total_tokens"] or 0)
        else:
            token_delta = sum(estimate_token_count(text) for text in fallback_messages)
        return token_delta, len(fallback_messages), 0

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
                return await self.compressor.needs_compression(
                    db=db,
                    user_id=user_id,
                    session_id=session_id,
                )
        except Exception as exc:
            logger.error("[ChatMemoryService] compression need check failed: %s", exc)
            return False

    async def compress_session(
        self,
        *,
        user_id: int,
        session_id: str,
        reason: str = "compress_session",
    ):
        try:
            async with session_scope() as db:
                return await self.compressor.maybe_compress(
                    db=db,
                    user_id=user_id,
                    session_id=session_id,
                    reason=reason,
                )
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
                after_message_id = int(chat_session.last_ltm_message_id or 0) if chat_session else 0
                new_dialogue, message_count, latest_message_id = await self._build_dialogue_since(
                    db=db,
                    user_id=user_id,
                    session_id=session_id,
                    after_message_id=after_message_id,
                    limit=60,
                )
                if not new_dialogue or latest_message_id <= after_message_id:
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
                return {**result, "latest_message_id": latest_message_id}
        except Exception as exc:
            logger.error("[ChatMemoryService] long-term update failed: %s", exc)
            return {"updated": False, "analyzed": False, "error": str(exc)}

    async def should_update_long_term_memory(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str,
        assistant_reply: str,
    ) -> tuple[bool, dict[str, Any]]:
        """判断本轮是否应该尝试长期记忆更新，返回调度信息。"""
        signal_detected = has_stable_signal(user_message) or (
            has_stable_signal(assistant_reply)
            and any(keyword in assistant_reply for keyword in ("以后", "下次", "记住", "偏好", "纠正"))
        )
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
                    return signal_detected, {
                        "signal_detected": signal_detected,
                        "ltm_token_count": 0,
                        "ltm_message_count": 0,
                    }

                token_count = int(chat_session.ltm_token_count or 0)
                message_count = int(chat_session.ltm_message_count or 0)
                threshold_due = token_count >= LTM_MIN_TOKENS or message_count >= LTM_MIN_MESSAGES
                last_updated = chat_session.last_ltm_updated_at
                cooldown_ok = (
                    last_updated is None
                    or (now() - last_updated).total_seconds() >= LTM_COOLDOWN_MINUTES * 60
                )
                has_new_messages = message_count > 0
                return (signal_detected or threshold_due) and cooldown_ok and has_new_messages, {
                    "signal_detected": signal_detected,
                    "threshold_due": threshold_due,
                    "cooldown_ok": cooldown_ok,
                    "ltm_token_count": token_count,
                    "ltm_message_count": message_count,
                    "last_ltm_message_id": int(chat_session.last_ltm_message_id or 0),
                }
        except Exception as exc:
            logger.error("[ChatMemoryService] long-term schedule check failed: %s", exc)
            return False, {"signal_detected": False, "error": str(exc)}

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
            .where(
                ChatMessage.user_id == user_id,
                ChatMessage.session_id == session_id,
                ChatMessage.module == self.module,
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
            content = (message.content or "").strip()
            if not content:
                continue
            role_label = "学生" if message.role == "user" else "辅导老师"
            lines.append(f"{role_label}：{content[:700]}")
        return "\n".join(lines), len(messages), latest_message_id


# -------------------------------------------------------------------
# 模块级缓存：按 module 名缓存 ChatMemoryService 单例
# 确保同一 module 的所有调用共享同一实例，避免重复初始化管线组件。
# -------------------------------------------------------------------
_chat_memory_service_cache: dict[str, ChatMemoryService] = {}


# -------------------------------------------------------------------
# get_chat_memory_service: 获取指定 module 的 ChatMemoryService 单例
#
# 按 module 隔离缓存，首次访问时创建实例并缓存，后续直接返回。
# module 参数区分不同业务域（如 mentor、quiz），各域的记忆管线
# 使用独立的压缩器和长期记忆服务实例。
# -------------------------------------------------------------------
def get_chat_memory_service(*, module: str = "mentor") -> ChatMemoryService:
    if module not in _chat_memory_service_cache:
        _chat_memory_service_cache[module] = ChatMemoryService(module=module)
    return _chat_memory_service_cache[module]
