"""Chat-agent factories for the agent layer."""

from functools import lru_cache

from app.agents.chat.tutor_agent import TutorAgent

CHAT_MODULE_NAME = "mentor"


@lru_cache(maxsize=1)
def build_tutor_agent() -> TutorAgent:
    return TutorAgent()


__all__ = ["CHAT_MODULE_NAME", "build_tutor_agent", "TutorAgent"]
