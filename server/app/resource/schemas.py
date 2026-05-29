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
}

# 默认 Agent 顺序和默认启用列表
AGENT_DEFAULT_ORDER: list[str] = ["content", "mindmap", "quiz", "code", "reading", "ppt"]
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
    comment_level: Literal["minimal", "standard", "verbose"] = "standard"
    include_test: bool = True
    difficulty: Literal["beginner", "intermediate", "advanced"] = "beginner"


class ReadingConfig(BaseModel):
    """阅读推荐 Agent 配置。"""
    reading_depth: Literal["course_extended", "engineering", "frontier"] = "course_extended"
    max_items: int = Field(default=5, ge=1, le=10)
    resource_quality: Literal["classic", "latest", "balanced"] = "balanced"
    include_practice: bool = True
    language_preference: Literal["chinese", "english", "both"] = "chinese"

    @field_validator("language_preference", mode="before")
    @classmethod
    def normalize_language_preference(cls, value: Any) -> Any:
        if value == "bilingual":
            return "both"
        return value


class PptConfig(BaseModel):
    """PPT Agent 配置。"""
    template_id: Literal["theme-logic-blue"] = "theme-logic-blue"
    page_count: int = Field(default=6, ge=3, le=20)
    difficulty: Literal["beginner", "intermediate", "advanced"] = "intermediate"
    output_format: Literal["preview"] = "preview"


class OutputOptions(BaseModel):
    """输出选项。"""
    output_format: Literal["json"] = "json"


class AgentConfigs(BaseModel):
    """Agent 配置集合。"""
    model_config = ConfigDict(extra="forbid")

    content: ContentConfig = Field(default_factory=ContentConfig)
    mindmap: MindmapConfig = Field(default_factory=MindmapConfig)
    quiz: QuizConfig = Field(default_factory=QuizConfig)
    code: CodeConfig = Field(default_factory=CodeConfig)
    reading: ReadingConfig = Field(default_factory=ReadingConfig)
    ppt: PptConfig = Field(default_factory=PptConfig)

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

class LearningBlueprint(BaseModel):
    """Planning Agent 生成的内部教学蓝图，供多个资源 Agent 共享。

    不作为 GeneratedResourceItem 保存，不返回给前端，不写入 Neo4j。
    """
    topic: str = Field(description="学习主题")
    learner_goal: str = Field(default="", description="本轮学习目标")
    prerequisite_concepts: list[str] = Field(default_factory=list, description="前置概念")
    core_concepts: list[str] = Field(default_factory=list, description="核心概念")
    difficult_points: list[str] = Field(default_factory=list, description="难点与易错点")
    concept_relations: list[str] = Field(default_factory=list, description="概念间关系")
    example_scenarios: list[str] = Field(default_factory=list, description="推荐案例或场景")
    practice_targets: list[str] = Field(default_factory=list, description="练习目标")
    resource_guidance: dict[str, str] = Field(default_factory=dict, description="各类资源的生成侧重点")


class AgentInstruction(BaseModel):
    """Planning Agent 为单个下游 Agent 生成的个性化指令。"""
    agent_id: str
    focus: str = Field(default="", description="该 Agent 应重点关注的方面")
    difficulty: str = Field(default="intermediate", description="建议难度")
    personalization_notes: str = Field(default="", description="个性化建议")
    constraints: list[str] = Field(default_factory=list, description="特殊约束")


class ExecutionPlan(BaseModel):
    """Planning Agent 的完整输出。"""
    blueprint: LearningBlueprint
    agent_instructions: list[AgentInstruction] = Field(default_factory=list)
    personalization_summary: str = Field(default="", description="个性化分析总结")


# ======================================================================
# 内部状态模型
# ======================================================================

class WorkerState(BaseModel):
    """Agent 运行时需要的所有输入，扁平结构。"""
    resource_id: int | None = None
    learning_need: str = ""
    learning_scenario: str = "self_study"
    agent_name: str = ""
    agent_config: dict[str, Any] = Field(default_factory=dict)
    # Planning Agent 的产出（所有 Agent 共享）
    blueprint: LearningBlueprint | None = None
    # Planning Agent 为该 Agent 定制的指令
    instruction: AgentInstruction | None = None
    # 用户画像
    profile: dict[str, Any] = Field(default_factory=dict)


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
    status: str = "completed"
    error_message: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class StudyPathStep(BaseModel):
    """Review Agent 生成的个性化学习路径步骤。"""
    order: int
    resource_type: str
    title: str
    reason: str = Field(default="", description="为什么在这个位置学习该资源")
    estimated_time: int | None = Field(default=None, description="预估学习时间(分钟)")
    focus_points: list[str] = Field(default_factory=list, description="学习时应重点关注的知识点")


class ReviewResult(BaseModel):
    """Review Agent 的审查结果。"""
    passed: bool = True
    overall_score: int = Field(default=100, ge=0, le=100)
    consistency_score: int = Field(default=100, ge=0, le=100, description="知识一致性评分")
    personalization_score: int = Field(default=100, ge=0, le=100, description="个性化匹配度评分")
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    failed_agents: list[str] = Field(default_factory=list)
    study_path: list[StudyPathStep] = Field(default_factory=list)


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


class ResourceDetailResponse(BaseModel):
    """Resource detail response with content."""

    id: int
    title: str
    resource_type: str
    status: str = "pending"
    content: str | None = None
    metadata: dict | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SingleResourceRequest(BaseModel):
    """Request for single-agent resource generation (path planning / on-demand use)."""
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


class ResourceListResponse(BaseModel):
    """Resource list response."""

    items: list[ResourceResponse] = Field(default_factory=list)
    total: int = 0

__all__ = [
    # Constants
    "AGENT_META",
    "AGENT_DEFAULT_ORDER",
    "AGENT_DEFAULT_ENABLED",
    # Request models
    "ResourceGenerationRequest",
    "SingleResourceRequest",
    # Learning blueprint & planning
    "LearningBlueprint",
    "AgentInstruction",
    "ExecutionPlan",
    # Internal state
    "WorkerState",
    "WorkerResult",
    "GeneratedResourceItem",
    "StudyPathStep",
    "ReviewResult",
    "ResourceBundle",
    # Response models
    "AgentMeta",
    "ResourceItemResponse",
    "ResourceResponse",
    "ResourceDetailResponse",
    "ResourceListResponse",
]
