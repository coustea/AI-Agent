"""Resource 模块智能体包导出定义 (app.resource.agents)。

导出主规划智能体 PlanAgent 与通用执行智能体 SubAgent，
并为系统外部模块（如 path 学习路径系统）提供统一轻量兼容导出。
"""

from __future__ import annotations

from typing import Any

from app.resource.agents.planner import PlanAgent, PlannerAgent, PlanningAgent
from app.resource.agents.subagent import SubAgent
from app.resource.schemas import QuizPayload, ReadingPayload


class _AgentFactory:
    """包装 SubAgent 角色工厂，以兼容旧版无参实例化。"""

    def __init__(self, role: str) -> None:
        """初始化工厂并记录角色名称。"""
        self.role = role

    def __call__(self, *args: Any, **kwargs: Any) -> SubAgent:
        """实例化并返回具备指定角色的 SubAgent。"""
        return SubAgent(role=self.role)


ContentAgent = _AgentFactory("资深课程讲师")
MindmapAgent = _AgentFactory("知识体系架构师")
QuizAgent = _AgentFactory("教学测评出题专家")
CodeAgent = _AgentFactory("资深软件研发专家")
ReadingAgent = _AgentFactory("学科文献策展人")
PPTAgent = _AgentFactory("课件制作专家")
CartoonAgent = _AgentFactory("概念动画专家")

# 兼容外部调用的 Registry 字典
AGENT_REGISTRY: dict[str, Any] = {
    "planning": PlanAgent,
    "planner": PlanAgent,
    "content": ContentAgent,
    "mindmap": MindmapAgent,
    "quiz": QuizAgent,
    "code": CodeAgent,
    "reading": ReadingAgent,
    "ppt": PPTAgent,
    "cartoon": CartoonAgent,
}

__all__ = [
    "PlanAgent",
    "PlannerAgent",
    "PlanningAgent",
    "SubAgent",
    "ContentAgent",
    "MindmapAgent",
    "QuizAgent",
    "CodeAgent",
    "ReadingAgent",
    "PPTAgent",
    "CartoonAgent",
    "AGENT_REGISTRY",
    "QuizPayload",
    "ReadingPayload",
]
