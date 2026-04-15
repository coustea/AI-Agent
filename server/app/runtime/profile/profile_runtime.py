"""Profile runtimes."""

from __future__ import annotations

from app.agents.profile import build_fact_agent, build_profile_agent
from app.ports.runtime import ProfileRuntime


class LearnerProfileRuntime(ProfileRuntime):
    async def build_profile(self, user_id: int, session_id: str | None = None) -> bool:
        agent = build_profile_agent()
        return await agent.build_profile(user_id=user_id, session_id=session_id)

    async def extract_facts(self, user_id: int, session_id: str) -> bool:
        agent = build_fact_agent()
        return await agent.extract_and_save_fact(user_id=user_id, session_id=session_id)
