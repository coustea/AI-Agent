"""
资源生成 Agent 公共基础模块。

提供：
  build_resource_context — 构建 standalone 多智能体资源生成 prompt 上下文
  build_node_context     — 构建路径规划节点资源生成 prompt 上下文
  build_agent_config_section — 将 agent_config 字典转为结构化 Markdown 配置段
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


# ── Agent config 字段的人类可读标签映射 ──────────────────────────────────

_CONTENT_LABELS: dict[str, str | dict] = {
    "structure": "讲解结构",
    "include_common_mistakes": "涵盖易错点解析",
    "include_examples": "丰富生活化示例",
    "focus_mode": {
        "weak_points": "聚焦薄弱点",
        "key_concepts": "聚焦核心概念",
        "full_coverage": "全面覆盖",
    },
    "depth_level": {
        "quick": "快速概览",
        "standard": "标准深度",
        "deep": "深度剖析",
    },
}

_MINDMAP_LABELS: dict[str, str | dict] = {
    "map_type": {
        "knowledge_tree": "核心知识树",
        "exam_map": "高频考点图",
        "comparison_map": "对比复习图",
    },
    "max_depth": "节点发散层级",
    "highlight_weak": "高亮薄弱知识点",
    "leaf_detail": {
        "keyword": "仅关键词（每节点 ≤8 字）",
        "brief_note": "关键词+简要说明（每节点 ≤20 字）",
        "annotated": "关键词+详细注释（每节点 ≤40 字，含定义或要点）",
    },
    "show_relations": "标注概念关系（→因果、⇄对比、⇢依赖、⊂包含）",
}

_QUIZ_LABELS: dict[str, str | dict] = {
    "question_count": "题目数量",
    "difficulty_mode": {
        "basic": "基础巩固",
        "adaptive": "动态自适应",
        "exam": "硬核考试",
    },
    "weak_point_weight": "薄弱点侧重权重",
    "exam_style": "考试风格",
    "include_analysis": "每题包含详细解析",
    "question_types": {
        "single": "单选",
        "multiple": "多选",
        "judge": "判断",
        "fill": "填空",
    },
}

_CODE_LABELS: dict[str, str | dict] = {
    "programming_language": "编程语言",
    "case_type": {
        "basic_demo": "基础教学",
        "algorithm_template": "算法模板",
        "debug_demo": "调试演示",
    },
    "difficulty": {
        "beginner": "入门",
        "intermediate": "进阶",
        "advanced": "挑战",
    },
}

_READING_LABELS: dict[str, str | dict] = {
    "reading_depth": {
        "course_extended": "课程内延展",
        "engineering": "工程化实践",
        "frontier": "前沿学术论文",
    },
    "max_items": "拓展上限",
    "language_preference": {
        "chinese": "中文优先",
        "english": "英文原版",
        "both": "中英双语",
    },
}

_VIDEO_LABELS: dict[str, str | dict] = {
    "duration_seconds": "预估微课时长",
    "scene_count": "场景数",
    "voice": {
        "teacher": "亲和导师",
        "coach": "硬核教练",
        "concise": "简洁旁白",
    },
    "aspect_ratio": "画面比例",
    "include_captions": "包含字幕",
}

# agent_id → 标签映射
_AGENT_CONFIG_LABELS: dict[str, dict[str, str | dict]] = {
    "content": _CONTENT_LABELS,
    "mindmap": _MINDMAP_LABELS,
    "quiz": _QUIZ_LABELS,
    "code": _CODE_LABELS,
    "reading": _READING_LABELS,
    "video": _VIDEO_LABELS,
}

_AGENT_CONFIG_TITLES: dict[str, str] = {
    "content": "内容配置",
    "mindmap": "思维导图配置",
    "quiz": "习题配置",
    "code": "代码配置",
    "reading": "阅读配置",
    "video": "视频配置",
}

# 每个基础 agent 在 prompt 中输出的结构化配置字段（排除运行时注入的非用户字段）
_AGENT_CONFIG_FIELDS: dict[str, list[str]] = {
    "content": ["structure", "include_common_mistakes", "include_examples", "focus_mode", "depth_level"],
    "mindmap": ["map_type", "max_depth", "highlight_weak", "leaf_detail", "show_relations"],
    "quiz": ["question_count", "difficulty_mode", "weak_point_weight", "exam_style", "include_analysis", "question_types"],
    "code": ["programming_language", "case_type", "difficulty"],
    "reading": ["reading_depth", "max_items", "language_preference"],
    "video": ["duration_seconds", "scene_count", "voice", "aspect_ratio", "include_captions"],
}


def _format_config_value(field: str, value: object, labels: dict[str, str | dict]) -> str:
    """将单个 config 字段值格式化为人类可读的中文描述。"""
    label_or_map = labels.get(field)
    if label_or_map is None:
        return str(value)

    # 布尔值：标签 + 是/否
    if isinstance(value, bool):
        return f"{'启用' if value else '关闭'}{label_or_map}" if isinstance(label_or_map, str) else str(value)

    # 枚举映射：查找中文标签
    if isinstance(label_or_map, dict) and isinstance(value, str):
        return label_or_map.get(value, value)

    # 列表值（如 question_types）
    if isinstance(value, list):
        if isinstance(label_or_map, dict):
            mapped = []
            for item in value:
                item_str = str(item)
                mapped.append(label_or_map.get(item, label_or_map.get(item_str, item_str)))
            return ", ".join(mapped)
        return ", ".join(str(item) for item in value)

    # 简单值 + 标签
    if isinstance(label_or_map, str):
        return f"{label_or_map}: {value}"

    return str(value)


def build_agent_config_section(agent_id: str, config: dict) -> str | None:
    """将 agent_config 字典转为结构化 Markdown 配置段。

    只输出 _AGENT_CONFIG_FIELDS 中定义的用户可配置字段，
    忽略运行时注入的字段（如 agent_id、teaching_strategy 等）。

    Args:
        agent_id: Agent 标识符
        config: agent_config 字典

    Returns:
        Markdown 格式的配置段，若该 agent 无用户可配字段则返回 None
    """
    fields = _AGENT_CONFIG_FIELDS.get(agent_id)
    if not fields:
        return None

    labels = _AGENT_CONFIG_LABELS.get(agent_id, {})
    title = _AGENT_CONFIG_TITLES.get(agent_id, f"{agent_id} 配置")

    lines = [f"## {title}"]
    for field in fields:
        value = config.get(field)
        if value is None:
            continue
        formatted = _format_config_value(field, value, labels)
        lines.append(f"- {formatted}")

    return "\n".join(lines) if len(lines) > 1 else None


# ── 上下文构建 ──────────────────────────────────────────────────────────


def build_resource_context(input_data: ResourceInput) -> list[str]:
    """构建 standalone 多智能体资源生成上下文。

    统一注入：学习需求 + 学习场景 + 用户画像 + Worker 任务 + 上游交接 + Agent 配置
    """
    parts = [f"## 学习需求\n{input_data.learning_need}"]
    parts.append(f"## 学习场景\n{input_data.learning_scenario}")

    if input_data.profile:
        profile_text = (
            json.dumps(input_data.profile, ensure_ascii=False, indent=2)
            if isinstance(input_data.profile, dict)
            else input_data.profile
        )
        parts.append(f"## 学习者画像\n{profile_text}")

    if input_data.teaching_plan:
        agent_id = (input_data.agent_config.get("agent_id") if input_data.agent_config else None) or input_data.agent_name
        if not agent_id:
            raise ValueError("resource Agent input missing agent_id")
        parts.extend(build_worker_task_context(input_data.teaching_plan, agent_id))

    if input_data.upstream_handoffs:
        handoffs = {
            agent_id: handoff.model_dump(mode="json")
            for agent_id, handoff in input_data.upstream_handoffs.items()
        }
        parts.append("## 上游交接摘要\n" + json.dumps(handoffs, ensure_ascii=False, indent=2))

    # 统一注入 Agent 配置
    effective_agent_id = (input_data.agent_config.get("agent_id") if input_data.agent_config else None) or input_data.agent_name
    if effective_agent_id and input_data.agent_config:
        config_section = build_agent_config_section(effective_agent_id, input_data.agent_config)
        if config_section:
            parts.append(config_section)

    return parts


def build_worker_task_context(plan: TeachingPlan, agent_id: str) -> list[str]:
    """只向指定 Agent 注入自己的可执行任务及对应大纲切片。"""
    task = plan.task_for(agent_id)
    outline_by_id = {item.id: item for item in plan.outline}
    parts = [
        f"## Worker Task（{agent_id}）",
        f"**任务目标**：{task.objective}",
    ]

    section_lines = ["## 你负责的大纲项"]
    for section in task.assigned_sections:
        item = outline_by_id[section.outline_id]
        section_lines.extend(
            [
                f"### {item.id}: {item.title}",
                f"- 学习目标：{item.learning_objective}",
                f"- 职责类型：{section.responsibility}",
                f"- 执行指令：{section.instruction}",
                f"- 关键知识点：{'、'.join(item.key_points)}",
                f"- 核心项：{'是，必须覆盖' if item.must_not_miss else '否'}",
            ]
        )
    parts.append("\n".join(section_lines))

    parts.append(
        "## 交付合约\n"
        f"- 输出格式：{task.deliverable.format}\n"
        + "\n".join(f"- 交付要求：{item}" for item in task.deliverable.requirements)
    )
    parts.append(
        "## 验收标准\n"
        + "\n".join(f"- {item}" for item in task.acceptance_criteria)
    )
    parts.append(
        "## 禁止事项\n"
        + "\n".join(f"- {item}" for item in task.exclusions)
    )
    if task.avoid_overlap_with:
        parts.append(
            "## 避重边界\n避免与以下 Agent 生成同质内容："
            + "、".join(task.avoid_overlap_with)
        )
    parts.append(f"## 全局学习目标\n{plan.global_plan.learning_goal}")
    parts.append(f"## 全局教学策略\n{plan.teaching_strategy}")
    parts.append(f"## 计划难度\n{plan.global_plan.difficulty}")
    return parts


def build_basic_handoff(
    *,
    source_agent: str,
    title: str,
    summary: str,
    examples: list[str] | None = None,
    visual_ideas: list[str] | None = None,
    practice_refs: list[str] | None = None,
    code_refs: list[str] | None = None,
) -> DownstreamContext:
    """构建基础的 DownstreamContext 交接摘要。"""
    return DownstreamContext(
        source_agent=source_agent,
        title=title,
        one_sentence_summary=summary,
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

    if input_data.profile:
        profile_text = (
            json.dumps(input_data.profile, ensure_ascii=False, indent=2)
            if isinstance(input_data.profile, dict)
            else input_data.profile
        )
        parts.append(f"## 学习者画像\n{profile_text}")

    # 统一注入 Agent 配置（路径节点场景）
    if input_data.agent_config:
        effective_agent_id = input_data.agent_config.get("agent_id")
        if effective_agent_id:
            config_section = build_agent_config_section(effective_agent_id, input_data.agent_config)
            if config_section:
                parts.append(config_section)

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
