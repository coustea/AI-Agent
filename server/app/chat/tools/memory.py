"""Read-only learner memory tools for chat agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from langchain_core.tools import tool

from app.chat.memory.service import ChatMemoryService

if TYPE_CHECKING:
    from app.chat.tools.memory import DefaultMemoryReader


class MemoryReader(ABC):
    """Read-only interface for learner profile and long-term memory."""

    @abstractmethod
    async def get_user_profile(self, dimension: str | None = None) -> str:
        """Return current user profile markdown or a specific dimension summary."""

    @abstractmethod
    async def get_long_term_memory(self, category: str | None = None) -> str:
        """Return long-term memory markdown or a specific category summary."""


class DefaultMemoryReader(MemoryReader):
    """Memory reader backed by MemoryService."""

    def __init__(self, *, user_id: int, memory_service: ChatMemoryService) -> None:
        self._user_id = user_id
        self._memory_service = memory_service

    async def get_user_profile(self, dimension: str | None = None) -> str:
        return await self._memory_service.get_profile_markdown(self._user_id, dimension=dimension)

    async def get_long_term_memory(self, category: str | None = None) -> str:
        return await self._memory_service.get_memory_markdown(self._user_id, category=category)


def make_memory_tools(reader: DefaultMemoryReader) -> list:
    """Build memory tools bound to the current user."""

    @tool("get_user_profile")
    async def get_user_profile(dimension: str = None) -> str:
        """Read the current learner profile.

        Supported profile dimensions:
        - major_background
        - student_stage
        - course_context
        - knowledge_level
        - learning_goal_type
        - weak_knowledge_points
        - cognitive_style
        - resource_preference_weight
        - learning_pace
        - practice_profile
        """
        return await reader.get_user_profile(dimension)

    @tool("get_long_term_memory")
    async def get_long_term_memory(category: str = None) -> str:
        """Read the learner long-term memory.

        Supported categories include:
        - learning_background
        - long_term_goals
        - learning_preferences
        - stable_weaknesses
        - interaction_rules
        - effective_strategies
        - corrections
        """
        return await reader.get_long_term_memory(category)

    return [get_user_profile, get_long_term_memory]
