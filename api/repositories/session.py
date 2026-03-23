"""Redis 会话和消息管理。"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, List

from api.services.redis_service import RedisService

# Redis TTL: 7 天（604800 秒）
SESSION_TTL = 604800


class SessionRepository:
    """基于 Redis 的会话和消息 Repository。"""

    def __init__(self, redis_client: RedisService):
        self.redis = redis_client

    # ================= 会话管理 =================

    def create_session(self, user_id: int, title: str = "新会话") -> dict:
        """创建新会话。"""
        session_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        session_data = {
            "user_id": user_id,
            "session_id": session_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
        }

        # 存储会话信息
        session_key = f"session:{user_id}:{session_id}"
        self.redis.set(session_key, json.dumps(session_data), ex=SESSION_TTL)

        # 添加到用户的会话列表
        user_sessions_key = f"user:{user_id}:sessions"
        self.redis.lpush(user_sessions_key, session_id)
        self.redis.expire(user_sessions_key, SESSION_TTL)

        return session_data

    def get_session(self, user_id: int, session_id: str) -> Optional[dict]:
        """获取会话信息。"""
        session_key = f"session:{user_id}:{session_id}"
        data = self.redis.get(session_key)

        if data:
            return json.loads(data)
        return None

    def list_sessions(self, user_id: int) -> List[dict]:
        """获取用户的所有会话。"""
        user_sessions_key = f"user:{user_id}:sessions"
        session_ids = self.redis.lrange(user_sessions_key, 0, -1)

        sessions = []
        for session_id in session_ids:
            session = self.get_session(user_id, session_id)
            if session:
                sessions.append(session)

        # 按 updated_at 倒序
        sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return sessions

    def update_session(
        self, user_id: int, session_id: str, title: Optional[str] = None
    ) -> bool:
        """更新会话。"""
        session = self.get_session(user_id, session_id)
        if not session:
            return False

        if title:
            session["title"] = title
        session["updated_at"] = datetime.utcnow().isoformat()

        session_key = f"session:{user_id}:{session_id}"
        self.redis.set(session_key, json.dumps(session), ex=SESSION_TTL)

        return True

    def delete_session(self, user_id: int, session_id: str) -> bool:
        """删除会话及其消息。"""
        session = self.get_session(user_id, session_id)
        if not session:
            return False

        # 删除会话信息
        session_key = f"session:{user_id}:{session_id}"
        self.redis.delete(session_key)

        # 删除消息
        messages_key = f"session:{user_id}:{session_id}:messages"
        self.redis.delete(messages_key)

        # 从用户会话列表中移除
        user_sessions_key = f"user:{user_id}:sessions"
        self.redis.lrem(user_sessions_key, 0, session_id)

        return True

    # ================= 消息管理 =================

    def add_message(
        self, user_id: int, session_id: str, role: str, content: str
    ) -> dict:
        """添加消息。"""
        now = datetime.utcnow().isoformat()

        message = {
            "role": role,
            "content": content,
            "timestamp": now,
        }

        messages_key = f"session:{user_id}:{session_id}:messages"

        # 获取当前消息列表
        messages_data = self.redis.get(messages_key)
        if messages_data:
            messages = json.loads(messages_data)
            # 生成 ID（自增）
            last_id = messages[-1].get("id", 0) if messages else 0
            message_id = last_id + 1
        else:
            messages = []
            message_id = 1

        message["id"] = message_id
        messages.append(message)

        # 保存消息列表（限制 1000 条）
        messages = messages[-1000:]
        self.redis.set(messages_key, json.dumps(messages), ex=SESSION_TTL)

        # 更新会话的 updated_at
        self.update_session(user_id, session_id)

        return message

    def get_messages(self, user_id: int, session_id: str) -> List[dict]:
        """获取会话的所有消息。"""
        messages_key = f"session:{user_id}:{session_id}:messages"
        messages_data = self.redis.get(messages_key)

        if messages_data:
            return json.loads(messages_data)
        return []

    def count_messages(self, user_id: int, session_id: str) -> int:
        """统计消息数量。"""
        messages_key = f"session:{user_id}:{session_id}:messages"
        messages_data = self.redis.get(messages_key)

        if messages_data:
            return len(json.loads(messages_data))
        return 0

    # ================= 工具方法 =================

    def get_chat_messages_for_agent(self, user_id: int, session_id: str) -> List[dict]:
        """获取适合 Agent 的消息列表（简化格式）。"""
        messages = self.get_messages(user_id, session_id)

        return [
            {
                "role": m["role"],
                "content": m["content"],
                "timestamp": m.get("timestamp", ""),
            }
            for m in messages
        ]
