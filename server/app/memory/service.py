"""记忆系统统一门面。"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.config import MSG_LIMIT
from app.memory.store import MemoryStore
from app.memory.types import (
    DEFAULT_SESSION_TITLE,
    ModuleName,
    estimate_token_count,
    should_include_session_summary,
    truncate_text,
)
from app.memory.compression import SessionCompressor
from app.memory.long_term import LongTermMemoryExtractor
from app.memory.profile import ProfileBuilder, render_profile_markdown

logger = get_logger(__name__)


class MemoryService:
    """统一入口：所有记忆相关操作通过此门面调用。"""

    def __init__(self, *, module: str = ModuleName.MENTOR) -> None:
        self.module = module
        self.store = MemoryStore()
        self.compressor = SessionCompressor(module=module, store=self.store)
        self.ltm_extractor = LongTermMemoryExtractor(module=module, store=self.store)
        self.profile_builder = ProfileBuilder(module=module, store=self.store)
        self.llm = get_llm()

    # ── 会话 ──

    async def create_session(self, *, user_id: int, title: str = DEFAULT_SESSION_TITLE) -> Any:
        return await self.store.create_session(user_id=user_id, module=self.module, title=title)

    async def get_session(self, session_id: str) -> Any:
        return await self.store.get_session(session_id)

    async def list_sessions(self, *, user_id: int, limit: int = 20) -> list[Any]:
        return await self.store.list_sessions(user_id=user_id, module=self.module, limit=limit)

    async def archive_session(self, *, user_id: int, session_id: str) -> bool:
        return await self.store.archive_session(user_id=user_id, session_id=session_id)

    async def update_session_title(self, *, user_id: int, session_id: str, title: str) -> bool:
        return await self.store.update_session_title(user_id=user_id, session_id=session_id, title=title)

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
        teaching_diagram: dict[str, Any] | None = None,
    ) -> None:
        await self.store.save_message(
            user_id=user_id,
            session_id=session_id,
            module=self.module,
            role=role,
            content=content,
            attachments=attachments,
            tool_calls=tool_calls,
            teaching_diagram=teaching_diagram,
        )

    async def list_messages(self, *, user_id: int, session_id: str, limit: int | None = None, only_unexpired: bool = True) -> list[Any]:
        return await self.store.list_messages(user_id=user_id, session_id=session_id, module=self.module, limit=limit, only_unexpired=only_unexpired)

    async def count_messages(self, *, user_id: int, session_id: str) -> int:
        return await self.store.count_messages(user_id=user_id, session_id=session_id, module=self.module)

    async def delete_short_term_messages(self, *, user_id: int, session_id: str) -> int:
        return await self.store.delete_session_messages(user_id=user_id, session_id=session_id, module=self.module)

    async def reset_session_counters(self, *, user_id: int, session_id: str) -> None:
        await self.store.reset_session_token_count(session_id)

    async def update_attachment_analyses(self, *, user_id: int, session_id: str, analyses: dict[str, Any]) -> bool:
        """更新会话的附件预分析结果。"""
        return await self.store.update_attachment_analyses(session_id=session_id, user_id=user_id, analyses=analyses)

    # ── 概要 ──

    async def list_summaries(self, *, user_id: int, session_id: str, limit: int = 3) -> list[Any]:
        return await self.store.list_summaries(user_id=user_id, session_id=session_id, module=self.module, limit=limit)

    # ── 画像 ──

    async def get_profile(self, *, user_id: int) -> Any:
        return await self.store.get_profile(user_id=user_id, module=self.module)

    async def get_or_create_profile(self, *, user_id: int) -> Any:
        return await self.store.get_or_create_profile(user_id=user_id, module=self.module)

    async def upsert_profile(
        self,
        *,
        user_id: int,
        session_id: str | None = None,
        onboarding: dict[str, Any] | None = None,
        reason: str = "manual",
    ) -> Any:
        return await self.profile_builder.upsert(
            user_id=user_id,
            session_id=session_id,
            onboarding=onboarding,
            reason=reason,
        )

    async def list_profile_history(self, *, user_id: int, limit: int = 20) -> list[Any]:
        return await self.store.list_profile_history(user_id=user_id, module=self.module, limit=limit)

    async def get_onboarding(self, *, user_id: int) -> dict[str, Any]:
        return await self.profile_builder.get_onboarding(user_id)

    # ── 长期记忆 ──

    async def get_long_term_memory(self, *, user_id: int) -> Any:
        return await self.store.get_long_term_memory(user_id=user_id, module=self.module)

    async def get_or_create_long_term_memory(self, *, user_id: int) -> Any:
        return await self.store.get_or_create_long_term_memory(user_id=user_id, module=self.module)

    # ── 工具记忆构建 ──

    async def get_profile_markdown(self, user_id: int) -> str:
        profile = await self.store.get_profile(user_id=user_id, module=self.module)
        if not profile:
            return "暂无画像信息（新用户），请直接开始对话。"
        if profile.profile_markdown and profile.profile_markdown.strip():
            return profile.profile_markdown
        if profile.profile_json:
            return render_profile_markdown(profile.profile_json)
        return "暂无画像信息。"

    async def get_memory_markdown(self, user_id: int) -> str:
        memory = await self.store.get_long_term_memory(user_id=user_id, module=self.module)
        if not memory or not memory.memory_markdown:
            return "暂无长期记忆。"
        return memory.memory_markdown

    def build_file_context(self, attachments: list[str]) -> str:
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

    async def build_recent_chat_context(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str,
        attachments: list[str] | None = None,
    ) -> tuple[list[AnyMessage], str]:
        raw_messages = await self.store.list_messages(user_id=user_id, session_id=session_id, module=self.module, limit=MSG_LIMIT)
        selected = self._select_recent_messages(raw_messages, user_message=user_message)
        messages: list[AnyMessage] = []
        for message in selected:
            if message.role == "user":
                messages.append(HumanMessage(content=message.content))
            elif message.role == "assistant":
                messages.append(AIMessage(content=message.content))
        content = user_message
        IMAGE_EXTS = {"png", "jpg", "jpeg", "gif", "webp"}
        image_urls, file_urls = [], []
        for url in (attachments or []):
            ext = url.rsplit(".", 1)[-1].lower().split("?")[0] if "." in url else ""
            if ext in IMAGE_EXTS:
                image_urls.append(url)
            else:
                file_urls.append(url)
        if image_urls:
            content += f"\n[Attached Images: {', '.join(image_urls)}]"
        if file_urls:
            content += f"\n[Attached Files: {', '.join(file_urls)}]"
        messages.append(HumanMessage(content=content))

        recent_ctx = self._render_recent_chat(selected)
        if should_include_session_summary(user_message):
            summary_ctx = await self._build_session_summary_context(user_id, session_id)
            if summary_ctx != "暂无会话概要。":
                recent_ctx = f"# 会话概要\n{summary_ctx}\n\n# 最近对话\n{recent_ctx}"
            cross_ctx = await self._build_cross_session_context(user_id, session_id)
            if cross_ctx:
                recent_ctx = f"{cross_ctx}\n\n{recent_ctx}"
        return messages, recent_ctx

    async def _build_session_summary_context(self, user_id: int, session_id: str) -> str:
        summaries = await self.store.list_summaries(user_id=user_id, session_id=session_id, module=self.module, limit=2)
        if not summaries:
            return "暂无会话概要。"
        return "\n\n---\n\n".join(summary.summary_markdown for summary in summaries if summary.summary_markdown)

    async def _build_cross_session_context(self, user_id: int, current_session_id: str, char_budget: int = 800) -> str:
        summaries = await self.store.list_cross_session_summaries(
            user_id=user_id,
            module=self.module,
            exclude_session_id=current_session_id,
            limit=5,
        )
        chunks: list[str] = []
        for summary in summaries:
            if summary.summary_markdown and summary.summary_markdown.strip():
                first_line = summary.summary_markdown.strip().split("\n")[0]
                chunks.append(f"- {first_line}")
        return truncate_text("# 其他会话概要\n" + "\n".join(chunks), char_budget) if chunks else ""

    @staticmethod
    def _select_recent_messages(messages: list[Any], *, user_message: str, char_budget: int = 4000) -> list[Any]:
        dialogue = [
            message
            for message in messages
            if getattr(message, "role", None) in {"user", "assistant"} and (getattr(message, "content", "") or "").strip()
        ]
        if dialogue and getattr(dialogue[-1], "role", None) == "user" and (getattr(dialogue[-1], "content", "") or "").strip() == (user_message or "").strip():
            dialogue = dialogue[:-1]
        selected: list[Any] = []
        used_chars = 0
        for message in reversed(dialogue):
            line = f"- {'用户' if getattr(message, 'role', '') == 'user' else '助手'}: {(getattr(message, 'content', '') or '').strip()}"
            next_size = len(line) + 1
            if selected and used_chars + next_size > char_budget:
                continue
            if not selected and next_size > char_budget:
                selected.append(message)
                break
            selected.append(message)
            used_chars += next_size
        return list(reversed(selected))

    @staticmethod
    def _render_recent_chat(messages: list[Any], char_budget: int = 4000) -> str:
        context = "\n".join(
            f"- {'用户' if getattr(m, 'role', '') == 'user' else '助手'}: {truncate_text((getattr(m, 'content', '') or '').strip(), char_budget)}"
            for m in messages
        )
        return truncate_text(context, char_budget) if context else "最近 7 天暂无历史对话。"

    # ── 工作流 ──

    async def after_turn(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str,
        assistant_reply: str,
        enable_long_term_memory: bool = True,
    ) -> None:
        delta = estimate_token_count(user_message) + estimate_token_count(assistant_reply)
        try:
            await self.store.add_session_token_count(session_id=session_id, user_id=user_id, module=self.module, delta=delta)
        except Exception as exc:
            logger.error("[MemoryService] token 计数更新失败 user=%s session=%s err=%s", user_id, session_id, exc)

        await self.post_turn(
            user_id=user_id,
            session_id=session_id,
            user_message=user_message,
            assistant_reply=assistant_reply,
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
        """单轮对话后执行记忆管线：压缩 → 长期记忆 → 画像。"""
        results: dict[str, bool] = {}

        try:
            summary = await self.compressor.maybe_compress(
                user_id=user_id,
                session_id=session_id,
                reason="post_turn",
            )
            results["compressed"] = summary is not None
        except Exception as exc:
            logger.error("[MemoryService] 压缩失败: %s", exc)
            results["compressed"] = False

        try:
            updated = await self.ltm_extractor.maybe_update(
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
            updated = await self.profile_builder.maybe_upsert(
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
                await self.compressor.maybe_compress(
                    user_id=user_id,
                    session_id=session_id,
                    force=True,
                    reason="logout",
                )
            except Exception as exc:
                logger.error("[MemoryService] 登出压缩失败: %s", exc)

        try:
            await self.profile_builder.upsert(user_id=user_id, session_id=session_id, reason="logout")
        except Exception as exc:
            logger.error("[MemoryService] 登出画像更新失败: %s", exc)

    # ── Token 计数 ──

    async def add_session_token_count(self, *, session_id: str, user_id: int, delta: int) -> int:
        return await self.store.add_session_token_count(session_id=session_id, user_id=user_id, module=self.module, delta=delta)


# ============ 模块级单例工厂 ============

_memory_service_cache: dict[str, MemoryService] = {}


def get_memory_service(*, module: str = ModuleName.MENTOR) -> MemoryService:
    """获取模块级 MemoryService 单例，同 module 复用同一实例。"""
    if module not in _memory_service_cache:
        _memory_service_cache[module] = MemoryService(module=module)
    return _memory_service_cache[module]
