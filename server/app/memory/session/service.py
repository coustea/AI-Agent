"""会话服务层。

模块职责：
- 会话业务逻辑
- 会话标题生成
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.models import ChatSession
from app.memory.session.store import SessionStore

logger = get_logger(__name__)


class SessionService:
    """会话服务。"""

    def __init__(self, module: str = "mentor") -> None:
        self.module = module
        self.store = SessionStore()
        self.llm = get_llm()

    async def create(self, user_id: int, title: str = "新对话") -> ChatSession:
        """创建会话。"""
        return await self.store.create(user_id, self.module, title)

    async def get(self, session_id: str) -> ChatSession | None:
        """获取会话。"""
        return await self.store.get(session_id)

    async def list(self, user_id: int, limit: int = 20) -> list[ChatSession]:
        """获取会话列表。"""
        return await self.store.list_by_user(user_id, self.module, limit)

    async def archive(self, user_id: int, session_id: str) -> bool:
        """归档会话。"""
        return await self.store.archive(session_id, user_id)

    async def update_title(self, user_id: int, session_id: str, title: str) -> bool:
        """更新会话标题。"""
        return await self.store.update_title(session_id, user_id, title)

    async def generate_title(
        self,
        user_id: int,
        session_id: str,
        first_message: str,
    ) -> str | None:
        """基于首条消息生成会话标题。"""
        if not (first_message or "").strip():
            return None

        prompt = f"""请根据用户的第一条消息生成一个简短的会话标题（10字以内）。

用户消息：{first_message[:200]}

要求：
1. 标题要简洁，概括主题
2. 不超过10个字
3. 只输出标题，不要其他内容"""

        try:
            logger.info("[SessionService] 生成会话标题")
            response = await self.llm.ainvoke(
                [
                    SystemMessage(content="你是一个会话标题生成助手。"),
                    HumanMessage(content=prompt),
                ],
                temperature=0.3,
                max_tokens=20,
            )
            title = self._normalize_title(response.content)
            if not title:
                return None
            await self.update_title(user_id, session_id, title)
            return title
        except Exception as exc:
            logger.warning(
                "[SessionService] 生成标题失败 user=%s session=%s err=%s",
                user_id, session_id, exc,
            )
            return None

    def _normalize_title(self, title: str) -> str | None:
        """规范化标题。"""
        text = str(title or "").strip().strip("`\"'""''")
        if not text:
            return None
        return text[:15] if len(text) > 15 else text
