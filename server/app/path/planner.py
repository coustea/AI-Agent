"""Path planning algorithms.

提供学习路径规划的核心算法，包括：
- 初始路径构建
- 节点评分
- 进度计算
- 路径调整
"""

from __future__ import annotations

from datetime import datetime
from math import ceil
from typing import Iterable

from app.path.schemas import Adjustment, PathNode, PathPlan, PathProgress, PathStage
from app.resource.utils import (
    CORE_AGENTS,
    STRUCTURE_AGENTS,
    PRACTICE_AGENTS,
    EXTENSION_AGENTS,
)

ENHANCEMENT_AGENTS = STRUCTURE_AGENTS + PRACTICE_AGENTS + EXTENSION_AGENTS
PRESENTATION_AGENTS: list[str] = []

NODE_TITLES: dict[str, str] = {
    "content": "核心知识讲解",
    "mindmap": "知识结构梳理",
    "quiz": "基础测验",
    "reading": "拓展阅读",
    "code": "代码实操",
    "image": "图解理解",
    "ppt": "知识输出演示",
    "video": "讲解脚本复盘",
}

STAGE_NODE_GROUPS: list[tuple[str, str, list[str]]] = [
    ("foundation", "基础阶段", list(CORE_AGENTS)),
    ("enhancement", "强化阶段", list(ENHANCEMENT_AGENTS)),
    ("application", "应用阶段", list(PRESENTATION_AGENTS)),
]


def _all_node_ids() -> list[str]:
    ordered: list[str] = []
    for _, _, nodes in STAGE_NODE_GROUPS:
        ordered.extend(nodes)
    return ordered


ALL_NODE_IDS = _all_node_ids()


def build_initial_plan(
    *,
    knowledge_level: str | None,
    learning_goal: str | None,
    weak_points: list[str] | None = None,
    planned_node_ids: set[str] | None = None,
    now: datetime | None = None,
) -> PathPlan:
    now = now or datetime.now()
    selected_ids = set(planned_node_ids or ALL_NODE_IDS)
    weak_points = weak_points or []

    stages: list[PathStage] = []
    for stage_id, stage_title, node_ids in STAGE_NODE_GROUPS:
        nodes = [
            PathNode(
                id=node_id,
                title=NODE_TITLES.get(node_id, node_id),
            )
            for node_id in node_ids
            if node_id in selected_ids
        ]
        if not nodes:
            continue
        stages.append(
            PathStage(
                id=stage_id,
                title=stage_title,
                nodes=nodes,
            )
        )

    if not stages:
        for stage_id, stage_title, node_ids in STAGE_NODE_GROUPS:
            stages.append(
                PathStage(
                    id=stage_id,
                    title=stage_title,
                    nodes=[PathNode(id=node_id, title=NODE_TITLES.get(node_id, node_id)) for node_id in node_ids],
                )
            )

    return PathPlan(
        version=1,
        generated_at=now,
        knowledge_level=knowledge_level,
        learning_goal=learning_goal,
        weak_points=weak_points,
        stages=stages,
        progress=PathProgress(
            overall=0,
            current_stage_id=stages[0].id if stages else None,
            confidence=60,
            eta_days=14,
        ),
        adjustments=[],
    )


def score_nodes(plan: PathPlan, *, weak_points: Iterable[str] | None = None) -> PathPlan:
    weak_set = {item for item in (weak_points or []) if item in ALL_NODE_IDS}
    updated_stages: list[PathStage] = []

    for stage in plan.stages:
        updated_nodes: list[PathNode] = []
        for node in stage.nodes:
            score = 50
            if node.id in {"content", "quiz"}:
                score += 10
            if node.id in weak_set:
                score += 25
            if node.id in {"ppt", "video"}:
                score -= 5
            updated_nodes.append(node.model_copy(update={"priority": max(0, min(score, 100))}))
        updated_stages.append(stage.model_copy(update={"nodes": updated_nodes}))

    return plan.model_copy(update={"stages": updated_stages})


def compute_progress(
    plan: PathPlan,
    *,
    completed_node_ids: set[str],
    pace: str | None = None,
) -> PathPlan:
    stages: list[PathStage] = []
    total_nodes = 0
    completed_nodes = 0

    for stage in plan.stages:
        nodes: list[PathNode] = []
        stage_total = len(stage.nodes)
        stage_done = 0

        for node in stage.nodes:
            total_nodes += 1
            if node.id in completed_node_ids:
                stage_done += 1
                completed_nodes += 1
                nodes.append(node.model_copy(update={"status": "success", "progress": 100}))
            else:
                nodes.append(node.model_copy(update={"status": "wait", "progress": 0}))

        if stage_total == 0:
            stage_status = "wait"
            stage_progress = 0
        elif stage_done == stage_total:
            stage_status = "success"
            stage_progress = 100
        elif stage_done > 0:
            stage_status = "processing"
            stage_progress = int(stage_done / stage_total * 100)
        else:
            stage_status = "wait"
            stage_progress = 0

        stages.append(stage.model_copy(update={"nodes": nodes, "status": stage_status, "progress": stage_progress}))

    current_stage_id: str | None = None
    for stage in stages:
        if stage.nodes and stage.status != "success":
            current_stage_id = stage.id
            break
    if current_stage_id is None and stages:
        current_stage_id = stages[-1].id

    if completed_nodes == 0:
        for index, stage in enumerate(stages):
            if stage.nodes:
                stages[index] = stage.model_copy(update={"status": "processing"})
                current_stage_id = stage.id
                break

    overall = int((completed_nodes / total_nodes) * 100) if total_nodes else 0
    eta_days = estimate_eta(remaining_count=max(total_nodes - completed_nodes, 0), pace=pace)
    progress = plan.progress.model_copy(
        update={
            "overall": overall,
            "current_stage_id": current_stage_id,
            "eta_days": eta_days,
        }
    )

    return plan.model_copy(update={"stages": stages, "progress": progress})


def adjust_plan(
    plan: PathPlan,
    *,
    weak_points: list[str] | None = None,
    feedback: str | None = None,
    now: datetime | None = None,
) -> PathPlan:
    now = now or datetime.now()
    normalized_weak = [item for item in (weak_points or []) if item in ALL_NODE_IDS]
    if not normalized_weak and not (feedback and feedback.strip()):
        return plan

    adjusted = score_nodes(plan, weak_points=normalized_weak)
    merged_weak = list(dict.fromkeys([*adjusted.weak_points, *normalized_weak]))
    reason = (feedback or "").strip() or "根据最新反馈自动调整学习路径"
    new_adjustment = Adjustment(
        at=now,
        reason=reason,
        impacted_nodes=normalized_weak,
    )

    return adjusted.model_copy(
        update={
            "weak_points": merged_weak,
            "adjustments": [*adjusted.adjustments, new_adjustment],
        }
    )


def derive_next_action(plan: PathPlan) -> str:
    for stage in plan.stages:
        if stage.id != plan.progress.current_stage_id:
            continue
        for node in stage.nodes:
            if node.status != "success":
                return f"优先完成「{node.title}」"
    return "继续保持，当前路径已完成"


def estimate_eta(*, remaining_count: int, pace: str | None) -> int:
    normalized = (pace or "").lower()
    if any(keyword in normalized for keyword in ("fast", "快", "rapid", "high")):
        capacity = 2.0
    elif any(keyword in normalized for keyword in ("slow", "慢", "low")):
        capacity = 0.5
    else:
        capacity = 1.0
    return max(1, ceil(remaining_count / capacity))
