"""教学图解 Schema + 生成器。

数据流：TeachingDiagramGenerator → LLM ainvoke_json(TeachingDiagram) → 前端渲染
每个 Payload 使用 extra="forbid" 严格约束字段，防止 LLM 输出多余内容。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Optional, Union

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.prompts import prompts

if TYPE_CHECKING:
    from app.chat.schemas.agent import TutorTurnContext
    from app.chat.schemas.evidence import EvidenceSet

logger = get_logger(__name__)


TeachingDiagramType = Literal[
    "comparison", "flowchart", "sequence", "framework", "summary", "hierarchy",
    "tree", "grid", "protocol", "timeline"
]


class TeachingContent(BaseModel):
    """教学图解的文本内容 — 所有图型共享此结构。"""
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

# ---- 7. 树形图 ----

class TreeDiagramNode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(description="节点唯一 ID")
    label: str = Field(description="节点标签/展示文本")
    left_id: Optional[str] = Field(default=None, description="左子节点 ID")
    right_id: Optional[str] = Field(default=None, description="右子节点 ID")
    type: Optional[str] = Field(default=None, description="节点类型（可选）")
    detail: Optional[str] = Field(default=None, description="节点详细说明（可选）")


class TreePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    root_id: str = Field(description="根节点 ID")
    nodes: list[TreeDiagramNode] = Field(description="树节点列表")


# ---- 8. 网格图 ----

class GridCell(BaseModel):
    model_config = ConfigDict(extra="forbid")
    index: int = Field(description="单元格索引/位置")
    label: str = Field(description="单元格展示文本")
    status: Optional[str] = Field(default=None, description="单元格状态（可选）")
    pointer: Optional[str] = Field(default=None, description="指向该单元格的指针名称/标签（可选）")
    detail: Optional[str] = Field(default=None, description="单元格详细说明（可选）")


class GridPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    layout: Literal["horizontal", "vertical", "matrix"] = Field(description="网格布局方向")
    cols: Optional[int] = Field(default=None, description="列数（仅在 matrix 布局下生效且建议提供）")
    cells: list[GridCell] = Field(description="网格单元格列表")


# ---- 9. 协议字段图 ----

class ProtocolField(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(description="协议字段名称")
    detail: Optional[str] = Field(default=None, description="协议字段详细说明")
    width_ratio: Optional[int] = Field(default=None, description="字段所占宽度比例（可选）")
    highlight: bool = Field(default=False, description="是否高亮突出显示")


class ProtocolPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    orientation: Literal["vertical", "horizontal_split"] = Field(description="协议报文展示方向")
    fields: list[ProtocolField] = Field(description="协议字段列表")


# ---- 10. 时间线轨道图 ----

class TimelineBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str = Field(description="时间块/事件标签")
    start: float = Field(description="开始时间/起始坐标位置")
    duration: float = Field(description="持续时间/时间块长度")
    status: Literal["normal", "active", "idle", "stall"] = Field(default="normal", description="时间块状态")


class TimelineTrack(BaseModel):
    model_config = ConfigDict(extra="forbid")
    track_name: str = Field(description="轨道/并发线路名称")
    blocks: list[TimelineBlock] = Field(description="该轨道下的时间块列表")


class TimelinePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    axis_label: str = Field(description="时间轴标签，如时间单位(ms, s)或阶段描述")
    tracks: list[TimelineTrack] = Field(description="时间线轨道列表")


# ---- 顶层 TeachingDiagram ----

class TeachingDiagram(BaseModel):
    """一次答疑对应的一张结构化教学图解。"""
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    thought: Optional[str] = Field(default=None, description="分析图解设计思路与教学目标匹配的过程")
    graph_type: TeachingDiagramType
    title: str = Field(min_length=1, max_length=80, description="主标题")
    subtitle: Optional[str] = Field(default=None, max_length=60, description="副标题")
    teaching_goal: str = Field(max_length=60, description="教学目标")
    course: Optional[str] = Field(default=None, max_length=30, description="课程名称")
    difficulty: Literal["beginner", "intermediate", "advanced"] = Field(default="intermediate", description="难度等级")
    visual_content: Union[
        ComparisonPayload, FlowchartPayload, SequencePayload,
        FrameworkPayload, SummaryPayload, HierarchyPayload,
        TreePayload, GridPayload, ProtocolPayload, TimelinePayload,
    ]
    teaching_content: TeachingContent

    @model_validator(mode="after")
    def validate_payload_type(self) -> "TeachingDiagram":
        """确保 graph_type 与 visual_content 的实际类型匹配。"""
        expected_type = {
            "comparison": ComparisonPayload,
            "flowchart": FlowchartPayload,
            "sequence": SequencePayload,
            "framework": FrameworkPayload,
            "summary": SummaryPayload,
            "hierarchy": HierarchyPayload,
            "tree": TreePayload,
            "grid": GridPayload,
            "protocol": ProtocolPayload,
            "timeline": TimelinePayload,
        }[self.graph_type]
        if not isinstance(self.visual_content, expected_type):
            raise ValueError("visual_content must match graph_type")
        return self


# ── 教学图解生成器 ──


class TeachingDiagramGenerator:
    """教学图解生成器：基于学生问题和回答，让 LLM 生成结构化图解 JSON。"""

    def __init__(self, llm=None) -> None:
        self.llm = llm or get_llm()

    async def generate(
        self,
        request: "TutorTurnContext",
        answer: str,
        evidence_set: "EvidenceSet",
    ) -> dict:
        attachment_context = "\n".join(
            item.summary for item in evidence_set.items if item.evidence_type == "attachment"
        ).strip()
        context_text = attachment_context or "无额外上下文。"
        prompt = (
            f"学生问题：\n{request.user_input}\n\n"
            f"最终回答：\n{answer}\n\n"
            f"上下文：\n{context_text}\n\n"
            "请生成一张能辅助学生理解答案的教学图解 JSON。"
        )
        diagram = await self.llm.ainvoke_json(
            TeachingDiagram,
            [
                SystemMessage(content=prompts.get("chat").get("teaching_diagram")),
                HumanMessage(content=prompt),
            ],
            temperature=0.1,
        )
        return diagram.model_dump(mode="json")
