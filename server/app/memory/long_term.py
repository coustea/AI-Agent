"""长期记忆提取。"""

from __future__ import annotations

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.models import ChatSessionSummary, UserLongTermMemory
from app.memory.prompt_manager import memory_prompts
from app.memory.types import (
    LTM_PERIODIC_THRESHOLD,
    MEMORY_UPDATE_COOLDOWN_SECONDS,
    MemoryUpdateOutput,
    has_stable_signal,
    make_default_memory_markdown,
    now,
)

logger = get_logger(__name__)


class LongTermMemoryExtractor:
    """长期记忆提取器：双层触发（正则即时 + 周期性 LLM 判断）。"""

    def __init__(self, *, module: str = "mentor") -> None:
        """初始化长期记忆提取器，指定模块名。"""
        self.module = module
        self.llm = get_llm()

    def should_consider_update(
        self,
        *,
        user_message: str,
        assistant_reply: str,
    ) -> bool:
        """检测对话中是否包含稳定信号，决定是否考虑更新长期记忆。"""
        if has_stable_signal(user_message):
            return True
        return has_stable_signal(assistant_reply) and any(
            keyword in assistant_reply for keyword in ("以后", "下次", "记住", "偏好", "纠正")
        )

    async def maybe_update(
        self,
        *,
        db: AsyncSession,
        user_id: int,
        session_id: str,
        user_message: str,
        assistant_reply: str,
        turn_count: int = 0,
    ) -> bool:
        """双层触发更新：信号即时触发或周期性 LLM 判断，返回是否更新成功。"""
        signal_detected = self.should_consider_update(user_message=user_message, assistant_reply=assistant_reply)
        periodic_trigger = turn_count > 0 and turn_count % LTM_PERIODIC_THRESHOLD == 0

        if not signal_detected and not periodic_trigger:
            return False

        trigger_reason = "signal" if signal_detected else "periodic"
        logger.info("[LongTermMemory] 触发更新: user_id=%s session_id=%s reason=%s turn=%d", user_id, session_id, trigger_reason, turn_count)

        try:
            existing = (
                await db.exec(select(UserLongTermMemory).where(UserLongTermMemory.user_id == user_id, UserLongTermMemory.module == self.module))
            ).first()

            if existing:
                old_memory = existing
            else:
                old_memory = UserLongTermMemory(
                    user_id=user_id,
                    module=self.module,
                    memory_markdown=make_default_memory_markdown(),
                    category="general",
                )
                db.add(old_memory)
                await db.flush()

            if not signal_detected and periodic_trigger:
                if old_memory.updated_at and (now() - old_memory.updated_at).total_seconds() < MEMORY_UPDATE_COOLDOWN_SECONDS:
                    return False

            latest_summary = (
                await db.exec(
                    select(ChatSessionSummary)
                    .where(
                        ChatSessionSummary.user_id == user_id,
                        ChatSessionSummary.session_id == session_id,
                        ChatSessionSummary.module == self.module,
                    )
                    .order_by(ChatSessionSummary.created_at.desc())
                    .limit(1)
                )
            ).first()
            prompt = memory_prompts.render_ltm_update(
                user_message=user_message[:1000],
                assistant_reply=assistant_reply[:1000],
                session_summary=latest_summary.summary_markdown if latest_summary else "暂无会话概要。",
                old_memory=old_memory.memory_markdown if old_memory else "暂无长期记忆。",
            )
            resp = await self.llm.ainvoke_json(
                MemoryUpdateOutput,
                prompt,
                function_name="update_long_term_memory",
                function_description="判断是否需要更新长期记忆，如需更新返回新的记忆 Markdown。",
                temperature=0.1,
            )
            if not resp.need_update or not resp.memory_markdown:
                return False

            if not existing:
                memory = old_memory
            else:
                memory = existing
                memory.version = (memory.version or 1) + 1
            memory.memory_markdown = resp.memory_markdown
            memory.category = "general"
            memory.updated_reason = "基于稳定信号更新长期记忆" if signal_detected else "周期性检查更新长期记忆"
            memory.source_session_ids = [session_id]
            memory.source_summary_ids = [latest_summary.id] if latest_summary and latest_summary.id else None
            memory.updated_at = now()
            db.add(memory)
            logger.info("[LongTermMemory] 更新成功: user_id=%s session_id=%s version=%d reason=%s", user_id, session_id, memory.version, memory.updated_reason)
            return True
        except Exception as exc:
            logger.error("[LongTermMemory] 更新失败 user=%s session=%s err=%s", user_id, session_id, exc)
            return False
