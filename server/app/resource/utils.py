"""
资源生成模块工具函数集合。

整合了 prompt 加载、画像格式化、依赖展开、Agent 注册表等通用工具。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.infra.logging import get_logger
from app.resource.registry import get_agent_registry
from app.resource.schemas import ResourcePlan
from app.shared.paths import WORKPLACE_DIR, RESOURCE_DIR

logger = get_logger(__name__)

# =============================================================================
# Agent 配置常量
# =============================================================================

CORE_AGENTS = ["content", "mindmap", "quiz"]
ENHANCEMENT_AGENTS = ["reading", "code"]
PRESENTATION_AGENTS: list[str] = ["ppt"]
ALL_AGENTS = CORE_AGENTS + ENHANCEMENT_AGENTS + PRESENTATION_AGENTS

DEFAULT_DEPENDENCIES: dict[str, list[str]] = {
    "content": [],
    "mindmap": [],
    "quiz": ["content"],
    "reading": ["content"],
    "code": ["mindmap", "content"],
    "ppt": ["content"],
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
    "ppt": "degraded_run",
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
    safe_topic = re.sub(r'[\\/*?:"<>|]', "", topic).strip()[:50]
    if not safe_topic:
        safe_topic = "untitled"

    target_dir = WORKPLACE_DIR / sub_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    safe_filename = f"{safe_topic}.{ext}"
    filepath = target_dir / safe_filename
    filepath.write_text(content, encoding="utf-8")
    return str(filepath)


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
    phases = [
        ("core_generating", "核心资源生成", plan.core_agents),
        ("enhancement_generating", "增强资源补充", plan.enhancement_agents),
        ("presentation_generating", "演示资源生成", plan.presentation_agents),
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
        recommended_order=["content", "mindmap", "quiz", "reading", "code"],
        profile_markdown=snapshot.profile_markdown,
    )


# =============================================================================
# Markdown 转 HTML
# =============================================================================

def markdown_to_mindmap_html(markdown: str, title: str = "知识思维导图") -> str:
    """将 Markdown 列表转换为交互式思维导图 HTML。

    Args:
        markdown: Markdown 格式的思维导图内容
        title: HTML 页面标题

    Returns:
        完整的 HTML 字符串
    """
    html_lines = _convert_markdown_lists_to_html(markdown)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            margin: 0;
        }}
        .mindmap-container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        .mindmap-title {{
            text-align: center;
            font-size: 28px;
            color: #333;
            margin-bottom: 30px;
            font-weight: 600;
        }}
        .mindmap-tree ul {{
            list-style: none;
            padding-left: 25px;
            margin: 10px 0;
        }}
        .mindmap-tree li {{
            position: relative;
            padding: 8px 0 8px 20px;
            margin: 5px 0;
            border-left: 2px solid #667eea;
        }}
        .mindmap-tree li::before {{
            content: '';
            position: absolute;
            left: -2px;
            top: 50%;
            width: 20px;
            height: 2px;
            background: #667eea;
        }}
        .mindmap-tree li:last-child {{
            border-left-color: transparent;
        }}
        .mindmap-tree > ul {{
            padding-left: 0;
        }}
        .mindmap-tree > ul > li {{
            border-left: none;
            padding-left: 0;
        }}
        .mindmap-tree > ul > li::before {{
            display: none;
        }}
        .node {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 500;
        }}
        .node.level-0 {{
            font-size: 18px;
            padding: 10px 20px;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }}
        .node.level-1 {{
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        }}
        .node.level-2 {{
            background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        }}
        .node.level-3 {{
            background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        }}
    </style>
</head>
<body>
    <div class="mindmap-container">
        <h1 class="mindmap-title">{title}</h1>
        <div class="mindmap-tree">
{html_lines}
        </div>
    </div>
</body>
</html>"""


def _convert_markdown_lists_to_html(markdown: str) -> str:
    """将 Markdown 列表转换为 HTML 树形结构。"""
    lines = markdown.strip().split("\n")
    html_parts: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # 计算缩进级别
        indent = len(line) - len(line.lstrip())
        level = indent // 2 if indent > 0 else 0

        # 移除列表标记
        if stripped.startswith("- ") or stripped.startswith("* "):
            content = stripped[2:]
        elif stripped.startswith("# "):
            content = stripped[2:]
            level = 0
        elif stripped.startswith("## "):
            content = stripped[3:]
            level = 1
        elif stripped.startswith("### "):
            content = stripped[4:]
            level = 2
        else:
            content = stripped

        # 生成节点
        node_class = f"level-{min(level, 3)}"
        html_parts.append(f'            <li><span class="node {node_class}">{content}</span></li>')

    # 包装成 ul 结构
    if html_parts:
        return "            <ul>\n" + "\n".join(html_parts) + "\n            </ul>"
    return ""


# =============================================================================
# Workspace 文件产物系统
# =============================================================================

import json
from datetime import datetime, timezone

import aiofiles

MAX_FILE_SIZE = 1024 * 1024  # 1MB

# manifest 缓存（简单实现，避免频繁读取文件）
_manifest_cache: dict[str, dict[str, Any]] = {}


def _get_workspace_dir(user_id: int, resource_id: int) -> Path:
    """获取 workspace 目录路径。"""
    return RESOURCE_DIR / str(user_id) / str(resource_id)


async def init_workspace(user_id: int, resource_id: int) -> Path:
    """初始化 workspace，创建目录结构和 manifest.json。

    Args:
        user_id: 用户 ID
        resource_id: 资源 ID

    Returns:
        workspace 目录路径
    """
    workspace_dir = _get_workspace_dir(user_id, resource_id)
    workspace_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = workspace_dir / "manifest.json"
    if not manifest_path.exists():
        initial_manifest = {
            "user_id": user_id,
            "resource_id": resource_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "initialized",
            "agents": {},
        }
        content = json.dumps(initial_manifest, ensure_ascii=False, indent=2)
        await write_file_atomic(manifest_path, content, workspace_dir)
        _manifest_cache[f"{user_id}_{resource_id}"] = initial_manifest
        logger.info("[Workspace] 初始化完成: %s", workspace_dir)

    return workspace_dir


async def read_manifest(user_id: int, resource_id: int) -> dict[str, Any]:
    """读取 manifest.json。

    Args:
        user_id: 用户 ID
        resource_id: 资源 ID

    Returns:
        manifest 字典
    """
    cache_key = f"{user_id}_{resource_id}"
    if cache_key in _manifest_cache:
        return _manifest_cache[cache_key]

    workspace_dir = _get_workspace_dir(user_id, resource_id)
    manifest_path = workspace_dir / "manifest.json"
    content = await read_file_safe(manifest_path, workspace_dir)
    if content is None:
        return {}

    manifest = json.loads(content)
    _manifest_cache[cache_key] = manifest
    return manifest


async def update_manifest(user_id: int, resource_id: int, updates: dict[str, Any]) -> None:
    """更新 manifest.json。

    Args:
        user_id: 用户 ID
        resource_id: 资源 ID
        updates: 要更新的字段
    """
    manifest = await read_manifest(user_id, resource_id)
    manifest.update(updates)
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()

    workspace_dir = _get_workspace_dir(user_id, resource_id)
    manifest_path = workspace_dir / "manifest.json"
    content = json.dumps(manifest, ensure_ascii=False, indent=2)
    await write_file_atomic(manifest_path, content, workspace_dir)

    cache_key = f"{user_id}_{resource_id}"
    _manifest_cache[cache_key] = manifest
    logger.debug("[Workspace] Manifest 已更新: %s", list(updates.keys()))


async def update_agent_status(
    user_id: int,
    resource_id: int,
    agent_name: str,
    status: str,
    artifact_path: str | None = None,
    error: str | None = None,
) -> None:
    """更新 Agent 执行状态。

    Args:
        user_id: 用户 ID
        resource_id: 资源 ID
        agent_name: Agent 名称
        status: 状态
        artifact_path: 产物路径
        error: 错误信息
    """
    manifest = await read_manifest(user_id, resource_id)
    agents = manifest.get("agents", {})

    if agent_name not in agents:
        agents[agent_name] = {
            "status": status,
            "dependencies": [],
            "artifact_path": artifact_path,
            "error": error,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
    else:
        agents[agent_name]["status"] = status
        if artifact_path:
            agents[agent_name]["artifact_path"] = artifact_path
        if error:
            agents[agent_name]["error"] = error
        if status in ("completed", "failed", "skipped"):
            agents[agent_name]["completed_at"] = datetime.now(timezone.utc).isoformat()

    await update_manifest(user_id, resource_id, {"agents": agents})


async def write_agent_artifact(
    user_id: int,
    resource_id: int,
    agent_name: str,
    content: str,
    file_type: str = "md",
) -> str:
    """写入 Agent 产物。

    Args:
        user_id: 用户 ID
        resource_id: 资源 ID
        agent_name: Agent 名称
        content: 产物内容
        file_type: 文件类型

    Returns:
        产物文件路径
    """
    workspace_dir = _get_workspace_dir(user_id, resource_id)
    artifact_path = workspace_dir / f"{agent_name}.{file_type}"
    return await write_file_atomic(artifact_path, content, workspace_dir)


async def read_agent_artifact(
    user_id: int,
    resource_id: int,
    agent_name: str,
    file_type: str = "md",
) -> str | None:
    """读取 Agent 产物。

    Args:
        user_id: 用户 ID
        resource_id: 资源 ID
        agent_name: Agent 名称
        file_type: 文件类型

    Returns:
        产物内容或 None
    """
    workspace_dir = _get_workspace_dir(user_id, resource_id)
    artifact_path = workspace_dir / f"{agent_name}.{file_type}"
    return await read_file_safe(artifact_path, workspace_dir, MAX_FILE_SIZE)


async def read_agent_report(
    user_id: int,
    resource_id: int,
    agent_name: str,
) -> str | None:
    """读取 Agent 执行报告。

    Args:
        user_id: 用户 ID
        resource_id: 资源 ID
        agent_name: Agent 名称

    Returns:
        报告内容或 None
    """
    workspace_dir = _get_workspace_dir(user_id, resource_id)
    report_path = workspace_dir / f"{agent_name}_report.md"
    return await read_file_safe(report_path, workspace_dir, MAX_FILE_SIZE)


def get_workspace_dir(user_id: int, resource_id: int) -> Path:
    """获取 workspace 目录路径。"""
    return _get_workspace_dir(user_id, resource_id)


# =============================================================================
# 文件读写工具
# =============================================================================

import os
import tempfile

import aiofiles
import aiofiles.os

MAX_FILE_SIZE = 1024 * 1024  # 1MB


def validate_path(path: Path, base_dir: Path) -> bool:
    """校验路径安全，防止目录穿越攻击。"""
    try:
        resolved = path.resolve()
        base_resolved = base_dir.resolve()
        return str(resolved).startswith(str(base_resolved))
    except Exception:
        return False


async def write_file_atomic(path: Path, content: str, base_dir: Path) -> str:
    """原子写入文件（tmp → rename）。

    Args:
        path: 目标文件路径
        content: 文件内容
        base_dir: 基础目录（用于安全校验）

    Returns:
        文件路径字符串
    """
    if not validate_path(path, base_dir):
        raise ValueError(f"Invalid path: {path}")

    fd, tmp_path = tempfile.mkstemp(dir=base_dir, suffix=".tmp")
    try:
        async with aiofiles.open(fd, "w", encoding="utf-8") as f:
            await f.write(content)
        await aiofiles.os.rename(tmp_path, str(path))
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    logger.info("[FileUtils] 文件已写入: %s", path)
    return str(path)


async def read_file_safe(path: Path, base_dir: Path, max_size: int = MAX_FILE_SIZE) -> str | None:
    """安全读取文件，限制大小。

    Args:
        path: 文件路径
        base_dir: 基础目录（用于安全校验）
        max_size: 最大文件大小

    Returns:
        文件内容或 None（文件不存在）
    """
    if not path.exists():
        return None

    if not validate_path(path, base_dir):
        raise ValueError(f"Invalid path: {path}")

    stat = await aiofiles.os.stat(path)
    if stat.st_size > max_size:
        raise ValueError(f"File too large: {stat.st_size} > {max_size}")

    async with aiofiles.open(path, "r", encoding="utf-8") as f:
        return await f.read()
