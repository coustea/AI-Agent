"""路径规划工作流 — LLM 输出修复和兜底路径生成。

两个核心函数：
- repair_generated_plan_from_macro_stages — 修复 LLM 输出中 stages/nodes 不对齐的问题
- build_fallback_path_plan — 当 LLM 规划失败时生成稳定的三阶段兜底路径
"""

from __future__ import annotations

from app.path.schemas import (
    AgentLearningPathPlan,
    AgentPathNode,
    AgentStage,
    CreateLearningPathRequest,
)


def repair_generated_plan_from_macro_stages(
    *,
    plan: AgentLearningPathPlan,
    macro_stages: list[AgentStage],
    request: CreateLearningPathRequest,
) -> AgentLearningPathPlan:
    """修复 LLM 生成的路径规划，确保 stages 和 nodes 正确对齐。

    修复策略：
    1. 如果 stages 为空但 macro_stages 有值 → 用 macro_stages 补充
    2. 如果 stages 为空但 nodes 有值 → 从 nodes 的 stage_id 推导 stages
    3. 如果 nodes 为空但 stages 有值 → 为每个 stage 自动生成一个链式节点
    """
    # 策略 1：用宏阶段补充缺失的 stages
    if not plan.stages and macro_stages:
        plan.stages = list(macro_stages)

    # 策略 2：从 nodes 的 stage_id 推导 stages
    if not plan.stages and plan.nodes:
        seen: set[str] = set()
        derived: list[AgentStage] = []
        for node in plan.nodes:
            if node.stage_id not in seen:
                seen.add(node.stage_id)
                derived.append(
                    AgentStage(stage_id=node.stage_id, title=node.title)
                )
        plan.stages = derived

    # 策略 3：从 stages 自动生成链式节点
    if not plan.nodes and plan.stages:
        previous_node_id = ""
        nodes: list[AgentPathNode] = []
        for index, stage in enumerate(plan.stages, 1):
            node_id = f"{stage.stage_id}-core"
            # 难度递进：第一个 beginner，最后一个 advanced，其余 intermediate
            difficulty = "beginner" if index == 1 else "intermediate"
            if index == len(plan.stages) and len(plan.stages) >= 3:
                difficulty = "advanced"
            node = AgentPathNode(
                node_id=node_id,
                stage_id=stage.stage_id,
                title=stage.title,
                prerequisites=[previous_node_id] if previous_node_id else [],
                difficulty=difficulty,
                priority=index * 10,
            )
            nodes.append(node)
            previous_node_id = node_id
        plan.nodes = nodes

    return plan


def build_fallback_path_plan(
    request: CreateLearningPathRequest,
) -> AgentLearningPathPlan:
    """构建兜底学习路径 — 当 LLM 结构化规划失败时使用。

    生成三阶段固定路径：
    1. 基础认知与前置补齐（2 个 beginner 节点）
    2. 核心机制与高频考点（3 个 intermediate 节点）
    3. 综合应用与复习巩固（1 个 advanced 节点）
    """
    topic = (request.topic or request.goal or "课程学习").strip()
    goal = (request.goal or topic).strip()

    stages = [
        AgentStage(stage_id="stage-1", title="基础认知与前置补齐"),
        AgentStage(stage_id="stage-2", title="核心机制与高频考点"),
        AgentStage(stage_id="stage-3", title="综合应用与复习巩固"),
    ]

    nodes = [
        AgentPathNode(
            node_id="node-1",
            stage_id="stage-1",
            title=f"{topic}学习地图与核心术语",
            prerequisites=[],
            difficulty="beginner",
            priority=1,
        ),
        AgentPathNode(
            node_id="node-2",
            stage_id="stage-1",
            title="前置基础补齐",
            prerequisites=["node-1"],
            difficulty="beginner",
            priority=2,
        ),
        AgentPathNode(
            node_id="node-3",
            stage_id="stage-2",
            title="核心概念与结构关系",
            prerequisites=["node-2"],
            difficulty="intermediate",
            priority=3,
        ),
        AgentPathNode(
            node_id="node-4",
            stage_id="stage-2",
            title="关键流程与典型机制",
            prerequisites=["node-3"],
            difficulty="intermediate",
            priority=4,
        ),
        AgentPathNode(
            node_id="node-5",
            stage_id="stage-2",
            title="易错点与薄弱点专项巩固",
            prerequisites=["node-4"],
            difficulty="intermediate",
            priority=5,
        ),
        AgentPathNode(
            node_id="node-6",
            stage_id="stage-3",
            title="综合练习与知识总结",
            prerequisites=["node-5"],
            difficulty="advanced",
            priority=6,
        ),
    ]

    return AgentLearningPathPlan(
        title=f"{topic}个性化学习路径", stages=stages, nodes=nodes
    )
