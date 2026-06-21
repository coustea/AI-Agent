"""资源生成 Agent 基类与注册表。

所有资源生成 Agent 继承 BaseResourceAgent，通过 @register_agent 装饰器
自动注册到全局 AGENT_REGISTRY 字典中，供路径模块和资源服务按 agent_id 查找调用。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.infra.logging import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from app.infra.agent_events import AgentEventEmitter
    from app.resource.schemas import AgentResult, NodeInput, ResourceInput


# 全局 Agent 注册表：agent_id → Agent 类
AGENT_REGISTRY: dict[str, type[BaseResourceAgent]] = {}


def register_agent(cls: type[BaseResourceAgent]) -> type[BaseResourceAgent]:
    """装饰器：将 Agent 类注册到全局注册表，按 agent_id 索引。"""
    AGENT_REGISTRY[cls.agent_id] = cls
    return cls


class BaseResourceAgent:
    """资源 Agent 基类。子类必须显式实现 resource 和 node 两个入口。"""

    agent_id: str
    agent_name: str

    def __init__(self, emitter: AgentEventEmitter | None = None) -> None:
        self.emitter = emitter

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        raise NotImplementedError(f"{self.__class__.__name__}.generate_resource is required")

    async def generate_node(self, input_data: NodeInput) -> AgentResult:
        raise NotImplementedError(f"{self.__class__.__name__}.generate_node is required")

    async def emit_start(self, message: str, progress: int = 10) -> None:
        if self.emitter:
            await self.emitter.emit_agent(
                self.agent_id,
                status="running",
                message=message,
                progress=progress,
            )

    async def emit_finish(self, result: AgentResult) -> None:
        if self.emitter:
            await self.emitter.emit_agent(
                self.agent_id,
                status="finished" if result.success else "failed",
                message=result.summary if result.success else (result.error or f"{self.agent_name}生成失败"),
                progress=100 if result.success else 0,
            )
