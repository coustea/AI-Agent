"""资源生成 Agent 模块。"""

from app.resource.agents.content import ContentAgent
from app.resource.agents.mindmap import MindmapAgent
from app.resource.agents.diagram import DiagramAgent
from app.resource.agents.quiz import QuizAgent
from app.resource.agents.code import CodeAgent
from app.resource.agents.reading import ReadingAgent

# Agent ID → Agent 类映射
AGENT_CLASSES: dict[str, type] = {
    "content": ContentAgent,
    "mindmap": MindmapAgent,
    "diagram": DiagramAgent,
    "quiz": QuizAgent,
    "code": CodeAgent,
    "reading": ReadingAgent,
}

__all__ = [
    "AGENT_CLASSES",
    "ContentAgent",
    "MindmapAgent",
    "DiagramAgent",
    "QuizAgent",
    "CodeAgent",
    "ReadingAgent",
]