"""Chat 模块数据模式定义。

包含 Agent 内部状态类型、教学图解 Schema 等。
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Optional, Union
from typing_extensions import TypedDict

from pydantic import BaseModel, ConfigDict, Field, model_validator
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from app.chat.tools.memory import MemoryReader


# ===================================================================
# Agent 内部状态类型（TypedDict，total=False 兼容 LangGraph 增量更新）
# ===================================================================

class TutorAgentContext(BaseModel):
    """Agent 初始化上下文 — 由 service 层构造后传入 TutorAgent。

    包含用户身份、系统提示词、只读能力和功能开关。
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    user_id: int
    session_id: str
    system_prompt: str
    session_summary_context: str = ""
    file_context: str = ""
    attachment_analysis_context: str = ""
    attachment_analysis: dict[str, Any] = Field(default_factory=dict)
    attachments: list[str] = Field(default_factory=list)
    enable_web_search: bool = False
    enable_knowledge_base: bool = False
    need_teaching_diagram: bool = False
    diagram_mode: Literal["requested", "off"] = "off"
    preferred_diagram_type: Optional["TeachingDiagramType"] = None
    generate_video: bool = False
    resource_mode: str = "none"
    memory_reader: MemoryReader | None = None


class TutorState(TypedDict, total=False):
    """LangGraph 运行状态 — 精简版。

    移除了 planner/compile_plan/execute_step/replan 相关的复杂状态字段。
    所有字段均为可选，支持 LangGraph 增量更新。
    """

    # ---- 用户身份与附件 ----
    user_id: int  # 用户ID
    session_id: str  # 会话ID
    attachments: Optional[list[str]]  # 附件URL列表
    need_teaching_diagram: bool  # 是否生成教学图解
    enable_web_search: bool  # 是否启用联网搜索
    enable_knowledge_base: bool  # 是否启用本地知识库检索
    teaching_diagram: Optional[dict[str, Any]]  # 生成的教学图解数据
    teaching_diagram_error: Optional[str]  # 教学图解生成错误信息
    diagram_type: Optional["TeachingDiagramType"]  # 教学图解类型

    # ---- 路由与执行模式 ----
    route: str  # 路由结果
    execution_mode: str  # 执行模式
    summary_type: str  # 总结类型
    search_result: str  # 搜索节点返回的搜索结果

    # ---- 上下文信息 ----
    retrieved_profile_context: str  # Agent 本轮按需读取的用户画像，只读
    retrieved_memory_context: str  # Agent 本轮按需读取的跨会话学习事实，只读
    session_summary_context: str  # 服务层注入的旧会话摘要，只读
    file_context: str  # 文件上下文
    attachment_analysis_context: str  # 附件分析上下文
    attachment_analysis: dict[str, Any]  # 附件分析结果

    # ---- Prompt 模板 ----
    system_prompt: str  # 系统提示词

    # ---- 对话消息 ----
    messages: Annotated[list[AnyMessage], add_messages]  # 消息列表（支持增量追加）

    # ---- 终止信息 ----
    answer_text: str  # 最终回答文本
    termination_reason: str  # 终止原因


# ===================================================================
# 教学图解 Schema（6 类图型：comparison / flowchart / sequence / framework / summary / hierarchy）
# ===================================================================

TeachingDiagramType = Literal["comparison", "flowchart", "sequence", "framework", "summary", "hierarchy"]


# ---- 辅助文字 ----
class TeachingContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    core_explanation: str = Field(max_length=400, description="核心解释")
    key_points: list[str] = Field(default_factory=list, max_length=5, description="要点列表")
    common_mistakes: list[str] = Field(default_factory=list, max_length=3, description="常见误区")
    examples: list[str] = Field(default_factory=list, max_length=3, description="示例")
    summary: str = Field(max_length=240, description="一句话总结")


# ---- 1. 对比图 ----
class ComparisonEntity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(max_length=20, description="实体名称")
    core_label: str = Field(max_length=30, description="核心标签")
    short_desc: str = Field(max_length=60, description="简短描述")


class ComparisonDimension(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(max_length=20, description="维度名称")
    left: str = Field(max_length=60, description="左侧内容")
    right: str = Field(max_length=60, description="右侧内容")
    highlight: Optional[str] = Field(default=None, max_length=60, description="重点标注")


class VisualSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    left_keyword: str = Field(max_length=10, description="左侧关键词")
    right_keyword: str = Field(max_length=10, description="右侧关键词")
    center_conclusion: str = Field(max_length=60, description="居中结论")


class ComparisonPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    left_entity: ComparisonEntity
    right_entity: ComparisonEntity
    dimensions: list[ComparisonDimension] = Field(min_length=2, max_length=8, description="对比维度列表")
    visual_summary: VisualSummary


# ---- 2. 流程图 ----
FlowchartNodeType = Literal["start", "process", "decision", "end", "danger"]


class FlowchartNode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(description="节点ID")
    title: str = Field(max_length=35, description="节点标题")
    short_desc: str = Field(default="", max_length=60, description="简短描述")
    type: FlowchartNodeType = Field(default="process", description="节点类型")


class FlowchartEdge(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")
    from_: str = Field(alias="from", description="起始节点ID")
    to: str = Field(description="目标节点ID")
    label: Optional[str] = Field(default=None, max_length=20, description="边标签")


class FlowchartPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")
    direction: Literal["vertical", "horizontal"] = Field(default="vertical", description="流向方向")
    nodes: list[FlowchartNode] = Field(min_length=2, max_length=20)
    edges: list[FlowchartEdge] = Field(min_length=1)


# ---- 3. 时序图 ----
class SequenceMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")
    from_: str = Field(alias="from", description="发送方")
    to: str = Field(description="接收方")
    label: str = Field(max_length=30, description="消息标签")
    detail: Optional[str] = Field(default=None, max_length=60, description="详细说明")


class SequencePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    actors: list[str] = Field(min_length=2, max_length=6, description="参与者列表")
    messages: list[SequenceMessage] = Field(min_length=1, max_length=20, description="交互消息列表")


# ---- 4. 知识框架图 ----
class FrameworkModule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(max_length=20, description="模块标题")
    items: list[str] = Field(min_length=1, max_length=8, description="知识点列表")


class FrameworkPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    center: str = Field(max_length=20, description="中心主题")
    modules: list[FrameworkModule] = Field(min_length=2, max_length=8, description="模块列表")


# ---- 5. 总结卡片图 ----
class SummaryCard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(max_length=20, description="卡片标题")
    short_desc: str = Field(max_length=60, description="卡片描述")


class SummaryPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cards: list[SummaryCard] = Field(min_length=2, max_length=8, description="卡片列表")


# ---- 6. 层级概括图 ----
class HierarchyBranch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(max_length=20, description="分支标题")
    children: list[str] = Field(min_length=1, max_length=8, description="子项列表")


class HierarchyPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    root: str = Field(max_length=20, description="根节点名称")
    branches: list[HierarchyBranch] = Field(min_length=2, max_length=8, description="分支列表")


# ---- 顶层 TeachingDiagram ----
class TeachingDiagram(BaseModel):
    """一次答疑对应的一张结构化教学图解。"""
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    graph_type: TeachingDiagramType
    title: str = Field(min_length=1, max_length=80, description="主标题")
    subtitle: Optional[str] = Field(default=None, max_length=60, description="副标题")
    teaching_goal: str = Field(max_length=60, description="教学目标")
    course: Optional[str] = Field(default=None, max_length=30, description="课程名称")
    difficulty: Literal["beginner", "intermediate", "advanced"] = Field(default="intermediate", description="难度等级")
    visual_content: Union[
        ComparisonPayload, FlowchartPayload, SequencePayload,
        FrameworkPayload, SummaryPayload, HierarchyPayload,
    ]
    teaching_content: TeachingContent

    @model_validator(mode="after")
    def validate_payload_type(self) -> "TeachingDiagram":
        expected_type = {
            "comparison": ComparisonPayload,
            "flowchart": FlowchartPayload,
            "sequence": SequencePayload,
            "framework": FrameworkPayload,
            "summary": SummaryPayload,
            "hierarchy": HierarchyPayload,
        }[self.graph_type]
        if not isinstance(self.visual_content, expected_type):
            raise ValueError("visual_content must match graph_type")
        return self