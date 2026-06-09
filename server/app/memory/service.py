"""记忆系统统一门面。"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlmodel import func, select

from app.infra.database import session_scope
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.models import (
    ChatMessage,
    ChatSession,
    ChatSessionSummary,
    UserLongTermMemory,
    UserProfile,
    UserProfileHistory,
)
from app.memory.compression import SessionCompressor
from app.memory.long_term import LongTermMemoryExtractor
from app.memory.profile import ProfileBuilder, render_profile_markdown
from app.memory.types import (
    DEFAULT_SESSION_TITLE,
    ModuleName,
    MESSAGE_EXPIRE_DAYS,
    TITLE_MAX_LENGTH,
    make_default_memory_markdown,
    make_default_profile_json,
    make_default_score_json,
    now,
    estimate_token_count,
)

logger = get_logger(__name__)


class MemoryService:
    """统一入口：所有记忆相关操作通过此门面调用。"""

    def __init__(self, *, module: str = ModuleName.MENTOR) -> None:
        """初始化记忆服务门面，创建子组件实例。"""
        self.module = module
        self.compressor = SessionCompressor(module=module)
        self.ltm_extractor = LongTermMemoryExtractor(module=module)
        self.profile_builder = ProfileBuilder(module=module)
        self.llm = get_llm()

    # ── 会话 ──

    async def create_session(self, *, user_id: int, title: str = DEFAULT_SESSION_TITLE) -> Any:
        """创建新的聊天会话。"""
        async with session_scope() as db:
            chat_session = ChatSession(user_id=user_id, module=self.module, title=title)
            db.add(chat_session)
            await db.commit()
            await db.refresh(chat_session)
            return chat_session

    async def get_session(self, session_id: str) -> Any:
        """按 ID 获取会话。"""
        async with session_scope() as db:
            return (await db.exec(select(ChatSession).where(ChatSession.id == session_id))).first()

    async def list_sessions(self, *, user_id: int, limit: int = 20) -> list[Any]:
        """获取用户的未归档会话列表，按更新时间倒序。"""
        async with session_scope() as db:
            stmt = select(ChatSession).where(ChatSession.user_id == user_id, ChatSession.is_archived.is_(False))
            stmt = stmt.where(ChatSession.module == self.module)
            result = await db.exec(stmt.order_by(ChatSession.updated_at.desc()).limit(limit))
            return list(result.all())

    async def archive_session(self, *, user_id: int, session_id: str) -> bool:
        """归档会话，返回是否成功。"""
        async with session_scope() as db:
            chat_session = (
                await db.exec(select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id))
            ).first()
            if not chat_session:
                return False
            chat_session.is_archived = True
            chat_session.updated_at = now()
            db.add(chat_session)
            await db.commit()
            return True

    async def update_session_title(self, *, user_id: int, session_id: str, title: str) -> bool:
        """更新会话标题，超长自动截断。"""
        async with session_scope() as db:
            chat_session = (
                await db.exec(select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id))
            ).first()
            if not chat_session:
                return False
            chat_session.title = title[:TITLE_MAX_LENGTH]
            chat_session.updated_at = now()
            db.add(chat_session)
            await db.commit()
            return True

    async def update_attachment_analyses(self, *, user_id: int, session_id: str, analyses: dict[str, Any]) -> bool:
        """更新会话的附件分析结果。"""
        async with session_scope() as db:
            chat_session = (
                await db.exec(select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id))
            ).first()
            if not chat_session:
                return False
            chat_session.attachment_analyses = analyses
            chat_session.updated_at = now()
            db.add(chat_session)
            await db.commit()
            return True

    async def generate_session_title(self, *, user_id: int, session_id: str, first_message: str) -> str | None:
        """根据首条消息用 LLM 生成会话标题，失败返回 None。"""
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
            logger.warning("[MemoryService] 生成会话标题失败 user=%s session=%s err=%s", user_id, session_id, exc)
            return None

    # ── 消息 ──

    async def save_message(
        self,
        *,
        user_id: int,
        session_id: str,
        role: str,
        content: str,
        attachments: list[dict[str, Any]] | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        knowledge_sources: list[dict[str, Any]] | None = None,
        teaching_diagram: dict[str, Any] | None = None,
        usage_metadata: dict[str, Any] | None = None,
    ) -> None:
        """保存一条聊天消息，同时确保会话存在。"""
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
                    knowledge_sources=knowledge_sources,
                    teaching_diagram=teaching_diagram,
                    usage_metadata=usage_metadata,
                )
            )
            await db.commit()

    async def list_messages(self, *, user_id: int, session_id: str, limit: int | None = None, only_unexpired: bool = True) -> list[Any]:
        """获取会话消息列表，可限制数量和排除过期消息。"""
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
        """统计会话消息总数。"""
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
        """删除会话的所有短期消息，返回删除数量。"""
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
        """重置会话的 token 和轮次计数器（压缩后调用）。"""
        async with session_scope() as db:
            chat_session = (await db.exec(select(ChatSession).where(ChatSession.id == session_id))).first()
            if chat_session:
                chat_session.summary_token_count = 0
                db.add(chat_session)
                await db.commit()

    # ── 概要 ──

    async def list_summaries(self, *, user_id: int, session_id: str, limit: int = 3) -> list[Any]:
        """获取会话的压缩概要列表，按时间倒序。"""
        async with session_scope() as db:
            stmt = (
                select(ChatSessionSummary)
                .where(
                    ChatSessionSummary.user_id == user_id,
                    ChatSessionSummary.session_id == session_id,
                    ChatSessionSummary.module == self.module,
                )
                .order_by(ChatSessionSummary.created_at.desc())
                .limit(limit)
            )
            return list((await db.exec(stmt)).all())

    async def get_session_summary_context(self, *, user_id: int, session_id: str) -> str:
        """拼接最近概要为上下文字符串，供 LLM 使用。"""
        summaries = await self.list_summaries(user_id=user_id, session_id=session_id, limit=2)
        if not summaries:
            return "暂无会话概要。"
        return "\n\n---\n\n".join(
            summary.summary_markdown
            for summary in summaries
            if summary.summary_markdown
        ) or "暂无会话概要。"

    # ── 画像 ──

    async def get_profile(self, *, user_id: int) -> Any:
        """获取用户画像记录，不存在返回 None。"""
        async with session_scope() as db:
            return (
                await db.exec(select(UserProfile).where(UserProfile.user_id == user_id, UserProfile.module == self.module))
            ).first()

    async def get_or_create_profile(self, *, user_id: int) -> Any:
        """获取用户画像，不存在则创建默认画像。"""
        async with session_scope() as db:
            profile = UserProfile(
                user_id=user_id,
                module=self.module,
                profile_json=make_default_profile_json(),
                profile_score_json=make_default_score_json(),
            )
            db.add(profile)
            try:
                await db.commit()
                await db.refresh(profile)
                return profile
            except IntegrityError:
                await db.rollback()
                existing = (
                    await db.exec(select(UserProfile).where(UserProfile.user_id == user_id, UserProfile.module == self.module))
                ).first()
                if existing:
                    return existing
                raise

    async def upsert_profile(
        self,
        *,
        user_id: int,
        session_id: str | None = None,
        onboarding: dict[str, Any] | None = None,
        reason: str = "manual",
    ) -> Any:
        """创建或更新用户画像，委托给 ProfileBuilder。"""
        async with session_scope() as db:
            return await self.profile_builder.upsert(db=db, user_id=user_id, session_id=session_id, onboarding=onboarding, reason=reason)

    async def apply_tutoring_profile_update(
        self,
        *,
        user_id: int,
        payload: dict[str, Any],
    ) -> Any:
        """应用辅导过程中的画像增量更新。"""
        async with session_scope() as db:
            return await self.profile_builder.apply_tutoring_update(db=db, user_id=user_id, payload=payload)

    async def list_profile_history(self, *, user_id: int, limit: int = 20) -> list[Any]:
        """获取用户画像变更历史记录。"""
        async with session_scope() as db:
            stmt = (
                select(UserProfileHistory)
                .where(UserProfileHistory.user_id == user_id, UserProfileHistory.module == self.module)
                .order_by(UserProfileHistory.created_at.desc())
                .limit(limit)
            )
            return list((await db.exec(stmt)).all())

    async def get_onboarding(self, *, user_id: int) -> dict[str, Any]:
        """获取用户入门信息（委托给 ProfileBuilder）。"""
        async with session_scope() as db:
            return await self.profile_builder.get_onboarding(db=db, user_id=user_id)

    # ── 长期记忆 ──

    async def get_long_term_memory(self, *, user_id: int) -> Any:
        """获取用户长期记忆记录。"""
        async with session_scope() as db:
            return (
                await db.exec(select(UserLongTermMemory).where(UserLongTermMemory.user_id == user_id, UserLongTermMemory.module == self.module))
            ).first()

    async def get_or_create_long_term_memory(self, *, user_id: int) -> Any:
        """获取或创建用户长期记忆（不存在时初始化默认模板）。"""
        async with session_scope() as db:
            existing = (
                await db.exec(select(UserLongTermMemory).where(UserLongTermMemory.user_id == user_id, UserLongTermMemory.module == self.module))
            ).first()
            if existing:
                return existing
            memory = UserLongTermMemory(
                user_id=user_id,
                module=self.module,
                memory_markdown=make_default_memory_markdown(),
                category="general",
            )
            db.add(memory)
            await db.commit()
            await db.refresh(memory)
            return memory

    # ── 只读 Agent 上下文 ──

    async def get_profile_markdown(self, user_id: int, dimension: str | None = None) -> str:
        """获取用户画像的 Markdown 文本，可指定只看单个维度。"""
        async with session_scope() as db:
            profile = (
                await db.exec(select(UserProfile).where(UserProfile.user_id == user_id, UserProfile.module == self.module))
            ).first()
            if not profile:
                return "暂无画像信息（新用户），请直接开始对话。"

            if dimension and profile.profile_json:
                from app.memory.profile import render_profile_dimension
                return render_profile_dimension(profile.profile_json, dimension)

            if profile.profile_markdown and profile.profile_markdown.strip():
                return profile.profile_markdown
            if profile.profile_json:
                return render_profile_markdown(profile.profile_json)
            return "暂无画像信息。"

    async def get_memory_markdown(self, user_id: int, category: str | None = None) -> str:
        """获取用户长期记忆的 Markdown 文本，可指定只看某个分类。"""
        async with session_scope() as db:
            memory = (
                await db.exec(select(UserLongTermMemory).where(UserLongTermMemory.user_id == user_id, UserLongTermMemory.module == self.module))
            ).first()
            if not memory or not memory.memory_markdown:
                return "暂无长期记忆。"

            if category:
                from app.memory.types import LTM_CATEGORY_NAMES
                import re
                target_title = LTM_CATEGORY_NAMES.get(category, category)
                pattern = re.compile(rf"## {re.escape(target_title)}\n(.*?)(?=\n## |\Z)", re.DOTALL)
                match = pattern.search(memory.memory_markdown)
                if match:
                    content = match.group(1).strip()
                    if content and content != "暂无信息。":
                        return f"## {target_title}\n{content}"
                return f"记忆中暂无指定的分类（{category}）信息。"

            return memory.memory_markdown

    def build_file_context(self, attachments: list[str]) -> str:
        """将附件 URL 列表转为 LLM 可读的文本上下文。"""
        IMAGE_EXTS = {"png", "jpg", "jpeg", "gif", "webp"}
        image_urls, file_urls = [], []
        for url in attachments:
            ext = url.rsplit(".", 1)[-1].lower().split("?")[0] if "." in url else ""
            if ext in IMAGE_EXTS:
                image_urls.append(url)
            else:
                file_urls.append(url)
        if not image_urls and not file_urls:
            return "本次对话无上传文件。"
        lines: list[str] = []
        if image_urls:
            lines.append(f"图片附件（{len(image_urls)}个）：")
            lines.extend(f"  - {url.split('/')[-1]}" for url in image_urls)
        if file_urls:
            lines.append(f"文档附件（{len(file_urls)}个）：")
            lines.extend(f"  - {url.split('/')[-1]}" for url in file_urls)
        return "\n".join(lines)

    # ── 工作流 ──

    async def after_turn(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str,
        assistant_reply: str,
        usage_metadata: dict[str, Any] | None = None,
    ) -> None:
        """单轮对话后处理：更新 token 计数并触发记忆管线。"""
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
                    chat_session = ChatSession(id=session_id, user_id=user_id, module=self.module, title=DEFAULT_SESSION_TITLE)
                chat_session.summary_token_count = max(0, (chat_session.summary_token_count or 0) + delta)
                chat_session.updated_at = now()
                db.add(chat_session)
                await db.commit()
        except Exception as exc:
            logger.error("[MemoryService] token 计数更新失败 user=%s session=%s err=%s", user_id, session_id, exc)

        await self.post_turn(
            user_id=user_id,
            session_id=session_id,
            user_message=user_message,
            assistant_reply=assistant_reply
        )

    async def post_turn(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str,
        assistant_reply: str,
        turn_count: int = 0
    ) -> dict[str, bool]:
        """单轮对话后执行记忆管线：压缩 → 长期记忆 → 画像。"""
        results: dict[str, bool] = {}

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
            logger.error("[MemoryService] 压缩失败: %s", exc)
            results["compressed"] = False
        try:
            async with session_scope() as db:
                updated = await self.ltm_extractor.maybe_update(
                    db=db,
                    user_id=user_id,
                    session_id=session_id,
                    user_message=user_message,
                    assistant_reply=assistant_reply,
                    turn_count=turn_count,
                )
                results["ltm_updated"] = updated
        except Exception as exc:
            logger.error("[MemoryService] 长期记忆更新失败: %s", exc)
            results["ltm_updated"] = False

        try:
            async with session_scope() as db:
                updated = await self.profile_builder.maybe_upsert(
                    db=db,
                    user_id=user_id,
                    session_id=session_id,
                    user_message=user_message,
                    assistant_reply=assistant_reply,
                    turn_count=turn_count,
                )
                results["profile_updated"] = updated
        except Exception as exc:
            logger.error("[MemoryService] 画像更新失败: %s", exc)
            results["profile_updated"] = False

        return results

    async def on_logout(self, *, user_id: int, session_id: str | None = None) -> None:
        """用户登出时强制压缩和画像更新。"""
        if session_id:
            try:
                async with session_scope() as db:
                    await self.compressor.maybe_compress(
                        db=db,
                        user_id=user_id,
                        session_id=session_id,
                        force=True,
                        reason="logout",
                    )
            except Exception as exc:
                logger.error("[MemoryService] 登出压缩失败: %s", exc)

        try:
            async with session_scope() as db:
                await self.profile_builder.upsert(db=db, user_id=user_id, session_id=session_id, reason="logout")
        except Exception as exc:
            logger.error("[MemoryService] 登出画像更新失败: %s", exc)



# ============ 模块级单例工厂 ============

_memory_service_cache: dict[str, MemoryService] = {}


def get_memory_service(*, module: str = ModuleName.MENTOR) -> MemoryService:
    """获取模块级 MemoryService 单例，同 module 复用同一实例。"""
    if module not in _memory_service_cache:
        _memory_service_cache[module] = MemoryService(module=module)
    return _memory_service_cache[module]
