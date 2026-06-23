"""请求模型与 Agent 配置 Schema。

包含：
- ResourceGenerationRequest — 多智能体资源生成请求
- SingleResourceRequest     — 单智能体资源生成请求
- AgentConfigs              — 各 agent 的配置集合
- 各 agent 配置类（ContentConfig / MindmapConfig / QuizConfig 等）
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.resource.schemas.meta import AGENT_DEFAULT_ENABLED, AGENT_DEFAULT_ORDER


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
    def normalize_language_preference(cls, value: Any) -> str:
        if value == "bilingual":
            return "both"
        return value


class PptConfig(BaseModel):
    """计算机教学课件配置。

    theme_id: 用户选择的主题颜色，将直接写入输出 PptDocument
    explanation_style: 控制讲解组织方式（概念优先/流程优先/对比优先）
    visual_emphasis: 控制可视化元素密度（极简/平衡/丰富）
    """

    model_config = ConfigDict(extra="forbid")

    theme_id: Literal["logic-blue", "paper-light", "lab-light"] = "logic-blue"
    explanation_style: Literal["conceptual", "procedural", "comparative"] = "conceptual"
    visual_emphasis: Literal["minimal", "balanced", "rich"] = "balanced"


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
        agent_ids = [item.agent_id.value for item in self.selected_agents]
        duplicate_agent_ids = sorted({agent_id for agent_id in agent_ids if agent_ids.count(agent_id) > 1})
        if duplicate_agent_ids:
            raise ValueError(f"selected_agents 包含重复 Agent: {duplicate_agent_ids}")
        enabled_agent_ids = {
            item.agent_id.value for item in self.selected_agents if item.enabled
        }
        if not enabled_agent_ids:
            raise ValueError("selected_agents 过滤 enabled=true 后不能为空")
        aggregation_agent_ids = enabled_agent_ids & {"ppt", "video"}
        base_agent_ids = enabled_agent_ids & {"content", "mindmap", "quiz", "code", "reading"}
        if aggregation_agent_ids and not base_agent_ids:
            raise ValueError(
                "PPT/Video 聚合 Agent 至少需要一个基础资源 Agent 提供素材"
            )
        self.selected_agents = sorted(self.selected_agents, key=_agent_sort_key)
        return self

    def enabled_agent_ids(self) -> list[str]:
        """获取启用的 Agent ID 列表，按前端优先级和默认顺序排序。"""
        return [
            item.agent_id.value
            for item in sorted(self.selected_agents, key=_agent_sort_key)
            if item.enabled
        ]
