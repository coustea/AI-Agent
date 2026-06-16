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

    if input_data.teaching_plan:
        parts.append(f"## 教学计划\n{input_data.teaching_plan.model_dump_json(indent=2)}")

    if input_data.upstream_handoffs:
        handoffs = {
            agent_id: handoff.model_dump(mode="json")
            for agent_id, handoff in input_data.upstream_handoffs.items()
        }
        parts.append("## 上游交接摘要\n" + json.dumps(handoffs, ensure_ascii=False, indent=2))

    return parts


from app.resource.schemas import DownstreamContext, DownstreamMaterial, ReusableAssets, TeachingPlan


def outline_ids_from_plan(plan: TeachingPlan | None) -> list[str]:
    if not plan:
        return []
    return [item.id for item in plan.outline]


def first_outline_id(plan: TeachingPlan | None) -> str:
    ids = outline_ids_from_plan(plan)
    return ids[0] if ids else ""


def _valid_outline_ids(plan: TeachingPlan | None, outline_ids: list[str] | None) -> list[str]:
    allowed = set(outline_ids_from_plan(plan))
    if not allowed:
        return []
    result: list[str] = []
    for outline_id in outline_ids or []:
        if outline_id in allowed and outline_id not in result:
            result.append(outline_id)
    return result


def select_outline_ids_by_keywords(plan: TeachingPlan | None, keywords: list[str]) -> list[str]:
    if not plan:
        return []
    normalized = [item.strip().lower() for item in keywords if item.strip()]
    if not normalized:
        return [first_outline_id(plan)] if first_outline_id(plan) else []
    matched: list[str] = []
    for item in plan.outline:
        haystack = " ".join([
            item.title,
            item.goal,
            " ".join(item.key_points),
            " ".join(item.suggested_examples),
            " ".join(item.suggested_visuals),
        ]).lower()
        if any(keyword in haystack for keyword in normalized):
            matched.append(item.id)
    return matched or ([first_outline_id(plan)] if first_outline_id(plan) else [])


def outline_coverage_summary(
    plan: TeachingPlan | None,
    handoffs: dict[str, DownstreamContext],
) -> dict[str, list[str]]:
    plan_ids = outline_ids_from_plan(plan)
    allowed = set(plan_ids)
    covered: list[str] = []
    for handoff in handoffs.values():
        for outline_id in handoff.covered_outline_ids:
            if outline_id in allowed and outline_id not in covered:
                covered.append(outline_id)
    return {
        "teaching_plan_outline_ids": plan_ids,
        "covered_source_outline_ids": covered,
        "missing_source_outline_ids": [oid for oid in plan_ids if oid not in covered],
    }


def clip_text(value: str, limit: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def first_content_excerpt(content: str, limit: int = 180) -> str:
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
    material_type: str,
    covered_outline_ids: list[str] | None = None,
    material_outline_id: str | None = None,
    key_points: list[str] | None = None,
    evidence: str = "",
    examples: list[str] | None = None,
    visual_ideas: list[str] | None = None,
    practice_refs: list[str] | None = None,
    code_refs: list[str] | None = None,
    cautions: list[str] | None = None,
) -> DownstreamContext:
    filtered_covered_ids = _valid_outline_ids(
        teaching_plan,
        covered_outline_ids or ([first_outline_id(teaching_plan)] if first_outline_id(teaching_plan) else []),
    )
    valid_material_ids = _valid_outline_ids(teaching_plan, [material_outline_id or ""])
    resolved_material_outline_id = (
        valid_material_ids[0]
        if valid_material_ids
        else (filtered_covered_ids[0] if filtered_covered_ids else "")
    )
    material = DownstreamMaterial(
        outline_id=resolved_material_outline_id,
        type=material_type,
        summary=clip_text(summary, 500),
        key_points=(key_points or [])[:8],
        evidence_excerpt=clip_text(evidence, 180),
        priority=1,
    )
    return DownstreamContext(
        source_agent=source_agent,
        title=clip_text(title, 120),
        one_sentence_summary=clip_text(summary, 180),
        covered_outline_ids=filtered_covered_ids,
        materials=[material] if material.summary else [],
        reusable_assets=ReusableAssets(
            examples=(examples or [])[:6],
            visual_ideas=(visual_ideas or [])[:6],
            practice_refs=(practice_refs or [])[:6],
            code_refs=(code_refs or [])[:6],
        ),
        cautions=(cautions or [])[:6],
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
