"""
资源生成模块 Schema 定义。

包含：
- 枚举类型定义（ResourceAgentId 等）
- 请求结构（ResourceGenerationRequest）
- Agent 配置结构（ContentAgentConfig, DiagramAgentConfig 等）
- 输出结构（GeneratedResourceItem, ResourceBundle）
- 工作流状态（WorkerState, WorkerResult）
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional

# 规划模式：rule=规则一次性规划, single_llm=单次LLM规划, layer_llm=分层LLM规划
PlanningMode = Literal["rule", "single_llm", "layer_llm"]
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# =============================================================================
# 枚举类型定义
# =============================================================================

class ResourceAgentId(str, Enum):
    """资源 Agent ID 枚举。仅支持 6 个活跃 Agent。"""
    CONTENT = "content"
    MINDMAP = "mindmap"
    DIAGRAM = "diagram"
    QUIZ = "quiz"
    READING = "reading"
    CODE = "code"


class AgentStatus(str, Enum):
    """Agent 执行状态枚举。"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class LearningScenario(str, Enum):
    """学习场景枚举。"""
    EXAM_PREP = "exam_prep"
    DAILY_REVIEW = "daily_review"
    PROJECT_PRACTICE = "project_practice"
    SELF_STUDY = "self_study"


# =============================================================================
# 请求结构
# =============================================================================

class AgentSelection(BaseModel):
    """Agent 选择项。"""
    agent_id: ResourceAgentId = Field(description="Agent ID")
    enabled: bool = Field(default=True, description="是否启用")
    priority: int = Field(default=0, ge=0, description="优先级，数值越小越优先")


class ContentAgentConfig(BaseModel):
    """内容讲解 Agent 配置。"""
    model_config = ConfigDict(extra="forbid")

    structure: Literal["progressive", "summary_first", "exam_points", "case_driven"] = Field(
        default="progressive",
        description="结构类型: progressive/summary_first/exam_points/case_driven",
    )
    include_common_mistakes: bool = Field(default=True, description="是否包含常见错误")
    include_examples: bool = Field(default=True, description="是否包含示例")
    focus_mode: Literal["weak_points", "key_concepts", "full_coverage"] = Field(
        default="full_coverage",
        description="聚焦模式: weak_points/key_concepts/full_coverage",
    )
    depth_level: Literal["quick", "standard", "deep"] = Field(
        default="standard",
        description="深度级别: quick/standard/deep",
    )


class MindmapAgentConfig(BaseModel):
    """思维导图 Agent 配置。"""
    model_config = ConfigDict(extra="forbid")

    map_type: Literal["knowledge_tree", "exam_map", "comparison_map"] = Field(
        default="knowledge_tree",
        description="导图类型: knowledge_tree/exam_map/comparison_map",
    )
    max_depth: int = Field(default=4, ge=2, le=5, description="最大深度，范围 2-5")
    highlight_weak: bool = Field(default=True, description="是否高亮短板")
    expand_weak_points: bool = Field(default=False, description="是否展开薄弱点分支")
    include_prerequisites: bool = Field(default=False, description="是否包含前置知识")


class DiagramAgentConfig(BaseModel):
    """知识图解 Agent 配置。"""
    model_config = ConfigDict(extra="forbid")

    diagram_type: Literal[
        "auto",
        "hierarchy",
        "flow",
        "compare",
        "relation",
        "state",
        "class",
        "er",
        "block",
        "packet",
        "git",
        "sequence",
        "activity",
        "usecase",
        "component",
        "package",
        "deployment",
        "object",
        "communication",
    ] = Field(
        default="auto",
        description="图解类型: auto/hierarchy/flow/compare/relation/state/class/er/block/packet/git/sequence/activity/usecase/component/package/deployment/object/communication",
    )
    visual_style: Literal["minimal", "exam"] = Field(default="minimal", description="视觉风格: minimal/exam")
    highlight_mode: Literal["weak_points", "key_points", "all"] = Field(
        default="key_points",
        description="高亮模式",
    )
    detail_level: Literal["concise", "standard", "detailed"] = Field(
        default="standard",
        description="细节级别",
    )


class QuizAgentConfig(BaseModel):
    """习题 Agent 配置。"""
    model_config = ConfigDict(extra="forbid")

    question_count: int = Field(default=10, ge=1, le=20, description="题目数量，范围 1-20")
    difficulty_mode: Literal["basic", "adaptive", "exam"] = Field(default="adaptive", description="难度模式: basic/adaptive/exam")
    weak_point_weight: int = Field(default=50, ge=0, le=100, description="薄弱点出题权重 0-100")
    exam_style: Literal["school", "考研", "考证", "interview"] = Field(
        default="school",
        description="考试风格",
    )
    include_analysis: bool = Field(default=True, description="是否包含详细解析")


class ReadingAgentConfig(BaseModel):
    """拓展阅读 Agent 配置。"""
    model_config = ConfigDict(extra="forbid")

    reading_depth: Literal["course_extended", "engineering", "frontier"] = Field(
        default="course_extended",
        description="阅读深度: course_extended/engineering/frontier"
    )
    max_items: int = Field(default=5, ge=1, le=10, description="最大条目数，范围 1-10")
    resource_quality: Literal["classic", "latest", "balanced"] = Field(
        default="balanced",
        description="资源时效偏好",
    )
    include_practice: bool = Field(default=False, description="是否包含实践资源")
    language_preference: Literal["chinese", "english", "both"] = Field(
        default="chinese",
        description="语言偏好",
    )


class CodeAgentConfig(BaseModel):
    """代码实操 Agent 配置。"""
    model_config = ConfigDict(extra="forbid")

    programming_language: Literal["python", "cpp", "java", "go", "javascript"] = Field(
        default="python",
        description="编程语言: python/cpp/java/go/javascript"
    )
    case_type: Literal["basic_demo", "algorithm_template", "debug_demo"] = Field(
        default="basic_demo",
        description="案例类型: basic_demo/algorithm_template/debug_demo"
    )
    comment_level: Literal["minimal", "standard", "verbose"] = Field(
        default="standard",
        description="注释详细程度",
    )
    include_test: bool = Field(default=False, description="是否包含测试用例")
    difficulty: Literal["beginner", "intermediate", "advanced"] = Field(
        default="beginner",
        description="代码难度",
    )


class AgentConfigs(BaseModel):
    """Agent 配置集合。"""
    model_config = ConfigDict(extra="forbid")

    content: ContentAgentConfig = Field(default_factory=ContentAgentConfig)
    mindmap: MindmapAgentConfig = Field(default_factory=MindmapAgentConfig)
    diagram: DiagramAgentConfig = Field(default_factory=DiagramAgentConfig)
    quiz: QuizAgentConfig = Field(default_factory=QuizAgentConfig)
    reading: ReadingAgentConfig = Field(default_factory=ReadingAgentConfig)
    code: CodeAgentConfig = Field(default_factory=CodeAgentConfig)


class OutputOptions(BaseModel):
    """输出选项。"""
    final_bundle_title: Optional[str] = Field(default=None, description="资源包标题")
    output_format: str = Field(default="json", description="输出格式")
    include_study_path: bool = Field(default=True, description="是否包含学习路径")
    include_agent_trace: bool = Field(default=True, description="是否包含 Agent 执行轨迹")
    include_review_result: bool = Field(default=True, description="是否包含审查结果")


# Agent 默认排序顺序
AGENT_DEFAULT_ORDER = ["content", "mindmap", "diagram", "code", "quiz", "reading"]

DEFAULT_SELECTED_AGENT_IDS = [
    ResourceAgentId.CONTENT,
    ResourceAgentId.MINDMAP,
    ResourceAgentId.DIAGRAM,
    ResourceAgentId.CODE,
    ResourceAgentId.QUIZ,
    ResourceAgentId.READING,
]


class ResourceGenerationRequest(BaseModel):
    """资源生成请求。"""
    model_config = ConfigDict(extra="forbid")

    learning_need: str = Field(min_length=1, description="用户自然语言输入的学习需求，包含课程、主题、薄弱点等所有信息")
    learning_scenario: LearningScenario = Field(
        default=LearningScenario.DAILY_REVIEW,
        description="学习场景",
    )
    planning_mode: PlanningMode = Field(default="rule", description="规划模式: rule/single_llm/layer_llm")
    selected_agents: list[AgentSelection] = Field(default_factory=list, description="选中的 Agent")
    agent_configs: AgentConfigs = Field(default_factory=AgentConfigs, description="Agent 配置")
    output_options: OutputOptions = Field(default_factory=OutputOptions, description="输出选项")

    @field_validator("learning_need")
    @classmethod
    def validate_learning_need(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("学习需求不能为空")
        return value

    @model_validator(mode="after")
    def validate_selection(self) -> "ResourceGenerationRequest":
        """校验 Agent 选择。"""
        if not self.selected_agents:
            self.selected_agents = [AgentSelection(agent_id=a) for a in DEFAULT_SELECTED_AGENT_IDS]
        enabled = [x for x in self.selected_agents if x.enabled]
        if not enabled:
            raise ValueError("selected_agents 过滤 enabled=true 后不能为空")
        order_map = {agent: idx for idx, agent in enumerate(AGENT_DEFAULT_ORDER)}
        self.selected_agents = sorted(
            self.selected_agents,
            key=lambda x: (x.priority, order_map.get(x.agent_id.value, 999)),
        )
        return self

    def enabled_agent_ids(self) -> list[str]:
        """获取启用的 Agent ID 列表，按优先级和默认顺序排序。"""
        enabled = [x for x in self.selected_agents if x.enabled]
        order_map = {agent: idx for idx, agent in enumerate(AGENT_DEFAULT_ORDER)}
        enabled.sort(key=lambda x: (x.priority, order_map.get(x.agent_id.value, 999)))
        result: list[str] = []
        for item in enabled:
            agent_id = item.agent_id.value
            if agent_id not in result:
                result.append(agent_id)
        return result


# =============================================================================
# 输出结构
# =============================================================================

class GeneratedResourceItem(BaseModel):
    """生成的资源项。"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: ResourceAgentId = Field(description="资源类型")
    title: str = Field(description="资源标题")
    format: str = Field(description="格式: markdown/json/mermaid/code")
    content: Any = Field(description="资源内容")
    summary: str = Field(default="", description="资源摘要")
    summary_data: dict[str, Any] = Field(default_factory=dict, description="结构化摘要，供下游Agent轻量交接")
    execution_report: str | None = Field(default=None, description="Agent 执行报告")
    metadata: dict[str, Any] = Field(default_factory=dict, description="元数据")


class StudyPathStep(BaseModel):
    """学习路径步骤。"""
    order: int = Field(description="步骤序号")
    resource_type: ResourceAgentId = Field(description="资源类型")
    title: str = Field(description="步骤标题")
    reason: str = Field(description="推荐理由")
    estimated_time: Optional[int] = Field(default=None, description="预计时间（分钟）")


class ReviewIssue(BaseModel):
    """审查问题。"""
    resource_type: Optional[ResourceAgentId] = Field(default=None, description="相关资源类型")
    level: str = Field(description="问题级别: info/warning/error")
    message: str = Field(description="问题描述")
    suggestion: str = Field(default="", description="改进建议")


class ReviewResult(BaseModel):
    """审查结果。"""
    passed: bool = Field(description="是否通过")
    score: int = Field(default=0, ge=0, le=100, description="评分 0-100")
    issues: list[ReviewIssue] = Field(default_factory=list, description="问题列表")
    suggestions: list[str] = Field(default_factory=list, description="改进建议")
    failed_agents: list[str] = Field(default_factory=list, description="失败Agent列表")
    skipped_agents: list[str] = Field(default_factory=list, description="跳过Agent列表")


class ResourceBundle(BaseModel):
    """资源包。"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    task_id: str = Field(description="任务 ID")
    title: str = Field(description="资源包标题")
    learning_need: str = Field(description="学习需求")
    selected_agents: list[AgentSelection] = Field(default_factory=list, description="选中的 Agent")
    resources: list[GeneratedResourceItem] = Field(default_factory=list, description="资源列表")
    study_path: list[StudyPathStep] = Field(default_factory=list, description="学习路径")
    review_result: Optional[ReviewResult] = Field(default=None, description="审查结果")
    status: str = Field(default="completed", description="状态: completed/completed_with_warnings/partial_completed/failed")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict, description="元数据")


# =============================================================================
# 工作流状态
# =============================================================================

class WorkerState(BaseModel):
    """Worker Agent 执行状态。"""
    model_config = ConfigDict(extra="allow")

    user_id: int = Field(default=0, description="用户 ID")
    resource_id: int | str = Field(default=0, description="资源 ID")
    agent_name: str = Field(description="Agent 名称")
    task: dict[str, Any] = Field(default_factory=dict, description="任务参数")
    learner_profile: dict[str, Any] = Field(default_factory=dict, description="后端加载的学习者画像")
    agent_config: dict[str, Any] = Field(default_factory=dict, description="当前 Agent 专属配置")
    workflow_plan: list[dict[str, Any]] = Field(default_factory=list, description="工作流计划")
    layer_index: int = Field(default=0, description="当前层索引")
    upstream_results: dict[str, Any] = Field(default_factory=dict, description="显式依赖 Agent 的轻量摘要")
    dependency_reports: dict[str, Any] = Field(default_factory=dict, description="依赖 Agent 交接报告")
    learning_scenario: str = Field(default="daily_review", description="学习场景")
    planner_input_params: dict[str, Any] = Field(default_factory=dict, description="MasterAgent 规划的动态输入参数")
    output_requirements: dict[str, Any] = Field(default_factory=dict, description="MasterAgent 规划的输出要求")
    personalized_constraints: list[str] = Field(default_factory=list, description="结合学习者画像生成的个性化约束")
    degraded: bool = Field(default=False, description="是否因依赖缺失而降级执行")
    missing_dependencies: list[str] = Field(default_factory=list, description="降级执行时缺失的依赖 Agent")
    failed_dependencies: list[str] = Field(default_factory=list, description="降级执行时失败的依赖 Agent")


class WorkerResult(BaseModel):
    """Worker Agent 执行结果。"""
    model_config = ConfigDict(extra="allow")

    success: bool = Field(default=False, description="是否成功")
    content: Any = Field(default=None, description="生成的内容")
    file_type: str = Field(default="json", description="文件类型")
    title: str | None = Field(default=None, description="资源标题")
    summary: str = Field(default="", description="资源摘要")
    summary_data: dict[str, Any] = Field(default_factory=dict, description="结构化摘要，供下游Agent轻量交接")
    metadata: dict[str, Any] = Field(default_factory=dict, description="资源元数据")
    error: str | None = Field(default=None, description="错误信息")


# =============================================================================
# 辅助类型
# =============================================================================

class LearnerProfileSnapshot(BaseModel):
    """学习者画像快照。"""
    user_id: int | None = None
    username: str | None = None
    major: str | None = None
    grade: str | None = None
    school: str | None = None
    profile_json: dict[str, Any] | None = None
    profile_score_json: dict[str, Any] | None = None
    version: int | None = None
    confidence: float | None = None
    updated_at: str | None = None

    @classmethod
    def from_sources(
        cls,
        user_data: dict[str, Any] | None = None,
        profile_data: dict[str, Any] | None = None,
    ) -> "LearnerProfileSnapshot":
        merged: dict[str, Any] = {}
        if user_data:
            merged.update(user_data)
        if profile_data:
            merged.update(profile_data)
        return cls.model_validate(merged)

    def as_agent_profile(self) -> dict[str, Any]:
        """返回 Agent 可用的画像字典。"""
        return self.model_dump(exclude_none=True)


# =============================================================================
# 动态规划数据结构
# =============================================================================

class AgentTask(BaseModel):
    """单个 Agent 的任务描述。"""
    agent_id: str = Field(description="Agent ID")
    layer: int = Field(default=0, description="所属规划层索引")
    layer_name: str | None = Field(default=None, description="所属规划层名称")
    task_description: str = Field(description="给该 Agent 的具体任务描述")
    depends_on: list[str] = Field(default_factory=list, description="依赖的上游 Agent")
    is_explicit: bool = Field(default=True, description="是否用户显式选择 (决定是否返回给前端)")
    priority: int = Field(default=0, description="执行优先级")
    config: dict[str, Any] = Field(default_factory=dict, description="Agent 专属配置")
    enabled: bool = Field(default=True, description="是否启用")
    resource_type: str | None = Field(default=None, description="资源类型")
    input_params: dict[str, Any] = Field(default_factory=dict, description="MasterAgent 为 WorkerAgent 规划的输入参数")
    output_requirements: dict[str, Any] = Field(default_factory=dict, description="MasterAgent 对输出格式和内容的要求")
    personalized_constraints: list[str] = Field(default_factory=list, description="个性化生成约束")
    planning_reason: str | None = Field(default=None, description="规划该 Agent 的理由")
    failure_policy: Literal["skip_on_dependency_failed", "degraded_run", "ignore_dependency"] = Field(
        default="skip_on_dependency_failed",
        description="依赖失败时的执行策略",
    )


class LayerPlan(BaseModel):
    """单层执行计划。"""
    layer: int = Field(description="层索引 (0, 1, 2)")
    agents: list[AgentTask] = Field(default_factory=list, description="本层要执行的 Agent 任务列表")
    reasoning: str = Field(default="", description="LLM 规划理由")
    fallback_used: bool = Field(default=False, description="是否使用规则兜底规划")


class PlanningContext(BaseModel):
    """MasterAgent 规划输入上下文。"""
    layer: int = Field(description="当前层 (0, 1, 2)")
    question: "ResourceGenerationRequest" = Field(description="用户原始请求")
    user_explicit_selection: list[str] = Field(default_factory=list, description="用户显式选择的 Agent ID")
    implicit_dependencies: list[str] = Field(default_factory=list, description="系统识别的隐式依赖")
    upstream_results: dict[str, Any] = Field(default_factory=dict, description="上游执行摘要")
    upstream_reports: dict[str, str] = Field(default_factory=dict, description="上游 Agent 执行报告")
    learner_profile: dict[str, Any] = Field(default_factory=dict, description="学习者画像摘要")

# 更新前向引用
ResourceGenerationRequest.model_rebuild()
