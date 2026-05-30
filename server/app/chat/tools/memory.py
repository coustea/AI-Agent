"""只读学习者上下文读取能力。

供 TutorAgent 在每轮对话中按需读取用户画像与长期记忆，
避免无差别注入全部上下文造成 prompt 冗余。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from langchain_core.tools import tool

from app.infra.logging import get_logger
from app.memory.service import MemoryService

if TYPE_CHECKING:
    from app.chat.tools.memory import DefaultMemoryReader

logger = get_logger(__name__)


class MemoryReader(ABC):
    """Agent 可按需读取学习者记忆的只读能力接口。"""

    @abstractmethod
    async def get_user_profile(self, dimension: str | None = None) -> str:
        """返回当前用户的学习画像 Markdown。"""

    @abstractmethod
    async def get_long_term_memory(self, category: str | None = None) -> str:
        """基于用户问题检索相关的长期学习记忆。"""


class DefaultMemoryReader(MemoryReader):
    """基于 MemoryService 的学习者记忆读取实现。"""

    def __init__(self, *, user_id: int, memory_service: MemoryService) -> None:
        self._user_id = user_id
        self._memory_service = memory_service

    async def get_user_profile(self, dimension: str | None = None) -> str:
        return await self._memory_service.get_profile_markdown(self._user_id, dimension=dimension)

    async def get_long_term_memory(self, category: str | None = None) -> str:
        return await self._memory_service.get_memory_markdown(self._user_id, category=category)


def make_memory_tools(reader: DefaultMemoryReader) -> list:
    """工厂函数：创建绑定了用户信息的 memory 工具。

    reader 已持有 user_id 和 memory_service，闭包内直接调用。
    返回的 tools 实例传给 LLM.bind_tools() 即可。
    """

    @tool("get_user_profile")
    async def get_user_profile(dimension: str = None) -> str:
        """读取当前用户的学习画像（基础水平、学习目标、偏好、薄弱点等）。
        如果想获取特定维度，传入维度的英文关键字（如 knowledge_foundation, weakness_points）。
        不传则返回完整画像概要。"""
        result = await reader.get_user_profile(dimension)
        logger.debug("[MemoryTool] get_user_profile: dimension=%s len=%d", dimension, len(result))
        return result

    @tool("get_long_term_memory")
    async def get_long_term_memory(category: str = None) -> str:
        """获取当前用户的长期学习记忆（历史偏好、有效辅导策略、纠正记录等）。
        如果想获取特定分类，传入分类的英文关键字（如 effective_strategies, stable_weaknesses）。
        不传则返回完整记忆概要。"""
        result = await reader.get_long_term_memory(category)
        logger.debug("[MemoryTool] get_long_term_memory: category=%s len=%d", category, len(result))
        return result

    return [get_user_profile, get_long_term_memory]