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
    # 校验请求的 agent_id 是否已注册
    if agent_id not in AGENT_REGISTRY:
        raise ValueError(f"Agent '{agent_id}' not found in AGENT_REGISTRY")

    # 实例化并调用该 Agent 的节点生成入口
    agent = AGENT_REGISTRY[agent_id]()
    result = await agent.generate_node(node_input)
    # 失败时记录告警但不中断调用方
    if not result.success:
        logger.warning(
            "path_node_resource agent %s failed: %s",
            agent_id,
            result.error or "unknown error",
        )
    return result
