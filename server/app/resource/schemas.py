"""
资源生成模块 Schema 定义。

包含：
- 枚举类型定义（ResourceAgentId, LearningGoal 等）
- 请求结构（ResourceGenerationRequest）
- Agent 配置结构（ContentAgentConfig, DiagramAgentConfig 等）
- 输出结构（GeneratedResourceItem, ResourceBundle）
- 工作流状态（WorkerState, WorkerResult, WorkflowState）
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
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


class LearningGoal(str, Enum):
    """学习目标枚举。"""
    PREVIEW = "preview"
    REVIEW = "review"
    EXAM = "exam"
    HOMEWORK = "homework"
    PRACTICE = "practice"
    DEEP_UNDERSTANDING = "deep_understanding"
    PROJECT_APPLICATION = "project_application"
    INTERVIEW = "interview"


class CurrentLevel(str, Enum):
    """当前水平枚举。"""
    ZERO = "zero"
    BASIC = "basic"
    NORMAL = "normal"
    GOOD = "good"
    ADVANCED = "advanced"


class TargetLevel(str, Enum):
    """目标水平枚举。"""
    UNDERSTAND = "understand"
    SOLVE_PROBLEM = "solve_problem"
    WRITE_CODE = "write_code"
    EXPLAIN_TO_OTHERS = "explain_to_others"
    APPLY_IN_PROJECT = "apply_in_project"


class ExplanationStyle(str, Enum):
    """讲解风格枚举。"""
    EASY = "easy"
    EXAM = "exam"
    TEXTBOOK = "textbook"
    PRACTICE = "practice"
    ANALOGY = "analogy"
    INTERVIEW = "interview"


class ContentDepth(str, Enum):
    """内容深度枚举。"""
    QUICK = "quick"
    STANDARD = "standard"
    STEP_BY_STEP = "step_by_step"
    DEEP = "deep"


class ExamplePreference(str, Enum):
    """示例偏好枚举。"""
    REAL_WORLD = "real_world"
    CODE = "code"
    EXAM = "exam"
    ENGINEERING = "engineering"
    VISUAL = "visual"


class OutputLanguage(str, Enum):
    """输出语言枚举。"""
    ZH = "zh"
    EN = "en"
    BILINGUAL = "bilingual"


class AgentStatus(str, Enum):
    """Agent 执行状态枚举。"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# =============================================================================
# 请求结构
# =============================================================================

class LearningTaskInput(BaseModel):
    """学习任务输入。"""
    course: str = Field(min_length=1, description="课程名称，不能为空")
    chapter: str = Field(default="", description="章节")
    topic: str = Field(min_length=1, description="学习主题，不能为空")
    weak_points: list[str] = Field(default_factory=list, description="知识短板标签列表")
    learning_goal: LearningGoal = Field(default=LearningGoal.REVIEW, description="学习目标")
    extra_requirement: str = Field(default="", description="用户补充要求")

    @field_validator("course", "topic")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("course 和 topic 不能为空字符串")
        return value

    @field_validator("weak_points", mode="before")
    @classmethod
    def validate_weak_points(cls, value: Any) -> list[str]:
        if value is None:
            return []
        return value


class PersonalizationConfig(BaseModel):
    """个性化配置。"""
    current_level: CurrentLevel = Field(default=CurrentLevel.BASIC, description="当前水平")
    target_level: TargetLevel = Field(default=TargetLevel.UNDERSTAND, description="目标水平")
    explanation_style: ExplanationStyle = Field(default=ExplanationStyle.EASY, description="讲解风格")
    content_depth: ContentDepth = Field(default=ContentDepth.STANDARD, description="内容深度")
    example_preference: ExamplePreference = Field(default=ExamplePreference.VISUAL, description="示例偏好")
    output_language: OutputLanguage = Field(default=OutputLanguage.ZH, description="输出语言")


class AgentSelection(BaseModel):
    """Agent 选择项。"""
    agent_id: ResourceAgentId = Field(description="Agent ID")
    enabled: bool = Field(default=True, description="是否启用")
    priority: int = Field(default=0, ge=0, description="优先级，数值越小越优先")


class ContentAgentConfig(BaseModel):
    """内容讲解 Agent 配置。"""
    structure: str = Field(default="progressive", description="结构类型: progressive/summary_first/qa/exam_points/case_driven")
    include_summary: bool = Field(default=True, description="是否包含总结")
    include_key_points: bool = Field(default=True, description="是否包含要点")
    include_common_mistakes: bool = Field(default=True, description="是否包含常见错误")
    include_memory_tips: bool = Field(default=True, description="是否包含记忆技巧")
    include_examples: bool = Field(default=True, description="是否包含示例")


class MindmapAgentConfig(BaseModel):
    """思维导图 Agent 配置。"""
    map_type: str = Field(default="knowledge_tree", description="导图类型: knowledge_tree/exam_map/flow_map/comparison_map/review_outline")
    max_depth: int = Field(default=4, ge=2, le=5, description="最大深度，范围 2-5")
    focus_on_weak_points: bool = Field(default=True, description="是否聚焦短板")
    include_exam_points: bool = Field(default=True, description="是否包含考点")
    include_common_mistakes: bool = Field(default=True, description="是否包含常见错误")
    output_format: str = Field(default="markdown", description="输出格式")


class DiagramAgentConfig(BaseModel):
    """知识图解 Agent 配置。"""
    diagram_type: str = Field(default="auto", description="图解类型: auto/concept_map/flowchart/sequence/state_transition/structure/comparison")
    render_format: str = Field(default="mermaid", description="渲染格式")
    visual_style: str = Field(default="minimal", description="视觉风格: minimal/blackboard/infographic/exam")
    include_explanation: bool = Field(default=True, description="是否包含说明")
    highlight_weak_points: bool = Field(default=True, description="是否高亮短板")


class QuizAgentConfig(BaseModel):
    """习题 Agent 配置。"""
    question_count: int = Field(default=10, ge=1, le=50, description="题目数量，范围 1-50")
    question_types: list[str] = Field(
        default_factory=lambda: ["choice", "blank", "short_answer"],
        description="题型列表: choice/multiple_choice/true_false/blank/short_answer/coding/case_analysis"
    )
    difficulty_mode: str = Field(default="adaptive", description="难度模式: basic/standard/exam/adaptive")
    difficulty_distribution: dict[str, int] = Field(
        default_factory=lambda: {"easy": 4, "medium": 4, "hard": 2},
        description="难度分布"
    )
    focus_on_weak_points: bool = Field(default=True, description="是否聚焦短板")
    include_answer: bool = Field(default=True, description="是否包含答案")
    include_analysis: bool = Field(default=True, description="是否包含解析")
    include_wrong_reason: bool = Field(default=True, description="是否包含错误原因")
    include_knowledge_tags: bool = Field(default=True, description="是否包含知识点标签")


class ReadingAgentConfig(BaseModel):
    """拓展阅读 Agent 配置。"""
    reading_depth: str = Field(
        default="course_extended",
        description="阅读深度: introductory/course_extended/exam/engineering/frontier"
    )
    source_types: list[str] = Field(
        default_factory=lambda: ["textbook", "article", "documentation"],
        description="来源类型: textbook/article/documentation/paper/practice_project"
    )
    max_items: int = Field(default=5, ge=1, le=20, description="最大条目数，范围 1-20")
    include_reason: bool = Field(default=True, description="是否包含推荐理由")
    include_reading_order: bool = Field(default=True, description="是否包含阅读顺序")


class CodeAgentConfig(BaseModel):
    """代码实操 Agent 配置。"""
    programming_language: str = Field(
        default="cpp",
        description="编程语言: c/cpp/java/python/go/javascript"
    )
    case_type: str = Field(
        default="basic_demo",
        description="案例类型: basic_demo/algorithm_template/experiment_task/debug_demo/mini_project"
    )
    include_comments: bool = Field(default=True, description="是否包含注释")
    include_input_output: bool = Field(default=True, description="是否包含输入输出示例")
    include_complexity: bool = Field(default=True, description="是否包含复杂度分析")
    include_debug_tips: bool = Field(default=True, description="是否包含调试技巧")
    include_exercises: bool = Field(default=True, description="是否包含练习题")


class AgentConfigs(BaseModel):
    """Agent 配置集合。"""
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
AGENT_DEFAULT_ORDER = ["content", "diagram", "mindmap", "code", "quiz", "reading"]

DEFAULT_SELECTED_AGENT_IDS = [
    ResourceAgentId.CONTENT,
    ResourceAgentId.DIAGRAM,
    ResourceAgentId.MINDMAP,
    ResourceAgentId.CODE,
    ResourceAgentId.QUIZ,
    ResourceAgentId.READING,
]


class ResourceGenerationRequest(BaseModel):
    """资源生成请求。"""
    task: LearningTaskInput = Field(description="学习任务")
    personalization: PersonalizationConfig = Field(default_factory=PersonalizationConfig, description="个性化配置")
    selected_agents: list[AgentSelection] = Field(default_factory=list, description="选中的 Agent")
    agent_configs: AgentConfigs = Field(default_factory=AgentConfigs, description="Agent 配置")
    output_options: OutputOptions = Field(default_factory=OutputOptions, description="输出选项")

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


class ResourceBundle(BaseModel):
    """资源包。"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    task_id: str = Field(description="任务 ID")
    title: str = Field(description="资源包标题")
    task: LearningTaskInput = Field(description="学习任务")
    personalization: PersonalizationConfig = Field(description="个性化配置")
    selected_agents: list[AgentSelection] = Field(default_factory=list, description="选中的 Agent")
    resources: list[GeneratedResourceItem] = Field(default_factory=list, description="资源列表")
    study_path: list[StudyPathStep] = Field(default_factory=list, description="学习路径")
    review_result: Optional[ReviewResult] = Field(default=None, description="审查结果")
    status: str = Field(default="completed", description="状态: completed/partial_completed/failed")
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
    learner_profile: dict[str, Any] = Field(default_factory=dict, description="学习者画像")
    personalization: dict[str, Any] = Field(default_factory=dict, description="个性化配置")
    agent_config: dict[str, Any] = Field(default_factory=dict, description="当前 Agent 专属配置")
    workflow_plan: list[dict[str, Any]] = Field(default_factory=list, description="工作流计划")
    dependencies: list[str] = Field(default_factory=list, description="依赖的 Agent")
    upstream_results: dict[str, Any] = Field(default_factory=dict, description="上游结果")
    dependency_reports: dict[str, Any] = Field(default_factory=dict, description="依赖报告")
    layer_index: int = Field(default=0, description="当前层索引")

    # 兼容旧字段
    profile: dict[str, Any] = Field(default_factory=dict, description="学习者画像（兼容旧字段）")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Agent 参数（兼容旧字段）")
    dependency_artifacts: dict[str, str] = Field(default_factory=dict, description="依赖产物（兼容旧字段）")


class WorkerResult(BaseModel):
    """Worker Agent 执行结果。"""
    model_config = ConfigDict(extra="allow")

    success: bool = Field(default=False, description="是否成功")
    content: Any = Field(default=None, description="生成的内容")
    file_type: str = Field(default="json", description="文件类型")
    title: str | None = Field(default=None, description="资源标题")
    summary: str = Field(default="", description="资源摘要")
    execution_report: str | None = Field(default=None, description="Agent 执行报告")
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
    profile_markdown: str | None = None
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
        return self.model_dump(exclude_none=True)


class LayerPlan(BaseModel):
    """分层规划结构。"""
    model_config = ConfigDict(extra="allow")

    layer_index: int = Field(default=0, description="层索引")
    reason: str = Field(default="", description="为什么执行这一层")
    agents: list[str] = Field(default_factory=list, description="当前层执行的 Agent")
    dependencies: dict[str, list[str]] = Field(default_factory=dict, description="依赖关系")
    agent_parameters: dict[str, dict[str, Any]] = Field(default_factory=dict, description="Agent 参数")
    expected_outputs: dict[str, str] = Field(default_factory=dict, description="每个 Agent 要做什么")
    visible_agents: list[str] = Field(default_factory=list, description="对用户可见的 Agent")
    hidden_dependency_agents: list[str] = Field(default_factory=list, description="依赖补全的隐藏 Agent")
    failure_policy: dict[str, str] = Field(default_factory=dict, description="失败策略")
    stop_after_this_layer: bool = Field(default=False, description="是否在当前层后停止")


class WorkflowState(BaseModel):
    """主流程状态。"""
    model_config = ConfigDict(extra="allow")

    user_id: int = Field(default=0)
    task_id: str = Field(default="")
    resource_id: int | str | None = Field(default=None)
    request: ResourceGenerationRequest | None = Field(default=None)
    task: LearningTaskInput | None = Field(default=None)
    personalization: PersonalizationConfig | None = Field(default=None)
    selected_agents: list[AgentSelection] = Field(default_factory=list)
    agent_configs: AgentConfigs | None = Field(default=None)
    output_options: OutputOptions | None = Field(default=None)
    learner_profile: dict[str, Any] = Field(default_factory=dict)
    workflow_plan: list[dict[str, Any]] = Field(default_factory=list)
    current_layer: int = Field(default=0)
    completed_agents: list[str] = Field(default_factory=list)
    failed_agents: list[str] = Field(default_factory=list)
    skipped_agents: list[str] = Field(default_factory=list)
    resources: list[GeneratedResourceItem] = Field(default_factory=list)
    upstream_results: dict[str, Any] = Field(default_factory=dict)
    review_result: ReviewResult | None = Field(default=None)
    bundle: ResourceBundle | None = Field(default=None)
    errors: list[str] = Field(default_factory=list)
    status: str = Field(default="pending")


class ResourcePlan(BaseModel):
    """资源计划。"""
    execution_groups: list[list[str]] = Field(default_factory=list)
    failure_policy: dict[str, str] = Field(default_factory=dict)
    core_agents: list[str] = Field(default_factory=list)
    enhancement_agents: list[str] = Field(default_factory=list)
    presentation_agents: list[str] = Field(default_factory=list)
    requested_agents: list[str] = Field(default_factory=list)
    execution_agents: list[str] = Field(default_factory=list)
    visible_agents: list[str] = Field(default_factory=list)
    hidden_dependency_agents: list[str] = Field(default_factory=list)
    dependencies: dict[str, list[str]] = Field(default_factory=dict)
    agent_parameters: dict[str, dict[str, Any]] = Field(default_factory=dict)

    @property
    def ordered_agents(self) -> list[str]:
        if self.execution_groups:
            ordered: list[str] = []
            for group in self.execution_groups:
                for agent in group:
                    if agent not in ordered:
                        ordered.append(agent)
            return ordered
        return self.core_agents + self.enhancement_agents + self.presentation_agents
