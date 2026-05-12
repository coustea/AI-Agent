"""Path planning module.

提供基于用户画像的个性化学习路径规划功能。
"""

from app.path.planner import (
    ALL_NODE_IDS,
    NODE_TITLES,
    build_initial_plan,
    build_resource_study_plan,
    compute_progress,
    adjust_plan,
    analyze_profile_dimensions,
    infer_resource_weak_points,
    recommend_next_nodes,
    derive_next_action,
)
from app.path.profile_recommender import (
    compute_node_scores,
    compute_learning_pace,
    estimate_completion_time,
    recommend_nodes,
    suggest_path_adjustment,
)
from app.path.schemas import (
    PathNode,
    PathStage,
    PathPlan,
    PathProgress,
    PathPlanData,
    PathSummary,
    PathInsight,
    Adjustment,
)
from app.path.service import PathService, PathUseCases, path_usecases

__all__ = [
    # Planner
    "ALL_NODE_IDS",
    "NODE_TITLES",
    "build_initial_plan",
    "build_resource_study_plan",
    "compute_progress",
    "adjust_plan",
    "analyze_profile_dimensions",
    "infer_resource_weak_points",
    "recommend_next_nodes",
    "derive_next_action",
    # Profile Recommender
    "compute_node_scores",
    "compute_learning_pace",
    "estimate_completion_time",
    "recommend_nodes",
    "suggest_path_adjustment",
    # Schemas
    "PathNode",
    "PathStage",
    "PathPlan",
    "PathProgress",
    "PathPlanData",
    "PathSummary",
    "PathInsight",
    "Adjustment",
    # Service
    "PathService",
    "PathUseCases",
    "path_usecases",
]
