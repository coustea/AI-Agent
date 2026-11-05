"""Resource 模块统一数据契约与 DTO 模型 (app.resource.schemas)。"""

from __future__ import annotations

from enum import Enum, StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.resource.catalog import AGENT_DEFAULT_ENABLED, AGENT_DEFAULT_ORDER
from app.shared.cartoon import CartoonGenerationConfig
from app.shared.ppt import PPTPreferences

MIN_SELECTED_AGENTS = 3
LearningScenario = Literal["exam_prep", "daily_review", "project_practice", "self_study", "path_learning"]


# ── 1. 任务生命周期状态 ────────────────────────────────────────────────────


class ResourceLifecycleStatus(StrEnum):
    """独立资源生成任务的生命周期状态。"""

    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


SUCCESSFUL_RESOURCE_STATUSES = frozenset(
    {
        ResourceLifecycleStatus.COMPLETED,
        ResourceLifecycleStatus.PARTIAL,
    }
)


# ── 2. 请求模型与 Agent 配置 ───────────────────────────────────────────────


class ResourceAgentId(str, Enum):
    """资源 Agent ID。"""

    CONTENT = "content"
    MINDMAP = "mindmap"
    QUIZ = "quiz"
    READING = "reading"
    CODE = "code"
    PPT = "ppt"
    CARTOON = "cartoon"


DEFAULT_SELECTED_AGENT_IDS: list[ResourceAgentId] = [
    ResourceAgentId(agent_id) for agent_id in AGENT_DEFAULT_ENABLED
]


class AgentSelection(BaseModel):
    """前端上传的 Agent 选择配置。"""

    agent_id: ResourceAgentId
    enabled: bool = True


class ContentConfig(BaseModel):
    """内容 Agent 配置。"""

    structure: Literal["progressive", "summary_first", "exam_points", "case_driven"] = "progressive"
    depth_level: Literal["quick", "standard", "deep"] = "standard"
    focus_mode: Literal["weak_points", "key_concepts", "full_coverage"] = "key_concepts"
    include_examples: bool = True


class MindmapConfig(BaseModel):
    """思维导图 Agent 配置。"""

    map_type: Literal["knowledge_tree", "exam_map", "comparison_map"] = "knowledge_tree"
    max_depth: int = Field(default=3, ge=2, le=5)
    leaf_detail: Literal["keyword", "brief_note", "annotated"] = "brief_note"
    show_relations: bool = True


class QuizConfig(BaseModel):
    """习题 Agent 配置。"""

    difficulty_mode: Literal["basic", "adaptive", "exam"] = "adaptive"
    question_count: int = Field(default=5, ge=1, le=20)
    emphasis: Literal["foundations", "application", "analysis"] = "foundations"
    question_types: list[Literal["single", "multiple", "judge", "fill"]] = Field(
        default_factory=lambda: ["single", "multiple", "judge", "fill"]
    )


class CodeConfig(BaseModel):
    """代码 Agent 配置。"""

    programming_language: Literal["python", "c", "cpp", "java", "go", "javascript", "typescript"] = "python"
    output_style: Literal["tutorial", "reference", "challenge"] = "tutorial"
    focus: Literal["syntax", "application", "debugging"] = "syntax"
    include_tests: bool = False


class ReadingConfig(BaseModel):
    """阅读推荐 Agent 配置。"""

    coverage: Literal["core", "extended", "broad"] = "extended"
    language_preference: Literal["chinese", "english", "both"] = "chinese"
    max_items: int = Field(default=3, ge=1, le=10)
    focus: Literal["textbook", "engineering", "research"] = "textbook"


class AgentConfigs(BaseModel):
    """Agent 配置集合。"""

    model_config = ConfigDict(extra="forbid")

    content: ContentConfig = Field(default_factory=ContentConfig)
    mindmap: MindmapConfig = Field(default_factory=MindmapConfig)
    quiz: QuizConfig = Field(default_factory=QuizConfig)
    code: CodeConfig = Field(default_factory=CodeConfig)
    reading: ReadingConfig = Field(default_factory=ReadingConfig)
    ppt: PPTPreferences = Field(default_factory=PPTPreferences)
    cartoon: CartoonGenerationConfig = Field(default_factory=CartoonGenerationConfig)

    def get(self, agent_id: str, default: Any = None) -> dict[str, Any]:
        value = getattr(self, agent_id, None)
        if value is None:
            return default
        return value.model_dump(mode="json")


def _agent_sort_key(item: AgentSelection) -> int:
    return (
        AGENT_DEFAULT_ORDER.index(item.agent_id.value)
        if item.agent_id.value in AGENT_DEFAULT_ORDER
        else 999
    )


class ResourceGenerationRequest(BaseModel):
    """资源生成请求。"""

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
                AgentSelection(agent_id=agent_id, enabled=True)
                for agent_id in DEFAULT_SELECTED_AGENT_IDS
            ]
        agent_ids = [item.agent_id.value for item in self.selected_agents]
        duplicate_agent_ids = sorted(
            {agent_id for agent_id in agent_ids if agent_ids.count(agent_id) > 1}
        )
        if duplicate_agent_ids:
            raise ValueError(f"selected_agents 包含重复 Agent: {duplicate_agent_ids}")
        enabled_agent_ids = {
            item.agent_id.value for item in self.selected_agents if item.enabled
        }
        if len(enabled_agent_ids) < MIN_SELECTED_AGENTS:
            raise ValueError(
                f"selected_agents 过滤 enabled=true 后至少需要 {MIN_SELECTED_AGENTS} 个 Agent"
            )
        aggregation_agent_ids = enabled_agent_ids & {"ppt", "cartoon"}
        base_agent_ids = enabled_agent_ids & {"content", "mindmap", "quiz", "code", "reading"}
        if aggregation_agent_ids and not base_agent_ids:
            raise ValueError("PPT/Cartoon 聚合 Agent 至少需要一个基础资源 Agent 提供素材")
        self.selected_agents = sorted(self.selected_agents, key=_agent_sort_key)
        return self

    def enabled_agent_ids(self) -> list[str]:
        return [
            item.agent_id.value
            for item in sorted(self.selected_agents, key=_agent_sort_key)
            if item.enabled
        ]


# ── 3. 协同计划与上游交接模型 ─────────────────────────────────────────────


class ResourcePlanTask(BaseModel):
    """单个 Agent 的结构化可执行任务。"""

    model_config = ConfigDict(extra="forbid")

    agent_id: str
    objective: str = Field(min_length=8, max_length=500)
    focus: list[str] = Field(min_length=1, max_length=8)
    required_elements: list[str] = Field(min_length=1, max_length=10)
    avoid: list[str] = Field(default_factory=list, max_length=8)


class ResourcePlan(BaseModel):
    """规划 Agent 交付的结构化控制协议。"""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    learner_goal: str = Field(min_length=8, max_length=600)
    scope: list[str] = Field(min_length=1, max_length=10)
    tasks: list[ResourcePlanTask] = Field(min_length=1, max_length=7)

    @field_validator("scope")
    @classmethod
    def reject_empty_strings(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values if value and value.strip()]
        if len(cleaned) != len(values):
            raise ValueError("计划列表不能包含空项")
        return cleaned

    @model_validator(mode="after")
    def reject_duplicate_tasks(self) -> "ResourcePlan":
        agent_ids = [task.agent_id for task in self.tasks]
        if len(agent_ids) != len(set(agent_ids)):
            raise ValueError("计划中不能为同一 Agent 分配重复任务")
        return self

    @property
    def agent_ids(self) -> list[str]:
        return [task.agent_id for task in self.tasks]

    def task_for(self, agent_id: str) -> ResourcePlanTask:
        for task in self.tasks:
            if task.agent_id == agent_id:
                return task
        raise KeyError(f"计划未包含 Agent: {agent_id}")


class DownstreamContext(BaseModel):
    """基础 Agent 向聚合 Agent (PPT/Cartoon) 提供的显式交接内容。"""

    model_config = ConfigDict(extra="forbid")

    source_agent: str
    title: str = ""
    one_sentence_summary: str = ""
    materials: list[str] = Field(default_factory=list, max_length=12)


class PlanValidationError(ValueError):
    pass


def validate_resource_plan(plan: ResourcePlan, expected_agent_ids: list[str]) -> ResourcePlan:
    expected = set(expected_agent_ids)
    actual = set(plan.agent_ids)
    if actual != expected:
        raise PlanValidationError(
            "计划任务分配与已选 Agent 不一致: "
            f"missing={sorted(expected - actual)} unexpected={sorted(actual - expected)}"
        )
    return plan


# ── 4. Agent 运行时输入/输出模型 ──────────────────────────────────────────


class AgentResult(BaseModel):
    """统一 Agent 输出结果。"""

    model_config = ConfigDict(extra="forbid")

    success: bool = True
    content: str = ""
    file_type: str = "markdown"
    title: str = ""
    summary: str = ""
    metrics: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str = ""


class ResourceInput(BaseModel):
    """多智能体资源生成输入。"""

    model_config = ConfigDict(extra="forbid")

    resource_id: int | None = None
    user_id: int | None = None
    username: str = ""
    learning_need: str
    learning_scenario: LearningScenario = "self_study"
    agent_name: str = ""
    agent_config: dict[str, Any] = Field(default_factory=dict)
    teaching_plan: ResourcePlan | None = None
    profile: dict[str, Any] = Field(default_factory=dict)
    upstream_handoffs: dict[str, DownstreamContext] = Field(default_factory=dict)


# ── 5. Quiz 题目蓝图与校验契约 ────────────────────────────────────────────


QuizQuestionType = Literal[
    "single_choice",
    "multiple_choice",
    "true_false",
    "fill_blank",
]
QuizDifficulty = Literal["basic", "medium", "advanced"]

QUESTION_TYPE_MAP: dict[str, QuizQuestionType] = {
    "single": "single_choice",
    "multiple": "multiple_choice",
    "judge": "true_false",
    "fill": "fill_blank",
}
DEFAULT_QUESTION_TYPES: tuple[QuizQuestionType, ...] = (
    "single_choice",
    "multiple_choice",
    "true_false",
    "fill_blank",
)


class QuizOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(pattern=r"^[A-D]$")
    content: str = Field(min_length=1, max_length=240)


class QuizQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(ge=1)
    type: QuizQuestionType
    question: str = Field(min_length=1, max_length=600)
    options: list[QuizOption] = Field(default_factory=list, max_length=4)
    answer: str | bool | list[str]
    explanation: str = Field(min_length=1, max_length=1200)
    difficulty: QuizDifficulty
    knowledge_points: list[str] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def validate_question_contract(self) -> "QuizQuestion":
        labels = [option.label for option in self.options]
        if len(labels) != len(set(labels)):
            raise ValueError("选项标签不能重复")

        if self.type in {"single_choice", "multiple_choice"}:
            if labels != ["A", "B", "C", "D"]:
                raise ValueError("选择题必须按 A、B、C、D 提供恰好四个选项")
        elif self.options:
            raise ValueError("判断题和填空题的 options 必须为空")

        if self.type == "single_choice":
            if not isinstance(self.answer, str) or self.answer not in labels:
                raise ValueError("单选题答案必须是一个有效选项标签")
        elif self.type == "multiple_choice":
            if not isinstance(self.answer, list):
                raise ValueError("多选题答案必须是选项标签数组")
            if len(self.answer) < 2 or len(self.answer) != len(set(self.answer)):
                raise ValueError("多选题必须包含至少两个不重复的正确选项")
            if any(answer not in labels for answer in self.answer):
                raise ValueError("多选题答案必须来自已有选项")
        elif self.type == "true_false":
            if type(self.answer) is not bool:
                raise ValueError("判断题答案必须是布尔值")
        elif not isinstance(self.answer, str) or not self.answer.strip():
            raise ValueError("填空题答案必须是非空字符串")

        return self


class QuizPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=1, max_length=300)
    questions: list[QuizQuestion] = Field(min_length=1, max_length=20)


class QuizBlueprintSlot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    type: QuizQuestionType
    difficulty: QuizDifficulty


def build_quiz_blueprint(
    *,
    question_count: int,
    question_types: list[str] | None,
    difficulty_mode: str,
) -> list[QuizBlueprintSlot]:
    """在调用模型前确定题目编号、题型和难度。"""
    normalized_types = [
        QUESTION_TYPE_MAP[value]
        for value in (question_types or [])
        if value in QUESTION_TYPE_MAP
    ]
    types = tuple(dict.fromkeys(normalized_types)) or DEFAULT_QUESTION_TYPES

    if difficulty_mode == "basic":
        difficulty_cycle: tuple[QuizDifficulty, ...] = ("basic",)
    elif difficulty_mode == "exam":
        difficulty_cycle = (
            "basic",
            "medium",
            "medium",
            "advanced",
            "basic",
            "medium",
            "medium",
            "advanced",
            "basic",
            "medium",
        )
    else:
        difficulty_cycle = ("basic", "medium", "basic", "medium", "advanced")

    return [
        QuizBlueprintSlot(
            id=index + 1,
            type=types[index % len(types)],
            difficulty=difficulty_cycle[index % len(difficulty_cycle)],
        )
        for index in range(question_count)
    ]


def validate_quiz_payload(
    payload: QuizPayload,
    blueprint: list[QuizBlueprintSlot],
) -> None:
    """校验模型输出与确定性蓝图完全一致。"""
    errors: list[str] = []
    if len(payload.questions) != len(blueprint):
        errors.append(
            f"题目数量应为 {len(blueprint)}，实际为 {len(payload.questions)}"
        )

    seen_questions: set[str] = set()
    for index, slot in enumerate(blueprint):
        if index >= len(payload.questions):
            break
        question = payload.questions[index]
        if question.id != slot.id:
            errors.append(f"第 {index + 1} 题 id 应为 {slot.id}，实际为 {question.id}")
        if question.type != slot.type:
            errors.append(f"第 {index + 1} 题类型应为 {slot.type}，实际为 {question.type}")
        if question.difficulty != slot.difficulty:
            errors.append(f"第 {index + 1} 题难度应为 {slot.difficulty}，实际为 {question.difficulty}")

        normalized_question = " ".join(question.question.split()).casefold()
        if normalized_question in seen_questions:
            errors.append(f"第 {index + 1} 题与前面题目重复")
        seen_questions.add(normalized_question)

    if errors:
        raise ValueError("；".join(errors[:12]))


# ── 6. 响应 DTO 模型 ──────────────────────────────────────────────────────


class GeneratedResourceItem(BaseModel):
    """生成的资源项，作为后端存储和前端 SSE 的统一资源契约。"""

    id: str
    type: ResourceAgentId
    title: str
    format: Literal["markdown", "json", "html", "mp4"]
    content: Any = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None


class ResourceAgentSnapshot(BaseModel):
    """单个 Agent 的持久化运行快照。"""

    agent_id: str
    status: Literal["pending", "running", "completed", "failed", "interrupted"]
    message: str
    progress: int = Field(ge=0, le=100)
    phase: str
    elapsed_ms: int | None = None
    artifact_id: str | None = None
    timestamp: int | None = None


class ResourceStatusSnapshot(BaseModel):
    """SSE/轮询状态接口返回的轻量任务快照。"""

    resource_id: int
    learning_need: str = ""
    status: ResourceLifecycleStatus
    selected_agents: list[ResourceAgentId] = Field(default_factory=list)
    agent_snapshots: dict[str, ResourceAgentSnapshot] = Field(default_factory=dict)
    current_message: str = ""
    resources: list[GeneratedResourceItem] = Field(default_factory=list)
    updated_at: str | None = None


class ResourceBundleMetadata(BaseModel):
    """资源包任务级元数据。"""

    failed_agents: list[str] = Field(default_factory=list)


class ResourceBundle(BaseModel):
    """资源生成完成后的完整资源包。"""

    id: str
    title: str = "个性化学习资源包"
    learning_need: str
    selected_agents: list[ResourceAgentId] = Field(default_factory=list)
    plan: dict[str, Any] | None = None
    resources: list[GeneratedResourceItem] = Field(default_factory=list)
    status: ResourceLifecycleStatus = ResourceLifecycleStatus.COMPLETED
    created_at: str
    updated_at: str
    metadata: ResourceBundleMetadata = Field(default_factory=ResourceBundleMetadata)


__all__ = [
    "AgentConfigs",
    "AgentResult",
    "AgentSelection",
    "CodeConfig",
    "ContentConfig",
    "DEFAULT_QUESTION_TYPES",
    "DEFAULT_SELECTED_AGENT_IDS",
    "DownstreamContext",
    "GeneratedResourceItem",
    "LearningScenario",
    "MIN_SELECTED_AGENTS",
    "MindmapConfig",
    "PlanValidationError",
    "QUESTION_TYPE_MAP",
    "QuizBlueprintSlot",
    "QuizConfig",
    "QuizDifficulty",
    "QuizOption",
    "QuizPayload",
    "QuizQuestion",
    "QuizQuestionType",
    "ReadingConfig",
    "ResourceAgentId",
    "ResourceAgentSnapshot",
    "ResourceBundle",
    "ResourceBundleMetadata",
    "ResourceGenerationRequest",
    "ResourceInput",
    "ResourceLifecycleStatus",
    "ResourcePlan",
    "ResourcePlanTask",
    "ResourceStatusSnapshot",
    "SUCCESSFUL_RESOURCE_STATUSES",
    "build_quiz_blueprint",
    "validate_quiz_payload",
    "validate_resource_plan",
]
