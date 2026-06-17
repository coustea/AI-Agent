"""路径规划校验 — 结构确定性校验 + 资源策略校验 + 规范化补全。"""

from __future__ import annotations

import re

from app.infra.logging import get_logger
from app.path.schemas import ALLOWED_RESOURCE_TYPES, AgentLearningPathPlan, AgentPathNode
from app.config import PATH_MIN_ESTIMATED_MINUTES, PATH_MAX_ESTIMATED_MINUTES

logger = get_logger(__name__)

VALID_DIFFICULTIES: tuple[str, ...] = ("beginner", "intermediate", "advanced")


class PathPlanValidationError(ValueError):
    """Raised when an LLM-generated path is structurally unsafe to persist."""


# ── Deterministic fallback rules ──────────────────────────────────────────

_DIFFICULTY_DEFAULTS: dict[str, dict] = {
    "beginner": {
        "primary_resource_type": "content",
        "required_resource_types": ["content", "quiz"],
        "optional_resource_types": ["mindmap"],
    },
    "intermediate": {
        "primary_resource_type": "content",
        "required_resource_types": ["content", "quiz", "mindmap"],
        "optional_resource_types": ["code"],
    },
    "advanced": {
        "primary_resource_type": "content",
        "required_resource_types": ["content", "code", "quiz"],
        "optional_resource_types": ["mindmap"],
    },
}

_TITLE_KEYWORD_RULES: list[tuple[re.Pattern[str], dict]] = [
    (re.compile(r"总结|复习|回顾"), {
        "primary_resource_type": "ppt",
        "required_resource_types": ["ppt", "quiz"],
        "optional_resource_types": ["mindmap"],
    }),
    (re.compile(r"拓展|前沿|论文|研究|文献"), {
        "primary_resource_type": "reading",
        "required_resource_types": ["reading", "quiz"],
        "optional_resource_types": ["content"],
    }),
    (re.compile(r"代码|算法|实现|实验|编程"), {
        "primary_resource_type": "code",
        "required_resource_types": ["content", "code", "quiz"],
        "optional_resource_types": ["mindmap"],
    }),
]

_GENERATION_FOCUS_BY_DIFFICULTY: dict[str, list[str]] = {
    "beginner": ["基础概念理解与初步练习"],
    "intermediate": ["知识体系构建与综合应用"],
    "advanced": ["深度实践与问题解决能力提升"],
}


def _make_default_policy(node: AgentPathNode) -> dict:
    """Build a deterministic default resource_policy for a node."""
    title = node.title or ""
    difficulty = (node.difficulty or "beginner").lower()

    for pattern, policy in _TITLE_KEYWORD_RULES:
        if pattern.search(title):
            return {
                **policy,
                "expected_resource_count": len(policy["required_resource_types"])
                + len(policy["optional_resource_types"]),
                "generation_focus": [f"{title}的学习资源"],
                "personalization_reason": f"基于标题关键词和{difficulty}难度自动匹配",
                "assessment_type": "quiz",
            }

    base = _DIFFICULTY_DEFAULTS.get(difficulty, _DIFFICULTY_DEFAULTS["beginner"])
    return {
        **base,
        "expected_resource_count": len(base["required_resource_types"])
        + len(base["optional_resource_types"]),
        "generation_focus": _GENERATION_FOCUS_BY_DIFFICULTY.get(
            difficulty, _GENERATION_FOCUS_BY_DIFFICULTY["beginner"]
        ),
        "personalization_reason": f"基于{difficulty}难度自动匹配默认策略",
        "assessment_type": "quiz",
    }


def _filter_resource_types(types: list[str] | None) -> list[str]:
    """Remove resource types that have no implemented agent."""
    if not types:
        return []
    return [t for t in types if t in ALLOWED_RESOURCE_TYPES]


def normalize_path_plan(plan: AgentLearningPathPlan) -> AgentLearningPathPlan:
    """Fill in missing resource_policy and generation_focus deterministically.

    Must run *before* validate_path_plan so validation sees a structurally
    complete plan.  Returns the same plan object (mutated in-place).
    """
    for node in plan.nodes:
        # ── resource_policy ───────────────────────────────────────────
        policy = node.resource_policy
        if policy is None:
            from app.path.schemas import NodeResourcePolicy
            default = _make_default_policy(node)
            node.resource_policy = NodeResourcePolicy(**default)
            logger.info("normalize: filled missing resource_policy for node %s", node.node_id)
        else:
            # Filter out unimplemented types from required and optional
            for field_name in ("required_resource_types", "optional_resource_types"):
                raw: list[str] = list(getattr(policy, field_name) or [])
                filtered = _filter_resource_types(raw)
                if filtered != raw:
                    removed = set(raw) - set(filtered)
                    logger.warning(
                        "normalize: removed unimplemented types %s from node %s.%s",
                        removed, node.node_id, field_name,
                    )
                    setattr(policy, field_name, filtered)

            # Ensure primary_resource_type is valid
            primary = policy.primary_resource_type
            if primary not in ALLOWED_RESOURCE_TYPES:
                default = _make_default_policy(node)
                policy.primary_resource_type = default["primary_resource_type"]
                logger.warning(
                    "normalize: replaced invalid primary_resource_type '%s' with '%s' for node %s",
                    primary, policy.primary_resource_type, node.node_id,
                )

            # Ensure primary is in required
            required = list(policy.required_resource_types)
            if policy.primary_resource_type not in required:
                required = [policy.primary_resource_type] + [
                    t for t in required if t != policy.primary_resource_type
                ]
                policy.required_resource_types = required

            # Recalculate expected_resource_count if missing or inconsistent
            opt = list(policy.optional_resource_types)
            max_count = len(required) + len(opt)
            if policy.expected_resource_count is None or policy.expected_resource_count > max_count:
                policy.expected_resource_count = max_count

            # Fill missing generation_focus
            if not policy.generation_focus:
                policy.generation_focus = _GENERATION_FOCUS_BY_DIFFICULTY.get(
                    (node.difficulty or "beginner").lower(),
                    _GENERATION_FOCUS_BY_DIFFICULTY["beginner"],
                )

            # Fill missing personalization_reason
            if not policy.personalization_reason or not policy.personalization_reason.strip():
                policy.personalization_reason = f"基于{(node.difficulty or 'beginner')}难度自动匹配"

    return plan


def validate_path_plan(plan: AgentLearningPathPlan) -> None:
    """Validate a generated path before persistence or replanning updates.

    Assumes normalize_path_plan has already been called, so resource_policy
    is guaranteed to exist on every node.
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
        if node.estimated_minutes is not None and (
            node.estimated_minutes < PATH_MIN_ESTIMATED_MINUTES or node.estimated_minutes > PATH_MAX_ESTIMATED_MINUTES
        ):
            raise PathPlanValidationError(
                f"节点 {node.node_id} 的 estimated_minutes 必须在 {PATH_MIN_ESTIMATED_MINUTES}-{PATH_MAX_ESTIMATED_MINUTES} 之间"
            )
        if node.difficulty and node.difficulty not in VALID_DIFFICULTIES:
            raise PathPlanValidationError(
                f"节点 {node.node_id} 的 difficulty 必须是 {', '.join(VALID_DIFFICULTIES)} 之一"
            )
        node_ids.add(node.node_id)
        adjacency[node.node_id] = list(node.prerequisites or [])

        # ── Strict resource_policy validation ───────────────────────────
        policy = node.resource_policy
        if policy is None:
            raise PathPlanValidationError(
                f"节点 {node.node_id} 缺少 resource_policy（normalize 未执行？）"
            )

        required = policy.required_resource_types or []
        if not required:
            raise PathPlanValidationError(
                f"节点 {node.node_id} 的 required_resource_types 不能为空"
            )

        invalid_required = [t for t in required if t not in ALLOWED_RESOURCE_TYPES]
        if invalid_required:
            raise PathPlanValidationError(
                f"节点 {node.node_id} 的 required_resource_types 包含未实现的类型: {', '.join(sorted(invalid_required))}"
            )

        primary = policy.primary_resource_type
        if not primary:
            raise PathPlanValidationError(
                f"节点 {node.node_id} 的 primary_resource_type 不能为空"
            )
        if primary not in ALLOWED_RESOURCE_TYPES:
            raise PathPlanValidationError(
                f"节点 {node.node_id} 的 primary_resource_type '{primary}' 未实现"
            )
        if primary not in required:
            raise PathPlanValidationError(
                f"节点 {node.node_id} 的 primary_resource_type '{primary}' 不在 required_resource_types 内"
            )

        optional = policy.optional_resource_types or []
        invalid_optional = [t for t in optional if t not in ALLOWED_RESOURCE_TYPES]
        if invalid_optional:
            raise PathPlanValidationError(
                f"节点 {node.node_id} 的 optional_resource_types 包含未实现的类型: {', '.join(sorted(invalid_optional))}"
            )

        if not policy.generation_focus:
            raise PathPlanValidationError(
                f"节点 {node.node_id} 的 generation_focus 不能为空"
            )

        max_count = len(required) + len(optional)
        if policy.expected_resource_count and policy.expected_resource_count > max_count:
            raise PathPlanValidationError(
                f"节点 {node.node_id} 的 expected_resource_count({policy.expected_resource_count}) 超过实际可用类型数({max_count})"
            )

        _check_node_quality(node)

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


def _check_node_quality(node: AgentPathNode) -> None:
    """Log quality warnings for nodes missing recommended fields."""
    if not node.mastery_target or not node.mastery_target.strip():
        logger.warning("节点 %s 缺少 mastery_target，建议填写掌握目标", node.node_id)
    if not node.recommendation_reason or not node.recommendation_reason.strip():
        logger.warning("节点 %s 缺少 recommendation_reason，建议填写推荐理由", node.node_id)


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
