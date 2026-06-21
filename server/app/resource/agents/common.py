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
    AgentAssignment,
    DownstreamContext,
    NodeInput,
    ReusableAssets,
    ResourceInput,
    TeachingPlan,
)
from app.resource.utils import format_learner_profile_for_prompt


def build_resource_context(input_data: ResourceInput) -> list[str]:
    """构建 standalone 多智能体资源生成上下文。

    TeachingPlan 存在时只注入该 Agent 的严格指派切片。
    """
    parts = [f"## 学习需求\n{input_data.learning_need}"]
    parts.append(f"## 学习场景\n{input_data.learning_scenario}")

    profile_text = format_learner_profile_for_prompt(input_data.profile)
    if profile_text:
        parts.append(f"## 学习者画像摘要\n{profile_text}")

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
    - 该 Agent 的 AgentAssignment（聚焦指令、风格约束、边界提醒、强调知识点、重叠回避）
    - 仅该 Agent 被指派的大纲项（而非全量 outline）
    """
    parts: list[str] = [f"## 教学计划 - Agent 指派（{agent_id}）"]

    assignment: AgentAssignment | None = None
    for a in plan.agent_assignments:
        if a.agent_id == agent_id:
            assignment = a
            break

    if assignment is None:
        if plan.teaching_strategy:
            parts.append(f"全局教学策略：{plan.teaching_strategy}")
        if plan.outline:
            outline_lines = ["全量大纲："]
            for item in plan.outline:
                outline_lines.append(f"- {item.id}: {item.title} (目标: {item.goal})")
            parts.append("\n".join(outline_lines))
        return parts

    if assignment.focus_instruction:
        parts.append(f"**聚焦指令**：{assignment.focus_instruction}")
    if assignment.style_constraint:
        parts.append(f"**风格约束**：{assignment.style_constraint}")
    if assignment.boundary_notes:
        parts.append("**边界提醒**：")
        for note in assignment.boundary_notes:
            parts.append(f"  - {note}")
    if assignment.key_points_emphasis:
        parts.append("**重点强调**：")
        for kp in assignment.key_points_emphasis:
            parts.append(f"  - {kp}")
    if assignment.avoid_overlap_with:
        parts.append(f"**避免与以下 Agent 内容重叠**：{', '.join(assignment.avoid_overlap_with)}")

    assigned_ids = set(assignment.assigned_outline_ids)
    sliced_outline = [item for item in plan.outline if item.id in assigned_ids]
    if sliced_outline:
        outline_lines = ["## 你负责的大纲项\n"]
        for item in sliced_outline:
            outline_lines.append(f"### {item.id}: {item.title}")
            outline_lines.append(f"目标：{item.goal}")
            if item.key_points:
                outline_lines.append("关键知识点：" + "、".join(item.key_points))
            if item.must_not_miss:
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
    return [item.id for item in plan.outline]


def assigned_outline_ids(plan: TeachingPlan | None, agent_id: str) -> list[str]:
    """获取指定 Agent 被指派的大纲 ID 列表。"""
    if not plan:
        return []
    for a in plan.agent_assignments:
        if a.agent_id == agent_id:
            return list(a.assigned_outline_ids)
    return [item.id for item in plan.outline]


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


def clip_text(value: str, limit: int) -> str:
    """截断文本到指定字符数，超出部分用省略号替代。"""
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def first_content_excerpt(content: str, limit: int = 180) -> str:
    """提取内容的第一个非标题/非空行作为摘要。"""
    for line in str(content or "").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped == "---" or stripped == "***":
            continue
        if stripped.startswith("- ") or stripped.startswith("* "):
            stripped = stripped[2:].strip()
        if stripped:
            return clip_text(stripped, limit)
    return ""


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
        title=clip_text(title, 120),
        one_sentence_summary=clip_text(summary, 180),
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
