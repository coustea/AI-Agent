"""学习路径规划算法模块。

提供基于用户画像 8 维度的动态学习路径规划算法，包括：
- 基于画像维度的节点评分
- 动态路径推荐
- 学习进度追踪
- 自适应路径调整
"""

from __future__ import annotations

from datetime import datetime
from math import ceil
from typing import Iterable

from app.path.schemas import Adjustment, PathNode, PathPlan, PathProgress, PathStage
# =============================================================================
# Agent 分组常量
# =============================================================================

FOUNDATION_AGENTS = ["content", "mindmap", "diagram"]
PRACTICE_PATH_AGENTS = ["quiz", "code"]
EXTENSION_PATH_AGENTS = ["reading"]

NODE_TITLES: dict[str, str] = {
    "content": "核心知识讲解",
    "mindmap": "知识结构梳理",
    "diagram": "图解理解",
    "quiz": "基础测验",
    "code": "代码实操",
    "reading": "拓展阅读",
}

STAGE_NODE_GROUPS: list[tuple[str, str, list[str]]] = [
    ("foundation", "基础建构", list(FOUNDATION_AGENTS)),
    ("practice", "练习巩固", list(PRACTICE_PATH_AGENTS)),
    ("extension", "拓展迁移", list(EXTENSION_PATH_AGENTS)),
]

# =============================================================================
# 画像维度到学习节点的映射
# =============================================================================

# 画像维度与推荐学习方式的映射
DIMENSION_LEARNING_STYLE_MAP: dict[str, dict[str, list[str]]] = {
    "knowledge_foundation": {
        "low": ["content", "mindmap", "reading"],
        "medium": ["content", "quiz"],
        "high": ["code", "quiz"],
    },
    "learning_goal": {
        "exam": ["quiz", "content", "mindmap"],
        "project": ["code", "content", "reading"],
        "research": ["reading", "content", "mindmap"],
        "general": ["content", "mindmap", "quiz"],
    },
    "cognitive_style": {
        "visual": ["mindmap", "diagram"],
        "auditory": ["content"],
        "reading": ["reading", "content"],
        "kinesthetic": ["code", "quiz"],
    },
    "weakness_points": {
        "concept": ["content", "mindmap", "reading"],
        "practice": ["code", "quiz"],
        "application": ["code", "reading"],
    },
    "practice_ability": {
        "low": ["content", "mindmap", "quiz"],
        "medium": ["code", "quiz"],
        "high": ["code", "quiz"],
    },
    "interaction_preference": {
        "guided": ["content", "quiz"],
        "exploratory": ["reading", "code", "mindmap"],
        "balanced": ["content", "quiz", "code"],
    },
}

# 节点类型与画像维度的关联权重
NODE_DIMENSION_WEIGHTS: dict[str, dict[str, float]] = {
    "content": {
        "knowledge_foundation": 0.3,
        "learning_goal": 0.2,
        "cognitive_style": 0.15,
        "weakness_points": 0.2,
        "practice_ability": 0.1,
        "interaction_preference": 0.05,
    },
    "mindmap": {
        "knowledge_foundation": 0.25,
        "cognitive_style": 0.35,
        "weakness_points": 0.2,
        "learning_goal": 0.1,
        "practice_ability": 0.05,
        "interaction_preference": 0.05,
    },
    "quiz": {
        "weakness_points": 0.35,
        "practice_ability": 0.25,
        "knowledge_foundation": 0.15,
        "learning_goal": 0.15,
        "cognitive_style": 0.05,
        "interaction_preference": 0.05,
    },
    "code": {
        "practice_ability": 0.35,
        "learning_goal": 0.25,
        "weakness_points": 0.2,
        "knowledge_foundation": 0.1,
        "cognitive_style": 0.05,
        "interaction_preference": 0.05,
    },
    "reading": {
        "learning_goal": 0.3,
        "knowledge_foundation": 0.25,
        "cognitive_style": 0.2,
        "weakness_points": 0.1,
        "practice_ability": 0.1,
        "interaction_preference": 0.05,
    },
    "diagram": {
        "cognitive_style": 0.4,
        "knowledge_foundation": 0.25,
        "weakness_points": 0.15,
        "learning_goal": 0.1,
        "practice_ability": 0.05,
        "interaction_preference": 0.05,
    },
}


def _all_node_ids() -> list[str]:
    """获取所有节点 ID 的有序列表。"""
    ordered: list[str] = []
    for _, _, nodes in STAGE_NODE_GROUPS:
        ordered.extend(nodes)
    return ordered


ALL_NODE_IDS = _all_node_ids()


# =============================================================================
# 画像维度分析函数
# =============================================================================


def analyze_profile_dimensions(profile_json: dict | None) -> dict[str, dict]:
    """分析用户画像的 8 个维度，返回结构化的维度分析结果。

    Args:
        profile_json: 用户画像 JSON 数据。

    Returns:
        包含每个维度分析结果的字典，格式为：
        {
            "dimension_key": {
                "level": "low" | "medium" | "high" | str,
                "confidence": float,
                "summary": str,
                "evidence": list[str],
            }
        }
    """
    if not profile_json:
        return {}

    dimensions = profile_json.get("dimensions", {})
    result: dict[str, dict] = {}

    for dim_key in [
        "knowledge_foundation",
        "learning_goal",
        "cognitive_style",
        "weakness_points",
        "mistake_preference",
        "practice_ability",
        "interaction_preference",
        "learning_history",
    ]:
        dim_data = dimensions.get(dim_key, {})
        summary = dim_data.get("summary", "") or ""
        confidence = dim_data.get("confidence", 0.0) or 0.0
        evidence = dim_data.get("evidence", []) or []

        # 根据维度内容推断等级
        level = _infer_dimension_level(dim_key, summary, evidence)

        result[dim_key] = {
            "level": level,
            "confidence": confidence,
            "summary": summary,
            "evidence": evidence if isinstance(evidence, list) else [],
        }

    return result


def _infer_dimension_level(dim_key: str, summary: str, evidence: list) -> str:
    """根据维度内容推断等级。

    Args:
        dim_key: 维度键名。
        summary: 维度摘要。
        evidence: 证据列表。

    Returns:
        推断的等级字符串。
    """
    summary_lower = (summary or "").lower()

    if dim_key == "knowledge_foundation":
        if any(kw in summary_lower for kw in ["扎实", "strong", "high", "熟练", "精通"]):
            return "high"
        elif any(kw in summary_lower for kw in ["薄弱", "weak", "low", "不足", "欠缺"]):
            return "low"
        return "medium"

    elif dim_key == "learning_goal":
        if any(kw in summary_lower for kw in ["考试", "exam", "认证", "certif"]):
            return "exam"
        elif any(kw in summary_lower for kw in ["项目", "project", "实践", "practical"]):
            return "project"
        elif any(kw in summary_lower for kw in ["研究", "research", "论文", "paper"]):
            return "research"
        return "general"

    elif dim_key == "cognitive_style":
        if any(kw in summary_lower for kw in ["视觉", "visual", "图像", "图表"]):
            return "visual"
        elif any(kw in summary_lower for kw in ["听觉", "auditory", "音频", "讲解"]):
            return "auditory"
        elif any(kw in summary_lower for kw in ["阅读", "reading", "文字", "文档"]):
            return "reading"
        elif any(kw in summary_lower for kw in ["动手", "kinesthetic", "实践", "操作"]):
            return "kinesthetic"
        return "balanced"

    elif dim_key == "practice_ability":
        if any(kw in summary_lower for kw in ["强", "strong", "丰富", "熟练"]):
            return "high"
        elif any(kw in summary_lower for kw in ["弱", "weak", "不足", "欠缺"]):
            return "low"
        return "medium"

    elif dim_key == "interaction_preference":
        if any(kw in summary_lower for kw in ["引导", "guided", "指导", "步骤"]):
            return "guided"
        elif any(kw in summary_lower for kw in ["探索", "exploratory", "自主", "自由"]):
            return "exploratory"
        return "balanced"

    elif dim_key == "weakness_points":
        if any(kw in summary_lower for kw in ["概念", "concept", "理论", "原理"]):
            return "concept"
        elif any(kw in summary_lower for kw in ["实践", "practice", "应用", "代码"]):
            return "practice"
        elif any(kw in summary_lower for kw in ["综合", "application", "整合"]):
            return "application"
        return "concept"

    return "medium"


# =============================================================================
# 核心规划算法
# =============================================================================


def build_initial_plan(
    *,
    knowledge_level: str | None,
    learning_goal: str | None,
    weak_points: list[str] | None = None,
    planned_node_ids: set[str] | None = None,
    now: datetime | None = None,
    profile_dimensions: dict[str, dict] | None = None,
) -> PathPlan:
    """构建初始学习路径计划。

    Args:
        knowledge_level: 知识水平评估。
        learning_goal: 学习目标。
        weak_points: 薄弱点列表。
        planned_node_ids: 已规划的节点 ID 集合。
        now: 当前时间。
        profile_dimensions: 画像维度分析结果。

    Returns:
        初始化的 PathPlan 对象。
    """
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
        profile_dimensions=profile_dimensions,
    )


def score_nodes_with_profile(
    plan: PathPlan,
    *,
    profile_dimensions: dict[str, dict],
    weak_points: Iterable[str] | None = None,
) -> PathPlan:
    """基于用户画像维度对节点进行智能评分。

    Args:
        plan: 当前路径计划。
        profile_dimensions: 画像维度分析结果。
        weak_points: 薄弱点节点列表。

    Returns:
        更新了节点优先级的 PathPlan 对象。
    """
    weak_set = {item for item in (weak_points or []) if item in ALL_NODE_IDS}
    updated_stages: list[PathStage] = []

    for stage in plan.stages:
        updated_nodes: list[PathNode] = []
        for node in stage.nodes:
            # 基础分数
            score = 50.0

            # 根据节点类型与画像维度的权重计算分数
            node_weights = NODE_DIMENSION_WEIGHTS.get(node.id, {})
            for dim_key, weight in node_weights.items():
                dim_data = profile_dimensions.get(dim_key, {})
                dim_level = dim_data.get("level", "medium")
                dim_confidence = dim_data.get("confidence", 0.5)

                # 根据维度等级调整分数
                level_bonus = _calculate_level_bonus(node.id, dim_key, dim_level)
                score += level_bonus * weight * dim_confidence

            # 薄弱点加成
            if node.id in weak_set:
                score += 25

            # 核心节点加成
            if node.id in {"content", "quiz"}:
                score += 10

            updated_nodes.append(node.model_copy(update={"priority": max(0, min(int(score), 100))}))
        updated_stages.append(stage.model_copy(update={"nodes": updated_nodes}))

    return plan.model_copy(update={"stages": updated_stages, "profile_dimensions": profile_dimensions})


def _calculate_level_bonus(node_id: str, dim_key: str, level: str) -> float:
    """计算维度等级对节点的分数加成。

    Args:
        node_id: 节点 ID。
        dim_key: 维度键名。
        level: 维度等级。

    Returns:
        分数加成值。
    """
    # 知识基础维度
    if dim_key == "knowledge_foundation":
        if level == "low" and node_id in ["content", "mindmap", "reading"]:
            return 20
        elif level == "high" and node_id in ["code", "quiz"]:
            return 15
        return 5

    # 学习目标维度
    elif dim_key == "learning_goal":
        if level == "exam" and node_id in ["quiz", "content"]:
            return 20
        elif level == "project" and node_id in ["code", "reading"]:
            return 20
        elif level == "research" and node_id in ["reading", "mindmap"]:
            return 15
        return 5

    # 认知风格维度
    elif dim_key == "cognitive_style":
        if level == "visual" and node_id in ["mindmap", "diagram"]:
            return 25
        elif level == "auditory" and node_id in ["content"]:
            return 20
        elif level == "reading" and node_id in ["reading", "content"]:
            return 20
        elif level == "kinesthetic" and node_id in ["code", "quiz"]:
            return 20
        return 5

    # 实践能力维度
    elif dim_key == "practice_ability":
        if level == "low" and node_id in ["content", "mindmap", "quiz"]:
            return 15
        elif level == "high" and node_id in ["code"]:
            return 20
        return 5

    # 交互偏好维度
    elif dim_key == "interaction_preference":
        if level == "guided" and node_id in ["content", "quiz"]:
            return 15
        elif level == "exploratory" and node_id in ["reading", "code", "mindmap"]:
            return 15
        return 5

    # 薄弱点维度
    elif dim_key == "weakness_points":
        if level == "concept" and node_id in ["content", "mindmap", "reading"]:
            return 20
        elif level == "practice" and node_id in ["code", "quiz"]:
            return 20
        elif level == "application" and node_id in ["code", "reading"]:
            return 15
        return 5

    return 0


def score_nodes(plan: PathPlan, *, weak_points: Iterable[str] | None = None) -> PathPlan:
    """对节点进行基础评分（向后兼容版本）。

    Args:
        plan: 当前路径计划。
        weak_points: 薄弱点节点列表。

    Returns:
        更新了节点优先级的 PathPlan 对象。
    """
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
            updated_nodes.append(node.model_copy(update={"priority": max(0, min(score, 100))}))
        updated_stages.append(stage.model_copy(update={"nodes": updated_nodes}))

    return plan.model_copy(update={"stages": updated_stages})


def compute_progress(
    plan: PathPlan,
    *,
    completed_node_ids: set[str],
    pace: str | None = None,
) -> PathPlan:
    """计算学习进度。

    Args:
        plan: 当前路径计划。
        completed_node_ids: 已完成节点 ID 集合。
        pace: 学习节奏偏好。

    Returns:
        更新了进度的 PathPlan 对象。
    """
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
    current_node_id: str | None = None
    for stage in stages:
        if stage.nodes and stage.status != "success":
            current_stage_id = stage.id
            current_node = next((node for node in stage.nodes if node.status != "success"), None)
            current_node_id = current_node.id if current_node else None
            break
    if current_stage_id is None and stages:
        current_stage_id = stages[-1].id
        current_node_id = stages[-1].nodes[-1].id if stages[-1].nodes else None

    if completed_nodes == 0:
        for index, stage in enumerate(stages):
            if stage.nodes:
                stages[index] = stage.model_copy(update={"status": "processing"})
                current_stage_id = stage.id
                current_node_id = stage.nodes[0].id
                break

    overall = int((completed_nodes / total_nodes) * 100) if total_nodes else 0
    eta_days = estimate_eta(remaining_count=max(total_nodes - completed_nodes, 0), pace=pace)
    progress = plan.progress.model_copy(
        update={
            "overall": overall,
            "current_stage_id": current_stage_id,
            "current_node_id": current_node_id,
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
    profile_dimensions: dict[str, dict] | None = None,
) -> PathPlan:
    """根据反馈和薄弱点调整学习路径。

    Args:
        plan: 当前路径计划。
        weak_points: 薄弱点节点列表。
        feedback: 用户反馈。
        now: 当前时间。
        profile_dimensions: 画像维度分析结果。

    Returns:
        调整后的 PathPlan 对象。
    """
    now = now or datetime.now()
    normalized_weak = [item for item in (weak_points or []) if item in ALL_NODE_IDS]
    if not normalized_weak and not (feedback and feedback.strip()):
        return plan

    # 使用画像维度进行智能评分，否则使用基础评分
    if profile_dimensions:
        adjusted = score_nodes_with_profile(plan, profile_dimensions=profile_dimensions, weak_points=normalized_weak)
    else:
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
    """推导下一步学习行动。

    Args:
        plan: 当前路径计划。

    Returns:
        下一步行动建议字符串。
    """
    for stage in plan.stages:
        if stage.id != plan.progress.current_stage_id:
            continue
        for node in stage.nodes:
            if node.status != "success":
                return f"优先完成「{node.title}」"
    return "继续保持，当前路径已完成"


def estimate_eta(*, remaining_count: int, pace: str | None) -> int:
    """估算剩余学习时间。

    Args:
        remaining_count: 剩余节点数量。
        pace: 学习节奏偏好。

    Returns:
        预估剩余天数。
    """
    normalized = (pace or "").lower()
    if any(keyword in normalized for keyword in ("fast", "快", "rapid", "high")):
        capacity = 2.0
    elif any(keyword in normalized for keyword in ("slow", "慢", "low")):
        capacity = 0.5
    else:
        capacity = 1.0
    return max(1, ceil(remaining_count / capacity))


# =============================================================================
# 智能推荐函数
# =============================================================================


def recommend_next_nodes(
    plan: PathPlan,
    *,
    top_n: int = 3,
    profile_dimensions: dict[str, dict] | None = None,
) -> list[dict]:
    """推荐下一步学习节点。

    Args:
        plan: 当前路径计划。
        top_n: 返回的推荐节点数量。
        profile_dimensions: 画像维度分析结果。

    Returns:
        推荐节点列表，每个元素包含 node_id、title、priority、reason。
    """
    candidates: list[dict] = []

    for stage in plan.stages:
        if stage.status == "success":
            continue
        for node in stage.nodes:
            if node.status == "success":
                continue

            reason = _generate_recommendation_reason(node, profile_dimensions)
            candidates.append({
                "node_id": node.id,
                "title": node.title,
                "priority": node.priority,
                "stage_id": stage.id,
                "reason": reason,
            })

    # 按优先级排序
    candidates.sort(key=lambda x: x["priority"], reverse=True)
    return candidates[:top_n]


def _generate_recommendation_reason(node: PathNode, profile_dimensions: dict[str, dict] | None) -> str:
    """生成推荐理由。

    Args:
        node: 节点对象。
        profile_dimensions: 画像维度分析结果。

    Returns:
        推荐理由字符串。
    """
    if not profile_dimensions:
        return f"根据学习路径规划，建议完成「{node.title}」"

    reasons: list[str] = []

    # 检查认知风格匹配
    cognitive_style = profile_dimensions.get("cognitive_style", {}).get("level", "")
    if cognitive_style == "visual" and node.id in ["mindmap", "diagram"]:
        reasons.append("符合您的视觉学习偏好")
    elif cognitive_style == "kinesthetic" and node.id in ["code", "quiz"]:
        reasons.append("适合动手实践的学习方式")

    # 检查学习目标匹配
    learning_goal = profile_dimensions.get("learning_goal", {}).get("level", "")
    if learning_goal == "exam" and node.id in ["quiz", "content"]:
        reasons.append("有助于备考")
    elif learning_goal == "project" and node.id in ["code", "reading"]:
        reasons.append("有助于项目实践")

    # 检查薄弱点
    weakness = profile_dimensions.get("weakness_points", {}).get("level", "")
    if weakness == "concept" and node.id in ["content", "mindmap"]:
        reasons.append("有助于巩固概念理解")
    elif weakness == "practice" and node.id in ["code", "quiz"]:
        reasons.append("有助于提升实践能力")

    if reasons:
        return f"推荐理由：{'；'.join(reasons)}"
    return f"根据学习路径规划，建议完成「{node.title}」"
