"""Chat 模块数据模式定义。

包含 API 层请求/响应模型、Agent 内部状态类型、知识图谱 Schema 等。
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal, Optional, Union
from typing_extensions import TypedDict

from pydantic import BaseModel, ConfigDict, Field, model_validator
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


# ===================================================================
# API 层数据模型（Pydantic BaseModel）
# ===================================================================

class AttachmentInfo(BaseModel):
    """单条附件信息。

    用于描述消息中包含的附件详情。
    """
    url: str  # 附件URL
    type: str  # 附件类型: "image" | "document"
    name: str  # 附件文件名


class ChatMessageItem(BaseModel):
    """返回给前端的消息条目。

    包含角色、内容、附件、知识图谱等。
    """
    role: str  # 消息角色: "user" | "assistant" | "tool"
    content: str  # 消息文本内容
    attachments: Optional[list[AttachmentInfo]] = None  # 附件列表
    teaching_diagram: Optional[dict[str, Any]] = None  # 教学图解数据
    created_at: Optional[datetime] = None  # 创建时间


class UploadResponse(BaseModel):
    """文件上传成功响应。

    返回上传文件的元信息。
    """
    url: str  # 文件访问URL
    file_type: str  # 文件类型: "image" | "document"
    original_name: str  # 原始文件名
    size_bytes: int  # 文件大小（字节）


# ===================================================================
# Agent 内部状态类型（TypedDict，total=False 兼容 LangGraph 增量更新）
# ===================================================================

class TutorAgentContext(BaseModel):
    """Agent 初始化上下文 — 由 service 层构造后传入 TutorAgent。

    包含用户身份、系统提示词、各类上下文和功能开关。
    """

    user_id: int
    session_id: str
    system_prompt: str
    session_summary_context: str
    recent_chat_context: str
    file_context: str
    attachment_analysis_context: str
    attachment_analysis: dict[str, Any] = Field(default_factory=dict)
    attachments: list[str] = Field(default_factory=list)
    enable_search: bool = False
    need_teaching_diagram: bool = False
    diagram_mode: Literal["requested", "off"] = "off"
    preferred_diagram_type: Optional["TeachingDiagramType"] = None
    generate_video: bool = False
    resource_mode: str = "none"




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
    enable_long_term_memory: bool  # 是否启用长期记忆读写
    teaching_diagram: Optional[dict[str, Any]]  # 生成的教学图解数据
    teaching_diagram_error: Optional[str]  # 教学图解生成错误信息
    diagram_type: Optional["TeachingDiagramType"]  # 教学图解类型

    # ---- 路由与执行模式 ----
    route: str  # 路由结果
    execution_mode: str  # 执行模式
    summary_type: str  # 总结类型
    search_result: str  # 搜索节点返回的搜索结果

    # ---- 上下文信息 ----
    recent_chat_context: str  # 近期对话上下文
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

TeachingDiagramType = Literal["contrast", "journey", "anatomy", "simulation"]


class TeachingDiagramModel(BaseModel):
    """教学图解模型基类。"""

    model_config = ConfigDict(extra="forbid")


class ContrastSide(TeachingDiagramModel):
    label: str = Field(min_length=1, max_length=30)
    definition: str = Field(min_length=1, max_length=160)
    signals: list[str] = Field(min_length=1, max_length=4)
    example: str = Field(min_length=1, max_length=160)


class ContrastPayload(TeachingDiagramModel):
    decision_rule: str = Field(min_length=1, max_length=240)
    left: ContrastSide
    right: ContrastSide
    scenario_conclusion: str = Field(min_length=1, max_length=240)


class JourneyStep(TeachingDiagramModel):
    title: str = Field(min_length=1, max_length=40)
    action: str = Field(min_length=1, max_length=180)
    rationale: str = Field(min_length=1, max_length=180)
    output: str = Field(min_length=1, max_length=180)
    warning: Optional[str] = Field(default=None, max_length=160)


class JourneyPayload(TeachingDiagramModel):
    goal: str = Field(min_length=1, max_length=200)
    steps: list[JourneyStep] = Field(min_length=3, max_length=6)
    result: str = Field(min_length=1, max_length=240)


class AnatomyPart(TeachingDiagramModel):
    name: str = Field(min_length=1, max_length=40)
    responsibility: str = Field(min_length=1, max_length=180)
    detail: str = Field(min_length=1, max_length=220)
    interaction_cue: Optional[str] = Field(default=None, max_length=160)


class AnatomyPayload(TeachingDiagramModel):
    subject: str = Field(min_length=1, max_length=80)
    parts: list[AnatomyPart] = Field(min_length=3, max_length=7)
    interaction_summary: str = Field(min_length=1, max_length=240)


class SimulationFrame(TeachingDiagramModel):
    stage: str = Field(min_length=1, max_length=40)
    state: str = Field(min_length=1, max_length=200)
    changed: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=200)
    learner_focus: str = Field(min_length=1, max_length=160)


class SimulationPayload(TeachingDiagramModel):
    scenario: str = Field(min_length=1, max_length=200)
    initial_state: str = Field(min_length=1, max_length=200)
    frames: list[SimulationFrame] = Field(min_length=2, max_length=6)
    result: str = Field(min_length=1, max_length=240)


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
    payload: Union[ContrastPayload, JourneyPayload, AnatomyPayload, SimulationPayload]

    @model_validator(mode="after")
    def validate_payload_type(self) -> "InsightCanvas":
        expected_type = {
            "contrast": ContrastPayload,
            "journey": JourneyPayload,
            "anatomy": AnatomyPayload,
            "simulation": SimulationPayload,
        }[self.type]
        if not isinstance(self.payload, expected_type):
            raise ValueError("teaching diagram payload must match diagram type")
        return self


# ===================================================================
# 旧图解 Schema（仅供未迁移模块单独引用，聊天 Agent 不再使用）
# ===================================================================

# 图解类型字面量
DiagramType = Literal[
    "hierarchy", "flow", "compare", "relation", "sequence", "state",
    "class", "er", "block", "packet", "git",
    "activity", "usecase", "component", "package", "deployment", "object", "communication",
]


class BaseDiagramModel(BaseModel):
    """图解模型基类。

    配置禁止额外字段、支持字段别名填充。
    """
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class DiagramNode(BaseDiagramModel):
    """图解节点。

    用于关系图、状态图等节点定义。
    """
    id: str = Field(min_length=1, max_length=40)  # 节点唯一标识
    label: str = Field(min_length=1, max_length=16)  # 节点显示标签
    description: Optional[str] = Field(default=None, max_length=40)  # 节点描述


class DiagramEdge(BaseDiagramModel):
    """图解边。

    用于关系图等边的定义。
    """
    source: str = Field(min_length=1, max_length=40)  # 源节点ID
    target: str = Field(min_length=1, max_length=40)  # 目标节点ID
    label: Optional[str] = Field(default=None, max_length=16)  # 边标签
    description: Optional[str] = Field(default=None, max_length=40)  # 边描述


class HierarchyNode(BaseDiagramModel):
    """层级节点。

    支持递归嵌套子节点，用于层级结构图。
    """
    id: str = Field(min_length=1, max_length=40)  # 节点唯一标识
    label: str = Field(min_length=1, max_length=16)  # 节点显示标签
    description: Optional[str] = Field(default=None, max_length=40)  # 节点描述
    children: list["HierarchyNode"] = Field(default_factory=list, max_length=8)  # 子节点列表


class HierarchySpec(BaseDiagramModel):
    """层级结构规格。

    定义层级图的根节点。
    """
    root: HierarchyNode  # 根节点


class FlowStep(BaseDiagramModel):
    """流程步骤。

    用于流程图中的步骤节点。
    """
    id: str = Field(min_length=1, max_length=40)  # 步骤唯一标识
    label: str = Field(min_length=1, max_length=16)  # 步骤显示标签
    description: Optional[str] = Field(default=None, max_length=40)  # 步骤描述


class FlowEdge(BaseDiagramModel):
    """流程边。

    用于流程图中步骤之间的连接。
    """
    source: str = Field(min_length=1, max_length=40)  # 源步骤ID
    target: str = Field(min_length=1, max_length=40)  # 目标步骤ID
    label: Optional[str] = Field(default=None, max_length=16)  # 边标签


class FlowSpec(BaseDiagramModel):
    """流程图规格。

    定义流程图的步骤和边。
    """
    steps: list[FlowStep] = Field(min_length=1, max_length=25)  # 步骤列表
    edges: list[FlowEdge] = Field(default_factory=list, max_length=40)  # 边列表

    @model_validator(mode="after")
    def validate_edges(self) -> "FlowSpec":
        """验证边的源和目标必须引用已存在的步骤ID。"""
        ids = {step.id for step in self.steps}
        for edge in self.edges:
            if edge.source not in ids or edge.target not in ids:
                raise ValueError("flow edge source/target must reference existing step ids")
        return self


class CompareItem(BaseDiagramModel):
    """对比项。

    用于对比图中的单个对比项。
    """
    label: str = Field(min_length=1, max_length=16)  # 对比项标签
    description: Optional[str] = Field(default=None, max_length=40)  # 对比项描述
    points: list[str] = Field(default_factory=list, max_length=6)  # 对比要点列表


class CompareSpec(BaseDiagramModel):
    """对比图规格。

    定义对比图的对比项和维度。
    """
    items: list[CompareItem] = Field(min_length=2, max_length=6)  # 对比项列表
    dimensions: list[str] = Field(default_factory=list, max_length=8)  # 对比维度列表


class RelationSpec(BaseDiagramModel):
    """关系图规格。

    定义关系图的节点和边。
    """
    nodes: list[DiagramNode] = Field(min_length=1, max_length=25)  # 节点列表
    edges: list[DiagramEdge] = Field(default_factory=list, max_length=40)  # 边列表

    @model_validator(mode="after")
    def validate_edges(self) -> "RelationSpec":
        """验证边的源和目标必须引用已存在的节点ID。"""
        ids = {node.id for node in self.nodes}
        for edge in self.edges:
            if edge.source not in ids or edge.target not in ids:
                raise ValueError("relation edge source/target must reference existing node ids")
        return self


class SequenceActor(BaseDiagramModel):
    """时序图参与者。

    用于时序图中的参与者定义。
    """
    id: str = Field(min_length=1, max_length=40)  # 参与者唯一标识
    label: str = Field(min_length=1, max_length=16)  # 参与者显示标签
    description: Optional[str] = Field(default=None, max_length=40)  # 参与者描述


class SequenceMessage(BaseDiagramModel):
    """时序图消息。

    用于时序图中参与者之间的消息传递。
    """
    from_actor: str = Field(alias="from", min_length=1, max_length=40)  # 发送者ID（使用别名 "from"）
    to_actor: str = Field(alias="to", min_length=1, max_length=40)  # 接收者ID（使用别名 "to"）
    label: str = Field(min_length=1, max_length=16)  # 消息标签
    description: Optional[str] = Field(default=None, max_length=40)  # 消息描述


class SequenceSpec(BaseDiagramModel):
    """时序图规格。

    定义时序图的参与者和消息。
    """
    actors: list[SequenceActor] = Field(min_length=2, max_length=6)  # 参与者列表
    messages: list[SequenceMessage] = Field(min_length=1, max_length=12)  # 消息列表

    @model_validator(mode="after")
    def validate_messages(self) -> "SequenceSpec":
        """验证消息的发送者和接收者必须引用已存在的参与者ID。"""
        ids = {actor.id for actor in self.actors}
        for message in self.messages:
            if message.from_actor not in ids or message.to_actor not in ids:
                raise ValueError("sequence message from/to must reference existing actor ids")
        return self


class StateTransition(BaseDiagramModel):
    """状态转换。

    用于状态图中状态之间的转换。
    """
    from_state: str = Field(alias="from", min_length=1, max_length=40)  # 源状态ID（使用别名 "from"）
    to_state: str = Field(alias="to", min_length=1, max_length=40)  # 目标状态ID（使用别名 "to"）
    label: str = Field(min_length=1, max_length=16)  # 转换标签
    description: Optional[str] = Field(default=None, max_length=40)  # 转换描述


class StateSpec(BaseDiagramModel):
    """状态图规格。

    定义状态图的状态和转换。
    """
    states: list[DiagramNode] = Field(min_length=1, max_length=25)  # 状态列表
    transitions: list[StateTransition] = Field(default_factory=list, max_length=40)  # 转换列表

    @model_validator(mode="after")
    def validate_transitions(self) -> "StateSpec":
        """验证转换的源和目标状态必须引用已存在的状态ID。"""
        ids = {state.id for state in self.states}
        for transition in self.transitions:
            if transition.from_state not in ids or transition.to_state not in ids:
                raise ValueError("state transition from/to must reference existing state ids")
        return self


class HierarchyDiagram(BaseDiagramModel):
    """层级结构图。

    用于展示知识点组成、分类、结构拆解。
    """
    type: Literal["hierarchy"]  # 图解类型标识
    title: str = Field(min_length=1, max_length=20)  # 图解标题
    summary: Optional[str] = Field(default=None, max_length=50)  # 图解摘要
    spec: HierarchySpec  # 层级结构规格


class FlowDiagram(BaseDiagramModel):
    """流程图。

    用于展示步骤、过程、运行机制。
    """
    type: Literal["flow"]  # 图解类型标识
    title: str = Field(min_length=1, max_length=20)  # 图解标题
    summary: Optional[str] = Field(default=None, max_length=50)  # 图解摘要
    spec: FlowSpec  # 流程规格


class CompareDiagram(BaseDiagramModel):
    """对比图。

    用于展示区别、优缺点、易混概念。
    """
    type: Literal["compare"]  # 图解类型标识
    title: str = Field(min_length=1, max_length=20)  # 图解标题
    summary: Optional[str] = Field(default=None, max_length=50)  # 图解摘要
    spec: CompareSpec  # 对比规格


class RelationDiagram(BaseDiagramModel):
    """关系图。

    用于展示依赖、因果、模块关系。
    """
    type: Literal["relation"]  # 图解类型标识
    title: str = Field(min_length=1, max_length=20)  # 图解标题
    summary: Optional[str] = Field(default=None, max_length=50)  # 图解摘要
    spec: RelationSpec  # 关系规格


class SequenceDiagram(BaseDiagramModel):
    """时序图。

    用于展示客户端/服务器、前后端、协议交互。
    """
    type: Literal["sequence"]  # 图解类型标识
    title: str = Field(min_length=1, max_length=20)  # 图解标题
    summary: Optional[str] = Field(default=None, max_length=50)  # 图解摘要
    spec: SequenceSpec  # 时序规格


class StateDiagram(BaseDiagramModel):
    """状态图。

    用于展示状态机、生命周期、算法过程。
    """
    type: Literal["state"]  # 图解类型标识
    title: str = Field(min_length=1, max_length=20)  # 图解标题
    summary: Optional[str] = Field(default=None, max_length=50)  # 图解摘要
    spec: StateSpec  # 状态规格


# ===================================================================
# 计算机学科专用图表 Schema
# ===================================================================


class ClassItem(BaseDiagramModel):
    """类图中的类定义。

    用于类图中的单个类。
    """
    name: str = Field(min_length=1, max_length=40)  # 类名
    annotation: Optional[str] = Field(default=None, max_length=20)  # 注解（如 interface）
    attributes: list[str] = Field(default_factory=list, max_length=8)  # 属性列表
    methods: list[str] = Field(default_factory=list, max_length=8)  # 方法列表


class ClassRelationship(BaseDiagramModel):
    """类图关系。

    用于类图中类之间的关系。
    """
    from_class: str = Field(alias="from", min_length=1, max_length=40)  # 源类名
    to_class: str = Field(alias="to", min_length=1, max_length=40)  # 目标类名
    type: str = Field(default="association", max_length=20)  # 关系类型
    label: Optional[str] = Field(default=None, max_length=16)  # 关系标签


class ClassSpec(BaseDiagramModel):
    """类图规格。

    定义类图的类和关系。
    """
    classes: list[ClassItem] = Field(min_length=1, max_length=8)  # 类列表
    relationships: list[ClassRelationship] = Field(default_factory=list, max_length=12)  # 关系列表


class ClassDiagram(BaseDiagramModel):
    """类图。

    用于展示类结构、继承关系、接口实现。
    """
    type: Literal["class"]  # 图解类型标识
    title: str = Field(min_length=1, max_length=20)  # 图解标题
    summary: Optional[str] = Field(default=None, max_length=50)  # 图解摘要
    spec: ClassSpec  # 类图规格


class ERField(BaseDiagramModel):
    """ER 图字段。

    用于实体中的字段定义。
    """
    name: str = Field(min_length=1, max_length=20)  # 字段名
    type: str = Field(min_length=1, max_length=20)  # 字段类型
    key: Optional[str] = Field(default=None, max_length=10)  # 键类型: pk/fk/unique


class EREntity(BaseDiagramModel):
    """ER 图实体。

    用于 ER 图中的实体定义。
    """
    name: str = Field(min_length=1, max_length=40)  # 实体名
    fields: list[ERField] = Field(min_length=1, max_length=12)  # 字段列表


class ERRelationship(BaseDiagramModel):
    """ER 图关系。

    用于实体之间的关系。
    """
    from_entity: str = Field(alias="from", min_length=1, max_length=40)  # 源实体名
    to_entity: str = Field(alias="to", min_length=1, max_length=40)  # 目标实体名
    type: Optional[str] = Field(default="||--||", max_length=10)  # 关系类型符号
    label: Optional[str] = Field(default=None, max_length=16)  # 关系标签


class ERSpec(BaseDiagramModel):
    """ER 图规格。

    定义 ER 图的实体和关系。
    """
    entities: list[EREntity] = Field(min_length=1, max_length=8)  # 实体列表
    relationships: list[ERRelationship] = Field(default_factory=list, max_length=12)  # 关系列表


class ERDiagram(BaseDiagramModel):
    """实体关系图。

    用于展示数据库表结构、字段关系。
    """
    type: Literal["er"]  # 图解类型标识
    title: str = Field(min_length=1, max_length=20)  # 图解标题
    summary: Optional[str] = Field(default=None, max_length=50)  # 图解摘要
    spec: ERSpec  # ER 图规格


class BlockItem(BaseDiagramModel):
    """方块图中的方块。

    用于方块图中的单个方块。
    """
    id: str = Field(min_length=1, max_length=40)  # 方块 ID
    type: Optional[str] = Field(default="block", max_length=10)  # 方块类型: block/space/x
    label: Optional[str] = Field(default=None, max_length=16)  # 方块标签


class BlockConnection(BaseDiagramModel):
    """方块图连接。

    用于方块之间的连接。
    """
    from_block: str = Field(alias="from", min_length=1, max_length=40)  # 源方块 ID
    to_block: str = Field(alias="to", min_length=1, max_length=40)  # 目标方块 ID
    label: Optional[str] = Field(default=None, max_length=16)  # 连接标签


class BlockSpec(BaseDiagramModel):
    """方块图规格。

    定义方块图的方块和连接。
    """
    columns: Optional[int] = Field(default=3, ge=1, le=10)  # 列数
    blocks: list[BlockItem] = Field(min_length=1, max_length=16)  # 方块列表
    connections: list[BlockConnection] = Field(default_factory=list, max_length=12)  # 连接列表


class BlockDiagram(BaseDiagramModel):
    """方块图。

    用于展示系统架构、模块布局。
    """
    type: Literal["block"]  # 图解类型标识
    title: str = Field(min_length=1, max_length=20)  # 图解标题
    summary: Optional[str] = Field(default=None, max_length=50)  # 图解摘要
    spec: BlockSpec  # 方块图规格


class PacketField(BaseDiagramModel):
    """网络包字段。

    用于网络包中的字段定义。
    """
    name: str = Field(min_length=1, max_length=20)  # 字段名
    start: int = Field(ge=0, le=128)  # 起始位
    length: int = Field(ge=1, le=64)  # 字段长度


class PacketSpec(BaseDiagramModel):
    """网络包规格。

    定义网络包的标题和字段。
    """
    title: Optional[str] = Field(default=None, max_length=20)  # 包标题
    fields: list[PacketField] = Field(min_length=1, max_length=16)  # 字段列表


class PacketDiagram(BaseDiagramModel):
    """网络包图。

    用于展示网络协议包结构、数据帧格式。
    """
    type: Literal["packet"]  # 图解类型标识
    title: str = Field(min_length=1, max_length=20)  # 图解标题
    summary: Optional[str] = Field(default=None, max_length=50)  # 图解摘要
    spec: PacketSpec  # 网络包规格


class GitCommit(BaseDiagramModel):
    """Git 提交/分支操作。

    用于 Git 图中的单个操作。
    """
    type: str = Field(default="commit", max_length=20)  # 操作类型: commit/branch/checkout/merge/cherry-pick
    id: Optional[str] = Field(default=None, max_length=40)  # 提交 ID
    name: Optional[str] = Field(default=None, max_length=40)  # 分支名
    tag: Optional[str] = Field(default=None, max_length=20)  # 标签
    target: Optional[str] = Field(default=None, max_length=40)  # cherry-pick 目标


class GitSpec(BaseDiagramModel):
    """Git 图规格。

    定义 Git 图的提交和分支操作。
    """
    commits: list[GitCommit] = Field(min_length=1, max_length=20)  # 提交/操作列表


class GitDiagram(BaseDiagramModel):
    """Git 图。

    用于展示 Git 分支、提交历史、合并流程。
    """
    type: Literal["git"]  # 图解类型标识
    title: str = Field(min_length=1, max_length=20)  # 图解标题
    summary: Optional[str] = Field(default=None, max_length=50)  # 图解摘要
    spec: GitSpec  # Git 图规格


# ===================================================================
# 软件工程教学常用图表 Schema
# ===================================================================


class ActivityNode(BaseDiagramModel):
    """活动图节点。

    用于活动图中的活动节点。
    """
    id: str = Field(min_length=1, max_length=40)  # 节点 ID
    label: str = Field(min_length=1, max_length=16)  # 节点标签
    nodeType: Optional[str] = Field(default="action", max_length=20)  # 节点类型: start/end/action/decision/fork/join
    description: Optional[str] = Field(default=None, max_length=40)  # 节点描述


class ActivityTransition(BaseDiagramModel):
    """活动图转换。

    用于活动之间的转换。
    """
    from_activity: str = Field(alias="from", min_length=1, max_length=40)  # 源活动 ID
    to_activity: str = Field(alias="to", min_length=1, max_length=40)  # 目标活动 ID
    label: Optional[str] = Field(default=None, max_length=16)  # 转换标签


class ActivitySpec(BaseDiagramModel):
    """活动图规格。

    定义活动图的活动和转换。
    """
    activities: list[ActivityNode] = Field(min_length=1, max_length=12)  # 活动列表
    transitions: list[ActivityTransition] = Field(default_factory=list, max_length=40)  # 转换列表


class ActivityDiagram(BaseDiagramModel):
    """活动图。

    用于展示业务流程、算法步骤、操作流程。
    """
    type: Literal["activity"]  # 图解类型标识
    title: str = Field(min_length=1, max_length=20)  # 图解标题
    summary: Optional[str] = Field(default=None, max_length=50)  # 图解摘要
    spec: ActivitySpec  # 活动图规格


class UsecaseActor(BaseDiagramModel):
    """用例图参与者。

    用于用例图中的参与者。
    """
    id: str = Field(min_length=1, max_length=40)  # 参与者 ID
    label: str = Field(min_length=1, max_length=16)  # 参与者标签


class UsecaseItem(BaseDiagramModel):
    """用例图用例。

    用于用例图中的用例。
    """
    id: str = Field(min_length=1, max_length=40)  # 用例 ID
    label: str = Field(min_length=1, max_length=16)  # 用例标签


class UsecaseRelationship(BaseDiagramModel):
    """用例图关系。

    用于参与者与用例之间的关系。
    """
    from_item: str = Field(alias="from", min_length=1, max_length=40)  # 源 ID
    to_item: str = Field(alias="to", min_length=1, max_length=40)  # 目标 ID
    type: Optional[str] = Field(default="association", max_length=20)  # 关系类型: association/include/extend/generalization
    label: Optional[str] = Field(default=None, max_length=16)  # 关系标签


class UsecaseSpec(BaseDiagramModel):
    """用例图规格。

    定义用例图的参与者、用例和关系。
    """
    system: Optional[str] = Field(default="系统", max_length=20)  # 系统名称
    actors: list[UsecaseActor] = Field(min_length=1, max_length=25)  # 参与者列表
    usecases: list[UsecaseItem] = Field(min_length=1, max_length=8)  # 用例列表
    relationships: list[UsecaseRelationship] = Field(default_factory=list, max_length=12)  # 关系列表


class UsecaseDiagram(BaseDiagramModel):
    """用例图。

    用于展示系统功能、用户交互、需求分析。
    """
    type: Literal["usecase"]  # 图解类型标识
    title: str = Field(min_length=1, max_length=20)  # 图解标题
    summary: Optional[str] = Field(default=None, max_length=50)  # 图解摘要
    spec: UsecaseSpec  # 用例图规格


class ComponentItem(BaseDiagramModel):
    """组件图组件。

    用于组件图中的组件。
    """
    id: str = Field(min_length=1, max_length=40)  # 组件 ID
    label: str = Field(min_length=1, max_length=16)  # 组件标签
    type: Optional[str] = Field(default="component", max_length=20)  # 组件类型: component/package
    children: list["ComponentItem"] = Field(default_factory=list, max_length=6)  # 子组件


class ComponentInterface(BaseDiagramModel):
    """组件图接口。

    用于组件图中的接口。
    """
    id: str = Field(min_length=1, max_length=40)  # 接口 ID
    label: str = Field(min_length=1, max_length=16)  # 接口标签
    ifaceType: Optional[str] = Field(default="provided", max_length=10)  # 接口类型: provided/required


class ComponentConnection(BaseDiagramModel):
    """组件图连接。

    用于组件之间的连接。
    """
    from_comp: str = Field(alias="from", min_length=1, max_length=40)  # 源组件 ID
    to_comp: str = Field(alias="to", min_length=1, max_length=40)  # 目标组件 ID
    type: Optional[str] = Field(default="dependency", max_length=20)  # 连接类型: dependency/interface
    label: Optional[str] = Field(default=None, max_length=16)  # 连接标签


class ComponentSpec(BaseDiagramModel):
    """组件图规格。

    定义组件图的组件、接口和连接。
    """
    components: list[ComponentItem] = Field(min_length=1, max_length=12)  # 组件列表
    interfaces: list[ComponentInterface] = Field(default_factory=list, max_length=8)  # 接口列表
    connections: list[ComponentConnection] = Field(default_factory=list, max_length=12)  # 连接列表


class ComponentDiagram(BaseDiagramModel):
    """组件图。

    用于展示系统架构、模块划分、接口依赖。
    """
    type: Literal["component"]  # 图解类型标识
    title: str = Field(min_length=1, max_length=20)  # 图解标题
    summary: Optional[str] = Field(default=None, max_length=50)  # 图解摘要
    spec: ComponentSpec  # 组件图规格


class PackageItem(BaseDiagramModel):
    """包图包。

    用于包图中的包。
    """
    id: str = Field(min_length=1, max_length=40)  # 包 ID
    label: str = Field(min_length=1, max_length=16)  # 包标签
    children: list["PackageItem"] = Field(default_factory=list, max_length=6)  # 子包


class PackageDependency(BaseDiagramModel):
    """包图依赖。

    用于包之间的依赖。
    """
    from_pkg: str = Field(alias="from", min_length=1, max_length=40)  # 源包 ID
    to_pkg: str = Field(alias="to", min_length=1, max_length=40)  # 目标包 ID
    type: Optional[str] = Field(default="dependency", max_length=20)  # 依赖类型: dependency/import/access
    label: Optional[str] = Field(default=None, max_length=16)  # 依赖标签


class PackageSpec(BaseDiagramModel):
    """包图规格。

    定义包图的包和依赖。
    """
    packages: list[PackageItem] = Field(min_length=1, max_length=8)  # 包列表
    dependencies: list[PackageDependency] = Field(default_factory=list, max_length=12)  # 依赖列表


class PackageDiagram(BaseDiagramModel):
    """包图。

    用于展示代码组织、模块依赖、架构划分。
    """
    type: Literal["package"]  # 图解类型标识
    title: str = Field(min_length=1, max_length=20)  # 图解标题
    summary: Optional[str] = Field(default=None, max_length=50)  # 图解摘要
    spec: PackageSpec  # 包图规格


class DeploymentNode(BaseDiagramModel):
    """部署图节点。

    用于部署图中的节点。
    """
    id: str = Field(min_length=1, max_length=40)  # 节点 ID
    label: str = Field(min_length=1, max_length=16)  # 节点标签
    type: Optional[str] = Field(default="device", max_length=20)  # 节点类型: device/execution
    artifacts: list[str] = Field(default_factory=list, max_length=6)  # 制品列表


class DeploymentConnection(BaseDiagramModel):
    """部署图连接。

    用于节点之间的连接。
    """
    from_node: str = Field(alias="from", min_length=1, max_length=40)  # 源节点 ID
    to_node: str = Field(alias="to", min_length=1, max_length=40)  # 目标节点 ID
    type: Optional[str] = Field(default="association", max_length=20)  # 连接类型: association/dependency
    label: Optional[str] = Field(default=None, max_length=16)  # 连接标签


class DeploymentSpec(BaseDiagramModel):
    """部署图规格。

    定义部署图的节点和连接。
    """
    nodes: list[DeploymentNode] = Field(min_length=1, max_length=8)  # 节点列表
    connections: list[DeploymentConnection] = Field(default_factory=list, max_length=12)  # 连接列表


class DeploymentDiagram(BaseDiagramModel):
    """部署图。

    用于展示运行环境、硬件节点、分布式系统架构。
    """
    type: Literal["deployment"]  # 图解类型标识
    title: str = Field(min_length=1, max_length=20)  # 图解标题
    summary: Optional[str] = Field(default=None, max_length=50)  # 图解摘要
    spec: DeploymentSpec  # 部署图规格


class ObjectItem(BaseDiagramModel):
    """对象图对象。

    用于对象图中的对象。
    """
    id: str = Field(min_length=1, max_length=40)  # 对象 ID
    name: Optional[str] = Field(default=None, max_length=20)  # 对象名
    class_name: Optional[str] = Field(default=None, alias="class", max_length=20)  # 类名
    attributes: list[str] = Field(default_factory=list, max_length=6)  # 属性列表


class ObjectLink(BaseDiagramModel):
    """对象图链接。

    用于对象之间的链接。
    """
    from_obj: str = Field(alias="from", min_length=1, max_length=40)  # 源对象 ID
    to_obj: str = Field(alias="to", min_length=1, max_length=40)  # 目标对象 ID
    type: Optional[str] = Field(default="association", max_length=20)  # 链接类型: association/aggregation/composition
    label: Optional[str] = Field(default=None, max_length=16)  # 链接标签


class ObjectSpec(BaseDiagramModel):
    """对象图规格。

    定义对象图的对象和链接。
    """
    objects: list[ObjectItem] = Field(min_length=1, max_length=8)  # 对象列表
    links: list[ObjectLink] = Field(default_factory=list, max_length=12)  # 链接列表


class ObjectDiagram(BaseDiagramModel):
    """对象图。

    用于展示对象实例、运行时状态、对象关系。
    """
    type: Literal["object"]  # 图解类型标识
    title: str = Field(min_length=1, max_length=20)  # 图解标题
    summary: Optional[str] = Field(default=None, max_length=50)  # 图解摘要
    spec: ObjectSpec  # 对象图规格


class CommunicationObject(BaseDiagramModel):
    """通信图对象。

    用于通信图中的对象。
    """
    id: str = Field(min_length=1, max_length=40)  # 对象 ID
    name: Optional[str] = Field(default=None, max_length=20)  # 对象名
    class_name: Optional[str] = Field(default=None, alias="class", max_length=20)  # 类名


class CommunicationMessage(BaseDiagramModel):
    """通信图消息。

    用于对象之间的消息。
    """
    from_obj: str = Field(alias="from", min_length=1, max_length=40)  # 源对象 ID
    to_obj: str = Field(alias="to", min_length=1, max_length=40)  # 目标对象 ID
    label: str = Field(min_length=1, max_length=16)  # 消息标签
    sequence: Optional[str] = Field(default=None, max_length=10)  # 序号


class CommunicationSpec(BaseDiagramModel):
    """通信图规格。

    定义通信图的对象和消息。
    """
    objects: list[CommunicationObject] = Field(min_length=1, max_length=8)  # 对象列表
    messages: list[CommunicationMessage] = Field(min_length=1, max_length=12)  # 消息列表


class CommunicationDiagram(BaseDiagramModel):
    """通信图。

    用于展示对象协作、消息流向、交互关系。
    """
    type: Literal["communication"]  # 图解类型标识
    title: str = Field(min_length=1, max_length=20)  # 图解标题
    summary: Optional[str] = Field(default=None, max_length=50)  # 图解摘要
    spec: CommunicationSpec  # 通信图规格


class DiagramRender(BaseDiagramModel):
    """图解渲染信息。

    包含渲染引擎和渲染源码。
    """
    engine: Literal["mermaid"]  # 渲染引擎（目前仅支持 mermaid）
    format: Literal["text"]  # 输出格式
    source: str = Field(min_length=1)  # 渲染源码


# 支持的图解类型联合
EnabledDiagram = Annotated[
    Union[
        # 基础图解类型
        HierarchyDiagram,
        FlowDiagram,
        CompareDiagram,
        RelationDiagram,
        SequenceDiagram,
        StateDiagram,
        # 计算机学科专用图表
        ClassDiagram,
        ERDiagram,
        BlockDiagram,
        PacketDiagram,
        GitDiagram,
        # 软件工程教学常用图表
        ActivityDiagram,
        UsecaseDiagram,
        ComponentDiagram,
        PackageDiagram,
        DeploymentDiagram,
        ObjectDiagram,
        CommunicationDiagram,
    ],
    Field(discriminator="type"),
]


class DiagramDecision(BaseDiagramModel):
    """图解决策结果。

    LLM 判断是否需要生成图解及选择图解类型。
    """
    need_diagram: bool  # 是否需要图解
    diagram_type: Optional[DiagramType] = None  # 图解类型
    reason: Optional[str] = Field(default=None, max_length=80)  # 决策原因


# 图解类型到模型类的映射
DIAGRAM_MODEL_MAP: dict[str, type[BaseDiagramModel]] = {
    # 基础图解类型
    "hierarchy": HierarchyDiagram,
    "flow": FlowDiagram,
    "compare": CompareDiagram,
    "relation": RelationDiagram,
    "sequence": SequenceDiagram,
    "state": StateDiagram,
    # 计算机学科专用图表
    "class": ClassDiagram,
    "er": ERDiagram,
    "block": BlockDiagram,
    "packet": PacketDiagram,
    "git": GitDiagram,
    # 软件工程教学常用图表
    "activity": ActivityDiagram,
    "usecase": UsecaseDiagram,
    "component": ComponentDiagram,
    "package": PackageDiagram,
    "deployment": DeploymentDiagram,
    "object": ObjectDiagram,
    "communication": CommunicationDiagram,
}


# 重建 forward reference
HierarchyNode.model_rebuild()
ComponentItem.model_rebuild()
PackageItem.model_rebuild()
