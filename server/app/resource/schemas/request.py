"""请求模型与 Agent 配置 Schema。

包含：
- ResourceGenerationRequest — 多智能体资源生成请求
- AgentConfigs              — 各 agent 的配置集合
- 各 agent 配置类（ContentConfig / MindmapConfig / QuizConfig 等）

各 agent 只暴露影响生成质量的核心参数，前后端完全对齐。
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.resource.schemas.meta import AGENT_DEFAULT_ENABLED, AGENT_DEFAULT_ORDER
from app.shared.ppt import PPTPreferences


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
    CARTOON = "cartoon"


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
    """内容 Agent 配置 — 4 个核心参数。"""

    structure: Literal["progressive", "summary_first", "exam_points", "case_driven"] = "progressive"
    depth_level: Literal["quick", "standard", "deep"] = "standard"
    focus_mode: Literal["weak_points", "key_concepts", "full_coverage"] = "key_concepts"
    include_examples: bool = True


class MindmapConfig(BaseModel):
    """思维导图 Agent 配置 — 4 个核心参数。"""

    map_type: Literal["knowledge_tree", "exam_map", "comparison_map"] = "knowledge_tree"
    max_depth: int = Field(default=3, ge=2, le=5)
    leaf_detail: Literal["keyword", "brief_note", "annotated"] = "brief_note"
    show_relations: bool = True


class QuizConfig(BaseModel):
    """习题 Agent 配置 — 4 个核心参数。"""

    difficulty_mode: Literal["basic", "adaptive", "exam"] = "basic"
    question_count: int = Field(default=5, ge=1, le=20)
    exam_style: Literal["school", "postgrad", "certification", "interview"] = "school"
    question_types: list[Literal["single", "multiple", "judge", "fill"]] = Field(
        default_factory=lambda: ["single", "multiple", "judge", "fill"]
    )


class CodeConfig(BaseModel):
    """代码 Agent 配置 — 4 个核心参数。"""

    programming_language: Literal["python", "c", "cpp", "java", "go", "javascript", "typescript"] = "python"
    difficulty: Literal["beginner", "intermediate", "advanced"] = "beginner"
    case_type: Literal["basic_demo", "algorithm_template", "debug_demo"] = "basic_demo"
    focus: Literal["syntax", "application", "debugging"] = "syntax"


class ReadingConfig(BaseModel):
    """阅读推荐 Agent 配置 — 4 个核心参数。"""

    reading_depth: Literal["course_extended", "engineering", "frontier"] = "course_extended"
    language_preference: Literal["chinese", "english", "both"] = "chinese"
    max_items: int = Field(default=5, ge=1, le=10)
    focus: Literal["textbook", "engineering", "paper"] = "textbook"


class VideoConfig(BaseModel):
    """视频 Agent 配置。后端保留能力，当前资源生成前端不暴露入口。"""

    voice: Literal["teacher", "coach"] = "teacher"
    duration_seconds: int = Field(default=180, ge=60, le=600)
    aspect_ratio: Literal["16:9", "9:16", "1:1"] = "16:9"
    include_captions: bool = True


class CartoonConfig(BaseModel):
    """动画讲解 Agent 配置。"""

    style: Literal["diagram", "minimal", "dark_tech"] = "diagram"
    voice: Literal["teacher", "coach"] = "teacher"
    video_length_seconds: int = Field(default=120, ge=60, le=180)
    focus: Literal["concept", "process", "comparison", "practice"] = "concept"


class AgentConfigs(BaseModel):
    """Agent 配置集合。"""
    model_config = ConfigDict(extra="forbid")

    content: ContentConfig = Field(default_factory=ContentConfig)
    mindmap: MindmapConfig = Field(default_factory=MindmapConfig)
    quiz: QuizConfig = Field(default_factory=QuizConfig)
    code: CodeConfig = Field(default_factory=CodeConfig)
    reading: ReadingConfig = Field(default_factory=ReadingConfig)
    ppt: PPTPreferences = Field(default_factory=PPTPreferences)
    video: VideoConfig = Field(default_factory=VideoConfig)
    cartoon: CartoonConfig = Field(default_factory=CartoonConfig)

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
        aggregation_agent_ids = enabled_agent_ids & {"ppt", "video", "cartoon"}
        base_agent_ids = enabled_agent_ids & {"content", "mindmap", "quiz", "code", "reading"}
        if aggregation_agent_ids and not base_agent_ids:
            raise ValueError(
                "PPT/Video/Cartoon 聚合 Agent 至少需要一个基础资源 Agent 提供素材"
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
