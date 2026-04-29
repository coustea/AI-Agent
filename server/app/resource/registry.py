"""
Agent 注册表。

维护 agent_name 到具体 Agent 类的映射。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Type

from app.infra.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AgentEntry:
    """Agent 注册条目。"""
    name: str
    role: str
    description: str
    agent_class: Type[Any]
    dependencies: list[str] = field(default_factory=list)
    execution_layer: int = 0
    failure_policy: str = "independent_fail"  # independent_fail, degraded_run, skip_on_dependency_failed

    @property
    def desc(self) -> str:
        return self.description

    @property
    def type(self) -> str:
        return "worker"

    @property
    def stage(self) -> str:
        return f"layer_{self.execution_layer}"


class AgentRegistry:
    """Agent 注册表 — 单例模式。"""

    _instance: "AgentRegistry | None" = None
    _agents: dict[str, AgentEntry] = field(default_factory=dict)

    def __new__(cls) -> "AgentRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._agents = {}
            cls._instance._initialized = False
        return cls._instance

    def register(self, entry: AgentEntry) -> None:
        """注册 Agent。"""
        self._agents[entry.name] = entry
        logger.debug("[Registry] 注册 Agent: %s -> %s", entry.name, entry.agent_class.__name__)

    def get(self, name: str) -> AgentEntry | None:
        """获取 Agent 条目。"""
        return self._agents.get(name)

    def get_all(self) -> dict[str, AgentEntry]:
        """获取所有 Agent。"""
        return self._agents.copy()

    def get_names(self) -> list[str]:
        """获取所有 Agent 名称。"""
        return list(self._agents.keys())

    def get_dependencies(self, name: str) -> list[str]:
        """获取 Agent 的依赖。"""
        entry = self._agents.get(name)
        return entry.dependencies if entry else []

    def get_execution_layer(self, name: str) -> int:
        """获取 Agent 的执行层。"""
        entry = self._agents.get(name)
        return entry.execution_layer if entry else 99


# 全局注册表实例
registry = AgentRegistry()


def register_agent(
    name: str,
    role: str,
    description: str,
    agent_class: Type[Any],
    dependencies: list[str] | None = None,
    execution_layer: int = 0,
    failure_policy: str = "independent_fail",
) -> None:
    """注册 Agent 的便捷函数。"""
    registry.register(AgentEntry(
        name=name,
        role=role,
        description=description,
        agent_class=agent_class,
        dependencies=dependencies or [],
        execution_layer=execution_layer,
        failure_policy=failure_policy,
    ))


def get_registry() -> AgentRegistry:
    """获取全局注册表。"""
    return registry


def get_agent_registry() -> dict[str, AgentEntry]:
    """兼容旧代码：返回 name -> AgentEntry 映射。"""
    ensure_initialized()
    return registry.get_all()


# 初始化默认 Agent 注册
def _init_default_agents() -> None:
    """初始化默认 Agent 注册。"""
    from app.resource.worker_agents import (
        ContentAgent,
        MindmapAgent,
        QuizAgent,
        CodeAgent,
        ReadingAgent,
        PptAgent,
    )

    # Layer 0: 基础内容
    register_agent(
        name="content",
        role="内容讲解 Agent",
        description="生成基础知识讲解 Markdown",
        agent_class=ContentAgent,
        dependencies=[],
        execution_layer=0,
    )

    register_agent(
        name="mindmap",
        role="思维导图 Agent",
        description="生成 Mermaid/Markdown 知识结构图",
        agent_class=MindmapAgent,
        dependencies=[],
        execution_layer=0,
    )

    # Layer 1: 扩展内容
    register_agent(
        name="quiz",
        role="习题 Agent",
        description="生成练习题、答案和解析",
        agent_class=QuizAgent,
        dependencies=["content"],
        execution_layer=1,
        failure_policy="degraded_run",
    )

    register_agent(
        name="code",
        role="代码示例 Agent",
        description="生成可运行代码、注释和讲解",
        agent_class=CodeAgent,
        dependencies=["content", "mindmap"],
        execution_layer=1,
        failure_policy="degraded_run",
    )

    register_agent(
        name="reading",
        role="拓展阅读 Agent",
        description="生成延伸阅读材料和参考方向",
        agent_class=ReadingAgent,
        dependencies=["content"],
        execution_layer=1,
        failure_policy="degraded_run",
    )

    register_agent(
        name="ppt",
        role="PPT Agent",
        description="基于模板生成可下载的演示文稿",
        agent_class=PptAgent,
        dependencies=["content"],
        execution_layer=2,
        failure_policy="degraded_run",
    )

    logger.info("[Registry] 默认 Agent 注册完成: %s", list(registry.get_names()))


# 延迟初始化
_initialized = False


def ensure_initialized() -> None:
    """确保注册表已初始化。"""
    global _initialized
    if not _initialized:
        _init_default_agents()
        _initialized = True
