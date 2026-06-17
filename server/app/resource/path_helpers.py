"""路径域资源生成辅助 — 为学习路径节点生成辅助资源。

由路径模块（path service/workflow）调用，独立于 standalone 资源编排流程。
支持的 agent 类型：content / mindmap / code / reading / quiz / ppt / video
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
    """为路径节点生成指定类型的辅助资源。

    从 AGENT_REGISTRY 查找对应 agent，调用 generate_node 方法。
    """
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
