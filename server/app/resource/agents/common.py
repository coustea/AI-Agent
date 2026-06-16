"""
资源生成 Agent 公共基础模块。

提供：
  build_resource_context — 构建 standalone 多智能体资源生成 prompt 上下文
  build_node_context     — 构建路径规划节点资源生成 prompt 上下文
  salvage_json_from_llm  — 从 LLM 输出中健壮地提取 JSON（处理 markdown fence 包裹）
"""

import json
import re

from app.resource.schemas import NodeInput, ResourceInput
from app.resource.utils import format_learner_profile_for_prompt


def build_resource_context(input_data: ResourceInput) -> list[str]:
    """构建 standalone 多智能体资源生成上下文。"""
    parts = [f"## 学习需求\n{input_data.learning_need}"]
    parts.append(f"## 学习场景\n{input_data.learning_scenario}")

    profile_text = format_learner_profile_for_prompt(input_data.profile)
    if profile_text:
        parts.append(f"## 学习者画像摘要\n{profile_text}")

    if input_data.blueprint:
        parts.append(f"## 教学蓝图\n{input_data.blueprint.model_dump_json(indent=2)}")

    if input_data.instruction:
        lines = [f"## 规划师指令\n- 重点: {input_data.instruction.focus}"]
        if input_data.instruction.difficulty:
            lines.append(f"- 难度: {input_data.instruction.difficulty}")
        if input_data.instruction.personalization_notes:
            lines.append(f"- 个性化建议: {input_data.instruction.personalization_notes}")
        for constraint in input_data.instruction.constraints:
            lines.append(f"- 约束: {constraint}")
        parts.append("\n".join(lines))

    if input_data.previous_results:
        lines = ["## 已生成资源摘要"]
        for agent_id, result in input_data.previous_results.items():
            if result.success:
                lines.append(f"- {agent_id}: {result.title or result.summary or '已生成'}")
        parts.append("\n".join(lines))

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

    profile_text = format_learner_profile_for_prompt(input_data.profile)
    if profile_text:
        parts.append(f"## 学习者画像摘要\n{profile_text}")

    parts.append("\n".join([
        "## 当前教程",
        f"- 标题: {input_data.tutorial_title}",
        f"- 摘要: {input_data.tutorial_summary or ''}",
        "",
        input_data.tutorial_markdown,
    ]))

    return parts


def salvage_json_from_llm(raw: str, *, require_key: str | None = None) -> dict | None:
    """从 LLM 输出中健壮地提取 JSON 字典。"""
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and (not require_key or require_key in data):
            return data
    except json.JSONDecodeError:
        pass

    match = re.search(r"```(?:json)?\s*\n(.*?)```", raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            if isinstance(data, dict) and (not require_key or require_key in data):
                return data
        except json.JSONDecodeError:
            pass

    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        try:
            data = json.loads(raw[start:end + 1])
            if isinstance(data, dict) and (not require_key or require_key in data):
                return data
        except json.JSONDecodeError:
            pass

    return None
