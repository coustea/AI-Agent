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
    SummaryLLMOutput,
    make_default_summary_json,
    render_summary_markdown,
)

logger = get_logger(__name__)


class SessionCompressor:
    """按触发条件把旧消息压缩为结构化概要。"""

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
        summary_json = None
        try:
            prompt = (
                "请压缩以下学习对话，保留后续教学真正需要的信息。\n\n"
                "必须提取：current_learning_task、original_user_questions、explained_content、"
                "current_understanding、current_confusions、teaching_methods_used、conversation_position、"
                "next_action、references、profile_candidates、memory_candidates。\n"
                "profile_candidates 记录可更新用户画像的信息；memory_candidates 只记录长期稳定偏好、固定事实、反复薄弱点。\n\n"
                f"对话记录：\n{chat_text[:5000]}"
            )

            logger.info("[MemoryCompression] LLM 开始会话压缩。")

            resp = await self.llm.ainvoke_json(
                SummaryLLMOutput,
                prompt,
                function_name="compress_learning_dialogue",
                function_description="压缩学习对话并提取画像/长期记忆候选。",
                temperature=0.1,
            )
            summary_json = resp.model_dump()
        except Exception as exc:
            logger.warning("[MemoryCompression] LLM 压缩失败，降级拼接概要: %s", exc)

        if summary_json is None:
            summary_json = make_default_summary_json()
            summary_json["current_learning_task"] = "对话概要（LLM 不可用，降级为文本拼接）"
            summary_json["original_user_questions"] = [chat_text[:800]]
            summary_json["conversation_position"] = reason

        summary = await self.store.create_summary(
            user_id=user_id,
            session_id=session_id,
            module=self.module,
            summary_markdown=render_summary_markdown(summary_json),
            summary_json=summary_json,
            summarized_message_count=len(target),
            start_message_id=target[0].id,
            end_message_id=target[-1].id,
            current_topic=(summary_json.get("current_learning_task") or "")[:200] or None,
            current_goal=(summary_json.get("next_action") or "")[:200] or None,
            current_status=summary_json.get("conversation_position") or None,
            next_action=summary_json.get("next_action") or None,
        )
        first_kept = dialogue[-keep_recent].id if keep_recent > 0 else (target[-1].id + 1 if target[-1].id else 0)
        if first_kept:
            await self.store.delete_messages_before(user_id=user_id, session_id=session_id, module=self.module, before_message_id=first_kept)
        await self.store.reset_session_token_count(session_id)
        return summary
