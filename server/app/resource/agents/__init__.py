"""资源生成智能体 — 通过 @register_agent 装饰器自动注册。

每个 agent 实现 BaseResourceAgent 的 generate_resource 和 generate_node 方法，
通过全局 AGENT_REGISTRY 字典按 agent_id 查找调用。
"""

from app.resource.agents.base import AGENT_REGISTRY, BaseResourceAgent, register_agent

# 导入所有 agent 以触发 @register_agent 注册
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
