from __future__ import annotations

from collections.abc import Awaitable, Callable

from sqlmodel import Session, func, select

from app.core.engine import engine  # ⭐ 引入全局的数据库引擎
from app.core.logging import get_logger
from app.models.common import ChatMessage, UserMemory
from app.models.profile_builder import UserProfile, UserProfileHistory

logger = get_logger(__name__)


class MemoryService:
    """
    统一记忆管理服务 (多 Agent 共享中枢)
    无需外部传入 Session，内部自动管理数据库连接生命周期。
    """

    def __init__(self):
        # 绑定引擎，供所有的 with 语句使用
        self.engine = engine

    # ==========================================
    # 1. 动态画像管理 (基于 user_id 共享)
    # ==========================================
    def get_user_profile(self, user_id: int) -> UserProfile | None:
        """获取用户的完整画像记录"""
        with Session(self.engine) as session:
            stmt = select(UserProfile).where(UserProfile.user_id == user_id)
            return session.exec(stmt).first()

    def update_user_profile(self, user_id: int, features: dict, change_reason: str = "系统自动更新") -> UserProfile:
        """更新用户的画像特征，并自动记录快照历史"""
        with Session(self.engine) as session:
            profile = session.exec(select(UserProfile).where(UserProfile.user_id == user_id)).first()
            is_new = False

            if not profile:
                profile = UserProfile(user_id=user_id)
                is_new = True

            # 动态更新非空字段
            for key, value in features.items():
                if hasattr(profile, key) and value is not None:
                    setattr(profile, key, value)

            session.add(profile)
            session.commit()
            session.refresh(profile)

            # 记录历史快照
            history_stmt = select(func.max(UserProfileHistory.version)).where(UserProfileHistory.user_id == user_id)
            max_version = session.exec(history_stmt).one_or_none() or 0

            snapshot = UserProfileHistory(
                user_id=user_id,
                version=max_version + 1,
                change_reason=change_reason,
                **features
            )
            session.add(snapshot)
            session.commit()
            return profile

    # ==========================================
    # 2. 短期记忆管理 (基于 user_id + session_id 共享)
    # ==========================================
    def save_message(self, user_id: int, session_id: str, module: str, role: str, content: str) -> int:
        """存入一条消息，返回当前会话消息总数"""
        with Session(self.engine) as session:
            msg = ChatMessage(
                user_id=user_id,
                session_id=session_id,
                module=module,
                role=role,
                content=content,
            )
            session.add(msg)
            session.commit()

        count = self.get_message_count(user_id, session_id, module)
        return count

    def get_recent_messages(self, user_id: int, session_id: str, module: str, limit: int | None = None) -> list[
        ChatMessage]:
        """获取指定会话的最近 N 条消息"""
        with Session(self.engine) as session:
            count_stmt = select(func.count()).where(
                ChatMessage.user_id == user_id,
                ChatMessage.session_id == session_id,
                ChatMessage.module == module,
            )
            total = session.exec(count_stmt).one()

            stmt = select(ChatMessage).where(
                ChatMessage.user_id == user_id,
                ChatMessage.session_id == session_id,
                ChatMessage.module == module,
            ).order_by(ChatMessage.created_at.asc())

            if limit is not None and limit > 0 and total > limit:
                stmt = stmt.offset(total - limit)

            return list(session.exec(stmt).all())

    def get_message_count(self, user_id: int, session_id: str, module: str) -> int:
        with Session(self.engine) as session:
            stmt = select(func.count()).where(
                ChatMessage.user_id == user_id,
                ChatMessage.session_id == session_id,
                ChatMessage.module == module,
            )
            return session.exec(stmt).one()

    # ==========================================
    # 3. 长期记忆管理 (基于 user_id 共享)
    # ==========================================
    def get_long_term_memories(self, user_id: int, module: str | None = None, limit: int = 10) -> list[UserMemory]:
        """获取用户的长期记忆列表"""
        with Session(self.engine) as session:
            stmt = select(UserMemory).where(UserMemory.user_id == user_id)
            if module is not None:
                stmt = stmt.where(UserMemory.source == module)
            stmt = stmt.order_by(UserMemory.created_at.desc()).limit(limit)
            return list(session.exec(stmt).all())

    def should_summarize(self, user_id: int, session_id: str, module: str, threshold: int = 20) -> bool:
        """判断短期记忆是否达到总结阈值"""
        count = self.get_message_count(user_id, session_id, module)
        return count >= threshold


# 初始化实例
memory_service = MemoryService()