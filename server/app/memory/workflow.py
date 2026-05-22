"""记忆工作流：单轮对话后的记忆管线。"""

from __future__ import annotations

from app.infra.logging import get_logger
from app.memory.compression import SessionCompressor
from app.memory.context import ContextBuilder
from app.memory.long_term import LongTermMemoryExtractor
from app.memory.profile import ProfileBuilder
from app.memory.store import MemoryStore
from app.memory.types import ModuleName

logger = get_logger(__name__)


class MemoryWorkflow:
    """编排单轮对话后的记忆管线：压缩 → 长期记忆 → 画像。"""

    def __init__(
        self,
        *,
        module: str = ModuleName.MENTOR,
        store: MemoryStore | None = None,
        compressor: SessionCompressor | None = None,
        long_term: LongTermMemoryExtractor | None = None,
        profile: ProfileBuilder | None = None,
    ) -> None:
        self.module = module
        self.store = store or MemoryStore()
        self.compressor = compressor or SessionCompressor(module=module, store=self.store)
        self.ltm_extractor = long_term or LongTermMemoryExtractor(module=module, store=self.store)
        self.profile_builder = profile or ProfileBuilder(module=module, store=self.store)
        self.context_builder = ContextBuilder(module=module, store=self.store)

    async def post_turn(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str,
        assistant_reply: str,
        turn_count: int = 0,
    ) -> dict[str, bool]:
        """单轮对话后执行记忆管线。"""
        results: dict[str, bool] = {}

        try:
            summary = await self.compressor.maybe_compress(
                user_id=user_id,
                session_id=session_id,
                reason="post_turn",
            )
            results["compressed"] = summary is not None
        except Exception as exc:
            logger.error("[MemoryWorkflow] 压缩失败: %s", exc)
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
            logger.error("[MemoryWorkflow] 长期记忆更新失败: %s", exc)
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
            logger.error("[MemoryWorkflow] 画像更新失败: %s", exc)
            results["profile_updated"] = False

        return results

    async def after_turn(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str,
        assistant_reply: str,
        enable_long_term_memory: bool = True,
    ) -> None:
        """兼容旧调用方式的别名。"""
        await self.post_turn(
            user_id=user_id,
            session_id=session_id,
            user_message=user_message,
            assistant_reply=assistant_reply,
        )

    async def build_context(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str = "",
    ):
        return await self.context_builder.build(user_id=user_id, session_id=session_id, user_message=user_message)

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
                logger.error("[MemoryWorkflow] 登出压缩失败: %s", exc)

        try:
            await self.profile_builder.upsert(user_id=user_id, session_id=session_id, reason="logout")
        except Exception as exc:
            logger.error("[MemoryWorkflow] 登出画像更新失败: %s", exc)
