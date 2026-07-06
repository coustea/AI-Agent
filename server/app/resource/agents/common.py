"""
资源生成 Agent 公共基础模块。

提供：
  build_resource_context — 构建 standalone 多智能体资源生成 prompt 上下文
  build_node_context     — 构建路径规划节点资源生成 prompt 上下文
"""

import json

from app.resource.schemas import (
    NodeInput,
    ResourceInput,
)


def _format_profile(profile: dict) -> str | None:
    """将学习者画像格式化为 Markdown 文本。

    画像可能以 Markdown 文本形式传入（key="markdown"），
    也可能是原始 JSON 字典。优先使用 Markdown 形式。
    """
    if not profile:
        return None
    profile_md = profile.get("markdown") if isinstance(profile, dict) else None
    if profile_md:
        return profile_md
    return json.dumps(profile, ensure_ascii=False, indent=2)


def build_resource_context(input_data: ResourceInput) -> list[str]:
    """构建 standalone 多智能体资源生成上下文。

    统一注入：学习需求 + 学习场景 + 用户画像 + Agent 配置 + 协同计划 + 上游交接
    """
    parts = [f"## 学习需求\n{input_data.learning_need}"]
    parts.append(f"## 学习场景\n{input_data.learning_scenario}")

    profile_text = _format_profile(input_data.profile)
    if profile_text:
        parts.append("## 学习者画像\n" + profile_text)

    # 注入 Agent 配置（排除运行时注入的 agent_id）
    if input_data.agent_config:
        config = {k: v for k, v in input_data.agent_config.items() if k != "agent_id"}
        if config:
            parts.append("## 生成配置\n" + json.dumps(config, ensure_ascii=False, indent=2))

    if input_data.teaching_plan:
        agent_id = (input_data.agent_config.get("agent_id") if input_data.agent_config else None) or input_data.agent_name
        if not agent_id:
            raise ValueError("resource Agent input missing agent_id")
        parts.extend(build_plan_context(input_data.teaching_plan, agent_id))

    if input_data.upstream_handoffs:
        handoffs = {
            agent_id: handoff.model_dump(mode="json")
            for agent_id, handoff in input_data.upstream_handoffs.items()
        }
        parts.append("## 上游交接摘要\n" + json.dumps(handoffs, ensure_ascii=False, indent=2))

    return parts


def build_plan_context(plan_markdown: str, agent_id: str) -> list[str]:
    """向指定 Agent 注入来自协同计划的上下文。

    直接注入完整 Markdown 计划，并高亮该 Agent 的专属段落。
    """
    parts = [f"## 协同计划（你的任务段落：### [{agent_id}]）"]

    # 使用 ResourcePlan.extract_agent_section 提取该 Agent 的专属段落
    from app.resource.schemas.plan import ResourcePlan
    plan = ResourcePlan(content=plan_markdown, title="")
    section = plan.extract_agent_section(agent_id)

    if section:
        parts.append("### 你的专属任务")
        parts.append(section)

    parts.append("### 完整协同计划")
    parts.append(plan_markdown)

    return parts


def build_node_context(input_data: NodeInput) -> list[str]:
    """构建路径规划当前节点资源生成上下文。"""
    parts = [
        f"## 路径目标\n{input_data.path_goal}",
        f"## 路径标题\n{input_data.path_title}",
        "\n".join([
            "## 当前节点",
            f"- 节点标题: {input_data.node_title}",
            f"- 节点标识: {input_data.node_key}",
            f"- 难度: {input_data.difficulty or ''}",
            f"- 掌握目标: {input_data.mastery_target or ''}",
        ]),
    ]

    if input_data.knowledge_points:
        parts.append("## 节点知识点\n" + "\n".join(f"- {item}" for item in input_data.knowledge_points))
    if input_data.weak_knowledge_points:
        parts.append("## 薄弱知识点\n" + "\n".join(f"- {item}" for item in input_data.weak_knowledge_points))
    if input_data.generation_focus:
        parts.append("## 生成重点\n" + "\n".join(f"- {item}" for item in input_data.generation_focus))

    profile_text = _format_profile(input_data.profile)
    if profile_text:
        parts.append("## 学习者画像\n" + profile_text)

    parts.append("\n".join([
        "## 当前教程",
        f"- 标题: {input_data.tutorial_title}",
        f"- 摘要: {input_data.tutorial_summary or ''}",
        "",
        input_data.tutorial_markdown,
    ]))

    return parts
