"""路径规划校验 — 结构校验 + 依赖环检测。

在 LLM 生成路径规划后、持久化到数据库前，进行以下校验：
- 非空 stages/nodes
- 唯一 ID
- 有效的阶段引用
- 有效的难度等级
- 无依赖环（DAG 校验）
- 至少一个起始节点（无前置依赖）
- 每个阶段至少包含一个节点
"""

from __future__ import annotations

from app.infra.logging import get_logger
from app.path.schemas import AgentLearningPathPlan

logger = get_logger(__name__)

# 合法的难度等级
VALID_DIFFICULTIES: tuple[str, ...] = ("beginner", "intermediate", "advanced")


class PathPlanValidationError(ValueError):
    """路径规划结构校验失败 — LLM 输出不安全，不应持久化。"""


def validate_path_plan(plan: AgentLearningPathPlan) -> None:
    """校验生成的路径规划，不合格时抛出 PathPlanValidationError。

    校验项：
    1. stages 和 nodes 非空
    2. 阶段 ID 唯一且非空
    3. 节点 ID 唯一且非空
    4. 节点引用的 stage_id 存在
    5. 难度等级合法
    6. 前置依赖节点存在且不自引用
    7. 无依赖环
    8. 至少一个无前置依赖的起始节点
    9. 每个阶段至少包含一个节点
    """
    if not plan.stages:
        raise PathPlanValidationError("学习路径必须包含至少一个阶段")
    if not plan.nodes:
        raise PathPlanValidationError("学习路径必须包含至少一个学习节点")

    # 校验阶段 ID 唯一性
    stage_ids: set[str] = set()
    for stage in plan.stages:
        if not stage.stage_id.strip():
            raise PathPlanValidationError("阶段 stage_id 不能为空")
        if stage.stage_id in stage_ids:
            raise PathPlanValidationError(f"阶段 ID 重复: {stage.stage_id}")
        stage_ids.add(stage.stage_id)

    # 校验节点：ID 唯一性、阶段引用、难度等级、构建邻接表
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

    # 校验前置依赖：存在性 + 不自引用
    for node_id, prerequisites in adjacency.items():
        for prerequisite_id in prerequisites:
            if prerequisite_id == node_id:
                raise PathPlanValidationError(f"节点 {node_id} 不能依赖自身")
            if prerequisite_id not in node_ids:
                raise PathPlanValidationError(f"节点 {node_id} 引用了不存在的前置节点: {prerequisite_id}")

    # 校验无依赖环
    _assert_no_dependency_cycle(adjacency)

    # 校验至少有一个起始节点
    root_nodes = [node for node in plan.nodes if not node.prerequisites]
    if not root_nodes:
        raise PathPlanValidationError("学习路径必须至少包含一个无前置依赖的起始节点")

    # 校验每个阶段至少包含一个节点
    _validate_stage_node_coverage(plan, stage_ids)


def _validate_stage_node_coverage(plan: AgentLearningPathPlan, stage_ids: set[str]) -> None:
    """校验每个阶段至少包含一个节点。"""
    stages_with_nodes: set[str] = set()
    for node in plan.nodes:
        stages_with_nodes.add(node.stage_id)
    empty_stages = stage_ids - stages_with_nodes
    if empty_stages:
        raise PathPlanValidationError(
            f"以下阶段没有节点: {', '.join(sorted(empty_stages))}"
        )


def _assert_no_dependency_cycle(adjacency: dict[str, list[str]]) -> None:
    """DFS 检测依赖环，发现环时抛出异常。"""
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str, trail: list[str]) -> None:
        if node_id in visited:
            return
        if node_id in visiting:
            # 检测到环，输出环路径
            cycle = " -> ".join([*trail, node_id])
            raise PathPlanValidationError(f"学习路径依赖存在环: {cycle}")

        visiting.add(node_id)
        for prerequisite_id in adjacency.get(node_id, []):
            visit(prerequisite_id, [*trail, node_id])
        visiting.remove(node_id)
        visited.add(node_id)

    for node_id in adjacency:
        visit(node_id, [])
