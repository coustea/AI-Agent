"""长期记忆提取。"""

from __future__ import annotations

import time
from typing import Any

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.memory.store import MemoryStore
from app.memory.types import (
    MEMORY_UPDATE_COOLDOWN_SECONDS,
    MemoryUpdateOutput,
    has_stable_signal,
    render_memory_markdown,
)

logger = get_logger(__name__)


class LongTermMemoryExtractor:
    """只在明确稳定信号出现时更新长期记忆。"""

    def __init__(self, *, module: str = "mentor", store: MemoryStore | None = None) -> None:
        self.module = module
        self.store = store or MemoryStore()
        self.llm = get_llm()
        self._last_update_at: dict[int, float] = {}

    def should_consider_update(
        self,
        *,
        user_message: str,
        assistant_reply: str,
        summary_candidates: list[str] | None = None,
    ) -> bool:
        if has_stable_signal(user_message):
            return True
        if summary_candidates:
            return any(has_stable_signal(str(item)) for item in summary_candidates)
        # 助手回复只有在记录了用户纠正/后续规则时才算信号，不因文本长短触发。
        return has_stable_signal(assistant_reply) and any(keyword in assistant_reply for keyword in ("以后", "下次", "记住", "偏好", "纠正"))

    async def maybe_update(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str,
        assistant_reply: str,
        compression_result: Any | None = None,
    ) -> bool:
        summary_json = getattr(compression_result, "summary_json", None) if compression_result else None
        summary_candidates = (summary_json or {}).get("memory_candidates") or []
        if not self.should_consider_update(
            user_message=user_message,
            assistant_reply=assistant_reply,
            summary_candidates=summary_candidates,
        ):
            return False

        now_ts = time.time()
        last = self._last_update_at.get(user_id, 0)
        if now_ts - last < MEMORY_UPDATE_COOLDOWN_SECONDS and not summary_candidates:
            return False

        try:
            old_memory = await self.store.get_or_create_long_term_memory(user_id=user_id, module=self.module)
            latest_summary = await self.store.get_latest_summary(user_id=user_id, session_id=session_id, module=self.module)
            prompt = self._build_prompt(
                user_message=user_message,
                assistant_reply=assistant_reply,
                summary_text=latest_summary.summary_markdown if latest_summary else "暂无会话概要。",
                old_memory_text=old_memory.memory_markdown if old_memory else "暂无长期记忆。",
                summary_candidates=summary_candidates,
            )
            resp = await self.llm.ainvoke_json(
                MemoryUpdateOutput,
                prompt,
                function_name="update_long_term_memory",
                function_description="判断是否需要更新长期记忆，如需更新返回新的记忆 JSON。",
                temperature=0.1,
            )
            if not resp.need_update or not resp.memory_json:
                return False
            await self.store.update_long_term_memory(
                user_id=user_id,
                module=self.module,
                memory_markdown=render_memory_markdown(resp.memory_json),
                memory_json=resp.memory_json,
                updated_reason="基于稳定信号更新长期记忆",
                source_session_ids=[session_id],
                source_summary_ids=[latest_summary.id] if latest_summary and latest_summary.id else None,
            )
            self._last_update_at[user_id] = time.time()
            return True
        except Exception as exc:
            logger.error("[LongTermMemory] 更新失败 user=%s session=%s err=%s", user_id, session_id, exc)
            return False

    def _build_prompt(
        self,
        *,
        user_message: str,
        assistant_reply: str,
        summary_text: str,
        old_memory_text: str,
        summary_candidates: list[str],
    ) -> str:
        candidates = "\n".join(f"- {item}" for item in summary_candidates) or "暂无。"
        return f"""请根据对话内容更新用户长期记忆。

只保存长期稳定、未来可复用的信息，例如用户固定偏好、学习背景、长期目标、反复薄弱点、用户纠正。
不要保存当前会话临时状态、一次性作业中间过程、普通闲聊或仅因文本很长而产生的信息。

用户消息：
{user_message[:1000]}

助手回复：
{assistant_reply[:1000]}

概要候选：
{candidates[:1200]}

会话概要：
{summary_text[:2000]}

旧长期记忆：
{old_memory_text[:3000]}

返回 need_update 与完整 memory_json。"""
