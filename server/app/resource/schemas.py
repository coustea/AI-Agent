"""Resource 模块统一数据契约与 DTO 模型 (app.resource.schemas)。

全面采用 Plan-and-Execute 架构，统一步伐与参数，消除冗余繁杂的单 Agent 独立配置。
"""

from __future__ import annotations

from enum import Enum, StrEnum
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ── 1. 任务生命周期与状态枚举 ──────────────────────────────────────────────


class ResourceLifecycleStatus(StrEnum):
    """资源生成总任务的生命周期状态。"""

    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class TaskStatus(StrEnum):
    """单个子任务 (SubAgent 任务) 的执行状态。"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ResourceAgentId(str, Enum):
    """资源 Agent 标识枚举（兼容定义）。"""

    CONTENT = "content"
    MINDMAP = "mindmap"
    QUIZ = "quiz"
    READING = "reading"
    CODE = "code"
    PPT = "ppt"
    CARTOON = "cartoon"


DifficultyLevel = Literal["beginner", "intermediate", "advanced"]
TaskType = Literal["text", "tool"]

SUPPORTED_RESOURCE_TYPES = [
    "content",
    "mindmap",
    "quiz",
    "code",
    "reading",
    "ppt",
    "cartoon",
]


# ── 2. 统一请求模型 ─────────────────────────────────────────────────────────


class ResourceGenerationRequest(BaseModel):
    """统一资源生成请求（前后端交互契约）。"""

    model_config = ConfigDict(extra="ignore")

    topic: str = Field(default="", description="学习主题或核心概念")
    learning_goal: str = Field(default="", max_length=500, description="具体学习目标或掌握深度期望")
    target_resources: list[str] = Field(
        default_factory=lambda: ["content", "mindmap", "quiz"],
        description="期望交付的资源清单：content, mindmap, quiz, code, reading, ppt, cartoon",
    )
    difficulty: DifficultyLevel = Field(
        default="intermediate",
        description="学习难度阶段：beginner(初学入门)、intermediate(进阶掌握)、advanced(精通探究)",
    )
    preferences: dict[str, Any] = Field(
        default_factory=dict,
        description="全局偏好字典（例如 programming_language='python', voice='teacher' 等）",
    )

    # 兼容过渡字段
    learning_need: str | None = Field(default=None, description="兼容旧版字段别名")
    learning_scenario: str | None = Field(default="self_study", description="兼容旧版字段别名")
    selected_agents: list[Any] | None = Field(default=None, description="兼容旧版字段别名")
    agent_configs: Any | None = Field(default=None, description="兼容旧版字段别名")

    @model_validator(mode="before")
    @classmethod
    def normalize_input(cls, data: Any) -> Any:
        """规范化输入数据，平滑处理别名与默认值。"""
        if isinstance(data, dict):
            if not data.get("topic") and data.get("learning_need"):
                data["topic"] = data["learning_need"]
            if not data.get("learning_need") and data.get("topic"):
                data["learning_need"] = data["topic"]
            if not data.get("target_resources") and data.get("selected_agents"):
                raw_agents = data.get("selected_agents") or []
                selected: list[str] = []
                for item in raw_agents:
                    if isinstance(item, dict) and item.get("enabled", True):
                        selected.append(str(item.get("agent_id")))
                    elif isinstance(item, str):
                        selected.append(item)
                if selected:
                    data["target_resources"] = selected
        return data

    def enabled_agent_ids(self) -> list[str]:
        """兼容获取已启用的资源类型列表。"""
        return self.target_resources


# ── 3. Plan-and-Execute 任务图与规划模型 ────────────────────────────────────


class TaskNode(BaseModel):
    """PlanAgent 规划生成的单项子任务节点。"""

    task_id: str = Field(default="", description="任务标识，通常与 resource_type 一致，如 content, ppt")
    title: str = Field(default="", description="任务标题，如 'Python 异步编程深度讲义'")
    resource_type: str = Field(default="", description="生成的资源类型：content, mindmap, quiz, code, reading, ppt, cartoon")
    task_type: TaskType = Field(default="text", description="执行类型：text(大模型生成) 或 tool(调用专用工具)")
    tool_name: str | None = Field(default=None, description="当 task_type 为 tool 时调用的工具名")
    dependencies: list[str] = Field(default_factory=list, description="依赖的前置 task_id 列表")
    subagent_role: str = Field(default="学科专家", description="执行该任务的 SubAgent 角色说明")
    task_prompt: str = Field(default="", description="分配给 SubAgent 的具体生成提示与上下文指导")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="任务当前状态")
    progress: int = Field(default=0, ge=0, le=100, description="任务执行进度百分比 0-100")
    message: str = Field(default="等待调度", description="当前最新执行日志或状态描述")
    elapsed_ms: int | None = Field(default=None, description="耗时（毫秒）")
    error: str | None = Field(default=None, description="失败原因说明")

    # 兼容历史测试字段
    agent_id: str = ""
    objective: str = ""
    focus: list[str] = Field(default_factory=list)
    required_elements: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def norm_task(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("task_id") and data.get("agent_id"):
                data["task_id"] = data["agent_id"]
            if not data.get("agent_id") and data.get("task_id"):
                data["agent_id"] = data["task_id"]
        return data


class ExecutionPlan(BaseModel):
    """由主规划智能体 (PlanAgent) 制定并驱动执行的任务执行图。"""

    topic: str = Field(default="", description="学习主题")
    learning_goal: str = Field(default="", description="核心学习目标")
    difficulty: DifficultyLevel = Field(default="intermediate", description="难度定位")
    overview: str = Field(default="", description="学习路径与规划总体说明")
    tasks: list[Any] = Field(default_factory=list, description="DAG 规划子任务节点列表")

    # 兼容历史测试属性
    schema_version: int = Field(default=2)
    learner_goal: str = Field(default="")
    scope: list[str] = Field(default_factory=list)

    @field_validator("scope")
    @classmethod
    def reject_empty_scope(cls, values: list[str]) -> list[str]:
        """校验 scope 列表不含空项。"""
        if any(not v or not v.strip() for v in values):
            raise ValueError("scope 列表不能包含空项")
        return values

    @field_validator("tasks")
    @classmethod
    def validate_tasks_not_empty(cls, values: list[Any]) -> list[Any]:
        """校验显式传入的任务列表不可为空。"""
        if values is not None and len(values) == 0:
            raise ValueError("tasks 列表不能为空")
        return values

    @property
    def agent_ids(self) -> list[str]:
        """获取所有规划任务的 agent_id 列表。"""
        res: list[str] = []
        for t in self.tasks:
            tid = getattr(t, "task_id", None) or getattr(t, "agent_id", None)
            if tid:
                res.append(str(tid))
            elif isinstance(t, dict):
                res.append(str(t.get("task_id") or t.get("agent_id") or ""))
        return res

    def get_task(self, task_id: str) -> TaskNode | None:
        """根据 task_id 查找任务节点。"""
        for task in self.tasks:
            tid = getattr(task, "task_id", None) or getattr(task, "agent_id", None)
            if tid == task_id:
                return task
        return None

    def ready_tasks(self, completed_task_ids: set[str], running_task_ids: set[str]) -> list[TaskNode]:
        """获取当前已满足所有前置依赖且未在运行中的就绪任务。"""
        ready: list[TaskNode] = []
        for task in self.tasks:
            tid = getattr(task, "task_id", None) or getattr(task, "agent_id", None)
            if tid in completed_task_ids or tid in running_task_ids:
                continue
            status = getattr(task, "status", TaskStatus.PENDING)
            if status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.SKIPPED):
                continue
            deps = getattr(task, "dependencies", [])
            if all(dep in completed_task_ids for dep in deps):
                ready.append(task)
        return ready


# ── 4. 产物与执行结果统一模型 ───────────────────────────────────────────────


class AgentResult(BaseModel):
    """子智能体执行或工具调用的标准化输出结果。"""

    model_config = ConfigDict(extra="forbid")

    success: bool = Field(description="执行是否成功")
    title: str = Field(default="", description="产物展示标题")
    file_type: str = Field(default="markdown", description="文件格式：markdown, json, pptx, mp4")
    content: str | dict[str, Any] | list[Any] | None = Field(default=None, description="产物主要内容")
    summary: str | None = Field(default=None, description="产物要点或摘要")
    metrics: dict[str, Any] = Field(default_factory=dict, description="度量指标（如题数、幻灯片页数等）")
    metadata: dict[str, Any] = Field(default_factory=dict, description="产物附带元数据")
    error: str | None = Field(default=None, description="错误信息（当失败时）")


# ── 5. 结构化产物格式定义 (Quiz / Reading 等) ──────────────────────────────


class QuizOption(BaseModel):
    """单道测验题目的选项。"""

    key: str = Field(default="", description="选项标识 (A, B, C, D)")
    text: str = Field(default="", description="选项文本内容")
    label: str = Field(default="", description="兼容旧版字段别名")
    content: str = Field(default="", description="兼容旧版字段别名")

    @model_validator(mode="before")
    @classmethod
    def normalize_option(cls, d: Any) -> Any:
        if isinstance(d, dict):
            if not d.get("key") and d.get("label"):
                d["key"] = d["label"]
            if not d.get("label") and d.get("key"):
                d["label"] = d["key"]
            if not d.get("text") and d.get("content"):
                d["text"] = d["content"]
            if not d.get("content") and d.get("text"):
                d["content"] = d["text"]
        return d


class QuizQuestion(BaseModel):
    """结构化测验题目模型。"""

    id: int | str = Field(description="题目序号或唯一标识")
    type: Literal["single", "multiple", "judge", "fill", "single_choice", "multiple_choice", "true_false"] = Field(
        default="single", description="题目类型"
    )
    question: str = Field(description="题干内容")
    options: list[QuizOption] = Field(default_factory=list, description="选择题选项列表")
    answer: str | list[str] = Field(description="参考标准答案")
    explanation: str = Field(default="", description="详细答案解析")
    knowledge_point: str = Field(default="", description="考查的核心知识点")
    difficulty: str = Field(default="basic", description="题目难度")


class QuizPayload(BaseModel):
    """习题资源标准 Payload。"""

    title: str = Field(default="", description="测验标题")
    summary: str = Field(default="", description="测验摘要")
    questions: list[QuizQuestion] = Field(default_factory=list, description="题目列表")


class ReadingResource(BaseModel):
    """推荐阅读条目模型。"""

    model_config = ConfigDict(extra="ignore")

    title: str = Field(description="阅读材料标题")
    author: str = Field(default="佚名", description="作者或组织机构")
    url: str | None = Field(default=None, description="在线参考链接或来源")
    difficulty: str = Field(default="introductory", description="推荐阅读难度")
    description: str = Field(default="", description="材料核心内容简介与推荐理由")
    reading_time: str = Field(default="15 分钟", description="预估阅读时间")
    source: str = Field(default="", description="来源或出版社")
    relevance: str = Field(default="", description="相关度阐述")
    id: str | None = Field(default=None, description="标识")
    type: str | None = Field(default=None, description="类型")
    language: str | None = Field(default=None, description="语言")


class ReadingPayload(BaseModel):
    """拓展阅读资源标准 Payload。"""

    title: str = Field(default="", description="阅读标题")
    summary: str = Field(default="", description="阅读摘要")
    recommendations: list[ReadingResource] = Field(default_factory=list, description="推荐阅读列表")
    resources: list[ReadingResource] = Field(default_factory=list, description="兼容旧版 resources 字段")
    items: list[ReadingResource] = Field(default_factory=list, description="兼容旧版字段别名")

    @model_validator(mode="before")
    @classmethod
    def normalize_reading(cls, d: Any) -> Any:
        """规范化阅读材料字段别名。"""
        if isinstance(d, dict):
            res = d.get("resources") or d.get("recommendations") or d.get("items") or []
            d.setdefault("resources", res)
            d.setdefault("recommendations", res)
            d.setdefault("items", res)
        return d


# ── 6. 展示与查询 DTO 模型 ──────────────────────────────────────────────────


class GeneratedResourceItemDTO(BaseModel):
    """资源项明细 DTO。"""

    id: str = Field(description="产物标识")
    type: str = Field(description="资源类型")
    title: str = Field(description="资源标题")
    format: str = Field(description="格式：markdown, json, pptx, mp4")
    content: Any = Field(default=None, description="内容主体")
    metadata: dict[str, Any] = Field(default_factory=dict, description="元数据字典")
    created_at: str | None = Field(default=None, description="创建时间 ISO 字符串")


class TaskSnapshotDTO(BaseModel):
    """任务实时快照 DTO。"""

    task_id: str
    status: TaskStatus
    message: str
    progress: int
    elapsed_ms: int | None = None
    artifact_title: str | None = None


class ResourceStatusSnapshot(BaseModel):
    """资源生成任务轮询状态快照。"""

    resource_id: int
    topic: str = ""
    status: str = "pending"
    tasks: list[TaskNode] = Field(default_factory=list)
    current_message: str = ""
    overall_progress: int = 0
    resources: list[GeneratedResourceItemDTO] = Field(default_factory=list)
    updated_at: str | None = None
    learning_need: str = ""
    selected_agents: list[str] = Field(default_factory=list)
    agent_snapshots: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def sync_compat_fields(cls, data: Any) -> Any:
        """同步前后端兼容别名。"""
        if isinstance(data, dict):
            if not data.get("topic") and data.get("learning_need"):
                data["topic"] = data["learning_need"]
            if not data.get("learning_need") and data.get("topic"):
                data["learning_need"] = data["topic"]
        return data


class GeneratedResourceBundleDTO(BaseModel):
    """已完成资源包完整产物详情。"""

    id: str
    topic: str = ""
    learning_goal: str = ""
    status: str = "completed"
    plan: dict[str, Any] | None = None
    resources: list[GeneratedResourceItemDTO] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    title: str = ""
    learning_need: str = ""
    selected_agents: list[str] = Field(default_factory=list)


# ── 7. 兼容过渡模型 ────────────────────────────────────────────────────────


class DownstreamContext(BaseModel):
    """下游上下文传输模型（兼容过渡）。"""

    source_agent: str = ""
    title: str = ""
    one_sentence_summary: str = ""
    materials: list[str] = Field(default_factory=list)
    key_points: list[str] = Field(default_factory=list)


class ResourcePlanTask(TaskNode):
    """兼容旧测试的任务模型。"""

    pass


class AgentSelection(BaseModel):
    """兼容旧前端的 Agent 选择项。"""

    agent_id: str
    enabled: bool = True


class ContentConfig(BaseModel):
    """兼容旧模型。"""

    structure: str = "progressive"


class MindmapConfig(BaseModel):
    """兼容旧模型。"""

    map_type: str = "knowledge_tree"


class QuizConfig(BaseModel):
    """兼容旧模型。"""

    question_count: int = 5


class CodeConfig(BaseModel):
    """兼容旧模型。"""

    programming_language: str = "python"


class ReadingConfig(BaseModel):
    """兼容旧模型。"""

    coverage: str = "extended"


class AgentConfigs(BaseModel):
    """兼容旧模型。"""

    model_config = ConfigDict(extra="allow")


class ResourceInput(BaseModel):
    """兼容历史资源输入契约。"""

    learning_need: str = ""
    agent_name: str = ""
    teaching_plan: Any = None
    agent_config: dict[str, Any] = Field(default_factory=dict)
    upstream_handoffs: dict[str, Any] = Field(default_factory=dict)
    profile: dict[str, Any] = Field(default_factory=dict)
    learning_scenario: str = "daily_review"
    username: str = "anonymous"
    resource_id: str | int = "default"


# 别名兼容
TaskPlan = ExecutionPlan
ResourcePlan = ExecutionPlan
GeneratedResourceItem = GeneratedResourceItemDTO
ResourceBundle = GeneratedResourceBundleDTO
SUCCESSFUL_RESOURCE_STATUSES = frozenset(
    {
        ResourceLifecycleStatus.COMPLETED,
        ResourceLifecycleStatus.PARTIAL,
    }
)
