"""
资源生成模块工具函数集合。

整合了 prompt 加载、画像格式化、依赖展开、Agent 上下文构建等通用工具。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.infra.logging import get_logger
from app.utils.paths import RESOURCE_DIR

logger = get_logger(__name__)

# =============================================================================
# Agent 配置常量
# =============================================================================

CORE_AGENTS = ["content"]
STRUCTURE_AGENTS = ["diagram", "mindmap"]
PRACTICE_AGENTS = ["code", "quiz"]
EXTENSION_AGENTS = ["reading"]
ALL_AGENTS = CORE_AGENTS + STRUCTURE_AGENTS + PRACTICE_AGENTS + EXTENSION_AGENTS


# =============================================================================
# Prompt 加载与上下文构建
# =============================================================================

def load_prompt(agent_dir: Path) -> str:
    """加载 Agent 的 prompt.md 文件。"""
    prompt_path = agent_dir / "prompt.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"prompt 文件不存在: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def format_profile_fields(profile: dict[str, Any], fields: list[tuple[str, str]]) -> str:
    """格式化画像字段为 Markdown 列表。"""
    if not profile:
        return ""
    parts: list[str] = []
    for key, label in fields:
        value = profile.get(key)
        if value:
            parts.append(f"- {label}: {value}")
    return "\n".join(parts)


# =============================================================================
# 文件保存与工具加载
# =============================================================================

def save_resource_file(
    topic: str,
    content: str,
    user_id: int,
    resource_id: int,
    ext: str = "md",
    prefix: str | None = None,
    agent_type: str | None = None,
) -> str:
    """保存资源文件到统一路径: workplace/resource/{user_id}/{resource_id}/{agent_type}/{topic}.{ext}

    Args:
        topic: 主题名称（用于生成文件名）
        content: 文件内容
        user_id: 用户 ID
        resource_id: 资源 ID
        ext: 文件扩展名
        prefix: 可选文件名前缀，用于隔离不同 Agent 的产物
        agent_type: Agent 类型（如 content, mindmap, quiz 等），如果提供则保存到子目录

    Returns:
        文件路径
    """
    safe_topic = re.sub(r'[\\/*?:"<>|]', "", topic).strip()[:50]
    if not safe_topic:
        safe_topic = "untitled"

    if agent_type:
        target_dir = RESOURCE_DIR / str(user_id) / str(resource_id) / agent_type
    else:
        target_dir = RESOURCE_DIR / str(user_id) / str(resource_id)
    target_dir.mkdir(parents=True, exist_ok=True)

    safe_prefix = re.sub(r'[\\/*?:"<>|]', "", prefix or "").strip()
    filename = f"{safe_prefix}_{safe_topic}.{ext}" if safe_prefix else f"{safe_topic}.{ext}"
    filepath = target_dir / filename

    filepath.write_text(content, encoding="utf-8")
    return str(filepath)


# =============================================================================
# 画像加载
# =============================================================================

_memory_layer = None


def _get_memory_layer():
    """获取 MemoryLayer 单例。"""
    global _memory_layer
    if _memory_layer is None:
        from app.memory import MemoryLayer
        _memory_layer = MemoryLayer(module="mentor")
    return _memory_layer


async def load_user_profile(user_id: int) -> dict:
    """加载用户基础信息和画像。

    Returns:
        包含 user_data 和 profile_data 的字典，用于构建 Agent 上下文。
    """
    from sqlmodel.ext.asyncio.session import AsyncSession
    from app.infra.database import engine
    from app.infra.models import User

    # 加载用户基础信息
    user_data = {"user_id": user_id}
    async with AsyncSession(engine) as session:
        user = await session.get(User, user_id)
        if user:
            user_data = {
                "user_id": user.id,
                "username": user.username,
            }
            logger.info("[Profile] 已读取用户基础信息: user_id=%s", user_id)

    # 加载画像
    profile_data = {}
    profile = await _get_memory_layer().get_profile(user_id=user_id)
    if profile:
        profile_data = profile.model_dump(exclude_none=True)
        updated_at = profile_data.get("updated_at")
        if updated_at is not None:
            profile_data["updated_at"] = updated_at.isoformat()

        # 从 profile_json.student_profile 提取 major/grade/school
        profile_json = profile_data.get("profile_json") or {}
        student_profile = profile_json.get("student_profile") or {}
        if student_profile:
            user_data["major"] = student_profile.get("major")
            user_data["grade"] = student_profile.get("grade")
            user_data["school"] = student_profile.get("school")

        logger.info("[Profile] 已读取用户画像: user_id=%s fields=%s", user_id, list(profile_data.keys()))

    return {"user_data": user_data, "profile_data": profile_data}


async def load_profile_snapshot(user_id: int) -> dict:
    """加载用户画像快照，返回原始字典数据。"""
    return await load_user_profile(user_id)


def _parse_profile(profile) -> dict[str, str]:
    """从 JSON 画像中提取资源生成需要的关键信息。"""
    result: dict[str, str] = {}
    if not profile:
        return result

    if hasattr(profile, "profile_json") and profile.profile_json and profile.profile_json.get("dimensions"):
        dimensions = profile.profile_json.get("dimensions", {})
        student_profile = profile.profile_json.get("student_profile") or {}
        result["技术能力判断"] = dimensions.get("knowledge_foundation", {}).get("summary") or ""
        result["当前学习/项目背景"] = dimensions.get("learning_goal", {}).get("summary") or ""
        result["学习偏好"] = dimensions.get("interaction_preference", {}).get("summary") or ""
        result["当前薄弱点"] = dimensions.get("weakness_points", {}).get("summary") or ""
        result["兴趣方向"] = ""
        interests = student_profile.get("current_focus", [])
        if isinstance(interests, list):
            result["兴趣方向"] = ", ".join(interests)
        strategies = profile.profile_json.get("recommended_strategy", [])
        if isinstance(strategies, list):
            result["推荐辅导策略"] = "\n".join(strategies)
    return result


def format_profile_json_for_prompt(profile_json: dict[str, Any] | None) -> str:
    """Format JSON-first learner profile for prompts without Markdown conversion."""
    if not profile_json:
        return ""
    payload = dict(profile_json)
    return json.dumps(payload, ensure_ascii=False, indent=2)


# =============================================================================
# Markdown 提取与规范化
# =============================================================================

_MARKDOWN_FENCE_RE = re.compile(r"```(?:markdown|md)?\s*\n(.*?)\n```", re.DOTALL | re.IGNORECASE)


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


def extract_markdown_from_llm_output(content: str) -> str:
    """从 LLM 输出中提取 Markdown 内容。

    LLM 可能将输出包裹在 ```markdown ... ``` 围栏中，或返回原始
    markdown。此函数剥离围栏并规范化缩进。
    """
    raw = (content or "").strip()
    if not raw:
        return ""

    match = _MARKDOWN_FENCE_RE.search(raw)
    if match:
        raw = match.group(1).strip()

    return _normalize_markdown_indent(raw)


# =============================================================================
# Task 字段辅助
# =============================================================================


def learning_need_from_task(task: dict) -> str:
    """从 task 字典中返回 learning_need 字符串。

    当 learning_need 不存在时回退到 task.get("topic") 或 "未知学习需求"。
    """
    return str(task.get("learning_need") or task.get("topic") or "未知学习需求").strip() or "未知学习需求"


def title_from_learning_need(task: dict[str, Any], suffix: str, *, max_chars: int = 32) -> str:
    """从 task 的 learning_need 和 suffix 构建资源标题。"""
    need = learning_need_from_task(task)
    if len(need) > max_chars:
        need = f"{need[:max_chars]}..."
    return f"{need} - {suffix}"


# =============================================================================
# 依赖 / 上游结果格式化
# =============================================================================


def format_dependency_reports_for_prompt(dependency_reports: list[dict] | None) -> str:
    """将依赖报告列表格式化为 prompt 可读的文本块。"""
    if not dependency_reports:
        return ""

    parts: list[str] = []
    for i, dep in enumerate(dependency_reports, 1):
        agent = dep.get("agent_name", f"dep-{i}")
        status = dep.get("status", "unknown")
        summary = dep.get("summary", "")
        parts.append(f"### 依赖 {i}: {agent} (状态: {status})")
        if summary:
            parts.append(summary)
    return "\n\n".join(parts)


def format_upstream_results_for_prompt(upstream_results: list[dict] | None) -> str:
    """将上游结果列表格式化为 prompt 可读的文本块。"""
    if not upstream_results:
        return ""

    parts: list[str] = []
    for i, res in enumerate(upstream_results, 1):
        agent = res.get("agent_name", f"upstream-{i}")
        status = res.get("status", "unknown")
        md = res.get("markdown", res.get("content", ""))
        parts.append(f"### 上游 {i}: {agent} (状态: {status})")
        if md:
            parts.append(md)
    return "\n\n".join(parts)


# =============================================================================
# 画像格式化 (用于 prompt)
# =============================================================================


def format_learner_profile_for_prompt(learner_profile: dict[str, Any] | None) -> str:
    """将学习者画像字典渲染为 prompt 可读的文本块。"""
    if not learner_profile:
        return ""

    profile_json = learner_profile.get("profile_json")
    profile_data = learner_profile.get("profile_data")
    if not isinstance(profile_json, dict) and isinstance(profile_data, dict):
        profile_json = profile_data.get("profile_json")
    if isinstance(profile_json, dict):
        return json.dumps(profile_json, ensure_ascii=False, indent=2)

    user_data = learner_profile.get("user_data")
    lines: list[str] = []
    if isinstance(user_data, dict):
        for key, label in (
            ("major", "专业"),
            ("grade", "年级"),
            ("school", "学校"),
            ("username", "用户名"),
        ):
            value = user_data.get(key)
            if value:
                lines.append(f"- {label}: {value}")
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


# =============================================================================
# 后端上下文构建
# =============================================================================


def append_backend_context_for_prompt(parts: list[str], state) -> None:
    """将后端提供的上下文（画像、依赖）追加到 prompt parts 列表。

    *parts* 会被就地修改。适配新 WorkerState（profile / dependencies）。
    """
    # 画像上下文
    profile = getattr(state, "profile", None) or (
        state.task.get("profile") if isinstance(getattr(state, "task", None), dict) else None
    )
    if profile:
        profile_text = format_learner_profile_for_prompt(profile)
        if profile_text:
            parts.extend(["", "## 学习者画像", profile_text])

    # 依赖 / 上游上下文
    deps = getattr(state, "dependencies", None) or []
    if deps:
        dep_text = format_upstream_results_for_prompt(deps)
        if dep_text:
            parts.extend(["", "## 依赖资源", dep_text])

    outline = getattr(state, "outline", None)
    if outline:
        parts.extend(["", "## 内容大纲", str(outline)])


# =============================================================================
# LLM 摘要生成
# =============================================================================


async def generate_summary_with_llm(markdown: str, learning_need: str = "") -> str:
    """使用 LLM 为学习资源生成文本摘要。"""
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
            "spark_x",
            [HumanMessage(content=prompt)],
            model_kwargs={"temperature": 0.3},
        )
        summary = response.content if hasattr(response, "content") else str(response)
        return summary.strip()
    except Exception:
        return ""


def _build_content_summary_data_local(markdown: str, learning_need: str = "") -> dict[str, Any]:
    """从 ContentAgent Markdown 输出中本地提取结构化摘要（不调用 LLM）。"""
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


async def build_content_summary_data_with_llm(markdown: str, llm_manager=None, learning_need: str = "") -> dict[str, Any]:
    """用 LLM 提取 ContentAgent 的结构化交接摘要，失败时回退到本地解析。

    Args:
        markdown: 资源 markdown 内容。
        llm_manager: LLM 管理器实例（可选，默认通过 get_llm_manager 获取）。
        learning_need: 学习需求描述（可选）。
    """
    from langchain_core.messages import HumanMessage
    from app.infra.llm import get_llm_manager
    from app.utils.json import parse_first_json_object

    fallback = _build_content_summary_data_local(markdown, learning_need)
    if not markdown or not markdown.strip():
        return fallback

    manager = llm_manager or get_llm_manager()

    prompt = f"""请从课程讲解中提取供下游多智能体协作使用的结构化摘要。
只输出严格 JSON，不要 Markdown 或解释文本。

JSON 字段：
{{
  "topic": "主题",
  "course": "课程名或空字符串",
  "key_points": ["核心知识点"],
  "principles": ["核心原理"],
  "weak_points": ["薄弱点或难点"],
  "common_mistakes": ["常见误区"],
  "examples": ["示例或案例"],
  "learning_suggestions": ["学习建议"]
}}

学习需求：{learning_need[:160]}

课程讲解：
{markdown[:4500]}"""

    try:
        response = await manager.ainvoke(
            "spark_max",
            [HumanMessage(content=prompt)],
            model_kwargs={"temperature": 0.1},
        )
        content = response.content if hasattr(response, "content") else str(response)
        parsed = parse_first_json_object(content)
    except Exception:
        return fallback

    result = dict(fallback)
    for key in (
        "topic",
        "course",
        "key_points",
        "principles",
        "weak_points",
        "common_mistakes",
        "examples",
        "learning_suggestions",
    ):
        value = parsed.get(key)
        if isinstance(value, list):
            cleaned = [str(item).strip() for item in value if str(item).strip()]
            result[key] = cleaned[:8]
        elif isinstance(value, str) and value.strip():
            result[key] = value.strip()[:160] if key in {"topic", "course"} else [value.strip()[:160]]
    return result


# =============================================================================
# AgentContextBuilder — 按 Agent 类型裁剪上下文
# =============================================================================


class AgentContextBuilder:
    """按 Agent 类型裁剪上下文，避免 prompt token 过长。

    AgentContextBuilder 使用示例：
        builder = AgentContextBuilder()
        context = builder.build_for_agent("content", state)
        # context 包含：learning_need, learning_scenario, profile 简要字段,
        #              agent_config, outline 等
    """

    # Agent ID 常量
    CONTENT = "content"
    MINDMAP = "mindmap"
    DIAGRAM = "diagram"
    CODE = "code"
    QUIZ = "quiz"
    READING = "reading"

    # 学习者画像简要字段
    _PROFILE_BRIEF_FIELDS = [
        ("major", "专业"),
        ("grade", "年级"),
        ("school", "学校"),
        ("current_focus", "当前关注"),
        ("learning_style", "学习偏好"),
    ]

    _PROFILE_DIMENSION_FIELDS = [
        "knowledge_foundation",
        "learning_goal",
        "weakness_points",
        "interaction_preference",
        "cognitive_style",
        "motivation",
    ]

    _WEAK_POINT_FIELDS = ["weak_points", "knowledge_gaps", "struggling_topics"]

    def build_for_agent(self, agent_id: str, state: Any) -> str:
        """构建指定 Agent 的上下文字符串。

        Args:
            agent_id: Agent ID（content/mindmap/diagram/code/quiz/reading）
            state: WorkerState 实例，包含 profile、agent_config、dependencies 等

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
            return self._build_generic(state)
        return builder(state)

    # ------------------------------------------------------------------
    # 各 Agent 专用上下文
    # ------------------------------------------------------------------

    def _for_content(self, state: Any) -> str:
        """ContentAgent 需要完整画像信息。"""
        parts: list[str] = []

        learning_need = self._get_learning_need(state)
        if learning_need:
            parts.append(f"## 学习需求\n{learning_need}")

        scenario = self._get_learning_scenario(state)
        if scenario:
            parts.append(f"## 学习场景\n{scenario}")

        profile_brief = self._get_profile_brief(state)
        if profile_brief:
            parts.append(f"## 学习者画像摘要\n{profile_brief}")

        agent_config = self._get_agent_config(state)
        if agent_config:
            config_text = self._format_config(agent_config, [
                ("structure", "结构类型"),
                ("include_common_mistakes", "包含常见错误"),
                ("include_examples", "包含示例"),
                ("focus_mode", "聚焦模式"),
                ("depth_level", "深度级别"),
            ])
            parts.append(f"## Agent 配置\n{config_text}")

        constraints = self._get_personalized_constraints(state)
        if constraints:
            parts.append(f"## 个性化约束\n{constraints}")

        return "\n\n".join(parts)

    def _for_mindmap(self, state: Any) -> str:
        """MindmapAgent 需要学习需求、配置和上游摘要。"""
        parts: list[str] = []

        learning_need = self._get_learning_need(state)
        if learning_need:
            parts.append(f"## 学习需求\n{learning_need}")

        scenario = self._get_learning_scenario(state)
        if scenario:
            parts.append(f"## 学习场景\n{scenario}")

        profile_brief = self._get_profile_brief(state)
        if profile_brief:
            parts.append(f"## 学习者画像摘要\n{profile_brief}")

        agent_config = self._get_agent_config(state)
        if agent_config:
            config_text = self._format_config(agent_config, [
                ("map_type", "导图类型"),
                ("max_depth", "最大深度"),
                ("highlight_weak", "高亮短板"),
                ("expand_weak_points", "展开薄弱点"),
                ("include_prerequisites", "包含前置知识"),
            ])
            parts.append(f"## Agent 配置\n{config_text}")

        summary_data = self._get_upstream_summary(state, self.CONTENT)
        if summary_data:
            parts.append(f"## 内容摘要\n{summary_data}")

        return "\n\n".join(parts)

    def _for_diagram(self, state: Any) -> str:
        """DiagramAgent 需要学习需求、配置和上游摘要。"""
        parts: list[str] = []

        learning_need = self._get_learning_need(state)
        if learning_need:
            parts.append(f"## 学习需求\n{learning_need}")

        scenario = self._get_learning_scenario(state)
        if scenario:
            parts.append(f"## 学习场景\n{scenario}")

        profile_brief = self._get_profile_brief(state)
        if profile_brief:
            parts.append(f"## 学习者画像摘要\n{profile_brief}")

        agent_config = self._get_agent_config(state)
        if agent_config:
            config_text = self._format_config(agent_config, [
                ("diagram_type", "图解类型"),
                ("visual_style", "视觉风格"),
                ("highlight_mode", "高亮模式"),
                ("detail_level", "细节级别"),
            ])
            parts.append(f"## Agent 配置\n{config_text}")

        summary_data = self._get_upstream_summary(state, self.CONTENT)
        if summary_data:
            parts.append(f"## 内容摘要\n{summary_data}")

        return "\n\n".join(parts)

    def _for_code(self, state: Any) -> str:
        """CodeAgent 需要学习需求、配置和上游摘要。"""
        parts: list[str] = []

        learning_need = self._get_learning_need(state)
        if learning_need:
            parts.append(f"## 学习需求\n{learning_need}")

        scenario = self._get_learning_scenario(state)
        if scenario:
            parts.append(f"## 学习场景\n{scenario}")

        profile_brief = self._get_profile_brief(state)
        if profile_brief:
            parts.append(f"## 学习者画像摘要\n{profile_brief}")

        agent_config = self._get_agent_config(state)
        if agent_config:
            config_text = self._format_config(agent_config, [
                ("programming_language", "编程语言"),
                ("case_type", "案例类型"),
                ("comment_level", "注释级别"),
                ("include_test", "包含测试"),
                ("difficulty", "难度"),
            ])
            parts.append(f"## Agent 配置\n{config_text}")

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

        profile_brief = self._get_profile_brief(state)
        if profile_brief:
            parts.append(f"## 学习者画像摘要\n{profile_brief}")

        agent_config = self._get_agent_config(state)
        if agent_config:
            config_text = self._format_config(agent_config, [
                ("question_count", "题目数量"),
                ("difficulty_mode", "难度模式"),
                ("weak_point_weight", "薄弱点权重"),
                ("exam_style", "考试风格"),
                ("include_analysis", "包含解析"),
                ("question_types", "题型偏好"),
            ])
            parts.append(f"## Agent 配置\n{config_text}")

        content_summary = self._get_upstream_summary(state, self.CONTENT)
        if content_summary:
            parts.append(f"## 内容摘要\n{content_summary}")

        code_summary = self._get_upstream_summary(state, self.CODE)
        if code_summary:
            parts.append(f"## 代码摘要\n{code_summary}")

        weak_points = self._get_weak_points_brief(state)
        if weak_points:
            parts.append(f"## 薄弱点信息\n{weak_points}")

        return "\n\n".join(parts)

    def _for_reading(self, state: Any) -> str:
        """ReadingAgent 需要学习需求、配置和上游摘要。"""
        parts: list[str] = []

        learning_need = self._get_learning_need(state)
        if learning_need:
            parts.append(f"## 学习需求\n{learning_need}")

        scenario = self._get_learning_scenario(state)
        if scenario:
            parts.append(f"## 学习场景\n{scenario}")

        profile_brief = self._get_profile_brief(state)
        if profile_brief:
            parts.append(f"## 学习者画像摘要\n{profile_brief}")

        agent_config = self._get_agent_config(state)
        if agent_config:
            config_text = self._format_config(agent_config, [
                ("reading_depth", "阅读深度"),
                ("max_items", "最大条目数"),
                ("resource_quality", "资源质量"),
                ("include_practice", "包含实践"),
                ("language_preference", "语言偏好"),
            ])
            parts.append(f"## Agent 配置\n{config_text}")

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

    # ------------------------------------------------------------------
    # 数据提取辅助方法
    # ------------------------------------------------------------------

    def _get_learning_need(self, state: Any) -> str:
        """从 state.task 中提取 learning_need。"""
        task = getattr(state, "task", {}) or {}
        return str(task.get("learning_need") or "").strip()

    def _get_learning_scenario(self, state: Any) -> str:
        """从 state 中提取 learning_scenario 并转换为中文描述。"""
        scenario = getattr(state, "learning_scenario", "") or ""
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
        profile = getattr(state, "profile", None) or {}
        lines: list[str] = []

        user_data = profile.get("user_data") if isinstance(profile, dict) else None
        if isinstance(user_data, dict):
            for key, label in self._PROFILE_BRIEF_FIELDS:
                value = user_data.get(key)
                if value:
                    lines.append(f"- {label}: {value}")

        profile_data = profile.get("profile_data") if isinstance(profile, dict) else None
        # 优先从 profile_json 中提取，兼容 load_user_profile 返回的 profile_data.profile_json
        profile_json = profile.get("profile_json") if isinstance(profile, dict) else None
        if not isinstance(profile_json, dict) and isinstance(profile_data, dict):
            profile_json = profile_data.get("profile_json")
        if isinstance(profile_json, dict):
            student_profile = profile_json.get("student_profile")
            if isinstance(student_profile, dict):
                for key, label in self._PROFILE_BRIEF_FIELDS:
                    value = student_profile.get(key)
                    if value:
                        line = f"- {label}: {value}"
                        if line not in lines:
                            lines.append(line)
            for key, label in self._PROFILE_BRIEF_FIELDS:
                value = profile_json.get(key)
                if value:
                    line = f"- {label}: {value}"
                    if line not in lines:
                        lines.append(line)
            dimensions = profile_json.get("dimensions")
            if isinstance(dimensions, dict):
                for key in self._PROFILE_DIMENSION_FIELDS:
                    value = dimensions.get(key)
                    if isinstance(value, dict) and value.get("summary"):
                        lines.append(f"- {key}: {value['summary']}")
        else:
            # 直接从顶层字段提取
            for key, label in self._PROFILE_BRIEF_FIELDS:
                value = profile.get(key)
                if value:
                    lines.append(f"- {label}: {value}")
            dimensions = profile.get("dimensions")
            if isinstance(dimensions, dict):
                for key in self._PROFILE_DIMENSION_FIELDS:
                    value = dimensions.get(key)
                    if isinstance(value, dict) and value.get("summary"):
                        lines.append(f"- {key}: {value['summary']}")

        return "\n".join(lines)

    def _get_weak_points_brief(self, state: Any) -> str:
        """提取学习者画像中的薄弱点信息。"""
        profile = getattr(state, "profile", None) or {}
        lines: list[str] = []

        profile_data = profile.get("profile_data") if isinstance(profile, dict) else None
        profile_json = profile.get("profile_json") if isinstance(profile, dict) else None
        if not isinstance(profile_json, dict) and isinstance(profile_data, dict):
            profile_json = profile_data.get("profile_json")
        source = profile_json if isinstance(profile_json, dict) else profile

        dimensions = source.get("dimensions") if isinstance(source, dict) else None
        if isinstance(dimensions, dict):
            weakness = dimensions.get("weakness_points")
            if isinstance(weakness, dict):
                summary = weakness.get("summary")
                if summary:
                    lines.append(f"- weakness_points: {str(summary)[:200]}")
                details = weakness.get("details")
                if isinstance(details, list) and details:
                    lines.append(f"- weakness_details: {', '.join(str(item) for item in details[:5])}")

        if isinstance(source, dict):
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
        """从 dependencies 中提取指定 agent 的摘要。"""
        deps = getattr(state, "dependencies", None) or []
        if not deps:
            return ""

        # 在 dependencies 列表中查找匹配 agent_name 的项
        agent_result = None
        for dep in deps:
            metadata = dep.get("metadata")
            metadata_agent_id = metadata.get("agent_id") if isinstance(metadata, dict) else None
            if dep.get("agent_name") == agent_id or dep.get("agent_id") == agent_id or metadata_agent_id == agent_id:
                agent_result = dep
                break
        if not agent_result:
            return ""

        # 优先使用 summary_data
        summary_data = agent_result.get("summary_data")
        if isinstance(summary_data, dict) and summary_data:
            return json.dumps(summary_data, ensure_ascii=False, indent=2)[:1400]

        # 其次使用 summary
        summary = agent_result.get("summary")
        if summary and isinstance(summary, str) and summary.strip():
            return summary.strip()[:500]

        return ""

    # ------------------------------------------------------------------
    # 配置格式化辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _format_config(config: dict[str, Any], fields: list[tuple[str, str]]) -> str:
        """格式化 Agent 配置。"""
        lines: list[str] = []
        for key, label in fields:
            value = config.get(key)
            if value is not None:
                lines.append(f"- {label}: {value}")
        return "\n".join(lines)

    @staticmethod
    def _format_generic_config(config: dict[str, Any]) -> str:
        """格式化通用配置。"""
        lines: list[str] = []
        for key, value in config.items():
            if value is not None:
                lines.append(f"- {key}: {value}")
        return "\n".join(lines)
