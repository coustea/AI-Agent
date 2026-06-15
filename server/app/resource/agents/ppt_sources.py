"""PPT 素材捆绑 — 从资源系统 Worker 结果构建 MaterialBundle。

将 content/mindmap/quiz/code/reading 等上游 Agent 的成功输出，
有界地提取为 MaterialArtifact，供 PPT 内部流水线使用。
"""

from __future__ import annotations

from typing import Any

from app.resource.agents.ppt_models import MaterialArtifact, MaterialBundle, ResourceAgentId
from app.resource.schemas import WorkerResult


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


def build_material_bundle(
    *,
    learning_need: str,
    learning_scenario: str = "",
    profile: dict[str, Any] | None = None,
    blueprint: dict[str, Any] | None = None,
    instruction: dict[str, Any] | None = None,
    results: dict[str, WorkerResult] | None = None,
) -> MaterialBundle:
    """从资源系统结果构建 MaterialBundle。

    提取各上游 Agent 的成功输出，有界截断后打包为 MaterialArtifact。
    失败或缺失的 Agent 不阻塞 PPT 生成，仅记录元数据。
    """
    artifacts: dict[ResourceAgentId, MaterialArtifact] = {}

    for agent_id, limit in _SOURCE_LIMITS.items():
        result = (results or {}).get(agent_id)
        if result is None:
            continue
        if not result.success:
            # 失败结果仅记录元数据，不提供内容
            artifacts[agent_id] = MaterialArtifact(
                agent_id=agent_id,
                title=result.title or "",
                summary=result.summary or "",
                content="",
                metadata={"error": result.error, **result.metadata},
                success=False,
            )
            continue
        # 成功结果：有界截断内容
        content = result.content or ""
        artifacts[agent_id] = MaterialArtifact(
            agent_id=agent_id,
            title=result.title or "",
            summary=result.summary or "",
            content=_bounded_content(content, limit),
            metadata=result.metadata,
            success=True,
        )

    return MaterialBundle(
        learning_need=learning_need,
        learning_scenario=learning_scenario,
        profile=profile or {},
        blueprint=blueprint,
        instruction=instruction,
        artifacts=artifacts,
    )
