"""
资源生成模块 Pydantic 模型。

包含请求/响应/内部状态的所有数据结构。
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.resource.manifest import agent_order, default_agent_ids


# ======================================================================
# 请求模型
# ======================================================================

LearningScenario = Literal["exam_prep", "daily_review", "project_practice", "self_study"]
AGENT_DEFAULT_ORDER = agent_order()


class ResourceAgentId(str, Enum):
    """资源 Agent ID。"""

    CONTENT = "content"
    MINDMAP = "mindmap"
    DIAGRAM = "diagram"
    QUIZ = "quiz"
    READING = "reading"
    CODE = "code"


DEFAULT_SELECTED_AGENT_IDS: list[ResourceAgentId] = [
    ResourceAgentId(agent_id)
    for agent_id in default_agent_ids()
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
    max_depth: int = Field(default=4, ge=2, le=6)
    highlight_weak: bool = True
    expand_weak_points: bool = False
    include_prerequisites: bool = False


class DiagramConfig(BaseModel):
    """图表 Agent 配置。"""
    diagram_type: Literal[
        "auto", "hierarchy", "flow", "compare", "relation", "state",
        "class", "er", "block", "packet", "git", "sequence",
        "activity", "usecase", "component", "package", "deployment",
        "object", "communication",
    ] = "auto"
    visual_style: Literal["minimal", "exam"] = "minimal"
    highlight_mode: Literal["weak_points", "key_points", "all"] = "key_points"
    detail_level: Literal["concise", "standard", "detailed"] = "standard"


class QuizConfig(BaseModel):
    """习题 Agent 配置。"""
    question_count: int = Field(default=5, ge=1, le=50)
    difficulty_mode: Literal["basic", "adaptive", "exam"] = "basic"
    weak_point_weight: float = Field(default=50, ge=0.0, le=100.0)
    exam_style: Literal["school", "考研", "考证", "interview"] = "school"
    include_analysis: bool = True
    question_types: list[Literal["single", "multiple", "judge", "fill"]] = Field(
        default_factory=lambda: ["single", "multiple", "judge"]
    )


class CodeConfig(BaseModel):
    """代码 Agent 配置。"""
    programming_language: Literal["python", "cpp", "java", "go", "javascript"] = "python"
    case_type: Literal["basic_demo", "algorithm_template", "debug_demo"] = "basic_demo"
    comment_level: Literal["minimal", "standard", "verbose"] = "standard"
    include_test: bool = True
    difficulty: Literal["beginner", "intermediate", "advanced"] = "beginner"


class ReadingConfig(BaseModel):
    """阅读推荐 Agent 配置。"""
    reading_depth: Literal["course_extended", "engineering", "frontier"] = "course_extended"
    max_items: int = Field(default=5, ge=1, le=20)
    resource_quality: Literal["classic", "latest", "balanced"] = "balanced"
    include_practice: bool = True
    language_preference: Literal["chinese", "english", "both"] = "chinese"

    @field_validator("language_preference", mode="before")
    @classmethod
    def normalize_language_preference(cls, value: Any) -> Any:
        if value == "bilingual":
            return "both"
        return value


class OutputOptions(BaseModel):
    """输出选项。"""
    output_format: Literal["json"] = "json"


class AgentConfigs(BaseModel):
    """Agent 配置集合。"""

    content: ContentConfig = Field(default_factory=ContentConfig)
    mindmap: MindmapConfig = Field(default_factory=MindmapConfig)
    diagram: DiagramConfig = Field(default_factory=DiagramConfig)
    quiz: QuizConfig = Field(default_factory=QuizConfig)
    code: CodeConfig = Field(default_factory=CodeConfig)
    reading: ReadingConfig = Field(default_factory=ReadingConfig)

    def get(self, agent_id: str, default: Any = None) -> dict[str, Any]:
        value = getattr(self, agent_id, None)
        if value is None:
            return default
        return value.model_dump(mode="json")


class ResourceGenerationRequest(BaseModel):
    """资源生成请求 — 与前端 TypeScript 类型对齐。"""
    model_config = ConfigDict(extra="forbid")

    learning_need: str
    learning_scenario: LearningScenario = "self_study"
    selected_agents: list[AgentSelection] = Field(default_factory=list)
    agent_configs: AgentConfigs = Field(default_factory=AgentConfigs)
    output_options: OutputOptions = Field(default_factory=OutputOptions)

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
        self.selected_agents = sorted(
            self.selected_agents,
            key=lambda item: (
                item.priority,
                AGENT_DEFAULT_ORDER.index(item.agent_id.value) if item.agent_id.value in AGENT_DEFAULT_ORDER else 999,
            ),
        )
        return self

    def enabled_agent_ids(self) -> list[str]:
        """获取启用的 Agent ID 列表，按前端优先级和默认顺序排序。"""
        enabled = [item for item in self.selected_agents if item.enabled]
        enabled.sort(
            key=lambda item: (
                item.priority,
                AGENT_DEFAULT_ORDER.index(item.agent_id.value) if item.agent_id.value in AGENT_DEFAULT_ORDER else 999,
            ),
        )
        result: list[str] = []
        for item in enabled:
            if item.agent_id.value not in result:
                result.append(item.agent_id.value)
        return result


# ======================================================================
# 内部状态模型
# ======================================================================

class WorkerState(BaseModel):
    """Agent 执行状态。"""
    task: dict[str, Any] = Field(default_factory=dict)
    agent_name: str = ""
    agent_config: dict[str, Any] = Field(default_factory=dict)
    learning_scenario: str = "self_study"
    layer_index: int = 0
    # 上游依赖结果
    dependencies: list[dict[str, Any]] = Field(default_factory=list)
    # 用户画像
    profile: dict[str, Any] = Field(default_factory=dict)
    # 内容大纲 (content outline-first 模式)
    outline_only: bool = False
    outline: str | None = None


class WorkerResult(BaseModel):
    """Agent 执行结果。"""
    success: bool = True
    content: str = ""
    file_type: str = "markdown"
    title: str = ""
    summary: str = ""
    summary_data: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str = ""


class GeneratedResourceItem(BaseModel):
    """生成的资源项，作为后端存储和前端 SSE 的统一资源契约。"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: ResourceAgentId
    title: str
    format: str
    content: Any
    summary: str = ""
    summary_data: dict[str, Any] = Field(default_factory=dict)
    execution_report: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class StudyPathStep(BaseModel):
    """资源包内的轻量学习路径步骤。"""
    order: int
    resource_type: ResourceAgentId
    title: str
    reason: str
    estimated_time: int | None = None


class ReviewResult(BaseModel):
    """轻量资源审查结果。"""
    passed: bool = True
    score: int = Field(default=100, ge=0, le=100)
    issues: list[dict[str, Any]] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    failed_agents: list[str] = Field(default_factory=list)
    skipped_agents: list[str] = Field(default_factory=list)


class ResourceBundle(BaseModel):
    """资源生成完成后的资源包。"""
    id: str
    task_id: str
    topic: str | None = None
    title: str = "个性化学习资源包"
    learning_need: str
    selected_agents: list[str] = Field(default_factory=list)
    resources: list[GeneratedResourceItem] = Field(default_factory=list)
    study_path: list[StudyPathStep] = Field(default_factory=list)
    review_result: ReviewResult | None = None
    status: str = "completed"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)


ResourceGenerationRequest.model_rebuild()


# ======================================================================
# 响应模型
# ======================================================================

class AgentMeta(BaseModel):
    """Agent 元信息 (用于 /agents 接口)。"""
    agent_id: str
    name: str
    description: str
    icon: str = ""
    layer: int = 0
    layer_name: str = ""
    default_enabled: bool = True


class ResourceItemResponse(BaseModel):
    """单个资源项响应。"""
    id: int
    resource_id: int
    agent_name: str
    title: str
    content: str
    file_type: str
    summary: str = ""
    summary_data: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResourceResponse(BaseModel):
    """资源列表响应。"""
    id: int
    user_id: int
    learning_need: str
    learning_scenario: str
    status: str = "completed"
    items: list[ResourceItemResponse] = Field(default_factory=list)
