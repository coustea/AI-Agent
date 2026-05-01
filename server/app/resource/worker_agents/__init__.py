"""
Worker Agents 包初始化。

导出 6 个活跃 Agent：
- ContentAgent: 课程讲解文档
- MindmapAgent: 知识点思维导图
- DiagramAgent: 知识图解（image 统一为 diagram）
- QuizAgent: 个性化练习题
- ReadingAgent: 拓展阅读
- CodeAgent: 代码实操案例
"""

from app.resource.worker_agents.content_agent import ContentAgent
from app.resource.worker_agents.mindmap_agent import MindmapAgent
from app.resource.worker_agents.diagram_agent import DiagramAgent
from app.resource.worker_agents.quiz_agent import QuizAgent
from app.resource.worker_agents.reading_agent import ReadingAgent
from app.resource.worker_agents.code_agent import CodeAgent

__all__ = [
    "ContentAgent",
    "MindmapAgent",
    "DiagramAgent",
    "QuizAgent",
    "ReadingAgent",
    "CodeAgent",
]
