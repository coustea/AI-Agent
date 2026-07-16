"""
资源生成 Agent 公共基础模块。

提供：
  build_resource_context — 构建 standalone 多智能体资源生成 prompt 上下文
  build_path_context     — 从 PathResourceRequest 构建上下文（统一接口）
"""

import json
from typing import TYPE_CHECKING

from app.resource.schemas import ResourceInput
from app.resource.agent_preferences import build_agent_preference_instruction

if TYPE_CHECKING:
    from app.path.schemas import PathResourceRequest


def _format_profile(profile: dict) -> str | None:
    """将学习者画像格式化为 Markdown 文本。

    画像可能以 Markdown 文本形式传入（key="markdown"），
    也可能是原始 JSON 字典。优先使用 Markdown 形式。
    """
    if not profile:
        return None
    # 优先使用已渲染的 Markdown 画像
    profile_md = profile.get("markdown") if isinstance(profile, dict) else None
    if profile_md:
        return profile_md
    # 否则将原始字典序列化
    return json.dumps(profile, ensure_ascii=False, indent=2)


def build_resource_context(input_data: ResourceInput) -> list[str]:
    """构建 standalone 多智能体资源生成上下文。

    统一注入：学习需求 + 学习场景 + 用户画像 + Agent 配置 + 协同计划 + 上游交接
    """
    parts = [f"## 学习需求\n{input_data.learning_need}"]
    parts.append(f"## 学习场景\n{input_data.learning_scenario}")

    # 注入学习者画像
    profile_text = _format_profile(input_data.profile)
    if profile_text:
        parts.append("## 学习者画像\n" + profile_text)

    # 参数必须转成面向输出的 LLM 指令，不能把实现 JSON 当作提示词契约。
    if input_data.agent_config:
        config = {k: v for k, v in input_data.agent_config.items() if k != "agent_id"}
        preference_instruction = build_agent_preference_instruction(
            input_data.agent_name,
            config,
        )
        if preference_instruction:
            parts.append(preference_instruction)

    # 注入协同计划并高亮本 Agent 专属段落
    if input_data.teaching_plan:
        agent_id = (input_data.agent_config.get("agent_id") if input_data.agent_config else None) or input_data.agent_name
        if not agent_id:
            raise ValueError("resource Agent input missing agent_id")
        parts.extend(build_plan_context(input_data.teaching_plan, agent_id))

    # 注入上游 Agent 的交接摘要
    if input_data.upstream_handoffs:
        handoffs = {
            agent_id: handoff.model_dump(mode="json")
            for agent_id, handoff in input_data.upstream_handoffs.items()
        }
        parts.append("## 上游交接摘要\n" + json.dumps(handoffs, ensure_ascii=False, indent=2))

    return parts


def build_plan_context(plan: "ResourcePlan", agent_id: str) -> list[str]:
    """向 Agent 注入显式任务与全局协作约束。"""
    task = plan.task_for(agent_id)
    return [
        "## 你的结构化任务\n" + json.dumps(task.model_dump(mode="json"), ensure_ascii=False, indent=2),
        "## 全局协作计划\n" + json.dumps(
            {
                "schema_version": plan.schema_version,
                "learner_goal": plan.learner_goal,
                "scope": plan.scope,
            },
            ensure_ascii=False,
            indent=2,
        ),
    ]


def build_path_context(request: "PathResourceRequest") -> list[str]:
    """从 PathResourceRequest 构建上下文（路径规划统一接口）。"""
    parts = [
        f"## 路径目标\n{request.path_goal}",
        f"## 路径标题\n{request.path_title}",
        "\n".join([
            "## 当前节点",
            f"- 节点标题: {request.node_title}",
            f"- 节点标识: {request.node_key}",
            f"- 难度: {request.difficulty or ''}",
        ]),
    ]

    # 注入知识点、薄弱点
    if request.knowledge_points:
        parts.append("## 节点知识点\n" + "\n".join(f"- {item}" for item in request.knowledge_points))
    if request.weak_knowledge_points:
        parts.append("## 薄弱知识点\n" + "\n".join(f"- {item}" for item in request.weak_knowledge_points))

    # 注入学习者画像
    profile_text = _format_profile(request.profile)
    if profile_text:
        parts.append("## 学习者画像\n" + profile_text)

    # 注入教程内容
    tutorial = request.tutorial
    if tutorial:
        parts.append("\n".join([
            "## 当前教程",
            f"- 标题: {tutorial.title}",
            f"- 摘要: {tutorial.summary or ''}",
            "",
            tutorial.content_markdown,
        ]))

    return parts
