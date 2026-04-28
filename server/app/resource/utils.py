"""
资源生成模块工具函数集合。

整合了 prompt 加载、画像格式化、依赖展开、Agent 注册表等通用工具。
"""

from __future__ import annotations

import importlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from app.infra.logging import get_logger
from app.resource.schemas import ResourcePlan
from app.shared.paths import WORKPLACE_DIR, RESOURCE_DIR

logger = get_logger(__name__)

# =============================================================================
# Agent 配置常量
# =============================================================================

CORE_AGENTS = ["content", "mindmap", "quiz"]
ENHANCEMENT_AGENTS = ["reading", "code"]
PRESENTATION_AGENTS = ["ppt"]
ALL_AGENTS = CORE_AGENTS + ENHANCEMENT_AGENTS + PRESENTATION_AGENTS

DEFAULT_DEPENDENCIES: dict[str, list[str]] = {
    "content": [],
    "mindmap": [],
    "quiz": ["content"],
    "reading": ["content"],
    "code": ["mindmap", "content"],
    "ppt": ["content", "mindmap"],
}

DEFAULT_EXECUTION_LAYER: dict[str, int] = {
    "content": 0,
    "mindmap": 0,
    "quiz": 1,
    "reading": 1,
    "code": 1,
    "ppt": 2,
}

DEFAULT_FAILURE_POLICY: dict[str, str] = {
    "content": "independent_fail",
    "mindmap": "independent_fail",
    "quiz": "degraded_run",
    "reading": "degraded_run",
    "code": "degraded_run",
    "ppt": "skip_on_dependency_failed",
}

FAILURE_POLICIES = {"independent_fail", "degraded_run", "skip_on_dependency_failed"}


# =============================================================================
# Prompt 加载与上下文构建
# =============================================================================

def load_prompt(agent_dir: Path) -> str:
    """加载 Agent 的 prompt.md 文件。"""
    prompt_path = agent_dir / "prompt.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"prompt 文件不存在: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def format_profile_fields(profile: dict[str, Any], fields: list[tuple[str, str]]) -> str:
    """格式化画像字段为 Markdown 列表。"""
    if not profile:
        return ""
    parts: list[str] = []
    for key, label in fields:
        value = profile.get(key)
        if value:
            parts.append(f"- {label}: {value}")
    return "\n".join(parts)


def parse_markdown_sections(markdown_text: str | None) -> dict[str, str]:
    """按二级标题解析 Markdown 文本。"""
    sections: dict[str, str] = {}
    if not markdown_text:
        return sections

    current_section: str | None = None
    current_content: list[str] = []
    for raw_line in markdown_text.split("\n"):
        heading = re.match(r"^##\s+(.+?)\s*$", raw_line)
        if heading:
            if current_section is not None:
                sections[current_section] = "\n".join(current_content).strip()
            current_section = heading.group(1).strip()
            current_content = []
            continue
        if current_section is not None:
            current_content.append(raw_line)
    if current_section is not None:
        sections[current_section] = "\n".join(current_content).strip()
    return sections


def append_context(
    system_prompt: str,
    *,
    state: dict[str, Any],
    format_user_profile: Callable[[dict[str, Any]], str] | None = None,
    extract_memory: Callable[[dict[str, Any]], str] | None = None,
) -> str:
    """追加用户画像、协作上下文、知识库参考到系统提示。"""
    profile = state.get("user_profile", {}) or {}
    if format_user_profile:
        profile_str = format_user_profile(profile)
        if profile_str:
            system_prompt += f"\n\n## [学习者画像]\n{profile_str}"

    shared_memory = state.get("shared_memory", {}) or {}
    if extract_memory:
        memory_ctx = extract_memory(shared_memory)
        if memory_ctx:
            system_prompt += f"\n\n## [协作上下文]\n{memory_ctx}"

    kb_context = state.get("knowledge_base_context", "")
    if kb_context:
        system_prompt += f"\n\n## [知识库参考]\n{kb_context}"
    return system_prompt


# =============================================================================
# 文件保存与工具加载
# =============================================================================

def save_resource_file(
    topic: str,
    content: str,
    user_id: int,
    resource_id: int,
    ext: str = "md",
    prefix: str | None = None,
) -> str:
    """保存资源文件到统一路径: workplace/resource/{user_id}/{resource_id}/{topic}.{ext}

    Args:
        topic: 主题名称（用于生成文件名）
        content: 文件内容
        user_id: 用户 ID
        resource_id: 资源 ID
        ext: 文件扩展名
        prefix: 可选文件名前缀，用于隔离不同 Agent 的产物

    Returns:
        文件路径
    """
    safe_topic = re.sub(r'[\\/*?:"<>|]', "", topic).strip()[:50]
    if not safe_topic:
        safe_topic = "untitled"

    target_dir = RESOURCE_DIR / str(user_id) / str(resource_id)
    target_dir.mkdir(parents=True, exist_ok=True)

    safe_prefix = re.sub(r'[\\/*?:"<>|]', "", prefix or "").strip()
    filename = f"{safe_prefix}_{safe_topic}.{ext}" if safe_prefix else f"{safe_topic}.{ext}"
    filepath = target_dir / filename

    filepath.write_text(content, encoding="utf-8")
    return str(filepath)


def save_to_workplace(sub_dir: str, topic: str, content: str, ext: str = "md") -> str:
    """保存内容到 workplace 目录，返回文件路径。

    已废弃：请使用 save_resource_file 统一保存到 workplace/{user_id}/{resource_id}/
    """
    from app.tools.registry import get as get_tool

    return get_tool("save_to_workplace").invoke(
        {"sub_dir": sub_dir, "topic": topic, "content": content, "ext": ext}
    )


def load_registered_tools(tool_names: list[str]) -> list[Any]:
    """从工具注册表加载指定工具。"""
    from app.tools import registry

    registry.ensure_loaded()
    return registry.get_many(tool_names)


# =============================================================================
# Agent 注册表
# =============================================================================

@dataclass
class AgentEntry:
    """Agent 注册条目。"""
    role: str
    desc: str
    type: str
    stage: str
    agent_loader: Callable[[], Any]
    method: str
    result_summary: Callable[[dict], str] = field(default=lambda r: "")
    extra_kwargs: dict = field(default_factory=dict)


def _load_agent(module_path: str, attr_name: str) -> Callable[[], Any]:
    """创建 Agent 懒加载函数。"""
    def _loader() -> Any:
        module = importlib.import_module(module_path)
        return getattr(module, attr_name)
    return _loader


def build_agent_registry() -> dict[str, AgentEntry]:
    """构建 Agent 注册表。"""
    return {
        "content": AgentEntry(
            role="Content Agent",
            desc="撰写深度知识精讲",
            type="doc",
            stage="core",
            agent_loader=_load_agent("app.resource.agents.content", "content_writer"),
            method="generate_content",
            result_summary=lambda r: f"文档 {len(r.get('content', ''))} 字",
        ),
        "mindmap": AgentEntry(
            role="Mindmap Agent",
            desc="构建核心知识拓扑图",
            type="mindmap",
            stage="core",
            agent_loader=_load_agent("app.resource.agents.mindmap", "mindmap_generator"),
            method="generate_mindmap",
            result_summary=lambda r: f"导图已生成 → {r.get('file_path') or '内存结果'}",
        ),
        "quiz": AgentEntry(
            role="Quiz Agent",
            desc="生成分层练习题库",
            type="quiz",
            stage="core",
            agent_loader=_load_agent("app.resource.agents.quiz", "quiz_agent"),
            method="generate_quiz",
            result_summary=lambda r: f"共 {len(r.get('questions', []))} 道题",
        ),
        "reading": AgentEntry(
            role="Reading Agent",
            desc="检索拓展阅读与论文",
            type="reading",
            stage="enhancement",
            agent_loader=_load_agent("app.resource.agents.reading", "reading_agent"),
            method="generate_reading",
            result_summary=lambda r: f"共 {len(r.get('recommendations', []))} 条推荐",
        ),
        "code": AgentEntry(
            role="Code Agent",
            desc="编写可运行实操案例",
            type="code",
            stage="enhancement",
            agent_loader=_load_agent("app.resource.agents.code", "code_agent"),
            method="generate_code",
            result_summary=lambda r: f"语言: {r.get('detected_language', 'unknown')}",
        ),
        "ppt": AgentEntry(
            role="PPT Agent",
            desc="生成演示文稿与讲稿",
            type="ppt",
            stage="presentation",
            agent_loader=_load_agent("app.resource.agents.ppt", "ppt_agent"),
            method="generate_ppt",
            result_summary=lambda r: "PPT 大纲已生成",
        ),
    }


AGENT_REGISTRY: dict[str, AgentEntry] | None = None


def get_agent_registry() -> dict[str, AgentEntry]:
    """获取 Agent 注册表单例。"""
    global AGENT_REGISTRY
    if AGENT_REGISTRY is None:
        AGENT_REGISTRY = build_agent_registry()
    return AGENT_REGISTRY


# =============================================================================
# 资源计划构建
# =============================================================================

def expand_dependencies(selected: list[str], dependency_map: dict[str, list[str]]) -> list[str]:
    """展开资源依赖闭包，并按系统固定顺序输出。

    说明：
    - 输入是用户显式选择的资源（可能是部分资源）
    - 输出是"执行集合"：包含 selected 本身 + 所有递归依赖
    - 顺序按半动态编排既有顺序（core -> enhancement -> presentation）
    """
    if not selected:
        return []

    closure: set[str] = set()
    stack = list(selected)
    while stack:
        current = stack.pop()
        if current in closure:
            continue
        closure.add(current)
        stack.extend(dependency_map.get(current, []))

    ordered = [agent for agent in ALL_AGENTS if agent in closure]
    # 兼容未来扩展：如果出现未登记到 ALL_AGENTS 的 agent，保持原输入次序追加到末尾。
    for agent in selected:
        if agent in closure and agent not in ordered:
            ordered.append(agent)
    return ordered


def build_execution_groups(
    execution_agents: list[str],
    dependencies: dict[str, list[str]],
) -> list[list[str]]:
    """Build dependency-ordered parallel execution groups."""
    execution_set = set(execution_agents)
    remaining = list(execution_agents)
    completed: set[str] = set()
    groups: list[list[str]] = []

    while remaining:
        ready = [
            agent
            for agent in remaining
            if all(dep in completed or dep not in execution_set for dep in dependencies.get(agent, []))
        ]
        if not ready:
            logger.warning("[Planning] 依赖图存在环或缺口，剩余 Agent 将作为降级组执行: %s", remaining)
            ready = list(remaining)
        min_layer = min(DEFAULT_EXECUTION_LAYER.get(agent, 99) for agent in ready)
        group = [agent for agent in ready if DEFAULT_EXECUTION_LAYER.get(agent, 99) == min_layer]
        groups.append(group)
        completed.update(group)
        remaining = [agent for agent in remaining if agent not in set(group)]

    return groups


def execution_groups_follow_dependencies(
    groups: list[list[str]],
    dependencies: dict[str, list[str]],
) -> bool:
    """Return whether every dependency appears in an earlier group."""
    group_index: dict[str, int] = {}
    for index, group in enumerate(groups):
        for agent in group:
            group_index[agent] = index

    for agent, deps in dependencies.items():
        if agent not in group_index:
            return False
        for dep in deps:
            if dep in group_index and group_index[dep] >= group_index[agent]:
                return False
    return True


def build_default_resource_plan(
    task: dict[str, Any],
    allowed_agents: list[str] | None,
) -> ResourcePlan:
    """构建默认资源计划。"""
    if allowed_agents:
        requested_agents = [agent for agent in ALL_AGENTS if agent in set(allowed_agents)]
        execution_agents = expand_dependencies(requested_agents, DEFAULT_DEPENDENCIES)
        visible_agents = list(requested_agents)
        hidden_dependency_agents = [agent for agent in execution_agents if agent not in set(visible_agents)]
    else:
        requested_agents = list(ALL_AGENTS)
        execution_agents = list(ALL_AGENTS)
        visible_agents = list(ALL_AGENTS)
        hidden_dependency_agents = []

    execution_set = set(execution_agents)
    logger.info(
        "[Planning] 构建默认资源计划: course=%r requested=%s execution=%s visible=%s hidden=%s",
        task.get("course", ""),
        requested_agents,
        execution_agents,
        visible_agents,
        hidden_dependency_agents,
    )

    def _params() -> dict[str, Any]:
        return {
            "topic": task.get("course", ""),
            "major": task.get("major", ""),
            "course": task.get("course", ""),
            "gap": task.get("gap", ""),
            "need": task.get("need", "review"),
            "extra": task.get("extra", ""),
            "template_id": task.get("template_id", "python_ppt_template"),
            "template_source_url": task.get("template_source_url") or "",
            "template_config_url": task.get("template_config_url") or "",
        }

    dependencies = {
        agent: [dep for dep in DEFAULT_DEPENDENCIES.get(agent, []) if dep in execution_set]
        for agent in execution_agents
    }
    execution_groups = build_execution_groups(execution_agents, dependencies)

    return ResourcePlan(
        execution_groups=execution_groups,
        failure_policy={
            agent: DEFAULT_FAILURE_POLICY.get(agent, "independent_fail")
            for agent in execution_agents
        },
        core_agents=[agent for agent in CORE_AGENTS if agent in execution_set],
        enhancement_agents=[agent for agent in ENHANCEMENT_AGENTS if agent in execution_set],
        presentation_agents=[agent for agent in PRESENTATION_AGENTS if agent in execution_set],
        requested_agents=requested_agents,
        execution_agents=execution_agents,
        visible_agents=visible_agents,
        hidden_dependency_agents=hidden_dependency_agents,
        dependencies=dependencies,
        agent_parameters={agent: _params() for agent in execution_agents},
    )


def normalize_resource_plan(
    plan: ResourcePlan,
    allowed_agents: list[str] | None = None,
) -> ResourcePlan:
    """Normalize planner output into a safe executable plan."""
    registry = get_agent_registry()
    allowed_set = set(allowed_agents or ALL_AGENTS)

    visible_agents: list[str] = []
    for agent in plan.visible_agents or plan.requested_agents or []:
        if agent in registry and agent in allowed_set and agent not in visible_agents:
            visible_agents.append(agent)
    if not visible_agents:
        visible_agents = [agent for agent in ALL_AGENTS if agent in allowed_set]

    execution_seed = plan.execution_agents or visible_agents
    execution_agents = expand_dependencies(
        [agent for agent in execution_seed if agent in registry and agent in allowed_set],
        DEFAULT_DEPENDENCIES,
    )
    if not execution_agents:
        execution_agents = expand_dependencies(visible_agents, DEFAULT_DEPENDENCIES)

    execution_set = set(execution_agents)
    visible_agents = [agent for agent in visible_agents if agent in execution_set]
    hidden_dependency_agents = [agent for agent in execution_agents if agent not in set(visible_agents)]

    dependencies: dict[str, list[str]] = {}
    for agent in execution_agents:
        raw_deps = plan.dependencies.get(agent, DEFAULT_DEPENDENCIES.get(agent, []))
        dependencies[agent] = [
            dep
            for dep in raw_deps
            if dep in execution_set and dep != agent
        ]

    groups: list[list[str]] = []
    seen: set[str] = set()
    for raw_group in plan.execution_groups:
        group = [
            agent
            for agent in raw_group
            if agent in execution_set and agent not in seen
        ]
        if group:
            groups.append(group)
            seen.update(group)
    missing_agents = [agent for agent in execution_agents if agent not in seen]
    if missing_agents:
        generated_groups = build_execution_groups(missing_agents, dependencies)
        groups.extend(generated_groups)
    if not groups:
        groups = build_execution_groups(execution_agents, dependencies)
    elif not execution_groups_follow_dependencies(groups, dependencies):
        logger.warning("[Planning] Planner 执行组不满足依赖顺序，将按依赖重建: %s", groups)
        groups = build_execution_groups(execution_agents, dependencies)

    failure_policy = {}
    for agent in execution_agents:
        policy = plan.failure_policy.get(agent) or DEFAULT_FAILURE_POLICY.get(agent, "independent_fail")
        if policy not in FAILURE_POLICIES:
            policy = DEFAULT_FAILURE_POLICY.get(agent, "independent_fail")
        failure_policy[agent] = policy

    return ResourcePlan(
        execution_groups=groups,
        failure_policy=failure_policy,
        core_agents=[agent for agent in CORE_AGENTS if agent in execution_set],
        enhancement_agents=[agent for agent in ENHANCEMENT_AGENTS if agent in execution_set],
        presentation_agents=[agent for agent in PRESENTATION_AGENTS if agent in execution_set],
        requested_agents=visible_agents,
        execution_agents=execution_agents,
        visible_agents=visible_agents,
        hidden_dependency_agents=hidden_dependency_agents,
        dependencies=dependencies,
        agent_parameters={
            agent: plan.agent_parameters.get(agent, {})
            for agent in execution_agents
        },
    )


def merge_planned_tasks_into_plan(
    plan: ResourcePlan,
    tasks: list[dict[str, Any]],
) -> ResourcePlan:
    """将旧版 Planner 任务合并到资源计划。"""
    for task in tasks:
        agent = task.get("agent")
        if agent not in plan.agent_parameters:
            logger.warning("[Planning] 跳过未注册的 Planner 任务: agent=%r", agent)
            continue
        parameters = task.get("parameters") or {}
        # 先保留默认参数，再用 planner 输出覆盖
        merged = {**plan.agent_parameters[agent], **parameters}
        plan.agent_parameters[agent] = merged
        logger.info("[Planning] 已合并 Planner 参数: agent=%s keys=%s", agent, list(parameters.keys()))
    return normalize_resource_plan(plan, plan.execution_agents)


def merge_planner_plan_into_default(
    default_plan: ResourcePlan,
    planner_plan: ResourcePlan,
) -> ResourcePlan:
    """Merge explicit planner output with deterministic defaults."""
    allowed = default_plan.execution_agents
    normalized = normalize_resource_plan(planner_plan, allowed)
    merged_parameters = {
        agent: {
            **default_plan.agent_parameters.get(agent, {}),
            **normalized.agent_parameters.get(agent, {}),
        }
        for agent in normalized.execution_agents
    }
    normalized.agent_parameters = merged_parameters
    normalized.requested_agents = [
        agent for agent in normalized.visible_agents if agent in default_plan.visible_agents
    ] or list(default_plan.visible_agents)
    normalized.visible_agents = list(normalized.requested_agents)
    normalized.hidden_dependency_agents = [
        agent for agent in normalized.execution_agents if agent not in set(normalized.visible_agents)
    ]
    return normalize_resource_plan(normalized, allowed)


def iter_plan_phases(plan: ResourcePlan) -> list[tuple[str, str, list[str]]]:
    """按阶段迭代资源计划。"""
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


# =============================================================================
# 协调器辅助函数
# =============================================================================

def normalize_selected_resources(selected_resources: list[str] | None) -> list[str] | None:
    """归一化用户选择的资源列表。"""
    if not selected_resources:
        return None

    normalized: list[str] = []
    seen: set[str] = set()
    registry = get_agent_registry()
    default_order = list(registry.keys())
    order_index = {name: idx for idx, name in enumerate(default_order)}

    for raw_name in selected_resources:
        name = str(raw_name).strip().lower()
        if not name or name not in registry or name in seen:
            continue
        normalized.append(name)
        seen.add(name)

    if not normalized:
        return None

    normalized.sort(key=lambda name: order_index[name])
    return normalized


def filter_tasks_by_selection(
    tasks: list[dict],
    allowed_agents: list[str] | None,
) -> list[dict]:
    """按选择的 Agent 过滤任务。"""
    if allowed_agents is None:
        return tasks
    allowed_set = set(allowed_agents)
    return [task for task in tasks if task.get("agent") in allowed_set]


def merge_extra(existing_extra: str, personalized_context) -> str:
    """合并额外参数与个性化上下文。"""
    additions = []
    if personalized_context.target_difficulty:
        additions.append(f"推荐难度：{personalized_context.target_difficulty}")
    if personalized_context.explanation_style:
        additions.append(f"讲解风格：{'；'.join(personalized_context.explanation_style)}")
    if personalized_context.emphasis:
        additions.append(f"强调事项：{'；'.join(personalized_context.emphasis)}")
    parts = [part for part in [existing_extra, " | ".join(additions)] if part]
    return "\n".join(parts)


def core_ready(plan: ResourcePlan, results: dict[str, dict]) -> bool:
    """检查核心 Agent 是否全部完成。"""
    for agent_name in plan.core_agents:
        if not results.get(agent_name, {}).get("success"):
            return False
    return True


# =============================================================================
# 画像加载
# =============================================================================

_memory_layer = None


def _get_memory_layer():
    """获取 MemoryLayer 单例。"""
    global _memory_layer
    if _memory_layer is None:
        from app.memory import MemoryLayer
        _memory_layer = MemoryLayer(module_name="mentor")
    return _memory_layer


async def load_user_profile(user_id: int) -> dict:
    """加载用户基础信息和画像。

    Returns:
        包含 user_data 和 profile_data 的字典，用于构建 LearnerProfileSnapshot。
    """
    from sqlmodel.ext.asyncio.session import AsyncSession
    from app.infra.database import engine
    from app.infra.models import User

    # 加载用户基础信息
    user_data = {"user_id": user_id}
    async with AsyncSession(engine) as session:
        user = await session.get(User, user_id)
        if user:
            user_data = {
                "user_id": user.id,
                "username": user.username,
                "major": user.major,
                "grade": user.grade,
                "school": user.school,
            }
            logger.info("[Profile] 已读取用户基础信息: user_id=%s", user_id)

    # 加载画像
    profile_data = {}
    profile = await _get_memory_layer().get_profile(user_id=user_id)
    if profile:
        profile_data = profile.model_dump(exclude_none=True)
        updated_at = profile_data.get("updated_at")
        if updated_at is not None:
            profile_data["updated_at"] = updated_at.isoformat()
        logger.info("[Profile] 已读取用户画像: user_id=%s fields=%s", user_id, list(profile_data.keys()))

    return {"user_data": user_data, "profile_data": profile_data}


async def load_profile_snapshot(user_id: int):
    """加载用户画像快照。"""
    from app.resource.schemas import LearnerProfileSnapshot

    data = await load_user_profile(user_id)
    return LearnerProfileSnapshot.from_sources(**data)


def _parse_profile_markdown(profile_markdown: str | None) -> dict[str, str]:
    """从画像 Markdown 中提取关键信息。

    参数：
    - profile_markdown: 画像 Markdown 文本

    返回：
    - 包含 knowledge_level、learning_goal、learning_pace、weakness、interest 等字段的字典
    """
    result: dict[str, str] = {}
    if not profile_markdown:
        return result

    sections = parse_markdown_sections(profile_markdown)
    result = {
        "技术能力判断": sections.get("技术能力判断", ""),
        "当前学习/项目背景": sections.get("当前学习/项目背景", ""),
        "学习偏好": sections.get("学习偏好", ""),
        "当前薄弱点": sections.get("当前薄弱点", ""),
        "兴趣方向": sections.get("兴趣方向", ""),
        "推荐辅导策略": sections.get("推荐辅导策略", ""),
    }
    return result


def build_personalized_context(snapshot, task: dict):
    """构建个性化任务上下文。"""
    from app.resource.schemas import PersonalizedTaskContext

    need = task.get("need", "review")
    difficulty = "intermediate"

    # 从 profile_markdown 解析信息
    profile_info = _parse_profile_markdown(snapshot.profile_markdown)
    technical_ability = profile_info.get("技术能力判断", "")

    # 根据知识水平文本判断难度
    if "初级" in technical_ability or "入门" in technical_ability or "基础" in technical_ability:
        difficulty = "basic"
    elif "高级" in technical_ability or "精通" in technical_ability or "专家" in technical_ability:
        difficulty = "advanced"

    explanation_style: list[str] = []
    learning_preference = profile_info.get("学习偏好", "")
    if learning_preference:
        explanation_style.append(learning_preference)
    if need == "exam":
        explanation_style.append("考点优先，短时高频强化")
    elif need == "deep":
        explanation_style.append("强调原理推导与工程细节")
    else:
        explanation_style.append("先图解梳理，再精讲与练习")

    emphasis: list[str] = []
    weakness = profile_info.get("当前薄弱点", "")
    if weakness:
        emphasis.append(f"重点纠偏：{weakness}")
    interest = profile_info.get("兴趣方向", "")
    if interest:
        emphasis.append(f"案例偏好：{interest}")
    if task.get("extra"):
        emphasis.append(f"本次额外要求：{task['extra']}")

    return PersonalizedTaskContext(
        course=task.get("course", ""),
        gap=task.get("gap", ""),
        need=need,
        extra=task.get("extra", ""),
        target_difficulty=difficulty,
        explanation_style=explanation_style,
        emphasis=emphasis,
        recommended_order=["content", "mindmap", "quiz", "reading", "code", "image", "ppt", "video"],
        profile_markdown=snapshot.profile_markdown,
    )
