"""概要服务层。

模块职责：
- 概要业务逻辑
- 会话压缩
"""

from __future__ import annotations

from app.infra.logging import get_logger
from app.memory.message.store import MessageStore
from app.memory.message.types import DIALOGUE_ROLES
from app.memory.session.store import SessionStore
from app.memory.summary.store import SummaryStore
from app.memory.summary.types import SUMMARY_TOKEN_THRESHOLD

logger = get_logger(__name__)


class SummaryService:
    """概要服务。"""

    def __init__(self, module: str = "mentor") -> None:
        self.module = module
        self.summary_store = SummaryStore()
        self.message_store = MessageStore()
        self.session_store = SessionStore()

    async def should_create(self, user_id: int, session_id: str) -> bool:
        """判断是否需要生成概要。"""
        count = await self.session_store.get_token_count(session_id)
        return count >= SUMMARY_TOKEN_THRESHOLD

    async def compress(
        self,
        user_id: int,
        session_id: str,
        keep_recent: int = 10,
    ) -> bool:
        """生成概要并压缩旧消息。"""
        # 获取对话消息
        messages = await self.message_store.get_recent(
            user_id, session_id, self.module, limit=50
        )
        dialogue = [
            m for m in messages
            if m.role in DIALOGUE_ROLES and m.content.strip()
        ]
        if not dialogue:
            return False

        # 生成简单概要
        chat_text = "\n".join(
            f"[{m.created_at.strftime('%m-%d %H:%M')}] {m.role}: {m.content[:500]}"
            for m in dialogue
        )
        logger.info("[SummaryService] 创建会话概要")

        await self.summary_store.create(
            user_id=user_id,
            session_id=session_id,
            module=self.module,
            summary_markdown=f"# 会话概要\n\n## 最近对话\n\n{chat_text[:3000]}",
            summary_json=None,
            summarized_message_count=len(dialogue),
        )

        # 清理旧消息
        if keep_recent > 0:
            await self.message_store.delete_old(
                user_id, session_id, self.module, keep_recent
            )

        # 重置计数
        await self.session_store.reset_token_count(session_id)
        return True

    async def list(
        self,
        user_id: int,
        session_id: str,
        limit: int = 3,
    ) -> list:
        """获取概要列表。"""
        return await self.summary_store.list(user_id, session_id, self.module, limit)

    async def get_latest(self, user_id: int, session_id: str):
        """获取最新概要。"""
        return await self.summary_store.get_latest(user_id, session_id, self.module)
