"""Resource Agent manifest.

This module is the single source for resource-agent runtime metadata:
ordering, frontend metadata, dependency hints, output format, and whether an
agent can consume the content outline produced by ContentAgent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ResourceAgentManifest:
    """Stable metadata for one resource Agent."""

    id: str
    name: str
    role: str
    description: str
    icon: str
    layer: int
    layer_name: str
    output_format: str
    dependencies: tuple[str, ...] = ()
    uses_content_outline: bool = False
    default_selected: bool = True
    default_enabled: bool = True


RESOURCE_AGENT_MANIFESTS: tuple[ResourceAgentManifest, ...] = (
    ResourceAgentManifest(
        id="content",
        name="课程内容",
        role="ContentAgent",
        description="生成专业课程讲解文档",
        icon="Document",
        layer=0,
        layer_name="核心内容层",
        output_format="markdown",
    ),
    ResourceAgentManifest(
        id="mindmap",
        name="思维导图",
        role="MindmapAgent",
        description="生成知识结构思维导图",
        icon="Mindmap",
        layer=0,
        layer_name="核心内容层",
        output_format="markdown",
        uses_content_outline=True,
    ),
    ResourceAgentManifest(
        id="diagram",
        name="图表",
        role="DiagramAgent",
        description="生成 Mermaid 图表",
        icon="Diagram",
        layer=1,
        layer_name="辅助理解层",
        output_format="mermaid",
        dependencies=("content",),
        uses_content_outline=True,
    ),
    ResourceAgentManifest(
        id="code",
        name="代码",
        role="CodeAgent",
        description="生成代码示例",
        icon="Code",
        layer=1,
        layer_name="辅助理解层",
        output_format="json",
        dependencies=("content",),
        uses_content_outline=True,
        default_enabled=False,
    ),
    ResourceAgentManifest(
        id="quiz",
        name="习题",
        role="QuizAgent",
        description="生成练习习题",
        icon="Quiz",
        layer=1,
        layer_name="辅助理解层",
        output_format="json",
        dependencies=("content",),
        uses_content_outline=True,
    ),
    ResourceAgentManifest(
        id="reading",
        name="阅读推荐",
        role="ReadingAgent",
        description="推荐学习资源",
        icon="Reading",
        layer=2,
        layer_name="拓展学习层",
        output_format="json",
        dependencies=("content",),
        uses_content_outline=True,
    ),
)


_MANIFEST_BY_ID = {manifest.id: manifest for manifest in RESOURCE_AGENT_MANIFESTS}


def get_agent_manifest(agent_id: str) -> ResourceAgentManifest | None:
    """Return the manifest for an Agent id."""
    return _MANIFEST_BY_ID.get(agent_id)


def agent_order() -> list[str]:
    """Return stable default execution/selection ordering."""
    return [manifest.id for manifest in RESOURCE_AGENT_MANIFESTS]


def default_agent_ids() -> list[str]:
    """Return Agent ids selected by default in a new request."""
    return [manifest.id for manifest in RESOURCE_AGENT_MANIFESTS if manifest.default_selected]


def content_outline_agent_ids() -> list[str]:
    """Return Agent ids that can consume the ContentAgent outline."""
    return [manifest.id for manifest in RESOURCE_AGENT_MANIFESTS if manifest.uses_content_outline]


def agent_meta_map() -> dict[str, dict[str, Any]]:
    """Return the legacy metadata shape used by the orchestrator and API."""
    return {
        manifest.id: {
            "name": manifest.name,
            "description": manifest.description,
            "icon": manifest.icon,
            "layer": manifest.layer,
            "layer_name": manifest.layer_name,
            "default_enabled": manifest.default_enabled,
        }
        for manifest in RESOURCE_AGENT_MANIFESTS
    }
