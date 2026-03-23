"""用户长期记忆服务层。"""

from datetime import datetime
from typing import Optional

from api.db.repositories.user_memory import UserMemoryRepository
from api.db.models import UserRead


class UserMemoryService:
    """用户长期记忆服务。"""

    def __init__(self):
        self.memory_repo = UserMemoryRepository()

    # ================= 记忆管理 =================

    def get_memory(self, user_id: int) -> Optional[str]:
        """获取用户的长期记忆。"""
        memory = self.memory_repo.get_user_memory(user_id)

        if memory:
            return f"【关于用户的长期记忆 (请根据以下偏好调整回答)】\n{memory}\n\n"

        return ""

    def set_memory(self, user_id: int, memory_summary: str) -> bool:
        """设置用户的长期记忆。"""
        if not memory_summary or len(memory_summary.strip()) == 0:
            return False

        return self.memory_repo.set_user_memory(user_id, memory_summary)

    def update_memory(self, user_id: int, memory_summary: str) -> bool:
        """更新用户的长期记忆。"""
        if not memory_summary or len(memory_summary.strip()) == 0:
            return False

        return self.memory_repo.update_user_memory(user_id, memory_summary)

    def delete_memory(self, user_id: int) -> bool:
        """删除用户的长期记忆。"""
        return self.memory_repo.delete_user_memory(user_id)

    def has_memory(self, user_id: int) -> bool:
        """检查用户是否有长期记忆。"""
        return self.memory_repo.check_memory_exists(user_id)

    # ================= 记忆增强 =================

    def append_memory(self, user_id: int, new_content: str) -> bool:
        """追加内容到用户的长期记忆。"""
        existing_memory = self.memory_repo.get_user_memory(user_id)

        if not existing_memory:
            return self.set_memory(user_id, new_content)

        # 追加新内容
        updated_memory = f"{existing_memory}\n\n【追加】\n{new_content}"

        # 限制长度（避免过长）
        max_length = 10000
        if len(updated_memory) > max_length:
            updated_memory = updated_memory[-max_length:]

        return self.memory_repo.set_user_memory(user_id, updated_memory)

    def append_summary(self, user_id: int, summary: str) -> bool:
        """追加对话总结到用户的长期记忆。"""
        existing_memory = self.memory_repo.get_user_memory(user_id)

        new_entry = f"\n\n## 对话总结\n日期：{datetime.utcnow().isoformat()}\n{summary}\n"

        if not existing_memory:
            return self.set_memory(user_id, new_entry)

        # 追加总结
        updated_memory = existing_memory + new_entry

        # 限制长度
        max_length = 10000
        if len(updated_memory) > max_length:
            # 删除最旧的部分（保留最新的）
            updated_memory = updated_memory[-max_length:]

        return self.memory_repo.set_user_memory(user_id, updated_memory)

    # ================= 格式化输出 =================

    def get_formatted_memory_for_agent(self, user_id: int) -> str:
        """获取适合 Agent 使用的记忆格式。"""
        memory = self.memory_repo.get_user_memory(user_id)

        if not memory or len(memory.strip()) == 0:
            return ""

        return f"【关于用户的长期记忆 (请根据以下偏好调整回答)】\n{memory}\n\n"
