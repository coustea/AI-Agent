"""资源生成 Agent 集合。"""

from app.resource.agents.planning import PlanningAgent
from app.resource.agents.content import ContentAgent
from app.resource.agents.mindmap import MindmapAgent
from app.resource.agents.knowledge import KnowledgeGraphAgent
from app.resource.agents.quiz import QuizAgent
from app.resource.agents.code import CodeAgent
from app.resource.agents.reading import ReadingAgent
from app.resource.agents.review import ReviewAgent

# agent_id → Agent 类的映射（用于 Phase 2 并行执行）
AGENT_CLASSES: dict[str, type] = {
    "content": ContentAgent,
    "mindmap": MindmapAgent,
    "knowledge_graph": KnowledgeGraphAgent,
    "quiz": QuizAgent,
    "code": CodeAgent,
    "reading": ReadingAgent,
}

__all__ = [
    "AGENT_CLASSES",
    "PlanningAgent",
    "ContentAgent",
    "MindmapAgent",
    "KnowledgeGraphAgent",
    "QuizAgent",
    "CodeAgent",
    "ReadingAgent",
    "ReviewAgent",
]
