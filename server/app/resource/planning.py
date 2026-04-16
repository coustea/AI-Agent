from __future__ import annotations

from typing import Any

from app.infra.logging import get_logger
from app.resource.schemas import ResourcePlan

logger = get_logger(__name__)

CORE_AGENTS = ["content", "mindmap", "quiz"]
ENHANCEMENT_AGENTS = ["reading", "code", "image"]
PRESENTATION_AGENTS = ["ppt", "video"]

DEFAULT_DEPENDENCIES: dict[str, list[str]] = {
    "content": [],
    "mindmap": [],
    "quiz": [],
    "reading": [],
    "code": [],
    "image": ["content", "mindmap"],
    "ppt": ["content", "mindmap", "image"],
    "video": ["content", "image", "ppt"],
}


def build_default_resource_plan(
    task: dict[str, Any],
    allowed_agents: list[str] | None,
) -> ResourcePlan:
    selected = allowed_agents or (CORE_AGENTS + ENHANCEMENT_AGENTS + PRESENTATION_AGENTS)
    selected_set = set(selected)
    logger.info(
        "[Planning] 构建默认资源计划: course=%r selected_agents=%s",
        task.get("course", ""),
        selected,
    )

    def _params() -> dict[str, Any]:
        return {
            "topic": task.get("course", ""),
            "major": task.get("major", ""),
            "course": task.get("course", ""),
            "gap": task.get("gap", ""),
            "need": task.get("need", "review"),
            "extra": task.get("extra", ""),
        }

    return ResourcePlan(
        core_agents=[agent for agent in CORE_AGENTS if agent in selected_set],
        enhancement_agents=[agent for agent in ENHANCEMENT_AGENTS if agent in selected_set],
        presentation_agents=[agent for agent in PRESENTATION_AGENTS if agent in selected_set],
        dependencies={
            agent: [dep for dep in DEFAULT_DEPENDENCIES.get(agent, []) if dep in selected_set]
            for agent in selected
        },
        agent_parameters={agent: _params() for agent in selected},
    )


def merge_planned_tasks_into_plan(
    plan: ResourcePlan,
    tasks: list[dict[str, Any]],
) -> ResourcePlan:
    for task in tasks:
        agent = task.get("agent")
        if agent not in plan.agent_parameters:
            logger.warning("[Planning] 跳过未注册的 Planner 任务: agent=%r", agent)
            continue
        parameters = task.get("parameters") or {}
        # 这里先保留默认参数，再用 planner 输出覆盖，避免 planner 漏字段时把执行链打断。
        merged = {**plan.agent_parameters[agent], **parameters}
        plan.agent_parameters[agent] = merged
        logger.info("[Planning] 已合并 Planner 参数: agent=%s keys=%s", agent, list(parameters.keys()))
    return plan


def iter_plan_phases(plan: ResourcePlan) -> list[tuple[str, str, list[str]]]:
    # video 单独拆到最后一段，确保它依赖的 PPT 和图解已经稳定产出。
    presentation_agents = [agent for agent in plan.presentation_agents if agent != "video"]
    video_agents = [agent for agent in plan.presentation_agents if agent == "video"]
    phases = [
        ("core_generating", "核心资源生成", plan.core_agents),
        ("enhancement_generating", "增强资源补充", plan.enhancement_agents),
        ("presentation_generating", "演示资源生成", presentation_agents),
        ("video_generating", "视频资源生成", video_agents),
    ]
    logger.info("[Planning] 阶段划分完成: %s", phases)
    return phases
