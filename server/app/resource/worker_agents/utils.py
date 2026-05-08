"""
Worker Agent 工具函数集合。

包含：
- Markdown 提取工具
- 格式化工具（上游结果、画像、依赖报告）
- append_backend_context_for_prompt（兼容旧接口）
- AgentContextBuilder：按 Agent 类型裁剪上下文，避免 prompt token 过长

AgentContextBuilder 使用示例：
    builder = AgentContextBuilder()
    context = builder.build_for_agent("content", state)
    # context 包含：learning_need, learning_scenario, learner_profile 简要字段,
    #              agent_config (structure, include_common_mistakes 等),
    #              personalized_constraints
"""

from __future__ import annotations

import json
import re
from typing import Any


# Markdown 代码块匹配
_MARKDOWN_FENCE_RE = re.compile(r"```(?:markdown|md)?\s*\n(.*?)\n```", re.DOTALL | re.IGNORECASE)


def extract_markdown_from_llm_output(content: str) -> str:
    """从 LLM 输出中提取 Markdown 内容。"""
    raw = (content or "").strip()
    if not raw:
        return ""

    match = _MARKDOWN_FENCE_RE.search(raw)
    if match:
        raw = match.group(1).strip()

    return _normalize_markdown_indent(raw)


def _normalize_markdown_indent(markdown_text: str) -> str:
    """规范化 Markdown 缩进，确保一级分支顶格。"""
    lines = markdown_text.splitlines()
    bullet_indents = [
        len(line) - len(line.lstrip(" "))
        for line in lines
        if line.lstrip(" ").startswith("- ")
    ]
    if not bullet_indents:
        return markdown_text.strip()

    min_indent = min(bullet_indents)
    if min_indent == 0:
        return markdown_text.strip()

    normalized = []
    for line in lines:
        if line.startswith(" " * min_indent):
            normalized.append(line[min_indent:])
        else:
            normalized.append(line)
    return "\n".join(normalized).strip()


def format_dependency_reports_for_prompt(dependency_reports: dict[str, Any] | None) -> str:
    """Format compact upstream execution reports for downstream agent prompts."""
    if not dependency_reports:
        return ""

    sections: list[str] = []
    for agent, report in dependency_reports.items():
        if not report:
            continue
        sections.append(f"### {agent}")
        sections.append(str(report).strip())
    return "\n".join(sections).strip()


def format_upstream_results_for_prompt(
    upstream_results: dict[str, Any] | None,
    *,
    skip_agents: dict[str, Any] | None = None,
    max_chars_per_agent: int = 900,
) -> str:
    """格式化显式依赖的上游摘要，不暴露完整资源正文，避免 prompt token 过长。"""
    if not upstream_results:
        return ""

    skipped = set((skip_agents or {}).keys())
    sections: list[str] = []
    for agent, result in upstream_results.items():
        if agent in skipped:
            continue
        preview = _format_dependency_summary(result, max_chars=max_chars_per_agent)
        if not preview:
            continue
        sections.append(f"### {agent}")
        sections.append(preview)
    return "\n".join(sections).strip()


def _format_dependency_summary(result: Any, *, max_chars: int) -> str:
    """格式化单个上游依赖摘要，只提取 title/summary/summary_data，不回退到完整 content。"""
    if not isinstance(result, dict):
        return str(result or "")[:max_chars].strip()

    lines: list[str] = []
    title = result.get("title")
    summary = result.get("summary")
    summary_data = result.get("summary_data")
    if title:
        lines.append(f"- 标题：{str(title)[:120]}")
    if summary:
        lines.append(f"- 摘要：{str(summary)[:240]}")
    # 从 summary_data 中提取结构化信息，供下游 Agent 理解上游产出
    if isinstance(summary_data, dict) and summary_data:
        for key, label in (
            ("key_points", "核心知识点"),
            ("principles", "核心原理"),
            ("weak_points", "薄弱点"),
            ("common_mistakes", "常见误区"),
            ("examples", "示例"),
            ("learning_suggestions", "学习建议"),
            ("covered_points", "覆盖知识点"),
            ("practice_points", "实践点"),
        ):
            value = summary_data.get(key)
            if isinstance(value, list) and value:
                lines.append(f"{label}：")
                lines.extend(f"- {str(item)[:120]}" for item in value[:6])
            elif isinstance(value, str) and value:
                lines.append(f"- {label}：{value[:240]}")
    return "\n".join(lines)[:max_chars].strip()


def format_learner_profile_for_prompt(learner_profile: dict[str, Any] | None) -> str:
    """Format backend-loaded learner profile for worker prompts."""
    if not learner_profile:
        return ""

    profile_json = learner_profile.get("profile_json")
    if isinstance(profile_json, dict):
        return json.dumps(profile_json, ensure_ascii=False, indent=2)

    lines: list[str] = []
    for key, label in (
        ("major", "专业"),
        ("grade", "年级"),
        ("school", "学校"),
        ("current_focus", "当前关注"),
        ("learning_style", "学习偏好"),
    ):
        value = learner_profile.get(key)
        if value:
            lines.append(f"- {label}: {value}")
    return "\n".join(lines).strip()


def append_backend_context_for_prompt(parts: list[str], state: Any) -> None:
    """追加后端上下文到 prompt，仅拼接显式依赖摘要，不拼接完整资源正文。"""
    profile_text = format_learner_profile_for_prompt(getattr(state, "learner_profile", {}))
    if profile_text:
        parts.extend(["", "## 学习者画像", profile_text])

    dependency_report_text = format_dependency_reports_for_prompt(getattr(state, "dependency_reports", {}))
    if dependency_report_text:
        parts.extend(["", "## 依赖交接报告", dependency_report_text])

    # 仅拼接显式依赖摘要；上游数据为空时不输出占位段落
    upstream_preview = format_upstream_results_for_prompt(getattr(state, "upstream_results", {}))
    if upstream_preview:
        parts.extend(["", "## 上游结果摘要", upstream_preview])


async def generate_summary_with_llm(markdown: str, learning_need: str = "") -> str:
    """使用 spark-x2-flash 生成内容摘要。"""
    from langchain_core.messages import HumanMessage
    from app.infra.llm import get_llm_manager

    if not markdown or not markdown.strip():
        return ""

    prompt = f"""请为以下学习内容生成一段简洁的摘要（100-150字），概括核心知识点：

学习主题：{learning_need[:100] if learning_need else "未指定"}

内容：
{markdown[:3000]}

要求：
1. 摘要要简洁，突出核心概念
2. 不要使用 Markdown 格式，直接输出纯文本
3. 不要添加额外解释"""

    try:
        llm_manager = get_llm_manager()
        response = await llm_manager.ainvoke(
            "spark_x2_flash",
            [HumanMessage(content=prompt)],
            model_kwargs={"temperature": 0.3},
        )
        summary = response.content if hasattr(response, "content") else str(response)
        return summary.strip()
    except Exception:
        return ""


def build_content_summary_data(markdown: str, learning_need: str = "") -> dict[str, Any]:
    """从 ContentAgent Markdown 输出中提取结构化摘要，供下游 Agent 轻量交接。"""
    text = (markdown or "").strip()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    topic = ""
    if lines and lines[0].startswith("#"):
        topic = lines[0].lstrip("#").strip()
    if not topic:
        topic = learning_need[:80]

    sections: dict[str, list[str]] = {}
    current = "default"
    for line in lines:
        if line.startswith("#"):
            current = line.lstrip("#").strip().lower()
            sections.setdefault(current, [])
            continue
        if line.startswith(("- ", "* ", "1. ")):
            sections.setdefault(current, []).append(re.sub(r"^[-*]\s+|^\d+\.\s+", "", line))

    def pick(keys: list[str], fallback: list[str] | None = None) -> list[str]:
        values: list[str] = []
        for key, items in sections.items():
            if any(token in key for token in keys):
                values.extend(items)
        if not values and fallback:
            values = fallback
        return [item for item in values if item][:8]

    fallback_points = [line for line in lines if line.startswith(("##", "###"))][:6]
    key_points = pick(["核心概念", "知识结构", "核心知识", "重点", "关键"], fallback_points)
    principles = pick(["核心原理", "原理", "机制", "底层原理"])
    # 薄弱点：从"薄弱点"、"易错点"、"难点"等章节提取
    weak_points = pick(["薄弱点", "易错点", "难点", "薄弱", "不足"])
    common_mistakes = pick(["常见误区", "注意事项", "误区", "错误", "陷阱"])
    examples = pick(["示例", "案例", "例子", "实例"])
    learning_suggestions = pick(["学习建议", "建议", "复习", "学习策略"])

    return {
        "topic": topic or learning_need[:80],
        "course": "",
        "key_points": key_points[:8],
        "principles": principles[:8],
        "weak_points": weak_points[:8],
        "common_mistakes": common_mistakes[:8],
        "examples": examples[:8],
        "learning_suggestions": learning_suggestions[:8],
    }


def learning_need_from_task(task: dict[str, Any]) -> str:
    """Return the frontend natural-language learning need from a worker task."""
    return str(task.get("learning_need") or "未说明").strip() or "未说明"


def title_from_learning_need(task: dict[str, Any], suffix: str, *, max_chars: int = 32) -> str:
    """Build a stable resource title from the frontend learning_need only."""
    learning_need = learning_need_from_task(task)
    if len(learning_need) > max_chars:
        learning_need = f"{learning_need[:max_chars]}..."
    return f"{learning_need} - {suffix}"


class AgentContextBuilder:
    """按 Agent 类型裁剪上下文，避免 prompt token 过长。"""

    # Agent ID 常量，与 ResourceAgentId 枚举对应
    CONTENT = "content"
    MINDMAP = "mindmap"
    DIAGRAM = "diagram"
    CODE = "code"
    QUIZ = "quiz"
    READING = "reading"

    # 学习者画像简要字段（用于 ContentAgent）
    _PROFILE_BRIEF_FIELDS = [
        ("major", "专业"),
        ("grade", "年级"),
        ("school", "学校"),
        ("current_focus", "当前关注"),
        ("learning_style", "学习偏好"),
    ]

    # 薄弱点简要字段（用于 QuizAgent）
    _WEAK_POINT_FIELDS = ["weak_points", "knowledge_gaps", "struggling_topics"]

    def build_for_agent(self, agent_id: str, state: Any) -> str:
        """构建指定 Agent 的上下文字符串。

        Args:
            agent_id: Agent ID（content/mindmap/diagram/code/quiz/reading）
            state: WorkerState 实例，包含 learner_profile、agent_config、upstream_results 等

        Returns:
            格式化的上下文字符串，仅包含该 Agent 需要的信息
        """
        builder_map = {
            self.CONTENT: self._for_content,
            self.MINDMAP: self._for_mindmap,
            self.DIAGRAM: self._for_diagram,
            self.CODE: self._for_code,
            self.QUIZ: self._for_quiz,
            self.READING: self._for_reading,
        }
        builder = builder_map.get(agent_id)
        if not builder:
            # 未匹配的 Agent 使用通用简化上下文
            return self._build_generic(state)
        return builder(state)

    def _for_content(self, state: Any) -> str:
        """ContentAgent 需要完整画像信息。"""
        parts: list[str] = []

        # 1. learning_need
        learning_need = self._get_learning_need(state)
        if learning_need:
            parts.append(f"## 学习需求\n{learning_need}")

        # 2. learning_scenario
        scenario = self._get_learning_scenario(state)
        if scenario:
            parts.append(f"## 学习场景\n{scenario}")

        # 3. learner_profile 简要字段
        profile_brief = self._get_profile_brief(state)
        if profile_brief:
            parts.append(f"## 学习者画像摘要\n{profile_brief}")

        # 4. agent_config (ContentAgentConfig)
        agent_config = self._get_agent_config(state)
        if agent_config:
            config_text = self._format_content_config(agent_config)
            parts.append(f"## Agent 配置\n{config_text}")

        # 5. personalized_constraints
        constraints = self._get_personalized_constraints(state)
        if constraints:
            parts.append(f"## 个性化约束\n{constraints}")

        return "\n\n".join(parts)

    def _for_mindmap(self, state: Any) -> str:
        """MindmapAgent 需要学习需求、配置和 content.summary_data。"""
        parts: list[str] = []

        learning_need = self._get_learning_need(state)
        if learning_need:
            parts.append(f"## 学习需求\n{learning_need}")

        scenario = self._get_learning_scenario(state)
        if scenario:
            parts.append(f"## 学习场景\n{scenario}")

        agent_config = self._get_agent_config(state)
        if agent_config:
            config_text = self._format_mindmap_config(agent_config)
            parts.append(f"## Agent 配置\n{config_text}")

        # content.summary_data
        summary_data = self._get_upstream_summary(state, self.CONTENT)
        if summary_data:
            parts.append(f"## 内容摘要\n{summary_data}")

        return "\n\n".join(parts)

    def _for_diagram(self, state: Any) -> str:
        """DiagramAgent 需要学习需求、配置和 content.summary_data。"""
        parts: list[str] = []

        learning_need = self._get_learning_need(state)
        if learning_need:
            parts.append(f"## 学习需求\n{learning_need}")

        scenario = self._get_learning_scenario(state)
        if scenario:
            parts.append(f"## 学习场景\n{scenario}")

        agent_config = self._get_agent_config(state)
        if agent_config:
            config_text = self._format_diagram_config(agent_config)
            parts.append(f"## Agent 配置\n{config_text}")

        # content.summary_data
        summary_data = self._get_upstream_summary(state, self.CONTENT)
        if summary_data:
            parts.append(f"## 内容摘要\n{summary_data}")

        return "\n\n".join(parts)

    def _for_code(self, state: Any) -> str:
        """CodeAgent 需要学习需求、配置和 content.summary_data。"""
        parts: list[str] = []

        learning_need = self._get_learning_need(state)
        if learning_need:
            parts.append(f"## 学习需求\n{learning_need}")

        scenario = self._get_learning_scenario(state)
        if scenario:
            parts.append(f"## 学习场景\n{scenario}")

        agent_config = self._get_agent_config(state)
        if agent_config:
            config_text = self._format_code_config(agent_config)
            parts.append(f"## Agent 配置\n{config_text}")

        # content.summary_data
        summary_data = self._get_upstream_summary(state, self.CONTENT)
        if summary_data:
            parts.append(f"## 内容摘要\n{summary_data}")

        return "\n\n".join(parts)

    def _for_quiz(self, state: Any) -> str:
        """QuizAgent 需要学习需求、配置、上游摘要和薄弱点信息。"""
        parts: list[str] = []

        learning_need = self._get_learning_need(state)
        if learning_need:
            parts.append(f"## 学习需求\n{learning_need}")

        scenario = self._get_learning_scenario(state)
        if scenario:
            parts.append(f"## 学习场景\n{scenario}")

        agent_config = self._get_agent_config(state)
        if agent_config:
            config_text = self._format_quiz_config(agent_config)
            parts.append(f"## Agent 配置\n{config_text}")

        # content.summary_data
        content_summary = self._get_upstream_summary(state, self.CONTENT)
        if content_summary:
            parts.append(f"## 内容摘要\n{content_summary}")

        # code.summary_data
        code_summary = self._get_upstream_summary(state, self.CODE)
        if code_summary:
            parts.append(f"## 代码摘要\n{code_summary}")

        # learner_profile.weak_points
        weak_points = self._get_weak_points_brief(state)
        if weak_points:
            parts.append(f"## 薄弱点信息\n{weak_points}")

        return "\n\n".join(parts)

    def _for_reading(self, state: Any) -> str:
        """ReadingAgent 需要学习需求、配置和 content.summary_data。"""
        parts: list[str] = []

        learning_need = self._get_learning_need(state)
        if learning_need:
            parts.append(f"## 学习需求\n{learning_need}")

        scenario = self._get_learning_scenario(state)
        if scenario:
            parts.append(f"## 学习场景\n{scenario}")

        agent_config = self._get_agent_config(state)
        if agent_config:
            config_text = self._format_reading_config(agent_config)
            parts.append(f"## Agent 配置\n{config_text}")

        # content.summary_data
        summary_data = self._get_upstream_summary(state, self.CONTENT)
        if summary_data:
            parts.append(f"## 内容摘要\n{summary_data}")

        return "\n\n".join(parts)

    def _build_generic(self, state: Any) -> str:
        """通用简化上下文，用于未匹配的 Agent。"""
        parts: list[str] = []

        learning_need = self._get_learning_need(state)
        if learning_need:
            parts.append(f"## 学习需求\n{learning_need}")

        scenario = self._get_learning_scenario(state)
        if scenario:
            parts.append(f"## 学习场景\n{scenario}")

        agent_config = self._get_agent_config(state)
        if agent_config:
            config_text = self._format_generic_config(agent_config)
            parts.append(f"## Agent 配置\n{config_text}")

        return "\n\n".join(parts)

    # =========================================================================
    # 数据提取辅助方法
    # =========================================================================

    def _get_learning_need(self, state: Any) -> str:
        """从 state.task 中提取 learning_need。"""
        task = getattr(state, "task", {}) or {}
        return str(task.get("learning_need") or "").strip()

    def _get_learning_scenario(self, state: Any) -> str:
        """从 state 中提取 learning_scenario。"""
        scenario = getattr(state, "learning_scenario", "") or ""
        # 转换为中文描述
        scenario_map = {
            "exam_prep": "备考冲刺",
            "daily_review": "日常复习",
            "project_practice": "项目实战",
            "self_study": "自主学习",
        }
        return scenario_map.get(scenario, scenario)

    def _get_agent_config(self, state: Any) -> dict[str, Any]:
        """从 state 中提取 agent_config。"""
        return getattr(state, "agent_config", {}) or {}

    def _get_personalized_constraints(self, state: Any) -> str:
        """从 state 中提取 personalized_constraints。"""
        constraints = getattr(state, "personalized_constraints", []) or []
        if not constraints:
            return ""
        return "\n".join(f"- {c}" for c in constraints)

    def _get_profile_brief(self, state: Any) -> str:
        """提取学习者画像简要字段。"""
        learner_profile = getattr(state, "learner_profile", {}) or {}
        lines: list[str] = []

        # 优先从 profile_json 中提取
        profile_json = learner_profile.get("profile_json")
        if isinstance(profile_json, dict):
            for key, label in self._PROFILE_BRIEF_FIELDS:
                value = profile_json.get(key)
                if value:
                    lines.append(f"- {label}: {value}")
        else:
            # 直接从顶层字段提取
            for key, label in self._PROFILE_BRIEF_FIELDS:
                value = learner_profile.get(key)
                if value:
                    lines.append(f"- {label}: {value}")

        return "\n".join(lines)

    def _get_weak_points_brief(self, state: Any) -> str:
        """提取学习者画像中的薄弱点信息。"""
        learner_profile = getattr(state, "learner_profile", {}) or {}
        lines: list[str] = []

        # 优先从 profile_json 中提取
        profile_json = learner_profile.get("profile_json")
        source = profile_json if isinstance(profile_json, dict) else learner_profile

        for field in self._WEAK_POINT_FIELDS:
            value = source.get(field)
            if value:
                if isinstance(value, list):
                    lines.append(f"- {field}: {', '.join(str(v) for v in value[:5])}")
                elif isinstance(value, dict):
                    keys = list(value.keys())[:5]
                    lines.append(f"- {field}: {', '.join(keys)}")
                else:
                    lines.append(f"- {field}: {str(value)[:100]}")

        return "\n".join(lines)

    def _get_upstream_summary(self, state: Any, agent_id: str) -> str:
        """从 upstream_results 中提取指定 agent 的摘要。优先使用 LLM 生成的 summary。"""
        upstream_results = getattr(state, "upstream_results", {}) or {}
        agent_result = upstream_results.get(agent_id)
        if not agent_result:
            return ""

        # 优先使用 LLM 生成的 summary（由 generate_summary_with_llm 生成）
        summary = agent_result.get("summary")
        if summary and isinstance(summary, str) and summary.strip():
            return summary.strip()[:500]

        # 其次使用 summary_data
        summary_data = agent_result.get("summary_data")
        if not summary_data:
            return ""

        # 格式化 summary_data
        if isinstance(summary_data, dict):
            # 提取关键信息
            key_fields = ["topic", "key_points", "principles", "main_points", "topics"]
            extracted: list[str] = []
            for field in key_fields:
                value = summary_data.get(field)
                if value:
                    if isinstance(value, list):
                        extracted.append(f"{field}: {', '.join(str(v) for v in value[:5])}")
                    elif isinstance(value, str):
                        extracted.append(f"{field}: {value[:100]}")
            return "\n".join(extracted) if extracted else str(summary_data)[:500]

        return str(summary_data)[:500]

    # =========================================================================
    # 配置格式化辅助方法
    # =========================================================================

    def _format_content_config(self, config: dict[str, Any]) -> str:
        """格式化 ContentAgentConfig。"""
        lines: list[str] = []
        fields = [
            ("structure", "结构类型"),
            ("include_common_mistakes", "包含常见错误"),
            ("include_examples", "包含示例"),
            ("focus_mode", "聚焦模式"),
            ("depth_level", "深度级别"),
        ]
        for key, label in fields:
            value = config.get(key)
            if value is not None:
                lines.append(f"- {label}: {value}")
        return "\n".join(lines)

    def _format_mindmap_config(self, config: dict[str, Any]) -> str:
        """格式化 MindmapAgentConfig。"""
        lines: list[str] = []
        fields = [
            ("map_type", "导图类型"),
            ("max_depth", "最大深度"),
            ("highlight_weak", "高亮短板"),
            ("expand_weak_points", "展开薄弱点"),
            ("include_prerequisites", "包含前置知识"),
        ]
        for key, label in fields:
            value = config.get(key)
            if value is not None:
                lines.append(f"- {label}: {value}")
        return "\n".join(lines)

    def _format_diagram_config(self, config: dict[str, Any]) -> str:
        """格式化 DiagramAgentConfig。"""
        lines: list[str] = []
        fields = [
            ("diagram_type", "图解类型"),
            ("visual_style", "视觉风格"),
            ("highlight_mode", "高亮模式"),
            ("detail_level", "细节级别"),
        ]
        for key, label in fields:
            value = config.get(key)
            if value is not None:
                lines.append(f"- {label}: {value}")
        return "\n".join(lines)

    def _format_code_config(self, config: dict[str, Any]) -> str:
        """格式化 CodeAgentConfig。"""
        lines: list[str] = []
        fields = [
            ("programming_language", "编程语言"),
            ("case_type", "案例类型"),
            ("comment_level", "注释级别"),
            ("include_test", "包含测试"),
            ("difficulty", "难度"),
        ]
        for key, label in fields:
            value = config.get(key)
            if value is not None:
                lines.append(f"- {label}: {value}")
        return "\n".join(lines)

    def _format_quiz_config(self, config: dict[str, Any]) -> str:
        """格式化 QuizAgentConfig。"""
        lines: list[str] = []
        fields = [
            ("question_count", "题目数量"),
            ("difficulty_mode", "难度模式"),
            ("weak_point_weight", "薄弱点权重"),
            ("exam_style", "考试风格"),
            ("include_analysis", "包含解析"),
        ]
        for key, label in fields:
            value = config.get(key)
            if value is not None:
                lines.append(f"- {label}: {value}")
        return "\n".join(lines)

    def _format_reading_config(self, config: dict[str, Any]) -> str:
        """格式化 ReadingAgentConfig。"""
        lines: list[str] = []
        fields = [
            ("reading_depth", "阅读深度"),
            ("max_items", "最大条目数"),
            ("resource_quality", "资源质量"),
            ("include_practice", "包含实践"),
            ("language_preference", "语言偏好"),
        ]
        for key, label in fields:
            value = config.get(key)
            if value is not None:
                lines.append(f"- {label}: {value}")
        return "\n".join(lines)

    def _format_generic_config(self, config: dict[str, Any]) -> str:
        """格式化通用配置。"""
        lines: list[str] = []
        for key, value in config.items():
            if value is not None:
                lines.append(f"- {key}: {value}")
        return "\n".join(lines)
