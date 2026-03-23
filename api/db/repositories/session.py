"""会话和消息的 Repository 层。"""

from datetime import datetime
from typing import Optional, List

from sqlmodel import select, Session

from api.db.models import Session as SessionModel, Message, SessionRead, MessageRead, SessionCreate, MessageCreate


class SessionRepository:
    """会话数据访问层。"""

    def __init__(self, session: Session):
        self.session = session

    # ================= 会话操作 =================

    def create_session(self, user_id: int, session_data: SessionCreate) -> SessionModel:
        """创建新会话。"""
        import uuid

        session = SessionModel(
            user_id=user_id,
            session_id=str(uuid.uuid4()),
            title=session_data.title or "新会话",
        )
        self.session.add(session)
        self.session.commit()
        self.session.refresh(session)
        return session

    def get_session_by_id(self, session_id: int) -> Optional[SessionModel]:
        """根据 ID 获取会话。"""
        return self.session.get(SessionModel, session_id)

    def get_session_by_session_id(self, session_id: str) -> Optional[SessionModel]:
        """根据 session_id 获取会话。"""
        statement = select(SessionModel).where(SessionModel.session_id == session_id)
        return self.session.exec(statement).first()

    def list_user_sessions(self, user_id: int, skip: int = 0, limit: int = 100) -> List[SessionModel]:
        """获取用户的所有会话。"""
        statement = (
            select(SessionModel)
            .where(SessionModel.user_id == user_id)
            .order_by(SessionModel.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return self.session.exec(statement).all()

    def update_session(self, session_id: int, title: Optional[str] = None) -> Optional[SessionModel]:
        """更新会话标题。"""
        session = self.get_session_by_id(session_id)
        if not session:
            return None

        if title:
            session.title = title
        session.updated_at = datetime.utcnow()

        self.session.add(session)
        self.session.commit()
        self.session.refresh(session)
        return session

    def delete_session(self, session_id: int) -> bool:
        """删除会话（级联删除消息）。"""
        session = self.get_session_by_id(session_id)
        if not session:
            return False

        # 删除关联的消息
        statement = select(Message).where(Message.session_id == session_id)
        messages = self.session.exec(statement).all()
        for msg in messages:
            self.session.delete(msg)

        # 删除会话
        self.session.delete(session)
        self.session.commit()
        return True

    # ================= 消息操作 =================

    def create_message(self, session_id: int, user_id: int, message_data: MessageCreate) -> Message:
        """创建新消息。"""
        message = Message(
            session_id=session_id,
            user_id=user_id,
            role=message_data.role,
            content=message_data.content,
        )
        self.session.add(message)
        self.session.commit()
        self.session.refresh(message)
        return message

    def list_session_messages(self, session_id: int, skip: int = 0, limit: int = 1000) -> List[Message]:
        """获取会话的所有消息。"""
        statement = (
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        return self.session.exec(statement).all()

    def count_session_messages(self, session_id: int) -> int:
        """统计会话的消息数量。"""
        statement = select(Message).where(Message.session_id == session_id)
        return len(self.session.exec(statement).all())
