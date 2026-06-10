"""路径规划模块 Pydantic 模型。

包含请求/响应/内部状态的所有数据结构。
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from app.infra.models import PathNode, PathNodeTutorial, PathNodeQuestion, PathNodeResource

# ======================================================================
# 请求模型
# ======================================================================


class CreateLearningPathRequest(BaseModel):
    """新学习路径创建请求。"""

    goal: str = Field(description="学习目标")
    topic: str = Field(default="", description="学习主题")
    module: str = Field(default="mentor", description="模块名称")
    current_knowledge: list[str] = Field(default_factory=list, description="当前已掌握的知识点")
    preferences: dict[str, Any] = Field(default_factory=dict, description="学习偏好")
    enable_search: bool = Field(default=False, description="是否允许规划阶段检索外部资料")


class AuxiliaryResourceRequest(BaseModel):
    """节点辅助资源生成请求。"""

    resource_type: str = Field(description="mindmap / code / ppt")


# ======================================================================
# 资源类型白名单
# ======================================================================

ALLOWED_RESOURCE_TYPES: tuple[str, ...] = (
    "content",
    "quiz",
    "mindmap",
    "code",
    "reading",
    "ppt",
)


# ======================================================================
# Agent 结构化输出模型
# ======================================================================


class NodeResourcePolicy(BaseModel):
    """资源推送策略 — 每个路径节点推荐生成哪些资源。"""

    primary_resource_type: str = Field(description="主要资源类型，如 'content'")
    required_resource_types: list[str] = Field(description="必须生成的资源类型列表")
    optional_resource_types: list[str] = Field(default_factory=list, description="可选增强资源类型列表")
    assessment_type: str = Field(default="quiz", description="掌握度评估方式: 'quiz', 'code', 'none'")
    generation_focus: list[str] = Field(default_factory=list, description="资源生成内容重点提示")
    personalization_reason: str = Field(description="为什么此策略适合该学习者")
    expected_resource_count: int = Field(default=2, ge=1, le=6, description="预期生成资源数量")


class LearningSignalSnapshot(BaseModel):
    """学习效果摘要 — 路径调整用的聚合信号。"""

    average_score: float | None = Field(default=None, description="平均测验分数 0-100")
    weak_topics: list[str] = Field(default_factory=list, description="薄弱知识点")
    preferred_resources: list[str] = Field(default_factory=list, description="偏好资源类型")
    negative_feedback: list[str] = Field(default_factory=list, description="负面反馈摘要")
    completed_resource_count: int = Field(default=0)
    viewed_resource_count: int = Field(default=0)
    active_minutes: int = Field(default=0)
    recommendations: list[str] = Field(default_factory=list, description="系统调整建议")


class LearningPathTutorialDTO(BaseModel):
    id: int
    tutorial_type: str
    version_no: int
    based_on_tutorial_id: int | None = None
    title: str
    summary: str | None = None
    content_markdown: str
    knowledge_points: list[str] = Field(default_factory=list)
    weak_knowledge_points: list[str] = Field(default_factory=list)
    created_at: str

    @classmethod
    def from_model(cls, tutorial: PathNodeTutorial) -> LearningPathTutorialDTO:
        return cls(
            id=tutorial.id,
            tutorial_type=tutorial.tutorial_type,
            version_no=tutorial.version_no,
            based_on_tutorial_id=tutorial.based_on_tutorial_id,
            title=tutorial.title,
            summary=tutorial.summary,
            content_markdown=tutorial.content_markdown,
            knowledge_points=list(tutorial.knowledge_points or []),
            weak_knowledge_points=list(tutorial.weak_knowledge_points or []),
            created_at=tutorial.created_at.isoformat() if tutorial.created_at else "",
        )


class LearningPathQuestionDTO(BaseModel):
    id: int
    question_no: int
    round_no: int
    mode: str
    type: str
    question: str
    choice: dict[str, Any] = Field(default_factory=dict)
    answer: str
    response: str | None = None
    analysis: str | None = None
    knowledge_points: list[str] = Field(default_factory=list)
    is_correct: bool | None = None

    @classmethod
    def from_model(cls, question: PathNodeQuestion) -> LearningPathQuestionDTO:
        return cls(
            id=question.id,
            question_no=question.question_no,
            round_no=question.round_no,
            mode=question.mode,
            type=question.type,
            question=question.question,
            choice=dict(question.choice or {}),
            answer=question.answer,
            response=question.response,
            analysis=question.analysis,
            knowledge_points=list(question.knowledge_points or []),
            is_correct=question.is_correct,
        )


class LearningPathResourceDTO(BaseModel):
    id: int
    resource_type: str
    version_no: int
    title: str
    content_format: str
    content_text: str | None = None
    content_json: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str

    @classmethod
    def from_model(cls, resource: PathNodeResource) -> LearningPathResourceDTO:
        return cls(
            id=resource.id,
            resource_type=resource.resource_type,
            version_no=resource.version_no,
            title=resource.title,
            content_format=resource.content_format,
            content_text=resource.content_text,
            content_json=resource.content_json,
            metadata=dict(resource.metadata_json or {}),
            created_at=resource.created_at.isoformat() if resource.created_at else "",
        )


class LearningPathNodeDTO(BaseModel):
    id: int
    node_id: str
    stage_id: str
    title: str
    status: str
    priority: int
    attempt_count: int
    mastery_target: str | None = None
    estimated_minutes: int | None = None
    difficulty: str | None = None
    recommendation_reason: str | None = None
    prerequisites: list[str] = Field(default_factory=list)
    resource_policy: NodeResourcePolicy | None = None
    current_tutorial_id: int | None = None

    @classmethod
    def from_model(cls, node: PathNode) -> LearningPathNodeDTO:
        return cls(
            id=node.id,
            node_id=node.node_id,
            stage_id=node.stage_id,
            title=node.title,
            status=node.status,
            priority=node.priority,
            attempt_count=node.attempt_count,
            mastery_target=node.mastery_target,
            estimated_minutes=node.estimated_minutes,
            difficulty=node.difficulty,
            recommendation_reason=node.recommendation_reason,
            prerequisites=list(node.prerequisites or []),
            resource_policy=dict(node.resource_policy) if node.resource_policy else None,
            current_tutorial_id=node.current_tutorial_id,
        )


class LearningPathOverviewResponse(BaseModel):
    id: int
    module: str
    title: str
    goal: str
    topic: str | None = None
    overall_progress: int
    eta_days: int
    confidence: int
    status: str
    current_node_key: str | None = None
    strategy_report: str | None = None
    adjustment_rationale: list[str] = Field(default_factory=list)
    stages: list[dict[str, Any]] = Field(default_factory=list)
    nodes: list[LearningPathNodeDTO] = Field(default_factory=list)
    created_at: str
    updated_at: str


class LearningPathHistoryItem(BaseModel):
    id: int
    title: str
    goal: str
    topic: str | None = None
    overall_progress: int
    status: str
    current_node_key: str | None = None
    updated_at: str


class LearningPathNodeWorkspaceResponse(BaseModel):
    path: LearningPathOverviewResponse
    node: LearningPathNodeDTO
    current_tutorial: LearningPathTutorialDTO | None = None
    tutorials: list[LearningPathTutorialDTO] = Field(default_factory=list)
    resources: list[LearningPathResourceDTO] = Field(default_factory=list)
    current_round: int = 0
    quiz_available: bool = False


class PathQuizRoundResponse(BaseModel):
    node_id: int
    tutorial_id: int | None = None
    round_no: int
    questions: list[LearningPathQuestionDTO] = Field(default_factory=list)


class PathQuizAnswerItem(BaseModel):
    question_id: int
    response: str


class PathQuizSubmitRequest(BaseModel):
    answers: list[PathQuizAnswerItem] = Field(default_factory=list, min_length=5, max_length=5)


class PathQuizSubmitResponse(BaseModel):
    node_id: int
    round_no: int
    score: int
    passed: bool
    outcome: str
    weak_knowledge_points: list[str] = Field(default_factory=list)
    next_node_id: int | None = None
    current_tutorial_id: int | None = None


class AgentQuestionItem(BaseModel):
    question: str = Field(description="题干")
    choice: dict[str, str] = Field(default_factory=dict, description="选项映射，如 {'A': 'xxx'}")
    answer: str = Field(description="正确答案，如 A")
    analysis: str = Field(default="", description="题目解析")
    knowledge_points: list[str] = Field(default_factory=list, description="涉及知识点")
    type: str = Field(default="single_choice", description="题型")


class AgentQuestionSet(BaseModel):
    questions: list[AgentQuestionItem] = Field(default_factory=list, min_length=0, max_length=5)


class AgentPathNode(BaseModel):
    """规划 Agent 输出的单个路径节点。"""

    node_id: str = Field(description="节点唯一标识")
    stage_id: str = Field(description="阶段标识")
    title: str = Field(description="节点标题")
    prerequisites: list[str] = Field(default_factory=list, description="前置节点 ID")
    mastery_target: str = Field(default="", description="掌握目标")
    estimated_minutes: int = Field(default=30, description="预估学习时间(分钟)")
    difficulty: str = Field(default="intermediate", description="难度等级")
    recommendation_reason: str = Field(default="", description="推荐理由")
    priority: int = Field(default=0, description="优先级")
    resource_policy: NodeResourcePolicy | None = Field(default=None, description="资源推送策略")


class AgentStage(BaseModel):
    """规划 Agent 输出的阶段。"""
    
    stage_id: str = Field(description="阶段标识，如'stage-1'")
    title: str = Field(description="阶段标题")
    description: str = Field(description="阶段描述")


class AgentLearningPathPlan(BaseModel):
    """规划 Agent 的结构化输出。"""

    title: str = Field(description="路径标题")
    eta_days: int = Field(default=14, description="预估学习天数")
    confidence: int = Field(default=60, ge=0, le=100, description="规划置信度百分比")
    strategy_report: str = Field(default="", description="个性化诊断与裁剪策略报告")
    adjustment_rationale: list[str] = Field(default_factory=list, description="调整理由列表")
    stages: list[AgentStage] = Field(default_factory=list, description="宏观阶段骨架列表")
    nodes: list[AgentPathNode] = Field(default_factory=list, description="所有阶段的具体学习节点列表")

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, value: Any) -> Any:
        if isinstance(value, float) and 0 <= value <= 1:
            return round(value * 100)
        return value

    @field_validator("adjustment_rationale", mode="before")
    @classmethod
    def normalize_adjustment_rationale(cls, value: Any) -> Any:
        if isinstance(value, str):
            stripped = value.strip()
            return [stripped] if stripped else []
        return value


class PathLearningEvaluationResponse(BaseModel):
    """路径内学习效果评估响应。"""

    path_id: int
    overall_progress: float = 0.0
    current_node_key: str | None = None
    signal_snapshot: LearningSignalSnapshot = Field(default_factory=LearningSignalSnapshot)
    needs_optimization: bool = False
    optimization_tips: list[str] = Field(default_factory=list)


__all__ = [
    # Request
    "CreateLearningPathRequest",
    "AuxiliaryResourceRequest",
    # Agent output
    "AgentPathNode",
    "AgentStage",
    "AgentLearningPathPlan",
    "AgentQuestionItem",
    "AgentQuestionSet",
    # Resource policy
    "NodeResourcePolicy",
    "LearningSignalSnapshot",
    "ALLOWED_RESOURCE_TYPES",
    # Response
    "LearningPathQuestionDTO",
    "LearningPathResourceDTO",
    "LearningPathTutorialDTO",
    "LearningPathNodeDTO",
    "LearningPathOverviewResponse",
    "LearningPathHistoryItem",
    "LearningPathNodeWorkspaceResponse",
    "PathQuizRoundResponse",
    "PathQuizSubmitRequest",
    "PathQuizSubmitResponse",
    "PathLearningEvaluationResponse",
]
