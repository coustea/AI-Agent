"""资源生成 Agent 注册中心。

当前资源模块采用轻量 orchestrator，但前端和服务层仍需要统一的
Agent 元信息查询入口。这里把当前 6 个可执行 Agent 暴露为稳定契约。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.infra.logging import get_logger
from app.resource.agents import AGENT_CLASSES
from app.resource.manifest import RESOURCE_AGENT_MANIFESTS

logger = get_logger(__name__)


@dataclass
class AgentEntry:
    """Agent 注册条目。"""

    id: str
    name: str
    role: str
    description: str
    agent_class: type[Any]
    dependencies: list[str] = field(default_factory=list)
    execution_layer: int = 0
    resource_type: str = ""
    output_format: str = "json"


_initialized = False
_registry: dict[str, AgentEntry] = {}


def ensure_initialized() -> None:
    """确保注册表已初始化。"""
    global _initialized, _registry
    if _initialized:
        return

    _registry = {}
    for manifest in RESOURCE_AGENT_MANIFESTS:
        agent_class = AGENT_CLASSES.get(manifest.id)
        if agent_class is None:
            logger.warning("[ResourceRegistry] Agent class missing for manifest: %s", manifest.id)
            continue
        _registry[manifest.id] = AgentEntry(
            id=manifest.id,
            name=manifest.name,
            role=manifest.role,
            description=manifest.description,
            agent_class=agent_class,
            dependencies=list(manifest.dependencies),
            execution_layer=manifest.layer,
            resource_type=manifest.id,
            output_format=manifest.output_format,
        )

    _initialized = True
    logger.info("[ResourceRegistry] Agent 注册完成: %s", list(_registry))


def get_agent_entry(agent_id: str) -> AgentEntry | None:
    """获取指定 Agent 的注册信息。"""
    ensure_initialized()
    return _registry.get(agent_id)


def get_enabled_agent_ids() -> list[str]:
    """获取启用的 Agent ID 列表。"""
    ensure_initialized()
    return list(_registry)
