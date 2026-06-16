"""PPT 素材捆绑 — 从 ResourceInput / NodeInput 构建 MaterialBundle。

将 content/mindmap/quiz/code/reading 等上游 Agent 的成功输出，
有界地提取为 MaterialArtifact，供 PPT 内部流水线使用。
"""

from __future__ import annotations

from typing import Any

from app.resource.agents.ppt_models import (
    MaterialArtifact,
    MaterialBundle,
    NodeMaterialContext,
    ResourceAgentId,
)
from app.resource.schemas import AgentResult, NodeInput, ResourceInput


# 各上游 Agent 内容截断上限（字符数）
_SOURCE_LIMITS: dict[ResourceAgentId, int] = {
    "content": 6000,
    "mindmap": 4000,
    "quiz": 3000,
    "code": 5000,
    "reading": 4000,
}


def _bounded_content(content: str, limit: int) -> str:
    """截断内容到指定字符数上限。"""
    if len(content) <= limit:
        return content
    return content[:limit]


def _extract_artifacts(results: dict[str, AgentResult]) -> dict[ResourceAgentId, MaterialArtifact]:
    """从 AgentResult 字典提取 MaterialArtifact。"""
    artifacts: dict[ResourceAgentId, MaterialArtifact] = {}

    for agent_id, limit in _SOURCE_LIMITS.items():
        result = results.get(agent_id)
        if result is None:
            continue
        if not result.success:
            artifacts[agent_id] = MaterialArtifact(
                agent_id=agent_id,
                title=result.title or "",
                summary=result.summary or "",
                content="",
                metadata={"error": result.error, **result.metadata},
                success=False,
            )
            continue
        content = result.content or ""
        artifacts[agent_id] = MaterialArtifact(
            agent_id=agent_id,
            title=result.title or "",
            summary=result.summary or "",
            content=_bounded_content(content, limit),
            metadata=result.metadata,
            success=True,
        )

    return artifacts


def build_resource_material(input_data: ResourceInput) -> MaterialBundle:
    """从 ResourceInput 构建 MaterialBundle（多智能体场景）。"""
    artifacts = _extract_artifacts(input_data.previous_results)

    return MaterialBundle(
        learning_need=input_data.learning_need,
        learning_scenario=input_data.learning_scenario,
        profile=input_data.profile,
        blueprint=input_data.blueprint.model_dump(mode="json") if input_data.blueprint else None,
        instruction=input_data.instruction.model_dump(mode="json") if input_data.instruction else None,
        artifacts=artifacts,
        source_type="resource",
        node_context=None,
    )


def build_node_material(input_data: NodeInput) -> MaterialBundle:
    """从 NodeInput 构建 MaterialBundle（路径节点场景）。"""
    node_context = NodeMaterialContext(
        path_title=input_data.path_title,
        path_goal=input_data.path_goal,
        node_title=input_data.node_title,
        node_key=input_data.node_key,
        difficulty=input_data.difficulty,
        knowledge_points=input_data.knowledge_points,
        weak_knowledge_points=input_data.weak_knowledge_points,
        generation_focus=input_data.generation_focus,
        tutorial_title=input_data.tutorial_title,
        tutorial_summary=input_data.tutorial_summary,
        tutorial_markdown=input_data.tutorial_markdown,
    )

    return MaterialBundle(
        learning_need=input_data.node_title,
        learning_scenario="path_learning",
        profile=input_data.profile,
        blueprint=None,
        instruction=None,
        artifacts={},
        source_type="node",
        node_context=node_context,
    )
