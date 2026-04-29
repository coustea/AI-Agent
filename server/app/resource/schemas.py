from __future__ import annotations

from enum import Enum
from typing import Any, Optional, TypedDict

from pydantic import BaseModel, Field, ConfigDict


class AgentStatus(str, Enum):
    """Agent 执行状态。"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class LayerPlan(BaseModel):
    """分层规划结构 — 每次只生成一层。"""
    model_config = ConfigDict(extra="allow")

    layer_index: int = Field(default=0, description="层索引")
    reason: str = Field(default="", description="为什么执行这一层")
    agents: list[str] = Field(default_factory=list, description="当前层执行的 Agent")
    dependencies: dict[str, list[str]] = Field(default_factory=dict, description="依赖关系，只能指向已完成 Agent")
    agent_parameters: dict[str, dict[str, Any]] = Field(default_factory=dict, description="Agent 参数")
    expected_outputs: dict[str, str] = Field(default_factory=dict, description="每个 Agent 要做什么")
    visible_agents: list[str] = Field(default_factory=list, description="对用户可见的 Agent")
    hidden_dependency_agents: list[str] = Field(default_factory=list, description="依赖补全的隐藏 Agent")
    failure_policy: dict[str, str] = Field(default_factory=dict, description="失败策略")
    stop_after_this_layer: bool = Field(default=False, description="是否在当前层后停止")


class WorkflowState(BaseModel):
    """主流程状态 — LangGraph StateGraph 使用。"""
    model_config = ConfigDict(extra="allow")

    user_id: int = Field(default=0, description="用户 ID")
    resource_id: int | None = Field(default=None, description="资源 ID")
    task: dict[str, Any] = Field(default_factory=dict, description="用户任务")
    learner_profile: dict[str, Any] = Field(default_factory=dict, description="学习者画像")
    layer_index: int = Field(default=0, description="当前层索引")
    completed_agents: list[str] = Field(default_factory=list, description="已完成的 Agent")
    layer_history: list[LayerPlan] = Field(default_factory=list, description="层历史记录")
    manifest: dict[str, Any] = Field(default_factory=dict, description="执行状态 manifest")
    results: dict[str, dict[str, Any]] = Field(default_factory=dict, description="Agent 执行结果")
    current_layer_plan: LayerPlan | None = Field(default=None, description="当前层计划")
    error: str | None = Field(default=None, description="错误信息")


class WorkerRequest(BaseModel):
    """Agent 依赖请求 JSON — Agent 输出此结构请求读取依赖。"""
    model_config = ConfigDict(extra="allow")

    need_read: bool = Field(default=False, description="是否需要读取依赖")
    artifacts: list[str] = Field(default_factory=list, description="需要读取的产物列表")
    reason: str = Field(default="", description="读取原因")


class TraceEvent(BaseModel):
    """可观测事件 — 记录到 trace.jsonl。"""
    model_config = ConfigDict(extra="allow")

    event_type: str = Field(description="事件类型")
    timestamp: str = Field(description="时间戳 ISO 格式")
    agent_name: str | None = Field(default=None, description="Agent 名称")
    layer_index: int | None = Field(default=None, description="层索引")
    data: dict[str, Any] = Field(default_factory=dict, description="事件数据")


class AgentManifestEntry(BaseModel):
    """Agent 执行状态条目 — manifest.json 中使用。"""
    model_config = ConfigDict(extra="allow")

    agent_name: str = Field(description="Agent 名称")
    status: AgentStatus = Field(default=AgentStatus.PENDING, description="执行状态")
    dependencies: list[str] = Field(default_factory=list, description="依赖的 Agent")
    artifact_path: str | None = Field(default=None, description="产物文件路径")
    error: str | None = Field(default=None, description="错误信息")
    started_at: str | None = Field(default=None, description="开始时间")
    completed_at: str | None = Field(default=None, description="完成时间")


class WorkerState(BaseModel):
    """Worker Agent 执行状态。"""
    model_config = ConfigDict(extra="allow")

    agent_name: str = Field(description="Agent 名称")
    task: dict[str, Any] = Field(default_factory=dict, description="任务参数")
    profile: dict[str, Any] = Field(default_factory=dict, description="学习者画像")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Agent 参数")
    dependencies: list[str] = Field(default_factory=list, description="依赖的 Agent")
    dependency_artifacts: dict[str, str] = Field(default_factory=dict, description="依赖产物内容")
    layer_index: int = Field(default=0, description="当前层索引")


class WorkerResult(BaseModel):
    """Worker Agent 执行结果。"""
    model_config = ConfigDict(extra="allow")

    success: bool = Field(default=False, description="是否成功")
    content: str = Field(default="", description="生成的内容")
    artifact_path: str | None = Field(default=None, description="产物文件路径")
    artifact_dir: str | None = Field(default=None, description="产物目录路径 (resource/userId/resourceId)")
    file_type: str = Field(default="md", description="文件类型 (md, pptx, png 等)")
    error: str | None = Field(default=None, description="错误信息")


class GraphState(TypedDict):
    """LangGraph 状态 — 用于 StateGraph。"""
    workflow_state: WorkflowState
    current_layer_plan: LayerPlan | None
    layer_results: dict[str, dict[str, Any]]
    should_continue: bool
    error: str | None


class LearningTask(BaseModel):
    course: str = Field(..., description="课程/主题")
    gap: str = Field(..., description="知识瓶颈/核心痛点")
    need: str = Field(default="review", description="资源偏好: exam/review/deep")
    extra: str = Field(default="", description="额外需求")
    template_id: str = Field(default="python_ppt_template", description="可选：PPT 模板标识（默认 python_ppt_template）")
    template_source_url: Optional[str] = Field(default=None, description="可选：在线 PPT 模板直链（.pptx）")
    template_config_url: Optional[str] = Field(default=None, description="可选：在线模板配置 JSON 直链")


class ResourceGenerateRequest(BaseModel):
    learning_task: LearningTask
    selected_resources: Optional[list[str]] = Field(
        default=None,
        description="可选：指定要生成的资源类型；未传或为空时默认全量生成",
    )


class LearnerProfileSnapshot(BaseModel):
    """学习者画像快照 — 用于资源生成 Agent 的个性化上下文。"""
    user_id: int | None = None
    username: str | None = None
    major: str | None = None
    grade: str | None = None
    school: str | None = None

    # 画像主体 Markdown
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
        # 把用户基础信息和画像字段合并成运行时快照，避免下游直接耦合数据库模型。
        merged: dict[str, Any] = {}
        if user_data:
            merged.update(user_data)
        if profile_data:
            merged.update(profile_data)
        return cls.model_validate(merged)

    def as_agent_profile(self) -> dict[str, Any]:
        # Agent prompt 只需要非空字段，减少无意义的 null 噪音。
        return self.model_dump(exclude_none=True)


class PersonalizedTaskContext(BaseModel):
    course: str
    gap: str
    need: str = "review"
    extra: str = ""
    target_difficulty: str = "intermediate"
    explanation_style: list[str] = Field(default_factory=list)
    emphasis: list[str] = Field(default_factory=list)
    recommended_order: list[str] = Field(default_factory=list)
    profile_markdown: str | None = None  # 画像 Markdown

    def as_prompt_context(self) -> dict[str, Any]:
        # 这里返回可序列化 dict，方便直接注入 planner prompt。
        return self.model_dump(exclude_none=True)


class ResourcePlan(BaseModel):
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
        # coordinator 用这个顺序统计总任务数和默认执行顺序。
        if self.execution_groups:
            ordered: list[str] = []
            for group in self.execution_groups:
                for agent in group:
                    if agent not in ordered:
                        ordered.append(agent)
            return ordered
        return self.core_agents + self.enhancement_agents + self.presentation_agents
