"""
资源生成 Agent 公共基础模块。

提供：
  build_resource_context — 构建 standalone 多智能体资源生成 prompt 上下文
  build_node_context     — 构建路径规划节点资源生成 prompt 上下文
  salvage_json_from_llm  — 从 LLM 输出中健壮地提取 JSON（处理 markdown fence 包裹）
"""

import json
import re

from app.resource.schemas import (
    DownstreamContext,
    NodeInput,
    ReusableAssets,
    ResourceInput,
    TeachingPlan,
)


def build_resource_context(input_data: ResourceInput) -> list[str]:
    """构建 standalone 多智能体资源生成上下文。

    TeachingPlan 存在时只注入该 Agent 的严格指派切片。
    """
    parts = [f"## 学习需求\n{input_data.learning_need}"]
    parts.append(f"## 学习场景\n{input_data.learning_scenario}")

    # profile 已经是 Markdown 格式，直接使用
    if input_data.profile:
        parts.append(input_data.profile)

    if input_data.teaching_plan:
        agent_id = (input_data.agent_config.get("agent_id") if input_data.agent_config else None) or input_data.agent_name
        if not agent_id:
            raise ValueError("resource Agent input missing agent_id")
        parts.extend(build_agent_assignment_context(input_data.teaching_plan, agent_id))

    if input_data.upstream_handoffs:
        handoffs = {
            agent_id: handoff.model_dump(mode="json")
            for agent_id, handoff in input_data.upstream_handoffs.items()
        }
        parts.append("## 上游交接摘要\n" + json.dumps(handoffs, ensure_ascii=False, indent=2))

    return parts


def build_agent_assignment_context(plan: TeachingPlan, agent_id: str) -> list[str]:
    """为指定 Agent 构建 assignment 切片上下文。

    注入：
    - 该 Agent 的指派信息（聚焦指令、覆盖的大纲项）
    - 仅该 Agent 被指派的大纲项（而非全量 outline）
    """
    parts: list[str] = [f"## 教学计划 - Agent 指派（{agent_id}）"]

    assignment: dict | None = None
    for a in plan.agent_assignments:
        if a.get("agent_id") == agent_id:
            assignment = a
            break

    if assignment is None:
        if plan.teaching_strategy:
            parts.append(f"全局教学策略：{plan.teaching_strategy}")
        if plan.outline:
            outline_lines = ["全量大纲："]
            for item in plan.outline:
                outline_lines.append(f"- {item.get('id', '')}: {item.get('title', '')}")
            parts.append("\n".join(outline_lines))
        return parts

    if assignment.get("focus_instruction"):
        parts.append(f"**聚焦指令**：{assignment['focus_instruction']}")

    assigned_ids = set(assignment.get("assigned_outline_ids", []))
    sliced_outline = [item for item in plan.outline if item.get("id") in assigned_ids]
    if sliced_outline:
        outline_lines = ["## 你负责的大纲项\n"]
        for item in sliced_outline:
            outline_lines.append(f"### {item.get('id', '')}: {item.get('title', '')}")
            if item.get("key_points"):
                outline_lines.append("关键知识点：" + "、".join(item["key_points"]))
            if item.get("must_not_miss"):
                outline_lines.append("⚠️ 核心大纲（必须覆盖）")
            outline_lines.append("")
        parts.append("\n".join(outline_lines))

    if plan.teaching_strategy:
        parts.append(f"## 全局教学策略\n{plan.teaching_strategy}")

    return parts


def outline_ids_from_plan(plan: TeachingPlan | None) -> list[str]:
    """获取教学计划中所有大纲项的 ID 列表。"""
    if not plan:
        return []
    return [item.get("id", "") for item in plan.outline]


def assigned_outline_ids(plan: TeachingPlan | None, agent_id: str) -> list[str]:
    """获取指定 Agent 被指派的大纲 ID 列表。"""
    if not plan:
        return []
    for a in plan.agent_assignments:
        if a.get("agent_id") == agent_id:
            return list(a.get("assigned_outline_ids", []))
    return [item.get("id", "") for item in plan.outline]


def outline_coverage_summary(
    plan: TeachingPlan | None,
    handoffs: dict[str, DownstreamContext],
) -> dict[str, list[str]]:
    """汇总大纲覆盖情况 — 哪些被覆盖、哪些缺失。"""
    plan_ids = outline_ids_from_plan(plan)
    covered: list[str] = []
    for handoff in handoffs.values():
        for outline_id in handoff.covered_outline_ids:
            if outline_id not in set(plan_ids):
                raise ValueError(f"handoff references unknown outline ID: {outline_id}")
            if outline_id not in covered:
                covered.append(outline_id)
    return {
        "teaching_plan_outline_ids": plan_ids,
        "covered_source_outline_ids": covered,
        "missing_source_outline_ids": [oid for oid in plan_ids if oid not in covered],
    }


def build_basic_handoff(
    *,
    source_agent: str,
    title: str,
    summary: str,
    teaching_plan: TeachingPlan | None,
    covered_outline_ids: list[str] | None = None,
    examples: list[str] | None = None,
    visual_ideas: list[str] | None = None,
    practice_refs: list[str] | None = None,
    code_refs: list[str] | None = None,
) -> DownstreamContext:
    """构建基础的 DownstreamContext 交接摘要。"""
    if teaching_plan is None:
        raise ValueError("standalone handoff requires TeachingPlan")
    provided_outline_ids = list(covered_outline_ids or [])
    if not provided_outline_ids:
        raise ValueError(f"Agent {source_agent!r} handoff must cover at least one outline ID")
    if len(provided_outline_ids) != len(set(provided_outline_ids)):
        raise ValueError(f"Agent {source_agent!r} handoff contains duplicate outline IDs")
    unknown_outline_ids = set(provided_outline_ids) - set(outline_ids_from_plan(teaching_plan))
    if unknown_outline_ids:
        raise ValueError(
            f"Agent {source_agent!r} handoff references unknown outline IDs: {sorted(unknown_outline_ids)}"
        )
    return DownstreamContext(
        source_agent=source_agent,
        title=title,
        one_sentence_summary=summary,
        covered_outline_ids=provided_outline_ids,
        reusable_assets=ReusableAssets(
            examples=(examples or [])[:6],
            visual_ideas=(visual_ideas or [])[:6],
            practice_refs=(practice_refs or [])[:6],
            code_refs=(code_refs or [])[:6],
        ),
    )



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

    # profile 已经是 Markdown 格式，直接使用
    if input_data.profile:
        parts.append(input_data.profile)

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
