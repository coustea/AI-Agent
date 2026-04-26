"""Chat 模块数据模式定义。

包含 API 层请求/响应模型、Agent 内部状态类型、图解 Schema 等。
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal, Optional, TypedDict, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


# ===================================================================
# API 层数据模型（Pydantic BaseModel）
# ===================================================================

class MentorChatRequest(BaseModel):
    """聊天请求模型。

    前端发送的聊天请求参数。
    """
    message: str  # 用户消息内容
    session_id: Optional[str] = None  # 会话ID，为空则使用默认会话
    image_urls: Optional[list[str]] = None  # 图片URL列表
    file_urls: Optional[list[str]] = None  # 文件URL列表
    need_diagram: Optional[bool] = False  # 是否生成图解（Mermaid SVG）
    generate_video: Optional[bool] = False  # 是否生成视频
    enable_search: Optional[bool] = False  # 是否启用联网搜索


class AttachmentInfo(BaseModel):
    """单条附件信息。

    用于描述消息中包含的附件详情。
    """
    url: str  # 附件URL
    type: str  # 附件类型: "image" | "document"
    name: str  # 附件文件名


class ToolCallRecord(BaseModel):
    """一次工具调用的完整记录（API 层）。

    记录工具名称、参数、结果和状态。
    """
    tool: str  # 工具名称
    args: dict | str  # 工具参数（字典或字符串）
    result: str | dict  # 工具返回结果
    status: str  # 调用状态: "success" | "error"


class ChatMessageItem(BaseModel):
    """返回给前端的消息条目。

    包含角色、内容、附件、工具调用记录等。
    """
    role: str  # 消息角色: "user" | "assistant" | "tool"
    content: str  # 消息文本内容
    attachments: Optional[list[AttachmentInfo]] = None  # 附件列表
    tool_calls: Optional[list[ToolCallRecord]] = None  # 工具调用记录
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

class ToolCallDetail(TypedDict, total=False):
    """工具调用记录（Agent 内部状态）。

    用于 Agent 内部追踪工具调用过程。
    """
    tool: str  # 工具名称
    args: dict[str, Any] | str  # 工具参数
    result: str  # 工具结果
    status: str  # 调用状态
    error: str  # 错误信息


class TutorState(TypedDict, total=False):
    """LangGraph 运行状态 — 精简版。

    移除了 planner/compile_plan/execute_step/replan 相关的复杂状态字段。
    所有字段均为可选，支持 LangGraph 增量更新。
    """

    # ---- 用户身份与附件 ----
    user_id: int  # 用户ID
    session_id: str  # 会话ID
    image_urls: Optional[list[str]]  # 图片URL列表
    file_urls: Optional[list[str]]  # 文件URL列表
    need_diagram: bool  # 是否生成图解
    generate_video: bool  # 是否生成视频
    request_generate_video: bool  # 请求生成视频标志
    enable_search: bool  # 是否启用搜索
    diagram: Optional[dict[str, Any]]  # 生成的图解数据
    diagram_error: Optional[str]  # 图解生成错误信息

    # ---- 路由与执行模式 ----
    route: str  # 路由结果: "direct" | "attachment_needed"
    execution_mode: str  # 执行模式: "direct" | "attachment"

    # ---- 上下文信息 ----
    profile_context: str  # 用户画像上下文
    fact_context: str  # 长期记忆上下文
    recent_chat_context: str  # 近期对话上下文
    file_context: str  # 文件上下文
    attachment_analysis_context: str  # 附件分析上下文
    attachment_analysis: dict[str, Any]  # 附件分析结果

    # ---- Prompt 模板 ----
    system_prompt: str  # 系统提示词

    # ---- 对话消息 ----
    messages: Annotated[list[AnyMessage], add_messages]  # 消息列表（支持增量追加）

    # ---- 终止与调试信息 ----
    answer_text: str  # 最终回答文本
    last_guard_decision: str  # 最近守卫决策: "need_diagram" | "generate_video" | "end"
    guard_reason: str  # 守卫决策原因
    termination_reason: str  # 终止原因
    image_generation_status: str  # 图片生成状态
    video_generation_status: str  # 视频生成状态
    image_generation_prompt: str  # 图片生成提示词
    video_generation_prompt: str  # 视频生成提示词
    image_generation_plan: dict[str, Any]  # 图片生成计划
    video_generation_plan: dict[str, Any]  # 视频生成计划


# ===================================================================
# 图解 Schema（从 diagram_schemas.py 合并）
# ===================================================================

# 图解类型字面量
DiagramType = Literal["hierarchy", "flow", "compare", "relation", "sequence", "state"]


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
    steps: list[FlowStep] = Field(min_length=1, max_length=8)  # 步骤列表
    edges: list[FlowEdge] = Field(default_factory=list, max_length=12)  # 边列表

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
    nodes: list[DiagramNode] = Field(min_length=1, max_length=8)  # 节点列表
    edges: list[DiagramEdge] = Field(default_factory=list, max_length=16)  # 边列表

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
    states: list[DiagramNode] = Field(min_length=1, max_length=8)  # 状态列表
    transitions: list[StateTransition] = Field(default_factory=list, max_length=12)  # 转换列表

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
        HierarchyDiagram,
        FlowDiagram,
        CompareDiagram,
        RelationDiagram,
        SequenceDiagram,
        StateDiagram,
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
    "hierarchy": HierarchyDiagram,
    "flow": FlowDiagram,
    "compare": CompareDiagram,
    "relation": RelationDiagram,
    "sequence": SequenceDiagram,
    "state": StateDiagram,
}


# 重建 HierarchyNode 的 forward reference
HierarchyNode.model_rebuild()
