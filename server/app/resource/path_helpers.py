"""Path-domain resource generation helpers.

These are called by the path domain to generate resources for individual
learning-path nodes. They are deliberately separate from the standalone
resource orchestration flow.
"""

from __future__ import annotations

from app.infra.logging import get_module_logger
from app.resource.agents import AGENT_REGISTRY
from app.resource.schemas import AgentResult, NodeInput

logger = get_module_logger("resource", sub="path_helpers")


async def generate_path_node_resource(
    agent_id: str,
    node_input: NodeInput,
) -> AgentResult:
    supported_agent_ids = {"content", "mindmap", "code", "reading", "quiz", "ppt", "video"}
    if agent_id not in supported_agent_ids:
        raise ValueError(f"Unsupported agent_id for path node: {agent_id}")
    if agent_id not in AGENT_REGISTRY:
        raise ValueError(f"Agent '{agent_id}' not found in AGENT_REGISTRY")

    agent = AGENT_REGISTRY[agent_id]()
    result = await agent.generate_node(node_input)
    if not result.success:
        logger.warning(
            "path_node_resource agent %s failed: %s",
            agent_id,
            result.error or "unknown error",
        )
    return result
