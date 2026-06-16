"""资源生成模块 Pydantic 模型。

包含请求/响应/内部状态的所有数据结构。
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ======================================================================
# Agent 元信息（替代 manifest.py）
# ======================================================================

AGENT_META: dict[str, dict[str, str]] = {
    "content": {"name": "课程内容", "icon": "Document", "description": "专业课程讲解文档"},
    "mindmap": {"name": "思维导图", "icon": "Mindmap", "description": "知识结构思维导图"},
    "quiz": {"name": "练习题", "icon": "Quiz", "description": "练习习题"},
    "code": {"name": "代码示例", "icon": "Code", "description": "代码实操案例"},
    "reading": {"name": "拓展阅读", "icon": "Reading", "description": "拓展阅读推荐"},
    "ppt": {"name": "PPT文稿", "icon": "DataBoard", "description": "PPT文稿生成"},
    "video": {"name": "讲解视频", "icon": "Video", "description": "结构化讲解视频脚本与分镜"},
}

# 默认 Agent 顺序和默认启用列表
AGENT_DEFAULT_ORDER: list[str] = ["content", "mindmap", "quiz", "code", "reading", "ppt", "video"]
AGENT_DEFAULT_ENABLED: list[str] = ["content", "mindmap", "quiz", "reading", "ppt"]


# ======================================================================
# 请求模型
# ======================================================================

LearningScenario = Literal["exam_prep", "daily_review", "project_practice", "self_study", "path_learning"]


class ResourceAgentId(str, Enum):
    """资源 Agent ID。"""

    CONTENT = "content"
    MINDMAP = "mindmap"
    QUIZ = "quiz"
    READING = "reading"
    CODE = "code"
    PPT = "ppt"
    VIDEO = "video"


DEFAULT_SELECTED_AGENT_IDS: list[ResourceAgentId] = [
    ResourceAgentId(agent_id)
    for agent_id in AGENT_DEFAULT_ENABLED
]


class AgentSelection(BaseModel):
    """前端上传的 Agent 选择配置。"""
    agent_id: ResourceAgentId
    enabled: bool = True
    priority: int = Field(default=0, ge=0, le=10)


class ContentConfig(BaseModel):
    """内容 Agent 配置。"""
    structure: Literal["progressive", "summary_first", "exam_points", "case_driven"] = "progressive"
    include_common_mistakes: bool = True
    include_examples: bool = True
    focus_mode: Literal["weak_points", "key_concepts", "full_coverage"] = "key_concepts"
    depth_level: Literal["quick", "standard", "deep"] = "standard"


class MindmapConfig(BaseModel):
    """思维导图 Agent 配置。"""
    map_type: Literal["knowledge_tree", "exam_map", "comparison_map"] = "knowledge_tree"
    max_depth: int = Field(default=3, ge=2, le=5)
    highlight_weak: bool = True
    expand_weak_points: bool = False
    include_prerequisites: bool = False


class QuizConfig(BaseModel):
    """习题 Agent 配置。"""
    question_count: int = Field(default=5, ge=1, le=20)
    difficulty_mode: Literal["basic", "adaptive", "exam"] = "basic"
    weak_point_weight: float = Field(default=50, ge=0.0, le=100.0)
    exam_style: Literal["school", "考研", "考证", "interview"] = "school"
    include_analysis: bool = True
    question_types: list[Literal["single", "multiple", "judge", "fill"]] = Field(
        default_factory=lambda: ["single", "multiple", "judge"]
    )


class CodeConfig(BaseModel):
    """代码 Agent 配置。"""
    programming_language: Literal["python", "c", "cpp", "java", "go", "javascript", "typescript"] = "python"
    case_type: Literal["basic_demo", "algorithm_template", "debug_demo"] = "basic_demo"
    difficulty: Literal["beginner", "intermediate", "advanced"] = "beginner"


class ReadingConfig(BaseModel):
    """阅读推荐 Agent 配置。"""
    reading_depth: Literal["course_extended", "engineering", "frontier"] = "course_extended"
    max_items: int = Field(default=5, ge=1, le=10)
    language_preference: Literal["chinese", "english", "both"] = "chinese"

    @field_validator("language_preference", mode="before")
    @classmethod
    def normalize_language_preference(cls, value: Any) -> Any:
        if value == "bilingual":
            return "both"
        return value


class PptConfig(BaseModel):
    """PPT Agent 配置。"""
    page_count: int = Field(default=6, ge=3, le=20)
    difficulty: Literal["beginner", "intermediate", "advanced"] = "intermediate"
    output_format: Literal["preview"] = "preview"


class VideoConfig(BaseModel):
    """Video Agent 配置。生成结构化预览 JSON，不渲染二进制视频。"""

    duration_seconds: int = Field(default=180, ge=60, le=600)
    scene_count: int = Field(default=6, ge=3, le=12)
    style: Literal["explainer", "lecture", "screencast", "case_walkthrough"] = "explainer"
    voice: Literal["teacher", "coach", "concise"] = "teacher"
    aspect_ratio: Literal["16:9", "9:16", "1:1"] = "16:9"
    include_captions: bool = True
    output_format: Literal["preview"] = "preview"


class AgentConfigs(BaseModel):
    """Agent 配置集合。"""
    model_config = ConfigDict(extra="forbid")

    content: ContentConfig = Field(default_factory=ContentConfig)
    mindmap: MindmapConfig = Field(default_factory=MindmapConfig)
    quiz: QuizConfig = Field(default_factory=QuizConfig)
    code: CodeConfig = Field(default_factory=CodeConfig)
    reading: ReadingConfig = Field(default_factory=ReadingConfig)
    ppt: PptConfig = Field(default_factory=PptConfig)
    video: VideoConfig = Field(default_factory=VideoConfig)

    def get(self, agent_id: str, default: Any = None) -> dict[str, Any]:
        value = getattr(self, agent_id, None)
        if value is None:
            return default
        return value.model_dump(mode="json")


def _agent_sort_key(item: AgentSelection) -> tuple[int, int]:
    return (item.priority, AGENT_DEFAULT_ORDER.index(item.agent_id.value) if item.agent_id.value in AGENT_DEFAULT_ORDER else 999)


class ResourceGenerationRequest(BaseModel):
    """资源生成请求 — 与前端 TypeScript 类型对齐。"""
    model_config = ConfigDict(extra="forbid")

    learning_need: str
    learning_scenario: LearningScenario = "self_study"
    selected_agents: list[AgentSelection] = Field(default_factory=list)
    agent_configs: AgentConfigs = Field(default_factory=AgentConfigs)

    @field_validator("learning_need")
    @classmethod
    def validate_learning_need(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("学习需求不能为空")
        return value

    @model_validator(mode="after")
    def validate_selection(self) -> "ResourceGenerationRequest":
        if not self.selected_agents:
            self.selected_agents = [
                AgentSelection(agent_id=agent_id, enabled=True, priority=index)
                for index, agent_id in enumerate(DEFAULT_SELECTED_AGENT_IDS)
            ]
        if not [item for item in self.selected_agents if item.enabled]:
            raise ValueError("selected_agents 过滤 enabled=true 后不能为空")
        self.selected_agents = sorted(self.selected_agents, key=_agent_sort_key)
        return self

    def enabled_agent_ids(self) -> list[str]:
        """获取启用的 Agent ID 列表，按前端优先级和默认顺序排序。"""
        return [
            item.agent_id.value
            for item in sorted(self.selected_agents, key=_agent_sort_key)
            if item.enabled
        ]


# ======================================================================
# 教学蓝图 & 执行计划模型（Planning Agent 输出）
# ======================================================================

class TeachingOutlineItem(BaseModel):
    """PlanningAgent 生成的全局教学大纲项，不绑定具体 agent。"""

    id: str = Field(pattern=r"^o[0-9]+$", description="稳定大纲 ID，如 o1、o2")
    title: str
    goal: str = ""
    key_points: list[str] = Field(default_factory=list)
    common_misconceptions: list[str] = Field(default_factory=list)
    suggested_examples: list[str] = Field(default_factory=list)
    suggested_visuals: list[str] = Field(default_factory=list)
    must_not_miss: bool = True


class TeachingPlan(BaseModel):
    """PlanningAgent 的唯一输出：总体方向、概要、大纲和边界。"""

    topic: str
    learning_goal: str = ""
    audience: str = ""
    difficulty: Literal["beginner", "intermediate", "advanced"] = "intermediate"
    teaching_strategy: str = ""
    summary: str = ""
    outline: list[TeachingOutlineItem] = Field(default_factory=list)
    boundaries: list[str] = Field(default_factory=list)


class ReusableAssets(BaseModel):
    examples: list[str] = Field(default_factory=list)
    misconceptions: list[str] = Field(default_factory=list)
    visual_ideas: list[str] = Field(default_factory=list)
    practice_refs: list[str] = Field(default_factory=list)
    code_refs: list[str] = Field(default_factory=list)


class DownstreamMaterial(BaseModel):
    outline_id: str = ""
    type: Literal["explanation", "structure", "practice", "code", "reading", "example", "visual"] = "explanation"
    summary: str = Field(default="", max_length=500)
    key_points: list[str] = Field(default_factory=list, max_length=8)
    evidence_excerpt: str = Field(default="", max_length=180)
    priority: int = Field(default=3, ge=1, le=5)


class DownstreamContext(BaseModel):
    """基础 agent 给 PPT/Video/Review 的短交接摘要。"""

    schema_version: Literal["resource_handoff/v1"] = "resource_handoff/v1"
    source_agent: str
    title: str = ""
    one_sentence_summary: str = Field(default="", max_length=180)
    covered_outline_ids: list[str] = Field(default_factory=list)
    materials: list[DownstreamMaterial] = Field(default_factory=list, max_length=8)
    reusable_assets: ReusableAssets = Field(default_factory=ReusableAssets)
    cautions: list[str] = Field(default_factory=list, max_length=6)


# ======================================================================
# Agent 运行时输入/输出模型
# ======================================================================

class AgentResult(BaseModel):
    """统一 Agent 输出结果，用于 standalone resource 和 path node resource。"""

    success: bool = True
    content: str = ""
    file_type: str = "markdown"
    title: str = ""
    summary: str = ""
    metrics: dict[str, Any] = Field(default_factory=dict)
    downstream_context: DownstreamContext | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str = ""


class ResourceInput(BaseModel):
    """standalone 多智能体资源生成输入。"""

    resource_id: int | None = None
    learning_need: str
    learning_scenario: LearningScenario = "self_study"
    agent_name: str = ""
    agent_config: dict[str, Any] = Field(default_factory=dict)
    teaching_plan: TeachingPlan | None = None
    profile: dict[str, Any] = Field(default_factory=dict)
    upstream_handoffs: dict[str, DownstreamContext] = Field(default_factory=dict)


class NodeInput(BaseModel):
    """路径规划当前节点资源生成输入。"""

    path_id: int
    node_id: int
    node_key: str
    path_title: str
    path_goal: str
    stage_id: str | None = None
    node_title: str
    difficulty: str | None = None
    mastery_target: str | None = None
    prerequisites: list[str] = Field(default_factory=list)
    knowledge_points: list[str] = Field(default_factory=list)
    weak_knowledge_points: list[str] = Field(default_factory=list)
    generation_focus: list[str] = Field(default_factory=list)
    tutorial_title: str
    tutorial_summary: str | None = None
    tutorial_markdown: str
    profile: dict[str, Any] = Field(default_factory=dict)
    existing_resources: dict[str, AgentResult] = Field(default_factory=dict)
    agent_config: dict[str, Any] = Field(default_factory=dict)


class GeneratedResourceItem(BaseModel):
    """生成的资源项，作为后端存储和前端 SSE 的统一资源契约。"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: ResourceAgentId
    title: str
    format: str
    content: Any
    summary: str = ""
    metrics: dict[str, Any] = Field(default_factory=dict)
    downstream_context: DownstreamContext | None = None
    execution_report: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: str = "completed"
    error_message: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ReviewResult(BaseModel):
    """Review Agent 的审查结果。"""
    passed: bool = True
    overall_score: int = Field(default=100, ge=0, le=100)
    consistency_score: int = Field(default=100, ge=0, le=100, description="知识一致性评分")
    personalization_score: int = Field(default=100, ge=0, le=100, description="个性化匹配度评分")
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    failed_agents: list[str] = Field(default_factory=list)


class ResourceBundle(BaseModel):
    """资源生成完成后的资源包。"""
    id: str
    task_id: str
    topic: str | None = None
    title: str = "个性化学习资源包"
    learning_need: str
    selected_agents: list[str] = Field(default_factory=list)
    resources: list[GeneratedResourceItem] = Field(default_factory=list)
    review_result: ReviewResult | None = None
    status: str = "completed"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)


# ======================================================================
# 响应模型
# ======================================================================

class SingleResourceRequest(BaseModel):
    """单智能体资源生成请求（路径规划 / 即调即用）。"""
    model_config = ConfigDict(extra="forbid")

    agent_id: ResourceAgentId
    learning_need: str

    @field_validator("learning_need")
    @classmethod
    def validate_learning_need(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("学习需求不能为空")
        return value


__all__ = [
    # Constants
    "AGENT_META",
    "AGENT_DEFAULT_ORDER",
    "AGENT_DEFAULT_ENABLED",
    # Request models
    "ResourceGenerationRequest",
    "SingleResourceRequest",
    # Learning blueprint & planning
    "TeachingOutlineItem",
    "TeachingPlan",
    "ReusableAssets",
    "DownstreamMaterial",
    "DownstreamContext",
    # Runtime input/output
    "AgentResult",
    "ResourceInput",
    "NodeInput",
    "GeneratedResourceItem",
    "ReviewResult",
    "ResourceBundle",
    # Response models
]
