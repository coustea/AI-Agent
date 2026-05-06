"""
Agent 注册表。

只注册活跃的 6 个 Agent：content, mindmap, diagram, quiz, reading, code。
移除 ppt, video, image（image 统一改为 diagram）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Type

from app.infra.logging import get_logger

logger = get_logger(__name__)

# 活跃的 Agent ID 列表
ACTIVE_AGENT_IDS = ["content", "mindmap", "diagram", "quiz", "reading", "code"]

# Agent 别名映射（image -> diagram）
ALIAS_MAP = {"image": "diagram"}

# 禁用的 Agent ID
DISABLED_AGENT_IDS = {"ppt", "video"}


@dataclass
class AgentEntry:
    """Agent 注册条目。"""
    name: str
    role: str
    description: str
    agent_class: Type[Any]
    dependencies: list[str] = field(default_factory=list)
    execution_layer: int = 0
    failure_policy: str = "independent_fail"

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
    """Agent 注册表单例。"""

    _instance: "AgentRegistry | None" = None
    _agents: dict[str, AgentEntry] = field(default_factory=dict)

    def __new__(cls) -> "AgentRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._agents = {}
        return cls._instance

    def register(self, entry: AgentEntry) -> None:
        self._agents[entry.name] = entry

    def get(self, name: str) -> AgentEntry | None:
        return self._agents.get(name)

    def get_all(self) -> dict[str, AgentEntry]:
        return self._agents.copy()

    def get_names(self) -> list[str]:
        return list(self._agents.keys())

    def get_dependencies(self, name: str) -> list[str]:
        entry = self._agents.get(name)
        return entry.dependencies if entry else []


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
    """注册 Agent。"""
    registry.register(
        AgentEntry(
            name=name,
            role=role,
            description=description,
            agent_class=agent_class,
            dependencies=dependencies or [],
            execution_layer=execution_layer,
            failure_policy=failure_policy,
        )
    )


def resolve_agent_id(agent_id: str) -> str | None:
    """解析 Agent ID。

    - 禁用的 Agent 返回 None
    - 别名映射到实际 Agent
    - 未知的 Agent 返回 None
    """
    value = str(agent_id).strip().lower()
    if value in DISABLED_AGENT_IDS:
        return None
    value = ALIAS_MAP.get(value, value)
    if value in ACTIVE_AGENT_IDS:
        return value
    return None


def get_enabled_agent_ids() -> list[str]:
    """获取启用的 Agent ID 列表。"""
    return list(ACTIVE_AGENT_IDS)


def get_registry() -> AgentRegistry:
    """获取注册表实例。"""
    return registry


def get_agent_registry() -> dict[str, AgentEntry]:
    """获取所有已注册的 Agent。"""
    ensure_initialized()
    return registry.get_all()


def get_agent_entry(agent_id: str) -> AgentEntry | None:
    """获取指定 Agent 的注册信息。"""
    ensure_initialized()
    return registry.get(agent_id)


# 初始化标志
_initialized = False


def ensure_initialized() -> None:
    """确保注册表已初始化。"""
    global _initialized
    if not _initialized:
        _init_default_agents()
        _initialized = True


def _init_default_agents() -> None:
    """初始化默认 Agent 注册。"""
    from app.resource.worker_agents import (
        CodeAgent,
        ContentAgent,
        DiagramAgent,
        MindmapAgent,
        QuizAgent,
        ReadingAgent,
    )

    registry._agents = {}

    # Layer 0: 认知建构层
    register_agent(
        name="content",
        role="内容讲解 Agent",
        description="生成课程讲解文档，包含概念解释、示例、注意事项",
        agent_class=ContentAgent,
        dependencies=[],
        execution_layer=0,
        failure_policy="independent_fail",
    )

    register_agent(
        name="mindmap",
        role="思维导图 Agent",
        description="生成知识点思维导图，使用 markmap 渲染",
        agent_class=MindmapAgent,
        dependencies=[],
        execution_layer=0,
        failure_policy="degraded_run",
    )

    register_agent(
        name="diagram",
        role="知识图解 Agent",
        description="生成 Mermaid 知识图解，支持 18 种图解类型",
        agent_class=DiagramAgent,
        dependencies=[],
        execution_layer=0,
        failure_policy="degraded_run",
    )

    # Layer 1: 实践拓展层
    register_agent(
        name="code",
        role="代码实操 Agent",
        description="生成代码实操案例，包含注释、讲解、调试技巧",
        agent_class=CodeAgent,
        dependencies=["content"],
        execution_layer=1,
        failure_policy="degraded_run",
    )

    register_agent(
        name="reading",
        role="拓展阅读 Agent",
        description="生成拓展阅读建议，推荐相关书籍、文章、文档",
        agent_class=ReadingAgent,
        dependencies=["content"],
        execution_layer=1,
        failure_policy="degraded_run",
    )

    # Layer 2: 检测巩固层
    register_agent(
        name="quiz",
        role="习题 Agent",
        description="生成个性化练习题，支持多种题型和难度",
        agent_class=QuizAgent,
        dependencies=["content", "code"],
        execution_layer=2,
        failure_policy="degraded_run",
    )

    logger.info("[Registry] 默认 Agent 注册完成: %s", registry.get_names())
