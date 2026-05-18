"""资源生成 Agent 注册中心。

当前资源模块采用轻量 orchestrator，但前端和服务层仍需要统一的
Agent 元信息查询入口。这里把当前 6 个可执行 Agent 暴露为稳定契约。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.infra.logging import get_logger
from app.resource.agents import AGENT_CLASSES
from app.resource.orchestrator import AGENT_META

logger = get_logger(__name__)

DEPENDS: dict[str, list[str]] = {
    "content": [],
    "mindmap": [],
    "diagram": ["content"],
    "quiz": ["content"],
    "code": ["content"],
    "reading": ["content"],
}

ROLE_NAMES: dict[str, str] = {
    "content": "ContentAgent",
    "mindmap": "MindmapAgent",
    "diagram": "DiagramAgent",
    "quiz": "QuizAgent",
    "code": "CodeAgent",
    "reading": "ReadingAgent",
}


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
    for agent_id, agent_class in AGENT_CLASSES.items():
        meta = AGENT_META.get(agent_id, {})
        _registry[agent_id] = AgentEntry(
            id=agent_id,
            name=str(meta.get("name") or agent_id),
            role=ROLE_NAMES.get(agent_id, f"{agent_id.capitalize()}Agent"),
            description=str(meta.get("description") or ""),
            agent_class=agent_class,
            dependencies=DEPENDS.get(agent_id, []),
            execution_layer=int(meta.get("layer", 0)),
            resource_type=agent_id,
            output_format=_format_for_agent(agent_id),
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


def _format_for_agent(agent_id: str) -> str:
    if agent_id == "diagram":
        return "mermaid"
    if agent_id in {"quiz", "code", "reading"}:
        return "json"
    return "markdown"
