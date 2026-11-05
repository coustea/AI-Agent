"""资源生成 Agent 公共上下文构建模块 (app.resource.agents.common)。"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from app.resource.schemas import ResourceInput, ResourcePlan

if TYPE_CHECKING:
    from app.path.schemas import PathResourceRequest


_PREFERENCE_VALUES: dict[str, dict[str, dict[Any, str]]] = {
    "content": {
        "structure": {
            "progressive": "按渐进式由浅入深组织",
            "summary_first": "先给总览再展开",
            "exam_points": "以考点为主线组织",
            "case_driven": "以案例驱动讲解",
        },
        "depth_level": {
            "quick": "保持快速概览深度",
            "standard": "保持标准讲解深度",
            "deep": "进行深入推导",
        },
        "focus_mode": {
            "weak_points": "优先解释易错薄弱点",
            "key_concepts": "聚焦核心概念",
            "full_coverage": "覆盖完整知识体系",
        },
        "include_examples": {True: "必须加入贴切示例", False: "不要加入示例"},
    },
    "mindmap": {
        "map_type": {
            "knowledge_tree": "按知识树展开",
            "exam_map": "按考试考点展开",
            "comparison_map": "按对比关系展开",
        },
        "leaf_detail": {
            "keyword": "叶子节点只保留关键词",
            "brief_note": "叶子节点加入简短注释",
            "annotated": "叶子节点加入解释性注释",
        },
        "show_relations": {True: "明确标出概念关系", False: "不要额外绘制关系说明"},
    },
    "quiz": {
        "difficulty_mode": {
            "basic": "题目保持基础难度",
            "adaptive": "题目难度逐步递进",
            "exam": "题目采用考试难度",
        },
        "emphasis": {
            "foundations": "侧重基础理解",
            "application": "侧重实际应用",
            "analysis": "侧重分析推理",
        },
    },
    "code": {
        "programming_language": {
            "python": "使用 Python",
            "c": "使用 C",
            "cpp": "使用 C++",
            "java": "使用 Java",
            "go": "使用 Go",
            "javascript": "使用 JavaScript",
            "typescript": "使用 TypeScript",
        },
        "output_style": {
            "tutorial": "以教学步骤呈现",
            "reference": "以可查阅的参考实现呈现",
            "challenge": "以挑战练习形式呈现",
        },
        "focus": {
            "syntax": "聚焦语法要点",
            "application": "聚焦应用实现",
            "debugging": "聚焦调试与错误定位",
        },
        "include_tests": {True: "必须给出可运行测试", False: "不要生成测试代码"},
    },
    "reading": {
        "coverage": {
            "core": "只推荐核心材料",
            "extended": "推荐核心及扩展材料",
            "broad": "提供广泛延伸材料",
        },
        "language_preference": {
            "chinese": "优先中文资料",
            "english": "优先英文资料",
            "both": "平衡中英文资料",
        },
        "focus": {
            "textbook": "偏向教材与系统课程",
            "engineering": "偏向工程实践资料",
            "research": "偏向研究论文与综述",
        },
    },
    "cartoon": {
        "visual_density": {
            "moderate": "每幕保持适中的模型对象数量",
            "rich": "每幕使用丰富但清晰的对象、关系与状态",
            "intensive": "在不牺牲可读性的前提下使用高密度概念模型",
        },
        "pace": {
            "fast": "使用紧凑的讲解和路径动画节奏",
            "balanced": "使用均衡的讲解、停顿与状态变化节奏",
            "calm": "为模型推演和理解停顿留出充足时间",
        },
        "voice": {"teacher": "使用教师风格语音", "coach": "使用教练风格语音"},
    },
}


def build_agent_preference_instruction(agent_id: str, config: dict[str, Any] | None) -> str:
    """将 Agent 参数翻译为无歧义的 LLM 生成指令。"""
    config = config or {}
    requirements: list[str] = []
    for key, choices in _PREFERENCE_VALUES.get(agent_id, {}).items():
        value = config.get(key)
        if value in choices:
            requirements.append(f"- {choices[value]}。")
    if agent_id == "mindmap" and "max_depth" in config:
        requirements.append(f"- 导图最大层级不得超过 {config['max_depth']} 层。")
    if agent_id == "quiz":
        if "question_count" in config:
            requirements.append(f"- 生成 {config['question_count']} 道题。")
        if config.get("question_types"):
            requirements.append(f"- 题型仅可使用：{'、'.join(config['question_types'])}。")
    if agent_id == "reading" and "max_items" in config:
        requirements.append(f"- 最多推荐 {config['max_items']} 项。")
    if agent_id == "cartoon" and "target_duration_seconds" in config:
        requirements.append(f"- 目标成片时长为 {config['target_duration_seconds']} 秒，必须保证机制推演完整。")
    return "## 本次生成偏好（必须落实到输出）\n" + "\n".join(requirements) if requirements else ""


def _format_profile(profile: dict) -> str | None:
    """将学习者画像格式化为 Markdown 文本。"""
    if not profile:
        return None
    profile_md = profile.get("markdown") if isinstance(profile, dict) else None
    if profile_md:
        return profile_md
    return json.dumps(profile, ensure_ascii=False, indent=2)


def build_plan_context(plan: ResourcePlan, agent_id: str) -> list[str]:
    """向 Agent 注入显式任务与全局协作约束。"""
    task = plan.task_for(agent_id)
    return [
        "## 你的结构化任务\n" + json.dumps(task.model_dump(mode="json"), ensure_ascii=False, indent=2),
        "## 全局协作计划\n"
        + json.dumps(
            {
                "schema_version": plan.schema_version,
                "learner_goal": plan.learner_goal,
                "scope": plan.scope,
            },
            ensure_ascii=False,
            indent=2,
        ),
    ]


def build_resource_context(input_data: ResourceInput) -> list[str]:
    """构建 standalone 多智能体资源生成上下文。"""
    parts = [
        f"## 学习需求\n{input_data.learning_need}",
        f"## 学习场景\n{input_data.learning_scenario}",
    ]

    profile_text = _format_profile(input_data.profile)
    if profile_text:
        parts.append("## 学习者画像\n" + profile_text)

    if input_data.agent_config:
        config = {k: v for k, v in input_data.agent_config.items() if k != "agent_id"}
        preference_instruction = build_agent_preference_instruction(
            input_data.agent_name,
            config,
        )
        if preference_instruction:
            parts.append(preference_instruction)

    if input_data.teaching_plan:
        agent_id = (
            input_data.agent_config.get("agent_id") if input_data.agent_config else None
        ) or input_data.agent_name
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

    if request.knowledge_points:
        parts.append("## 节点知识点\n" + "\n".join(f"- {item}" for item in request.knowledge_points))
    if request.weak_knowledge_points:
        parts.append("## 薄弱知识点\n" + "\n".join(f"- {item}" for item in request.weak_knowledge_points))

    profile_text = _format_profile(request.profile)
    if profile_text:
        parts.append("## 学习者画像\n" + profile_text)

    if request.programming_language:
        parts.append(f"## 编程语言偏好\n请使用 {request.programming_language} 编写代码示例。")
    if request.language_preference:
        lang_desc = {"chinese": "中文", "english": "英文", "both": "中英文兼顾"}.get(
            request.language_preference, request.language_preference
        )
        parts.append(f"## 阅读资料语言偏好\n优先推荐{lang_desc}资料。")

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
