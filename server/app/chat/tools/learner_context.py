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
    from app.chat.tools.learner_context import MemoryLearnerContextReader

logger = get_logger(__name__)


class LearnerContextReader(ABC):
    """Agent 可按需读取学习者上下文的只读能力接口。"""

    @abstractmethod
    async def read_learning_profile(self) -> str:
        """返回当前用户的学习画像 Markdown。"""

    @abstractmethod
    async def search_learning_memory(self, question: str) -> str:
        """基于用户问题检索相关的长期学习记忆。"""


class MemoryLearnerContextReader(LearnerContextReader):
    """基于 MemoryService 的学习者上下文读取实现。"""

    def __init__(self, *, user_id: int, memory_service: MemoryService) -> None:
        self._user_id = user_id
        self._memory_service = memory_service

    async def read_learning_profile(self) -> str:
        return await self._memory_service.get_profile_markdown(self._user_id)

    async def search_learning_memory(self, question: str) -> str:
        return await self._memory_service.get_memory_markdown(self._user_id)


def make_learner_tools(reader: MemoryLearnerContextReader) -> list:
    """工厂函数：创建绑定了用户信息的 learner context 工具。

    reader 已持有 user_id 和 memory_service，闭包内直接调用。
    返回的 tools 实例传给 LLM.bind_tools() 即可。
    """

    @tool("read_my_learning_profile")
    async def read_my_learning_profile() -> str:
        """读取当前用户的学习画像（基础水平、学习目标、偏好、薄弱点等）。
        仅当学生的问题涉及个性化辅导、结合自身情况回答时才调用此工具。
        普通概念问答不需要调用。"""
        return await reader.read_learning_profile()

    @tool("search_my_learning_memory")
    async def search_my_learning_memory(query: str) -> str:
        """基于问题关键词检索当前用户的既往学习记录和薄弱点。
        仅当需要了解学生过去的学习情况、错误记录或薄弱环节时才调用。
        query 参数应提炼出与学习历史相关的关键词。
        普通概念问答不需要调用。"""
        return await reader.search_learning_memory(query)

    return [read_my_learning_profile, search_my_learning_memory]