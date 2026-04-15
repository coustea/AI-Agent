"""Profile-agent factories for the agent layer."""

from app.agents.profile.fact_agent import MemoryExtractionAgent
from app.agents.profile.profile_agent import ProfileBuilderAgent


def build_profile_agent():
    return ProfileBuilderAgent()


def build_fact_agent():
    return MemoryExtractionAgent()


__all__ = ["build_fact_agent", "build_profile_agent", "MemoryExtractionAgent", "ProfileBuilderAgent"]
