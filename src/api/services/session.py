"""会话服务层。"""

from typing import List, Optional

from sqlmodel import Session

from api.db.repositories.session import SessionRepository
from api.db.models import (
    Session as SessionModel,
    Message,
    SessionCreate,
    SessionRead,
    MessageCreate,
    MessageRead,
    ChatRequest,
    ChatResponse,
)


class SessionService:
    """会话业务逻辑层。"""

    def __init__(self, db: Session):
        self.db = db
        self.session_repo = SessionRepository(db)

    # ================= 会话管理 =================

    def create_session(
        self, user_id: int, session_data: SessionCreate
    ) -> SessionRead:
        """创建新会话。"""
        session = self.session_repo.create_session(user_id, session_data)
        return SessionRead.model_validate(session)

    def get_session(self, session_id: str) -> Optional[SessionRead]:
        """获取会话信息。"""
        session = self.session_repo.get_session_by_session_id(session_id)
        if not session:
            return None
        return SessionRead.model_validate(session)

    def list_sessions(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[SessionRead]:
        """获取用户的会话列表。"""
        sessions = self.session_repo.list_user_sessions(user_id, skip, limit)
        return [SessionRead.model_validate(s) for s in sessions]

    def delete_session(self, session_id: str, user_id: int) -> bool:
        """删除会话（验证用户权限）。"""
        session = self.session_repo.get_session_by_session_id(session_id)
        if not session or session.user_id != user_id:
            return False

        return self.session_repo.delete_session(session.id)

    def update_session_title(self, session_id: str, user_id: int, title: str) -> Optional[SessionRead]:
        """更新会话标题。"""
        session = self.session_repo.get_session_by_session_id(session_id)
        if not session or session.user_id != user_id:
            return None

        updated = self.session_repo.update_session(session.id, title)
        return SessionRead.model_validate(updated)

    # ================= 消息管理 =================

    def get_messages(
        self, session_id: str, user_id: int, skip: int = 0, limit: int = 1000
    ) -> List[MessageRead]:
        """获取会话消息（验证用户权限）。"""
        session = self.session_repo.get_session_by_session_id(session_id)
        if not session or session.user_id != user_id:
            return []

        messages = self.session_repo.list_session_messages(session.id, skip, limit)
        return [MessageRead.model_validate(m) for m in messages]

    def add_user_message(
        self, session_id: str, user_id: int, content: str
    ) -> MessageRead:
        """添加用户消息。"""
        session = self.session_repo.get_session_by_session_id(session_id)
        if not session or session.user_id != user_id:
            raise ValueError("Session not found or access denied")

        message_data = MessageCreate(role="user", content=content)
        message = self.session_repo.create_message(session.id, user_id, message_data)
        return MessageRead.model_validate(message)

    def add_assistant_message(
        self, session_id: str, user_id: int, content: str
    ) -> MessageRead:
        """添加助手消息。"""
        session = self.session_repo.get_session_by_session_id(session_id)
        if not session or session.user_id != user_id:
            raise ValueError("Session not found or access denied")

        message_data = MessageCreate(role="assistant", content=content)
        message = self.session_repo.create_message(session.id, user_id, message_data)
        return MessageRead.model_validate(message)

    # ================= 聊天流程 =================

    def get_chat_messages(self, session_id: str, user_id: int) -> List[dict]:
        """获取适合 Agent 的消息列表（转换为 LangChain 格式）。"""
        messages = self.get_messages(session_id, user_id)

        # 转换为 LangChain 消息格式
        result = []
        for msg in messages:
            result.append({
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.created_at.isoformat()
            })

        return result
