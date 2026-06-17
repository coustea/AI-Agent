"""路径规划校验 — 结构校验 + 依赖环检测。"""

from __future__ import annotations

from app.infra.logging import get_logger
from app.path.schemas import AgentLearningPathPlan

logger = get_logger(__name__)

VALID_DIFFICULTIES: tuple[str, ...] = ("beginner", "intermediate", "advanced")


class PathPlanValidationError(ValueError):
    """Raised when an LLM-generated path is structurally unsafe to persist."""


def validate_path_plan(plan: AgentLearningPathPlan) -> None:
    """Validate a generated path before persistence.

    Checks: non-empty stages/nodes, unique IDs, valid references,
    valid difficulty, no dependency cycles, at least one root node,
    every stage has at least one node.
    """
    if not plan.stages:
        raise PathPlanValidationError("学习路径必须包含至少一个阶段")
    if not plan.nodes:
        raise PathPlanValidationError("学习路径必须包含至少一个学习节点")

    stage_ids: set[str] = set()
    for stage in plan.stages:
        if not stage.stage_id.strip():
            raise PathPlanValidationError("阶段 stage_id 不能为空")
        if stage.stage_id in stage_ids:
            raise PathPlanValidationError(f"阶段 ID 重复: {stage.stage_id}")
        stage_ids.add(stage.stage_id)

    node_ids: set[str] = set()
    adjacency: dict[str, list[str]] = {}
    for node in plan.nodes:
        if not node.node_id.strip():
            raise PathPlanValidationError("节点 node_id 不能为空")
        if node.node_id in node_ids:
            raise PathPlanValidationError(f"节点 ID 重复: {node.node_id}")
        if node.stage_id not in stage_ids:
            raise PathPlanValidationError(f"节点 {node.node_id} 引用了不存在的阶段: {node.stage_id}")
        if node.difficulty and node.difficulty not in VALID_DIFFICULTIES:
            raise PathPlanValidationError(
                f"节点 {node.node_id} 的 difficulty 必须是 {', '.join(VALID_DIFFICULTIES)} 之一"
            )
        node_ids.add(node.node_id)
        adjacency[node.node_id] = list(node.prerequisites or [])

    for node_id, prerequisites in adjacency.items():
        for prerequisite_id in prerequisites:
            if prerequisite_id == node_id:
                raise PathPlanValidationError(f"节点 {node_id} 不能依赖自身")
            if prerequisite_id not in node_ids:
                raise PathPlanValidationError(f"节点 {node_id} 引用了不存在的前置节点: {prerequisite_id}")

    _assert_no_dependency_cycle(adjacency)

    root_nodes = [node for node in plan.nodes if not node.prerequisites]
    if not root_nodes:
        raise PathPlanValidationError("学习路径必须至少包含一个无前置依赖的起始节点")

    _validate_stage_node_coverage(plan, stage_ids)


def _validate_stage_node_coverage(plan: AgentLearningPathPlan, stage_ids: set[str]) -> None:
    """Ensure every stage has at least one node."""
    stages_with_nodes: set[str] = set()
    for node in plan.nodes:
        stages_with_nodes.add(node.stage_id)
    empty_stages = stage_ids - stages_with_nodes
    if empty_stages:
        raise PathPlanValidationError(
            f"以下阶段没有节点: {', '.join(sorted(empty_stages))}"
        )


def _assert_no_dependency_cycle(adjacency: dict[str, list[str]]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str, trail: list[str]) -> None:
        if node_id in visited:
            return
        if node_id in visiting:
            cycle = " -> ".join([*trail, node_id])
            raise PathPlanValidationError(f"学习路径依赖存在环: {cycle}")

        visiting.add(node_id)
        for prerequisite_id in adjacency.get(node_id, []):
            visit(prerequisite_id, [*trail, node_id])
        visiting.remove(node_id)
        visited.add(node_id)

    for node_id in adjacency:
        visit(node_id, [])
