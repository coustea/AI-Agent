"""
资源生成 Agent 注册中心。

统一管理：
- Agent 元数据
- Agent 类映射
- Agent 层级关系
- Agent 依赖关系
- Agent 输出格式
- Agent 规划提示信息
- Agent 查询工具函数
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Type

from app.infra.logging import get_logger
from app.resource.worker_agents import (
    CodeAgent,
    ContentAgent,
    DiagramAgent,
    MindmapAgent,
    QuizAgent,
    ReadingAgent,
)

logger = get_logger(__name__)


# =============================================================================
# Agent 元数据统一配置
# =============================================================================

AGENT_META: dict[str, dict[str, Any]] = {
    "content": {
        "name": "课程讲解文档",
        "role": "ContentAgent",
        "display_name": "课程讲解智能体",
        "layer": 0,
        "stage": "concept_understanding",
        "stage_name": "认知建构层",
        "format": "markdown",
        "resource_type": "content",
        "difficulty": "basic",
        "estimated_time": 8,
        "priority": 0,
        "description": "生成系统化课程讲解文档，是后续代码、练习、阅读资源的知识基础。",
        "best_for": ["概念讲解", "原理说明", "知识点梳理", "易错点解释"],
        "objectives": ["理解核心概念", "掌握关键知识点"],
        "output": {"format": "markdown", "must_include": ["title", "key_points", "examples"]},
        "config_keys": ["structure", "include_common_mistakes", "include_examples"],
        "planning_hint": "如果用户需要系统学习某个知识点，content 通常应作为基础资源优先执行。",
        "planning_reason": "建立概念理解基础",
    },
    "mindmap": {
        "name": "思维导图",
        "role": "MindmapAgent",
        "display_name": "思维导图智能体",
        "layer": 0,
        "stage": "knowledge_structure",
        "stage_name": "认知建构层",
        "format": "markdown",
        "resource_type": "mindmap",
        "difficulty": "basic",
        "estimated_time": 5,
        "priority": 1,
        "description": "把主题拆解成结构化知识树，帮助学习者快速建立整体框架。",
        "best_for": ["知识结构梳理", "层级关系整理", "复习提纲"],
        "objectives": ["建立知识结构", "识别知识点关系"],
        "output": {"format": "markdown", "must_include": ["central_topic", "branches"]},
        "config_keys": ["map_type", "max_depth", "highlight_weak"],
        "planning_hint": "mindmap 可独立并发生成，用于快速形成主题结构，不默认等待 content。",
        "planning_reason": "快速梳理知识结构",
    },
    "diagram": {
        "name": "知识图解",
        "role": "DiagramAgent",
        "display_name": "知识图解智能体",
        "layer": 0,
        "stage": "visual_understanding",
        "stage_name": "认知建构层",
        "format": "mermaid",
        "resource_type": "diagram",
        "difficulty": "basic",
        "estimated_time": 5,
        "priority": 2,
        "description": "生成 Mermaid 图解，用流程、关系或状态变化帮助理解抽象知识。",
        "best_for": ["流程图", "关系图", "状态变化", "对比结构"],
        "objectives": ["通过图示理解过程和关系"],
        "output": {"format": "mermaid", "must_include": ["source", "description"]},
        "config_keys": ["diagram_type", "visual_style"],
        "planning_hint": "diagram 适合依赖 content 的关键原理摘要，以保证图解与讲解一致。",
        "planning_reason": "通过图解强化结构理解",
    },
    "quiz": {
        "name": "练习题",
        "role": "QuizAgent",
        "display_name": "练习题智能体",
        "layer": 2,
        "stage": "assessment",
        "stage_name": "检测巩固层",
        "format": "json",
        "resource_type": "quiz",
        "difficulty": "medium",
        "estimated_time": 15,
        "priority": 4,
        "description": "围绕核心知识点、薄弱点和常见误区生成练习题与解析。",
        "best_for": ["掌握度检测", "易错点巩固", "考试复习"],
        "objectives": ["检测理解程度", "巩固易错点"],
        "output": {"format": "json", "must_include": ["questions", "answers", "analysis"]},
        "config_keys": ["question_count", "difficulty_mode"],
        "planning_hint": "quiz 应优先依赖 content 的 key_points、weak_points 和 common_mistakes。",
        "planning_reason": "通过测验检验掌握度",
    },
    "reading": {
        "name": "拓展阅读推荐",
        "role": "ReadingAgent",
        "display_name": "拓展阅读智能体",
        "layer": 1,
        "stage": "extension",
        "stage_name": "实践拓展层",
        "format": "json",
        "resource_type": "reading",
        "difficulty": "extended",
        "estimated_time": 20,
        "priority": 5,
        "description": "基于学习主题推荐进一步阅读路径和资料，补充背景与应用场景。",
        "best_for": ["延伸学习", "资料推荐", "学习路径补充"],
        "objectives": ["拓展相关背景", "连接更多应用场景"],
        "output": {"format": "json", "must_include": ["items", "reason"]},
        "config_keys": ["reading_depth", "max_items"],
        "planning_hint": "reading 适合依赖 content 的主题摘要，推荐方向应服务当前学习目标。",
        "planning_reason": "补充延展学习材料",
    },
    "code": {
        "name": "代码实操案例",
        "role": "CodeAgent",
        "display_name": "代码实操智能体",
        "layer": 1,
        "stage": "practice",
        "stage_name": "实践拓展层",
        "format": "json",
        "resource_type": "code",
        "difficulty": "medium",
        "estimated_time": 12,
        "priority": 3,
        "description": "生成可运行代码案例、讲解和练习，把抽象概念落到实践操作。",
        "best_for": ["代码示例", "实践演示", "调试练习"],
        "objectives": ["通过实践验证概念", "掌握可运行案例"],
        "output": {"format": "json", "must_include": ["title", "language", "code", "explanation", "run_steps", "exercises"]},
        "config_keys": ["programming_language", "case_type"],
        "planning_hint": "code 应依赖 content 的 examples、key_points 和 principles，避免脱离讲解主题。",
        "planning_reason": "通过实操加深掌握",
    },
}


# =============================================================================
# Agent 依赖关系
# =============================================================================

DEPENDS: dict[str, list[str]] = {
    "content": [],
    "mindmap": [],
    "diagram": ["content"],
    "code": ["content"],
    "reading": ["content"],
    "quiz": ["content"],
}


# =============================================================================
# Agent 类映射
# =============================================================================

AGENT_CLASSES: dict[str, Type[Any]] = {
    "content": ContentAgent,
    "mindmap": MindmapAgent,
    "diagram": DiagramAgent,
    "quiz": QuizAgent,
    "reading": ReadingAgent,
    "code": CodeAgent,
}


# =============================================================================
# 层级配置
# =============================================================================

LAYER_AGENTS: dict[int, list[str]] = {
    0: ["content", "mindmap", "diagram"],
    1: ["code", "reading"],
    2: ["quiz"],
}

LAYER_NAMES: dict[int, str] = {
    0: "认知建构层",
    1: "实践拓展层",
    2: "检测巩固层",
}

LAYER_STAGES: dict[int, str] = {
    0: "layer_0",
    1: "layer_1",
    2: "layer_2",
}


# =============================================================================
# 学习路径与并发配置
# =============================================================================

RESOURCE_ORDER: list[str] = ["content", "mindmap", "diagram", "code", "quiz", "reading"]

ESTIMATED_MINUTES: dict[str, int] = {
    "content": 8,
    "diagram": 5,
    "mindmap": 5,
    "code": 12,
    "quiz": 15,
    "reading": 20,
}

MAX_PARALLEL = 3

AGENT_ALIASES: dict[str, str | None] = {
    "image": "diagram",
    "chart": "diagram",
    "flowchart": "diagram",
    "ppt": None,
    "video": None,
}


@dataclass
class AgentEntry:
    """Agent 注册条目。"""
    id: str
    name: str
    role: str
    description: str
    agent_class: Type[Any]
    dependencies: list[str] = field(default_factory=list)
    execution_layer: int = 0
    resource_type: str = ""
    output_format: str = "json"
    estimated_time: int = 10
    priority: int = 99
    objectives: list[str] = field(default_factory=list)


_initialized = False
_registry: dict[str, AgentEntry] = {}


def ensure_initialized() -> None:
    """确保注册表已初始化。"""
    global _initialized, _registry
    if _initialized:
        return

    _registry = {}
    for agent_id, meta in AGENT_META.items():
        agent_class = AGENT_CLASSES.get(agent_id)
        if agent_class is None:
            continue

        _registry[agent_id] = AgentEntry(
            id=agent_id,
            name=meta.get("display_name") or meta.get("name", agent_id),
            role=meta.get("role", f"{agent_id.capitalize()}Agent"),
            description=meta.get("description") or meta.get("name", agent_id),
            agent_class=agent_class,
            dependencies=DEPENDS.get(agent_id, []),
            execution_layer=int(meta.get("layer", 0)),
            resource_type=meta.get("resource_type", agent_id),
            output_format=meta.get("format", "json"),
            estimated_time=int(meta.get("estimated_time", 10)),
            priority=int(meta.get("priority", 99)),
            objectives=[str(item) for item in meta.get("objectives", [])],
        )

    _initialized = True
    logger.info("[Registry] Agent 注册完成: %s", list(_registry.keys()))


def get_agent_entry(agent_id: str) -> AgentEntry | None:
    """获取指定 Agent 的注册信息。"""
    ensure_initialized()
    return _registry.get(resolve_agent_id(agent_id) or agent_id)


def get_enabled_agent_ids() -> list[str]:
    """获取启用的 Agent ID 列表。"""
    return [agent_id for agent_id in AGENT_META if agent_id in AGENT_CLASSES]


def get_agent_registry() -> dict[str, AgentEntry]:
    """获取所有已注册的 Agent。"""
    ensure_initialized()
    return _registry.copy()


def resolve_agent_id(agent_id: str | None) -> str | None:
    """解析前端或历史数据中的 Agent 别名。"""
    if not agent_id:
        return None
    normalized = str(agent_id).strip().lower()
    if normalized in AGENT_CLASSES:
        return normalized
    return AGENT_ALIASES.get(normalized)


def get_agent_planning_catalog(agent_ids: list[str]) -> dict[str, dict[str, Any]]:
    """获取 MasterAgent 规划用的 Agent 能力目录。"""
    catalog: dict[str, dict[str, Any]] = {}
    for agent_id in agent_ids:
        meta = AGENT_META.get(agent_id)
        if not meta:
            continue
        layer = int(meta.get("layer", 0))
        catalog[agent_id] = {
            "name": meta.get("name", agent_id),
            "role": meta.get("role", f"{agent_id.capitalize()}Agent"),
            "description": meta.get("description", ""),
            "layer": layer,
            "stage_name": meta.get("stage_name", layer_name(layer)),
            "format": meta.get("format", "json"),
            "resource_type": meta.get("resource_type", agent_id),
            "best_for": meta.get("best_for", []),
            "depends_on": DEPENDS.get(agent_id, []),
            "config_keys": meta.get("config_keys", []),
            "output": meta.get("output", {"format": "json"}),
            "planning_hint": meta.get("planning_hint", meta.get("planning_reason", "")),
        }
    return catalog


def agent_name(agent_id: str) -> str:
    """获取 Agent 中文名称。"""
    return AGENT_META.get(agent_id, {}).get("name", agent_id)


def agent_role(agent_id: str) -> str:
    """获取 Agent 角色名（如 ContentAgent）。"""
    return AGENT_META.get(agent_id, {}).get("role", f"{agent_id.capitalize()}Agent")


def agent_layer(agent_id: str) -> int:
    """获取 Agent 所属层级。"""
    return int(AGENT_META.get(agent_id, {}).get("layer", 0))


def agent_output(agent_id: str) -> dict[str, Any]:
    """获取 Agent 默认输出要求。"""
    return AGENT_META.get(agent_id, {}).get("output", {"format": "json"})


def agent_format(agent_id: str) -> str:
    """获取 Agent 默认输出格式。"""
    return AGENT_META.get(agent_id, {}).get("format", "json")


def agent_time(agent_id: str) -> int:
    """获取 Agent 预计时间（分钟）。"""
    return int(AGENT_META.get(agent_id, {}).get("estimated_time", 10))


def agent_stage(agent_id: str) -> str:
    """获取 Agent 学习阶段。"""
    return AGENT_META.get(agent_id, {}).get("stage", "resource_generation")


def agent_difficulty(agent_id: str) -> str:
    """获取 Agent 默认难度。"""
    return AGENT_META.get(agent_id, {}).get("difficulty", "basic")


def agent_objectives(agent_id: str) -> list[str]:
    """获取 Agent 学习目标。"""
    return AGENT_META.get(agent_id, {}).get("objectives", ["完成当前资源学习目标"])


def agent_priority(agent_id: str) -> int:
    """获取 Agent 资源优先级。"""
    meta = AGENT_META.get(agent_id, {})
    if "priority" in meta:
        return int(meta.get("priority", 99))
    order = {agent: index for index, agent in enumerate(RESOURCE_ORDER)}
    return order.get(agent_id, 99)


def layer_name(layer: int) -> str:
    """获取层级名称。"""
    return LAYER_NAMES.get(layer, f"Layer {layer}")


def layer_stage(layer: int) -> str:
    """获取层级 stage 标识。"""
    return LAYER_STAGES.get(layer, "planning")
