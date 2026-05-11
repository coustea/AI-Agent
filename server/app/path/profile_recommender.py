"""Profile-based path recommendation engine.

基于用户画像 8 维度的动态路径推荐引擎，提供：
- 维度到节点类型的映射
- 个性化节点评分
- 动态路径调整建议
- 学习进度追踪

设计原则：
- 利用 UserProfile 的 8 个维度信息进行个性化推荐
- 支持冷启动（无画像）和热启动（有画像）场景
- 提供可解释的推荐理由
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.memory.memory_types import (
    ALL_PROFILE_DIMENSIONS,
    PROFILE_DIMENSION_COGNITIVE_STYLE,
    PROFILE_DIMENSION_INTERACTION_PREFERENCE,
    PROFILE_DIMENSION_KNOWLEDGE_FOUNDATION,
    PROFILE_DIMENSION_LEARNING_GOAL,
    PROFILE_DIMENSION_LEARNING_HISTORY,
    PROFILE_DIMENSION_MISTAKE_PREFERENCE,
    PROFILE_DIMENSION_PRACTICE_ABILITY,
    PROFILE_DIMENSION_WEAKNESS_POINTS,
)
from app.path.planner import ALL_NODE_IDS, NODE_TITLES


@dataclass
class NodeRecommendation:
    """节点推荐结果。"""
    node_id: str
    node_title: str
    priority_score: float
    confidence: float
    reasons: list[str]
    profile_dimensions_used: list[str]


@dataclass
class PathAdjustmentSuggestion:
    """路径调整建议。"""
    suggested_nodes_to_add: list[str]
    suggested_nodes_to_skip: list[str]
    suggested_node_order: list[str]
    adjustment_reason: str
    confidence: float


# 维度到节点类型的映射权重
# 每个维度对不同类型的学习资源有不同的推荐权重
DIMENSION_NODE_WEIGHTS: dict[str, dict[str, float]] = {
    PROFILE_DIMENSION_KNOWLEDGE_FOUNDATION: {
        "content": 1.5,
        "mindmap": 1.3,
        "reading": 1.0,
        "diagram": 1.2,
        "quiz": 0.8,
        "code": 0.7,
    },
    PROFILE_DIMENSION_LEARNING_GOAL: {
        "content": 1.0,
        "mindmap": 0.8,
        "reading": 1.2,
        "diagram": 0.7,
        "quiz": 1.3,
        "code": 1.4,
    },
    PROFILE_DIMENSION_COGNITIVE_STYLE: {
        "content": 1.0,
        "mindmap": 1.4,
        "reading": 0.8,
        "diagram": 1.5,
        "quiz": 1.0,
        "code": 1.2,
    },
    PROFILE_DIMENSION_WEAKNESS_POINTS: {
        "content": 1.3,
        "mindmap": 1.0,
        "reading": 0.9,
        "diagram": 1.1,
        "quiz": 1.5,
        "code": 1.2,
    },
    PROFILE_DIMENSION_MISTAKE_PREFERENCE: {
        "content": 1.0,
        "mindmap": 0.8,
        "reading": 0.7,
        "diagram": 0.9,
        "quiz": 1.6,
        "code": 1.3,
    },
    PROFILE_DIMENSION_PRACTICE_ABILITY: {
        "content": 0.7,
        "mindmap": 0.8,
        "reading": 0.6,
        "diagram": 0.7,
        "quiz": 1.2,
        "code": 1.6,
    },
    PROFILE_DIMENSION_INTERACTION_PREFERENCE: {
        "content": 0.9,
        "mindmap": 1.1,
        "reading": 0.8,
        "diagram": 1.0,
        "quiz": 1.3,
        "code": 1.1,
    },
    PROFILE_DIMENSION_LEARNING_HISTORY: {
        "content": 1.1,
        "mindmap": 1.0,
        "reading": 1.3,
        "diagram": 0.9,
        "quiz": 1.0,
        "code": 1.1,
    },
}

# 认知风格关键词到节点类型的映射
COGNITIVE_STYLE_KEYWORDS: dict[str, list[str]] = {
    "visual": ["diagram", "mindmap"],
    "图": ["diagram", "mindmap"],
    "图像": ["diagram", "mindmap"],
    "视觉": ["diagram", "mindmap"],
    "auditory": ["content"],
    "听": ["content"],
    "音频": ["content"],
    "讲解": ["content"],
    "kinesthetic": ["code", "quiz"],
    "动手": ["code", "quiz"],
    "实践": ["code", "quiz"],
    "操作": ["code", "quiz"],
    "reading": ["reading", "content"],
    "阅读": ["reading", "content"],
    "文字": ["reading", "content"],
    "文档": ["reading", "content"],
}

# 学习目标关键词到节点类型的映射
GOAL_KEYWORDS: dict[str, list[str]] = {
    "exam": ["quiz", "content", "mindmap"],
    "考试": ["quiz", "content", "mindmap"],
    "project": ["code", "reading"],
    "项目": ["code", "reading"],
    "understanding": ["content", "mindmap", "diagram"],
    "理解": ["content", "mindmap", "diagram"],
    "practice": ["code", "quiz"],
    "实践": ["code", "quiz"],
}


def _get_dimension_confidence(profile_json: dict[str, Any], dimension: str) -> float:
    """获取单个维度的置信度。"""
    dims = profile_json.get("dimensions", {})
    dim_data = dims.get(dimension, {})
    return float(dim_data.get("confidence", 0.0))


def _get_dimension_summary(profile_json: dict[str, Any], dimension: str) -> str:
    """获取单个维度的摘要。"""
    dims = profile_json.get("dimensions", {})
    dim_data = dims.get(dimension, {})
    return str(dim_data.get("summary", "") or "")


def _extract_keywords(text: str) -> list[str]:
    """从文本中提取关键词。"""
    text_lower = text.lower()
    keywords = []
    for key, node_types in COGNITIVE_STYLE_KEYWORDS.items():
        if key in text_lower:
            keywords.append(key)
    for key, node_types in GOAL_KEYWORDS.items():
        if key in text_lower:
            keywords.append(key)
    return keywords


def compute_node_scores(
    profile_json: dict[str, Any] | None,
    *,
    weak_points: list[str] | None = None,
    completed_node_ids: set[str] | None = None,
) -> dict[str, float]:
    """基于用户画像计算各节点类型的推荐分数。

    Args:
        profile_json: 用户画像 JSON，包含 8 维度信息。
        weak_points: 额外的薄弱点列表。
        completed_node_ids: 已完成的节点 ID 集合。

    Returns:
        节点 ID 到推荐分数的映射（0-100）。
    """
    scores: dict[str, float] = {node_id: 50.0 for node_id in ALL_NODE_IDS}
    completed = completed_node_ids or set()

    if not profile_json:
        # 冷启动：使用默认权重
        scores["content"] = 70.0
        scores["quiz"] = 65.0
        scores["mindmap"] = 60.0
        return scores

    dims = profile_json.get("dimensions", {})

    # 遍历每个维度，累加权重
    for dim_key in ALL_PROFILE_DIMENSIONS:
        dim_data = dims.get(dim_key, {})
        dim_confidence = float(dim_data.get("confidence", 0.0))
        dim_summary = str(dim_data.get("summary", "") or "")

        if dim_confidence < 0.1 and not dim_summary:
            continue

        weights = DIMENSION_NODE_WEIGHTS.get(dim_key, {})
        for node_id, weight in weights.items():
            if node_id in scores:
                # 置信度越高，权重影响越大
                adjusted_weight = weight * (0.5 + dim_confidence * 0.5)
                scores[node_id] += (adjusted_weight - 1.0) * 20

    # 基于认知风格关键词调整
    cognitive_style = _get_dimension_summary(profile_json, PROFILE_DIMENSION_COGNITIVE_STYLE)
    for keyword, node_types in COGNITIVE_STYLE_KEYWORDS.items():
        if keyword in cognitive_style.lower():
            for node_id in node_types:
                if node_id in scores:
                    scores[node_id] += 10

    # 基于学习目标关键词调整
    learning_goal = _get_dimension_summary(profile_json, PROFILE_DIMENSION_LEARNING_GOAL)
    for keyword, node_types in GOAL_KEYWORDS.items():
        if keyword in learning_goal.lower():
            for node_id in node_types:
                if node_id in scores:
                    scores[node_id] += 15

    # 薄弱点调整
    weakness_summary = _get_dimension_summary(profile_json, PROFILE_DIMENSION_WEAKNESS_POINTS)
    weak_points_list = weak_points or []
    combined_weak = set(weak_points_list)
    if weakness_summary:
        for keyword, node_types in GOAL_KEYWORDS.items():
            if keyword in weakness_summary.lower():
                combined_weak.update(node_types)

    for node_id in combined_weak:
        if node_id in scores:
            scores[node_id] += 25

    # 已完成节点降权
    for node_id in completed:
        if node_id in scores:
            scores[node_id] *= 0.3

    # 归一化到 0-100
    min_score = min(scores.values())
    max_score = max(scores.values())
    if max_score > min_score:
        for node_id in scores:
            scores[node_id] = max(0, min(100, (scores[node_id] - min_score) / (max_score - min_score) * 100))

    return scores


def recommend_nodes(
    profile_json: dict[str, Any] | None,
    *,
    weak_points: list[str] | None = None,
    completed_node_ids: set[str] | None = None,
    top_k: int = 5,
) -> list[NodeRecommendation]:
    """基于用户画像推荐学习节点。

    Args:
        profile_json: 用户画像 JSON。
        weak_points: 额外的薄弱点列表。
        completed_node_ids: 已完成的节点 ID 集合。
        top_k: 返回的推荐数量。

    Returns:
        推荐节点列表，按优先级降序排列。
    """
    scores = compute_node_scores(
        profile_json,
        weak_points=weak_points,
        completed_node_ids=completed_node_ids,
    )

    completed = completed_node_ids or set()
    recommendations: list[NodeRecommendation] = []

    for node_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        if node_id in completed:
            continue

        reasons = []
        dims_used = []

        if profile_json:
            dims = profile_json.get("dimensions", {})

            # 检查各维度对推荐的影响
            for dim_key in ALL_PROFILE_DIMENSIONS:
                dim_data = dims.get(dim_key, {})
                dim_confidence = float(dim_data.get("confidence", 0.0))
                weights = DIMENSION_NODE_WEIGHTS.get(dim_key, {})
                node_weight = weights.get(node_id, 1.0)

                if dim_confidence > 0.3 and node_weight > 1.1:
                    reasons.append(f"符合{dim_data.get('name', dim_key)}特征")
                    dims_used.append(dim_key)

        if node_id in (weak_points or []):
            reasons.append("针对薄弱点强化")
            dims_used.append(PROFILE_DIMENSION_WEAKNESS_POINTS)

        if not reasons:
            reasons.append("适合当前学习阶段")

        recommendations.append(NodeRecommendation(
            node_id=node_id,
            node_title=NODE_TITLES.get(node_id, node_id),
            priority_score=score,
            confidence=0.7 if profile_json else 0.4,
            reasons=reasons[:3],
            profile_dimensions_used=list(set(dims_used)),
        ))

        if len(recommendations) >= top_k:
            break

    return recommendations


def suggest_path_adjustment(
    profile_json: dict[str, Any] | None,
    current_plan_nodes: list[str],
    *,
    weak_points: list[str] | None = None,
    completed_node_ids: set[str] | None = None,
    feedback: str | None = None,
) -> PathAdjustmentSuggestion:
    """基于用户画像和反馈建议路径调整。

    Args:
        profile_json: 用户画像 JSON。
        current_plan_nodes: 当前路径中的节点列表。
        weak_points: 额外的薄弱点列表。
        completed_node_ids: 已完成的节点 ID 集合。
        feedback: 用户反馈文本。

    Returns:
        路径调整建议。
    """
    scores = compute_node_scores(
        profile_json,
        weak_points=weak_points,
        completed_node_ids=completed_node_ids,
    )

    completed = completed_node_ids or set()
    current_set = set(current_plan_nodes)

    # 找出高分但未在当前路径中的节点
    nodes_to_add = []
    for node_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        if node_id not in current_set and node_id not in completed and score > 60:
            nodes_to_add.append(node_id)

    # 找出低分但在当前路径中的节点
    nodes_to_skip = []
    for node_id in current_plan_nodes:
        if node_id not in completed and scores.get(node_id, 50) < 40:
            nodes_to_skip.append(node_id)

    # 重新排序：按分数降序
    remaining = [n for n in current_plan_nodes if n not in completed]
    new_order = sorted(remaining, key=lambda x: scores.get(x, 50), reverse=True)

    # 添加新节点
    for node_id in nodes_to_add[:2]:
        if node_id not in new_order:
            new_order.append(node_id)

    # 生成调整原因
    reasons = []
    if nodes_to_add:
        reasons.append(f"建议增加 {NODE_TITLES.get(nodes_to_add[0], nodes_to_add[0])}")
    if nodes_to_skip:
        reasons.append(f"建议跳过 {NODE_TITLES.get(nodes_to_skip[0], nodes_to_skip[0])}")
    if feedback:
        reasons.append(f"根据反馈：「{feedback[:50]}」")

    if not reasons:
        reasons.append("当前路径已优化，无需调整")

    return PathAdjustmentSuggestion(
        suggested_nodes_to_add=nodes_to_add[:3],
        suggested_nodes_to_skip=nodes_to_skip,
        suggested_node_order=new_order,
        adjustment_reason="；".join(reasons),
        confidence=0.75 if profile_json else 0.5,
    )


def compute_learning_pace(profile_json: dict[str, Any] | None) -> str:
    """基于用户画像计算学习节奏建议。

    Args:
        profile_json: 用户画像 JSON。

    Returns:
        学习节奏建议：'slow' | 'normal' | 'fast'
    """
    if not profile_json:
        return "normal"

    dims = profile_json.get("dimensions", {})

    # 基于认知风格和实践能力判断
    cognitive_style = _get_dimension_summary(profile_json, PROFILE_DIMENSION_COGNITIVE_STYLE)
    practice_ability = _get_dimension_summary(profile_json, PROFILE_DIMENSION_PRACTICE_ABILITY)
    interaction_pref = _get_dimension_summary(profile_json, PROFILE_DIMENSION_INTERACTION_PREFERENCE)

    # 关键词判断
    fast_keywords = ["快", "fast", "高效", "熟练", "强"]
    slow_keywords = ["慢", "slow", "基础", "薄弱", "弱"]

    cognitive_lower = cognitive_style.lower()
    practice_lower = practice_ability.lower()
    interaction_lower = interaction_pref.lower()
    combined = f"{cognitive_lower} {practice_lower} {interaction_lower}"

    fast_count = sum(1 for kw in fast_keywords if kw in combined)
    slow_count = sum(1 for kw in slow_keywords if kw in combined)

    if fast_count > slow_count + 1:
        return "fast"
    elif slow_count > fast_count + 1:
        return "slow"
    return "normal"


def estimate_completion_time(
    profile_json: dict[str, Any] | None,
    remaining_nodes: int,
) -> int:
    """基于用户画像估算完成时间。

    Args:
        profile_json: 用户画像 JSON。
        remaining_nodes: 剩余节点数量。

    Returns:
        预计完成天数。
    """
    pace = compute_learning_pace(profile_json)

    if pace == "fast":
        capacity = 2.5
    elif pace == "slow":
        capacity = 0.6
    else:
        capacity = 1.2

    # 基于实践能力调整
    if profile_json:
        practice_conf = _get_dimension_confidence(profile_json, PROFILE_DIMENSION_PRACTICE_ABILITY)
        if practice_conf > 0.7:
            capacity *= 1.2
        elif practice_conf < 0.3:
            capacity *= 0.8

    import math
    return max(1, math.ceil(remaining_nodes / capacity))
