"""Resource generation agents — auto-registered via @register_agent."""

from app.resource.agents.base import AGENT_REGISTRY, BaseResourceAgent, register_agent

# Import all agents to trigger @register_agent registration
from app.resource.agents.planning import PlanningAgent
from app.resource.agents.content import ContentAgent
from app.resource.agents.quiz import QuizAgent
from app.resource.agents.mindmap import MindmapAgent
from app.resource.agents.code import CodeAgent
from app.resource.agents.reading import ReadingAgent
from app.resource.agents.ppt import PptAgent
from app.resource.agents.video import VideoAgent

__all__ = [
    "AGENT_REGISTRY",
    "BaseResourceAgent",
    "register_agent",
    "PlanningAgent",
    "ContentAgent",
    "QuizAgent",
    "MindmapAgent",
    "CodeAgent",
    "ReadingAgent",
    "PptAgent",
    "VideoAgent",
]
