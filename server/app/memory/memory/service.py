"""长期记忆服务层。

模块职责：
- 判断是否需要更新长期记忆（含冷却期和信息增量判断）
- 从对话中提取长期稳定信息
- 调用 LLM 更新记忆
"""

from __future__ import annotations

import json
import time
from typing import Any

from pydantic import BaseModel, Field

from app.infra.llm import get_llm_manager
from app.infra.logging import get_logger
from app.memory.core.types import ModuleName
from app.memory.memory.store import LongTermMemoryStore
from app.memory.memory.types import (
    has_stable_signal,
    make_default_memory_json,
    render_memory_markdown,
)
from app.memory.profile.store import ProfileStore
from app.memory.summary.store import SummaryStore

logger = get_logger(__name__)

# 冷却期：同一用户两次 LLM 调用之间至少间隔的秒数
MEMORY_UPDATE_COOLDOWN_SECONDS: float = 300.0  # 5 分钟


class MemoryUpdateOutput(BaseModel):
    """记忆更新 LLM 输出模型。"""
    need_update: bool = Field(default=False)
    memory_json: dict[str, Any] | None = Field(default=None)


class LongTermMemoryService:
    """长期记忆服务。"""

    def __init__(self, module: str = ModuleName.MENTOR) -> None:
        self.module = module
        self.store = LongTermMemoryStore()
        self.profile_store = ProfileStore()
        self.summary_store = SummaryStore()
        self.llm = get_llm_manager()
        # 冷却期缓存：user_id -> 上次 LLM 调用的 Unix 时间戳
        self._last_update_at: dict[int, float] = {}

    async def get(self, user_id: int):
        """获取长期记忆。"""
        return await self.store.get(user_id, self.module)

    async def get_or_create(self, user_id: int):
        """获取或创建长期记忆。"""
        return await self.store.get_or_create(user_id, self.module)

    async def should_update(
        self,
        user_id: int,
        user_message: str,
        assistant_reply: str,
    ) -> bool:
        """判断是否需要更新长期记忆。

        综合判断：
        1. 冷却期（同一用户 5 分钟内不重复触发 LLM）
        2. 稳定信号检测
        3. 无明确信号时，文本量足够也触发
        """
        # 冷却期检查
        now = time.time()
        last = self._last_update_at.get(user_id, 0)
        if now - last < MEMORY_UPDATE_COOLDOWN_SECONDS:
            logger.debug(
                "[LongTermMemory] 冷却期内跳过 user_id=%s (%.0fs elapsed)",
                user_id, now - last,
            )
            return False

        # 稳定信号检测
        combined_text = f"{user_message}\n{assistant_reply}"
        if has_stable_signal(user_message):
            return True
        if has_stable_signal(assistant_reply):
            return True

        # 无明确信号时，对话文本量足够也触发（避免漏判）
        if len(combined_text.strip()) > 200:
            return True

        return False

    async def update_from_dialogue(
        self,
        user_id: int,
        session_id: str,
        user_message: str,
        assistant_reply: str,
    ) -> bool:
        """从对话更新长期记忆。返回是否更新成功。"""
        if not await self.should_update(user_id, user_message, assistant_reply):
            return False

        old_memory = await self.store.get_or_create(user_id, self.module)
        session_summary = await self.summary_store.get_latest(user_id, session_id, self.module)

        summary_text = session_summary.summary_markdown if session_summary else "暂无会话概要。"
        old_memory_text = old_memory.memory_markdown if old_memory else "暂无长期记忆。"

        try:
            prompt = self._build_prompt(
                user_message=user_message,
                assistant_reply=assistant_reply,
                summary_text=summary_text,
                old_memory_text=old_memory_text,
            )
            resp = await self.llm.generate_json(
                MemoryUpdateOutput,
                prompt,
                function_name="update_long_term_memory",
                function_description="判断是否需要更新长期记忆，如需更新返回新的记忆 JSON。",
                model_kwargs={"temperature": 0.1, "streaming": False},
            )
        except Exception as e:
            logger.error("[LongTermMemory] LLM 失败: %s", e)
            return False

        if not resp.need_update or not resp.memory_json:
            return False

        memory_markdown = render_memory_markdown(resp.memory_json)

        try:
            await self.store.update(
                user_id=user_id,
                module=self.module,
                memory_markdown=memory_markdown,
                memory_json=resp.memory_json,
                updated_reason="基于对话更新长期记忆",
                source_session_ids=[session_id],
            )
            self._last_update_at[user_id] = time.time()
            return True
        except Exception as e:
            logger.error("[LongTermMemory] 更新失败: %s", e)
            return False

    def _build_prompt(
        self,
        user_message: str,
        assistant_reply: str,
        summary_text: str,
        old_memory_text: str,
    ) -> str:
        """构建 LLM prompt。"""
        return f"""请根据对话内容判断是否需要更新用户的长期记忆。

用户消息：
{user_message[:1000]}

助手回复：
{assistant_reply[:1000]}

会话概要：
{summary_text[:2000]}

旧长期记忆：
{old_memory_text[:3000]}

请判断是否需要更新长期记忆。长期记忆只保存长期稳定、未来可复用的信息，不保存当前会话临时状态。

返回 JSON 格式：
- need_update: 是否需要更新
- memory_json: 如需更新，返回完整的记忆 JSON 结构"""
