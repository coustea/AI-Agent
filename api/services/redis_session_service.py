"""基于 Redis 的会话服务层。"""

from typing import List, Optional

from api.db.repositories.redis_session import RedisSessionRepository
from api.db.models import (
    SessionCreate,
    SessionRead,
    MessageRead,
    ChatRequest,
)
from api.services.redis_service import RedisService


class RedisSessionService:
    """基于 Redis 的会话服务。"""

    def __init__(self, redis_client: RedisService):
        self.redis = redis_client
        self.session_repo = RedisSessionRepository(redis_client)

    # ================= 会话管理 =================

    def create_session(self, user_id: int, session_data: SessionCreate) -> SessionRead:
        """创建新会话。"""
        session = self.session_repo.create_session(
            user_id, session_data.title or "新会话"
        )

        return SessionRead(
            session_id=session["session_id"],
            title=session["title"],
            created_at=session["created_at"],
            updated_at=session["updated_at"],
        )

    def get_session(self, user_id: int, session_id: str) -> Optional[SessionRead]:
        """获取会话信息。"""
        session = self.session_repo.get_session(user_id, session_id)
        if not session:
            return None

        return SessionRead(
            session_id=session["session_id"],
            title=session["title"],
            created_at=session["created_at"],
            updated_at=session["updated_at"],
        )

    def list_sessions(self, user_id: int) -> List[SessionRead]:
        """获取用户的会话列表。"""
        sessions = self.session_repo.list_sessions(user_id)

        return [
            SessionRead(
                session_id=s["session_id"],
                title=s["title"],
                created_at=s["created_at"],
                updated_at=s["updated_at"],
            )
            for s in sessions
        ]

    def delete_session(self, user_id: int, session_id: str) -> bool:
        """删除会话（验证用户权限）。"""
        session = self.session_repo.get_session(user_id, session_id)
        if not session or session["user_id"] != user_id:
            return False

        return self.session_repo.delete_session(user_id, session_id)

    def update_session_title(self, user_id: int, session_id: str, title: str) -> Optional[SessionRead]:
        """更新会话标题。"""
        session = self.session_repo.get_session(user_id, session_id)
        if not session or session["user_id"] != user_id:
            return None

        success = self.session_repo.update_session(user_id, session_id, title)
        if not success:
            return None

        updated = self.session_repo.get_session(user_id, session_id)
        return SessionRead(
            session_id=updated["session_id"],
            title=updated["title"],
            created_at=updated["created_at"],
            updated_at=updated["updated_at"],
        )

    # ================= 消息管理 =================

    def get_messages(self, user_id: int, session_id: str) -> List[MessageRead]:
        """获取会话消息（验证用户权限）。"""
        session = self.session_repo.get_session(user_id, session_id)
        if not session or session["user_id"] != user_id:
            return []

        messages = self.session_repo.get_messages(user_id, session_id)

        return [
            MessageRead(
                id=m["id"],
                role=m["role"],
                content=m["content"],
                created_at=m["timestamp"],
            )
            for m in messages
        ]

    def add_user_message(self, user_id: int, session_id: str, content: str) -> MessageRead:
        """添加用户消息。"""
        session = self.session_repo.get_session(user_id, session_id)
        if not session or session["user_id"] != user_id:
            raise ValueError("Session not found or access denied")

        message = self.session_repo.add_message(user_id, session_id, "user", content)

        return MessageRead(
            id=message["id"],
            role=message["role"],
            content=message["content"],
            created_at=message["timestamp"],
        )

    def add_assistant_message(self, user_id: int, session_id: str, content: str) -> MessageRead:
        """添加助手消息。"""
        session = self.session_repo.get_session(user_id, session_id)
        if not session or session["user_id"] != user_id:
            raise ValueError("Session not found or access denied")

        message = self.session_repo.add_message(user_id, session_id, "assistant", content)

        return MessageRead(
            id=message["id"],
            role=message["role"],
            content=message["content"],
            created_at=message["timestamp"],
        )

    # ================= 聊天流程 =================

    def get_chat_messages(self, user_id: int, session_id: str) -> List[dict]:
        """获取适合 Agent 的消息列表（验证用户权限）。"""
        session = self.session_repo.get_session(user_id, session_id)
        if not session or session["user_id"] != user_id:
            return []

        return self.session_repo.get_chat_messages_for_agent(user_id, session_id)
