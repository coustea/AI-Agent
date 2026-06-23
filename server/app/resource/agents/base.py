"""资源生成 Agent 基类与注册表。

所有资源生成 Agent 继承 BaseResourceAgent，通过 @register_agent 装饰器
自动注册到全局 AGENT_REGISTRY 字典中，供路径模块和资源服务按 agent_id 查找调用。
"""

# 允许使用前向引用（如字符串形式的类型标注），避免循环导入问题
from __future__ import annotations

# 仅类型检查时导入，避免循环依赖
from typing import TYPE_CHECKING

# 获取结构化日志器
from app.infra.logging import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    # Resource 事件发射器（仅类型标注用）
    from app.resource.event import ResourceEvents
    # Agent 输入输出 schema
    from app.resource.schemas import AgentResult, NodeInput, ResourceInput


# 全局 Agent 注册表：agent_id（如 "content"）→ Agent 类
AGENT_REGISTRY: dict[str, type[BaseResourceAgent]] = {}


def register_agent(cls: type[BaseResourceAgent]) -> type[BaseResourceAgent]:
    """装饰器：将 Agent 类注册到全局注册表，按 agent_id 索引。

    用法：@register_agent 标注在类定义上方，类必须有 agent_id 类属性。
    """
    # 以 agent_id 为 key 注册 Agent 类
    AGENT_REGISTRY[cls.agent_id] = cls
    return cls


class BaseResourceAgent:
    """资源 Agent 基类。子类必须显式实现 resource 和 node 两个入口。"""

    # Agent 唯一标识符，用于注册表查找和路由分发
    agent_id: str

    # Agent 显示名称，用于前端展示和日志
    agent_name: str

    def __init__(self, events: ResourceEvents | None = None, emitter: ResourceEvents | None = None) -> None:
        actual_events = events or emitter
        self.emitter = actual_events
        if actual_events is None:
            class NoopEvents:
                """空操作事件发射器，所有方法调用均为 no-op。"""
                def __getattr__(self, name):
                    async def noop(*args, **kwargs):
                        pass
                    return noop

            self.events = NoopEvents()
        else:
            self.events = actual_events

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        """独立资源生成入口（standalone 模式）。子类必须实现。"""
        raise NotImplementedError(f"{self.__class__.__name__}.generate_resource is required")

    async def generate_node(self, input_data: NodeInput) -> AgentResult:
        """路径节点资源生成入口。子类必须实现。"""
        raise NotImplementedError(f"{self.__class__.__name__}.generate_node is required")
