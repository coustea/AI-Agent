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
    enable_search: bool = False
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
    enable_search: bool  # 是否启用搜索
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
# 教学图解 Schema
# ===================================================================

TeachingDiagramType = Literal["node_graph", "sequence_timeline", "grid_timeline"]


class TeachingDiagramModel(BaseModel):
    """教学图解模型基类。"""

    model_config = ConfigDict(extra="forbid")


# 1. 拓扑图谱原语 (Node Graph Primitive)
NodeShapeType = Literal["circle", "rect", "diamond", "capsule", "actor", "cylinder", "uml_class"]
EdgeArrowType = Literal["association", "dependency", "inheritance", "aggregation", "composition", "none"]


class GraphNode(TeachingDiagramModel):
    id: str = Field(description="节点唯一ID，用于边连接")
    label: str = Field(description="节点显示的标题文本")
    x: int = Field(description="布局百分比 X坐标 (0-100)，指导前端对齐排版")
    y: int = Field(description="布局百分比 Y坐标 (0-100)，指导前端对齐排版")
    shape: NodeShapeType = Field(default="circle", description="节点形状")
    state: Literal["unvisited", "active", "visited"] = Field(default="unvisited", description="遍历状态")
    fields: Optional[list[str]] = Field(default=None, description="分栏字段列表。UML类图显示属性/方法，E-R显示属性")
    tooltip: Optional[str] = Field(default=None, description="Hover 时展示的辅助教学气泡说明")


class GraphEdge(TeachingDiagramModel):
    source: str = Field(description="源节点 ID")
    target: str = Field(description="目标节点 ID")
    label: Optional[str] = Field(default=None, description="连线上显示的文本说明")
    arrow_type: EdgeArrowType = Field(default="association", description="线型与 UML 箭头关系类型")
    is_flowing: bool = Field(default=False, description="是否处于流动状态（如数据流向）")
    is_backtrack: bool = Field(default=False, description="是否为算法回溯边")


class NodeGraphPayload(TeachingDiagramModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


# 2. 时序轨原语 (Sequence Timeline Primitive)
class SequenceMessage(TeachingDiagramModel):
    sender: str = Field(description="发送方参与者")
    receiver: str = Field(description="接收方参与者")
    label: str = Field(description="消息主标签（如 SYN）")
    details: Optional[str] = Field(default=None, description="详细字段或交互细节")
    highlight: bool = Field(default=False, description="是否高亮显示本条交互线")


class SequenceParticipantState(TeachingDiagramModel):
    participant: str = Field(description="参与者实体名")
    state_label: str = Field(description="此时该实体的内部状态机状态（如 ESTABLISHED）")


class SequenceStep(TeachingDiagramModel):
    step_index: int = Field(description="步骤序号")
    message: SequenceMessage = Field(description="传输的报文数据")
    active_states: list[SequenceParticipantState] = Field(default_factory=list, description="此步后参与者的状态机变化")


class SequenceTimelinePayload(TeachingDiagramModel):
    participants: list[str] = Field(description="参与者列表，如 ['Client', 'Server']")
    steps: list[SequenceStep] = Field(description="步骤时序列表")
    final_state: str = Field(description="状态交互的终极总结描述")


# 3. 时空网格原语 (Grid Timeline Primitive)
GridCellState = Literal["running", "ready", "blocked", "allocated", "free", "pointer", "highlight"]


class GridCell(TeachingDiagramModel):
    row_label: str = Field(description="行标识，如 P1, Stack, Heap, Page0")
    col_label: str = Field(description="列/刻度标识，如 0ms, 0x00, Offset")
    state: GridCellState = Field(default="highlight", description="单元格显示状态")
    label: str = Field(description="单元格内文字")
    pointer_target: Optional[str] = Field(default=None, description="指针指向的目标（若有，写 row_label/col_label 格式）")
    tooltip: Optional[str] = Field(default=None, description="单元格详细说明")


class GridTimelinePayload(TeachingDiagramModel):
    orientation: Literal["horizontal", "vertical"] = Field(default="horizontal", description="排布方向")
    rows: list[str] = Field(description="行轴集合")
    cols: list[str] = Field(description="列/时间轴集合")
    cells: list[GridCell] = Field(description="单元格数据")
    call_stack: Optional[list[str]] = Field(default=None, description="相关的函数调用栈帧快照（如展示递归）")
    timeline_summary: str = Field(description="时空排布的总结性描述")


class InsightCanvas(TeachingDiagramModel):
    """一次答疑对应的一张结构化教学图板。"""

    type: TeachingDiagramType
    title: str = Field(min_length=1, max_length=80)
    focus_question: str = Field(min_length=1, max_length=240)
    takeaway: str = Field(min_length=1, max_length=240)
    why_it_works: str = Field(min_length=1, max_length=400)
    pitfall: Optional[str] = Field(default=None, max_length=240)
    try_it: str = Field(min_length=1, max_length=240)
    personalization_note: Optional[str] = Field(default=None, max_length=240)
    payload: Union[NodeGraphPayload, SequenceTimelinePayload, GridTimelinePayload]

    @model_validator(mode="after")
    def validate_payload_type(self) -> "InsightCanvas":
        expected_type = {
            "node_graph": NodeGraphPayload,
            "sequence_timeline": SequenceTimelinePayload,
            "grid_timeline": GridTimelinePayload,
        }[self.type]
        if not isinstance(self.payload, expected_type):
            raise ValueError("teaching diagram payload must match diagram type")
        return self
