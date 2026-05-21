"""记忆系统后处理工作流。"""

from __future__ import annotations

from app.infra.logging import get_logger
from app.memory.compression import SessionCompressor
from app.memory.long_term import LongTermMemoryExtractor
from app.memory.profile import ProfileBuilder
from app.memory.store import MemoryStore
from app.memory.types import estimate_token_count

logger = get_logger(__name__)


class MemoryWorkflow:
    """对话回合结束后的记忆工作流。"""

    def __init__(
        self,
        *,
        module: str = "mentor",
        store: MemoryStore | None = None,
        compressor: SessionCompressor | None = None,
        long_term: LongTermMemoryExtractor | None = None,
        profile: ProfileBuilder | None = None,
    ) -> None:
        self.module = module
        self.store = store or MemoryStore()
        self.compressor = compressor or SessionCompressor(module=module, store=self.store)
        self.long_term = long_term or LongTermMemoryExtractor(module=module, store=self.store)
        self.profile = profile or ProfileBuilder(module=module, store=self.store)

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
            await self.store.add_session_token_count(
                session_id=session_id,
                user_id=user_id,
                module=self.module,
                delta=delta,
            )
        except Exception as exc:
            logger.error("[MemoryWorkflow] token 计数更新失败 user=%s session=%s err=%s", user_id, session_id, exc)

        compression_result = None
        try:
            compression_result = await self.compressor.maybe_compress(
                user_id=user_id,
                session_id=session_id,
                reason="post_turn",
            )
        except Exception as exc:
            logger.error("[MemoryWorkflow] 会话压缩失败 user=%s session=%s err=%s", user_id, session_id, exc)

        if enable_long_term_memory:
            try:
                if self.long_term.should_consider_update(
                    user_message=user_message,
                    assistant_reply=assistant_reply,
                    summary_candidates=(getattr(compression_result, "summary_json", None) or {}).get("memory_candidates", [])
                    if compression_result
                    else None,
                ):
                    await self.long_term.maybe_update(
                        user_id=user_id,
                        session_id=session_id,
                        user_message=user_message,
                        assistant_reply=assistant_reply,
                        compression_result=compression_result,
                    )
            except Exception as exc:
                logger.error("[MemoryWorkflow] 长期记忆提取失败 user=%s session=%s err=%s", user_id, session_id, exc)

        try:
            await self.profile.maybe_upsert(
                user_id=user_id,
                session_id=session_id,
                user_message=user_message,
                assistant_reply=assistant_reply,
                compression_result=compression_result,
            )
        except Exception as exc:
            logger.error("[MemoryWorkflow] 画像更新失败 user=%s session=%s err=%s", user_id, session_id, exc)
