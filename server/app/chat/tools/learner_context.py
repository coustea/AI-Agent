"""回合作用域内的只读学习者上下文能力，供 TutorAgent 使用。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from app.memory.service import MemoryService


@runtime_checkable
class LearnerContextReader(Protocol):
    """暴露给单次智能体执行的窄学习者上下文边界。"""

    async def read_learning_profile(self) -> str:
        """读取已记录的学习特征与偏好，用于个性化。"""
        ...

    async def search_learning_memory(self, query: str) -> str:
        """读取与连续性查询相关的长期学习证据。"""
        ...


@dataclass
class MemoryLearnerContextReader:
    """由 MemoryService 支持的只读适配器，为单次聊天回合缓存数据。"""

    user_id: int
    memory_service: MemoryService
    _profile_cache: str | None = field(default=None, init=False)
    _memory_cache: dict[str, str] = field(default_factory=dict, init=False)

    async def read_learning_profile(self) -> str:
        if self._profile_cache is None:
            self._profile_cache = await self.memory_service.get_profile_markdown(self.user_id)
        return self._profile_cache

    async def search_learning_memory(self, query: str) -> str:
        normalized_query = " ".join((query or "").split()).strip() or "__all__"
        if normalized_query not in self._memory_cache:
            # 现有记忆存储基于 Markdown；此边界后续可切换为
            # 语义检索，而无需修改 TutorAgent。
            self._memory_cache[normalized_query] = await self.memory_service.get_memory_markdown(
                self.user_id
            )
        return self._memory_cache[normalized_query]
