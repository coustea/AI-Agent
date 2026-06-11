"""Chat 模块核心数据模式 — 编排请求、证据模型、推理结果、教学图解 Schema。

所有 DTO 集中在此文件，打破原分散文件间的循环依赖。
按职责分为五组：

  1. 基础消息与证据 — ChatHistoryMessage / Evidence / EvidenceSet / UploadResponse
  2. 工具意图与最终回答 — ToolIntent / FinalAnswer / ReasoningResult（agent ↔ orchestrator 的合约类型）
  2. 工具意图与最终回答 — ToolIntent / FinalAnswer / FinalAnswerStream / ReasoningResult（agent ↔ orchestrator 的合约类型）
  3. 编排层基础模型 — TurnRequest / ConstraintReport（orchestrator 输入/输出约束）
  4. 教学图解 Schema — TeachingDiagram 及 6 种 payload（comparison/flowchart/sequence/framework/summary/hierarchy）
"""

from __future__ import annotations

from typing import Any, AsyncIterator, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ===================================================================
# 基础消息与证据
# ===================================================================


class ChatHistoryMessage(BaseModel):
    """前端传来的历史消息 DTO，与 DB ChatMessage 不直接对应。

    用于 SSE 请求中的 history 字段，转为 LangChain 消息后进入推理 prompt。
    """
    role: str = Field(..., description="消息角色: user / assistant / system / tool")
    content: str = Field(..., description="消息文本内容")
    tool_calls: list[dict] | None = Field(default=None, description="assistant 角色时携带的工具调用要求")
    tool_call_id: str | None = Field(default=None, description="tool 角色时对应的工具调用 ID")
    turn_id: int | None = Field(default=None, description="所属对话轮次 ID")
    message_kind: str | None = Field(default=None, description="assistant_tool_request / tool_result / assistant_answer")


EvidenceType = Literal[
    "attachment",
    "web_search",
    "knowledge_base",
    "learner_profile",
    "long_term_memory",
    "recent_evaluation",
]


class Evidence(BaseModel):
    """统一证据模型 — 各阶段产出的信息载体。

    每个阶段（附件分析/搜索/工具执行）产出的信息都封装为 Evidence，
    通过 usable_for_answer / usable_for_diagram 控制下游是否可见。
    """
    evidence_type: EvidenceType
    summary: str  # 人类可读的摘要，嵌入推理 prompt
    details: dict[str, Any] = Field(default_factory=dict)  # 结构化详情，供持久化和前端展示
    confidence: float = 0.7
    freshness: str = "turn"  # "turn" / "session" / "persistent"
    scope: str = "turn"  # 证据生命周期：turn 级 / session 级
    usable_for_answer: bool = True  # 是否注入推理 prompt
    usable_for_diagram: bool = True  # 是否注入图解生成


class EvidenceSet(BaseModel):
    """证据集合 — 编排流水线中各阶段产出的证据汇总容器。

    for_answer() / for_diagram() 分别过滤出对应下游可用的证据。
    """
    items: list[Evidence] = Field(default_factory=list)

    def for_answer(self) -> list[Evidence]:
        return [item for item in self.items if item.usable_for_answer]

    def for_diagram(self) -> list[Evidence]:
        return [item for item in self.items if item.usable_for_diagram]

    def extend(self, items: list[Evidence]) -> None:
        self.items.extend(items)


class UploadResponse(BaseModel):
    """文件上传成功后的响应 DTO，包含 URL、类型、大小等信息。"""
    url: str = Field(..., description="文件访问 URL")
    file_type: str = Field(default="document", description="image / document")
    original_name: str = Field(default="", description="原始文件名")
    size_bytes: int = Field(default=0, ge=0, description="文件大小")
    storage_key: str | None = Field(default=None, description="存储键")
    mime_type: str | None = Field(default=None, description="MIME 类型")
    extension: str | None = Field(default=None, description="文件扩展名")


# ===================================================================
# 工具意图与最终回答
# ===================================================================


class ToolIntent(BaseModel):
    """Agent 推理产出的「需要调工具」信号 — 由 orchestrator 执行后回填证据。

    tool_name: web_search / learner_profile / long_term_memory
    payload: 工具所需参数（如搜索 query、画像维度等）
    """
    tool_name: str
    payload: dict[str, Any] = Field(default_factory=dict)


class FinalAnswer(BaseModel):
    """Agent 推理产出的「直接回答」信号 — 推理循环终止条件。"""
    kind: Literal["final_answer"] = "final_answer"
    answer: str


class FinalAnswerStream:
    """Wraps an asynchronous iterator yielding string chunks for the final answer."""
    def __init__(self, stream: AsyncIterator[str]):
        self.stream = stream


ReasoningResult = ToolIntent | FinalAnswer  # Agent.reason() 的返回类型联合


# ===================================================================
# 编排层基础模型
# ===================================================================

class TurnRequest(BaseModel):
    """一轮对话的编排请求 — 由 service.py 构建，传入 orchestrator.run()。

    各标志位控制流水线是否启用对应阶段：
      attachment_analysis_enabled → 触发附件分析
      search_enabled              → 触发搜索
      diagram_enabled             → 触发教学图解
    """
    user_id: int
    session_id: str
    message: str
    attachments: list[str] = Field(default_factory=list)
    attachment_analysis_enabled: bool = False
    search_enabled: bool = False
    diagram_enabled: bool = False
    history: list[ChatHistoryMessage] = Field(default_factory=list)
    uploaded_file_ids_by_url: dict[str, int] = Field(default_factory=dict)  # URL → DB file_id 映射
    history_limit: int = 8  # 截取最近 N 条历史避免 token 溢出


class ConstraintReport(BaseModel):
    """推理循环约束报告 — 记录工具执行情况，防止重复调用和无限循环。

    由 orchestrator 在推理循环中逐步填充，最终随 TurnRunResult 返回。
    """
    executed_tools: list[str] = Field(default_factory=list)
    failed_tools: list[str] = Field(default_factory=list)
    skipped_tools: list[str] = Field(default_factory=list)
    max_steps_reached: bool = False
    unresolved_questions: list[str] = Field(default_factory=list)


# ===================================================================
# 教学图解 Schema（6 类图型：comparison / flowchart / sequence / framework / summary / hierarchy）
#
# 数据流：TeachingDiagramGenerator → LLM ainvoke_json(TeachingDiagram) → 前端渲染
# 每个 Payload 使用 extra="forbid" 严格约束字段，防止 LLM 输出多余内容。
# TeachingDiagram.validate_payload_type 确保 graph_type 与 visual_content 类型一致。
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
