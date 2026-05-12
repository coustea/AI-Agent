# -*- coding: utf-8 -*-
"""规则规划器。

根据用户选择的 Agent 和依赖关系，一次性生成完整 DAG。
"""

from __future__ import annotations

from typing import Any

from app.infra.logging import get_logger
from app.resource.registry import (
    AGENT_CLASSES,
    DEPENDS,
    agent_layer,
    agent_name,
    agent_output,
    layer_name,
)
from app.resource.schemas import (
    AgentTask,
    ResourceGenerationRequest,
)

logger = get_logger(__name__)


class RulePlanner:
    """规则规划器：根据用户选择的 Agent 和依赖关系，一次性生成完整 DAG。"""

    def plan(self, request: ResourceGenerationRequest) -> list[AgentTask]:
        """根据用户选择和依赖关系生成 AgentTask 列表。"""
        enabled_ids = request.enabled_agent_ids()
        agent_configs = request.agent_configs.model_dump()
        learning_need = request.learning_need

        tasks: list[AgentTask] = []
        for i, agent_id in enumerate(enabled_ids):
            if agent_id not in AGENT_CLASSES:
                continue

            deps = [dep for dep in DEPENDS.get(agent_id, []) if dep in enabled_ids]
            layer = agent_layer(agent_id)

            tasks.append(AgentTask(
                agent_id=agent_id,
                layer=layer,
                layer_name=layer_name(layer),
                task_description=f"根据用户需求「{learning_need[:80]}」生成{agent_name(agent_id)}。",
                depends_on=deps,
                is_explicit=True,
                priority=i,
                config=agent_configs.get(agent_id, {}),
                resource_type=agent_id,
                input_params={"topic": learning_need},
                output_requirements=agent_output(agent_id),
                personalized_constraints=["结合学习者画像"],
                planning_reason="",  # 规则规划不需要规划理由
                failure_policy="skip_on_dependency_failed",
            ))

        logger.info("[RulePlanner] 规划完成: %d 个任务", len(tasks))
        return tasks