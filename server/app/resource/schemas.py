"""Resource 模块数据契约与 DTO 模型 (app.resource.schemas)。

完全对齐 chat 模块快照流架构，由主 Agent 驱动子智能体工具交付成果。
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator


# ── 1. 基础类型与生成请求 ──────────────────────────────────────────────────


DifficultyLevel = Literal["beginner", "intermediate", "advanced"]
ResourceRunPhase = Literal[
    "queued",
    "preparing",
    "planning",
    "generating",
    "saving",
    "completed",
    "failed",
    "cancelled",
]
TerminalStatus = Literal["completed", "failed", "cancelled"]
TERMINAL_STATUSES: set[str] = {"completed", "failed", "cancelled"}


class ResourceGenerationRequest(BaseModel):
    """统一资源生成请求（前后端交互核心契约）。"""

    topic: str = Field(min_length=1, description="学习主题或核心概念")
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

    def enabled_agent_ids(self) -> list[str]:
        """获取已启用的资源目标列表。"""
        return self.target_resources


# ── 2. 产物与快照状态模型 ──────────────────────────────────────────────────


class ResourceArtifact(BaseModel):
    """由子智能体工具生成的单项教学产物。"""

    id: str = Field(description="产物唯一标识")
    kind: str = Field(description="产物类型：content, mindmap, quiz, code, reading, ppt, cartoon")
    title: str = Field(description="产物显示标题")
    file_type: str = Field(description="产物物理格式：markdown, json, pptx, mp4")
    url: str | None = Field(default=None, description="产物可下载链接或播放地址")
    preview_urls: list[str] = Field(default_factory=list, description="预览图片链接清单")
    content: Any | None = Field(default=None, description="文本正文或结构化 JSON 对象")
    summary: str = Field(default="", description="生成内容简要摘要")
    metadata: dict[str, Any] = Field(default_factory=dict, description="工具返回的元数据")


class ResourceStep(BaseModel):
    """主 Agent 调度的子智能体执行步骤记录。"""

    id: str = Field(description="步骤或调用标识")
    tool_name: str = Field(description="调用的子智能体工具名")
    title: str = Field(description="步骤业务标题")
    status: Literal["pending", "running", "completed", "failed"] = Field(
        default="pending", description="当前步骤状态"
    )
    progress: int = Field(default=0, ge=0, le=100, description="执行进度百分比 0-100")
    message: str = Field(default="", description="当前执行阶段日志或状态说明")
    elapsed_ms: int = Field(default=0, description="该步骤耗时（毫秒）")


class ResourceRunState(BaseModel):
    """Resource 模块全生命周期统一状态快照（对齐 chat.RunState）。"""

    run_id: str = Field(description="运行实例唯一标识")
    resource_id: int = Field(description="对应的持久化资源主键 ID")
    status: Literal["queued", "running", "completed", "failed", "cancelled"] = Field(
        default="queued", description="运行终态或就绪状态"
    )
    phase: ResourceRunPhase = Field(default="queued", description="当前宏观执行阶段")
    phase_label: str = Field(default="等待调度", description="执行阶段中文描述")
    thought_text: str = Field(default="", description="主 Agent 课程总规划师的思考与统筹流式文本")
    steps: list[ResourceStep] = Field(default_factory=list, description="各 SubAgent 执行步骤列表")
    artifacts: list[ResourceArtifact] = Field(default_factory=list, description="已就绪的教学产物列表")
    total_elapsed_ms: int = Field(default=0, description="总耗时（毫秒）")
    error: str = Field(default="", description="失败时的错误原因")


def encode_resource_sse(state: ResourceRunState) -> str:
    """将 ResourceRunState 快照编码为标准 SSE 数据包。"""
    payload = state.model_dump(mode="json")
    return f"event: run.state\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


# ── 3. 习题与阅读结构定义 (用于 SubAgent 校验) ──────────────────────────────


class QuizOption(BaseModel):
    """测验题目选项。"""

    key: str = Field(description="选项标识，如 A, B, C, D")
    text: str = Field(description="选项文本内容")

    @model_validator(mode="before")
    @classmethod
    def normalize_keys(cls, data: Any) -> Any:
        """规范化选项键值。"""
        if isinstance(data, dict):
            if "key" not in data and "label" in data:
                data["key"] = data["label"]
            if "text" not in data and "content" in data:
                data["text"] = data["content"]
        return data


class QuizQuestion(BaseModel):
    """随堂测验单道题目定义。"""

    id: int = Field(description="题目序号")
    type: Literal["single", "multiple", "judge", "fill"] = Field(
        default="single", description="题目题型"
    )
    question: str = Field(description="题干内容")
    options: list[QuizOption] = Field(default_factory=list, description="单选/多选题选项")
    answer: Any = Field(description="参考答案")
    explanation: str = Field(default="", description="答案解析与考核点")
    knowledge_point: str = Field(default="", description="考查的具体知识点")

    @model_validator(mode="before")
    @classmethod
    def normalize_type(cls, data: Any) -> Any:
        """规范化题目题型。"""
        if isinstance(data, dict) and "type" in data:
            val = str(data["type"]).lower()
            if val in ("single_choice", "single"):
                data["type"] = "single"
            elif val in ("multiple_choice", "multiple"):
                data["type"] = "multiple"
            elif val in ("true_false", "judge"):
                data["type"] = "judge"
        return data


class QuizPayload(BaseModel):
    """习题生成器产出标准结构。"""

    questions: list[QuizQuestion] = Field(default_factory=list, description="题目列表")


class ReadingResource(BaseModel):
    """推荐阅读材料条目。"""

    model_config = ConfigDict(extra="ignore")

    title: str = Field(description="阅读材料标题")
    author: str = Field(default="佚名", description="作者或组织机构")
    url: str | None = Field(default=None, description="在线参考链接")
    difficulty: str = Field(default="introductory", description="推荐阅读难度")
    description: str = Field(default="", description="内容简介与推荐理由")
    reading_time: str = Field(default="15 分钟", description="预估阅读时间")
    source: str = Field(default="", description="来源或出版社")
    relevance: str = Field(default="", description="相关度阐述")
    id: str | None = Field(default=None, description="标识")
    type: str | None = Field(default=None, description="类型")
    language: str | None = Field(default=None, description="语言")


class ReadingPayload(BaseModel):
    """拓展阅读生成器产出标准结构。"""

    title: str = Field(default="", description="阅读标题")
    summary: str = Field(default="", description="阅读摘要")
    resources: list[ReadingResource] = Field(default_factory=list, description="推荐阅读列表")

    @model_validator(mode="before")
    @classmethod
    def normalize_reading(cls, d: Any) -> Any:
        """规范化阅读材料字段。"""
        if isinstance(d, dict):
            res = d.get("resources") or d.get("recommendations") or []
            d["resources"] = res
        return d


# ── 4. 查询与持久化 DTO 模型 ────────────────────────────────────────────────


class GeneratedResourceItemDTO(BaseModel):
    """资源项明细 DTO。"""

    id: int = Field(description="产物数据库主键 ID")
    resource_id: int = Field(description="所属生成任务 ID")
    agent_type: str = Field(description="资源类型：content, ppt, etc.")
    title: str = Field(description="资源标题")
    content_json: dict[str, Any] | list[Any] | None = Field(default=None, description="结构化内容")
    content_text: str | None = Field(default=None, description="文本/Markdown 正文")
    metadata_json: dict[str, Any] = Field(default_factory=dict, description="元数据字典")
    created_at: datetime = Field(description="创建时间")

    @computed_field
    @property
    def type(self) -> str:
        """获取资源类型别名。"""
        return self.agent_type

    @computed_field
    @property
    def format(self) -> str:
        """获取内容格式标识。"""
        if self.agent_type in ("ppt", "cartoon"):
            return "json"
        return "markdown" if self.content_text else "json"

    @computed_field
    @property
    def content(self) -> Any:
        """获取资源正文内容。"""
        return self.content_json if self.content_json is not None else self.content_text


class GeneratedResourceBundleDTO(BaseModel):
    """完整资源产物聚合包 DTO。"""

    id: int = Field(description="生成任务主键 ID")
    user_id: int = Field(description="用户 ID")
    topic: str = Field(description="学习主题")
    learning_goal: str = Field(default="", description="学习目标")
    status: str = Field(description="任务状态")
    created_at: datetime = Field(description="创建时间")
    items: list[GeneratedResourceItemDTO] = Field(default_factory=list, description="各项教学产物清单")

    @computed_field
    @property
    def resources(self) -> list[GeneratedResourceItemDTO]:
        """获取资源项清单别名。"""
        return self.items

    @computed_field
    @property
    def title(self) -> str:
        """获取资源包标题。"""
        return self.topic


class ResourceHistoryItemDTO(BaseModel):
    """用户历史生成资源概览 DTO。"""

    id: int = Field(description="任务主键 ID")
    topic: str = Field(description="学习主题")
    learning_goal: str = Field(default="", description="学习目标")
    status: str = Field(description="状态")
    created_at: datetime = Field(description="创建时间")
    resource_count: int = Field(default=0, description="包含资源项数量")
    resource_types: list[str] = Field(default_factory=list, description="包含的资源类型清单")

    @computed_field
    @property
    def learning_need(self) -> str:
        """获取学习主题别名。"""
        return self.topic


# ── 5. 通用辅助模型 (供 path 模块及测试导入) ────────────────────────────────


class AgentResult(BaseModel):
    """资源生成产物结果封装。"""

    model_config = ConfigDict(extra="forbid")

    success: bool = True
    title: str = ""
    file_type: str = "markdown"
    content: Any = None
    summary: str = ""
    error: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DownstreamContext(BaseModel):
    """下游上下文传递模型。"""

    source_agent: str = ""
    title: str = ""
    one_sentence_summary: str = ""
    materials: list[str] = Field(default_factory=list)


class ResourcePlanTask(BaseModel):
    """规划单项任务模型。"""

    agent_id: str = ""
    objective: str = ""
    focus: list[str] = Field(default_factory=list)
    required_elements: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)


class ResourcePlan(BaseModel):
    """教学方案规划模型。"""

    schema_version: int = 1
    learner_goal: str = ""
    scope: list[str] = Field(default_factory=list)
    tasks: list[ResourcePlanTask] = Field(default_factory=list)

    @field_validator("tasks")
    @classmethod
    def validate_tasks(cls, v: list[ResourcePlanTask]) -> list[ResourcePlanTask]:
        """校验显式传入的 tasks 不可为空。"""
        if v is not None and len(v) == 0:
            raise ValueError("tasks 列表不可为空")
        return v

    @property
    def agent_ids(self) -> list[str]:
        """获取所有规划任务的 agent_id 列表。"""
        return [t.agent_id for t in self.tasks if t.agent_id]


class ResourceInput(BaseModel):
    """资源生成任务输入。"""

    resource_id: str | int = "default"
    username: str = "anonymous"
    learning_need: str = ""
    learning_scenario: str = "self_study"
    profile: dict[str, Any] = Field(default_factory=dict)
    teaching_plan: Any = None
    upstream_handoffs: dict[str, Any] = Field(default_factory=dict)

