"""将资源页公开参数翻译成每个 Agent 可执行的 LLM 生成指令。"""

from __future__ import annotations

from typing import Any


_VALUES: dict[str, dict[str, dict[Any, str]]] = {
    "content": {
        "structure": {"progressive": "按渐进式由浅入深组织", "summary_first": "先给总览再展开", "exam_points": "以考点为主线组织", "case_driven": "以案例驱动讲解"},
        "depth_level": {"quick": "保持快速概览深度", "standard": "保持标准讲解深度", "deep": "进行深入推导"},
        "focus_mode": {"weak_points": "优先解释易错薄弱点", "key_concepts": "聚焦核心概念", "full_coverage": "覆盖完整知识体系"},
        "include_examples": {True: "必须加入贴切示例", False: "不要加入示例"},
    },
    "mindmap": {
        "map_type": {"knowledge_tree": "按知识树展开", "exam_map": "按考试考点展开", "comparison_map": "按对比关系展开"},
        "leaf_detail": {"keyword": "叶子节点只保留关键词", "brief_note": "叶子节点加入简短注释", "annotated": "叶子节点加入解释性注释"},
        "show_relations": {True: "明确标出概念关系", False: "不要额外绘制关系说明"},
    },
    "quiz": {
        "difficulty_mode": {"basic": "题目保持基础难度", "adaptive": "题目难度逐步递进", "exam": "题目采用考试难度"},
        "emphasis": {"foundations": "侧重基础理解", "application": "侧重实际应用", "analysis": "侧重分析推理"},
    },
    "code": {
        "programming_language": {"python": "使用 Python", "c": "使用 C", "cpp": "使用 C++", "java": "使用 Java", "go": "使用 Go", "javascript": "使用 JavaScript", "typescript": "使用 TypeScript"},
        "output_style": {"tutorial": "以教学步骤呈现", "reference": "以可查阅的参考实现呈现", "challenge": "以挑战练习形式呈现"},
        "focus": {"syntax": "聚焦语法要点", "application": "聚焦应用实现", "debugging": "聚焦调试与错误定位"},
        "include_tests": {True: "必须给出可运行测试", False: "不要生成测试代码"},
    },
    "reading": {
        "coverage": {"core": "只推荐核心材料", "extended": "推荐核心及扩展材料", "broad": "提供广泛延伸材料"},
        "language_preference": {"chinese": "优先中文资料", "english": "优先英文资料", "both": "平衡中英文资料"},
        "focus": {"textbook": "偏向教材与系统课程", "engineering": "偏向工程实践资料", "research": "偏向研究论文与综述"},
    },
    "cartoon": {
        "depth": {"overview": "采用概览讲解", "standard": "采用标准讲解深度", "deep": "进行深入讲解"},
        "pace": {"fast": "使用紧凑讲解节奏", "normal": "使用正常讲解节奏", "slow": "放慢讲解节奏并留出理解停顿"},
    },
}


def build_agent_preference_instruction(agent_id: str, config: dict[str, Any] | None) -> str:
    """返回可直接拼入 LLM prompt 的、无歧义的用户偏好约束。"""
    config = config or {}
    requirements: list[str] = []
    for key, choices in _VALUES.get(agent_id, {}).items():
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
    return "## 本次生成偏好（必须落实到输出）\n" + "\n".join(requirements) if requirements else ""
