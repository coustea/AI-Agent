"""教学图解 Schema — 数据模型与校验。

数据流（重构后）：
  - LLM 在 <answer> 中用 <diagram> 标签直接输出图解 JSON
  - 后端提取 <diagram> 标签内容 → validate_visual() 校验 → 持久化
  - 校验失败时追加修复 HumanMessage → LLM 重试（最多 1 次）

每个 Payload 使用 extra="ignore" 宽松约束字段，避免 LLM 输出多余字段导致验证失败。
服务端通过 validate_visual() 做二次校验，确保 graph_type 与 visual_content 类型匹配。
"""

from __future__ import annotations

from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.infra.logging import get_logger

logger = get_logger(__name__)


TeachingDiagramType = Literal[
    "comparison", "flowchart", "sequence", "framework", "summary", "hierarchy",
    "tree", "grid", "protocol", "timeline"
]


class TeachingContent(BaseModel):
    """教学图解的文本内容 — 所有图型共享此结构。"""
    model_config = ConfigDict(extra="ignore")
    core_explanation: str = Field(default="", description="核心解释")
    key_points: list[str] = Field(default_factory=list, description="要点列表")
    common_mistakes: list[str] = Field(default_factory=list, description="常见误区")
    examples: list[str] = Field(default_factory=list, description="示例")
    summary: str = Field(default="", description="一句话总结")


# ---- 1. 对比图 ----

class ComparisonEntity(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = Field(default="", description="实体名称")
    core_label: str = Field(default="", description="核心标签")
    short_desc: str = Field(default="", description="简短描述")


class ComparisonDimension(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = Field(default="", description="维度名称")
    left: str = Field(default="", description="左侧内容")
    right: str = Field(default="", description="右侧内容")


class VisualSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")
    left_keyword: str = Field(default="", description="左侧关键词")
    right_keyword: str = Field(default="", description="右侧关键词")
    center_conclusion: str = Field(default="", description="居中结论")


class ComparisonPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    left_entity: ComparisonEntity
    right_entity: ComparisonEntity
    dimensions: list[ComparisonDimension] = Field(default_factory=list, description="对比维度列表")
    visual_summary: VisualSummary


# ---- 2. 流程图 ----

FlowchartNodeType = Literal["start", "process", "decision", "end", "danger"]


class FlowchartNode(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default="", description="节点ID")
    title: str = Field(default="", description="节点标题")
    short_desc: str = Field(default="", description="简短描述")
    type: FlowchartNodeType = Field(default="process", description="节点类型")


class FlowchartEdge(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    from_: str = Field(alias="from", default="", description="起始节点ID")
    to: str = Field(default="", description="目标节点ID")
    label: Optional[str] = Field(default=None, description="边标签")


class FlowchartPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    direction: Literal["vertical", "horizontal"] = Field(default="vertical", description="流向方向")
    nodes: list[FlowchartNode] = Field(default_factory=list)
    edges: list[FlowchartEdge] = Field(default_factory=list)


# ---- 3. 时序图 ----

class SequenceMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    from_: str = Field(alias="from", default="", description="发送方")
    to: str = Field(default="", description="接收方")
    label: str = Field(default="", description="消息标签")
    detail: Optional[str] = Field(default=None, description="详细说明")


class SequencePayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    actors: list[str] = Field(default_factory=list, description="参与者列表")
    messages: list[SequenceMessage] = Field(default_factory=list, description="交互消息列表")


# ---- 4. 知识框架图 ----

class FrameworkModule(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: str = Field(default="", description="模块标题")
    items: list[str] = Field(default_factory=list, description="知识点列表")


class FrameworkPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    center: str = Field(default="", description="中心主题")
    modules: list[FrameworkModule] = Field(default_factory=list, description="模块列表")


# ---- 5. 总结卡片图 ----

class SummaryCard(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: str = Field(default="", description="卡片标题")
    short_desc: str = Field(default="", description="卡片描述")


class SummaryPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    cards: list[SummaryCard] = Field(default_factory=list, description="卡片列表")


# ---- 6. 层级概括图 ----

class HierarchyBranch(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: str = Field(default="", description="分支标题")
    children: list[str] = Field(default_factory=list, description="子项列表")


class HierarchyPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    root: str = Field(default="", description="根节点名称")
    branches: list[HierarchyBranch] = Field(default_factory=list, description="分支列表")

# ---- 7. 树形图 ----

class TreeDiagramNode(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default="", description="节点唯一 ID")
    label: str = Field(default="", description="节点标签/展示文本")
    left_id: Optional[str] = Field(default=None, description="左子节点 ID")
    right_id: Optional[str] = Field(default=None, description="右子节点 ID")
    type: Optional[str] = Field(default=None, description="节点类型（可选）")
    detail: Optional[str] = Field(default=None, description="节点详细说明（可选）")


class TreePayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    root_id: str = Field(default="", description="根节点 ID")
    nodes: list[TreeDiagramNode] = Field(default_factory=list, description="树节点列表")


# ---- 8. 网格图 ----

class GridCell(BaseModel):
    model_config = ConfigDict(extra="ignore")
    index: int = Field(default=0, description="单元格索引/位置")
    label: str = Field(default="", description="单元格展示文本")
    status: Optional[str] = Field(default=None, description="单元格状态（可选）")
    pointer: Optional[str] = Field(default=None, description="指向该单元格的指针名称/标签（可选）")
    detail: Optional[str] = Field(default=None, description="单元格详细说明（可选）")


class GridPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    layout: Literal["horizontal", "vertical", "matrix"] = Field(default="horizontal", description="网格布局方向")
    cols: Optional[int] = Field(default=None, description="列数（仅在 matrix 布局下生效且建议提供）")
    cells: list[GridCell] = Field(default_factory=list, description="网格单元格列表")


# ---- 9. 协议字段图 ----

class ProtocolField(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = Field(default="", description="协议字段名称")
    detail: Optional[str] = Field(default=None, description="协议字段详细说明")
    width_ratio: Optional[int] = Field(default=None, description="字段所占宽度比例（可选）")
    highlight: bool = Field(default=False, description="是否高亮突出显示")


class ProtocolPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    orientation: Literal["vertical", "horizontal_split"] = Field(default="vertical", description="协议报文展示方向")
    fields: list[ProtocolField] = Field(default_factory=list, description="协议字段列表")


# ---- 10. 时间线轨道图 ----

class TimelineBlock(BaseModel):
    model_config = ConfigDict(extra="ignore")
    label: str = Field(default="", description="时间块/事件标签")
    start: float = Field(default=0, description="开始时间/起始坐标位置")
    duration: float = Field(default=1, description="持续时间/时间块长度")
    status: Literal["normal", "active", "idle", "stall"] = Field(default="normal", description="时间块状态")


class TimelineTrack(BaseModel):
    model_config = ConfigDict(extra="ignore")
    track_name: str = Field(default="", description="轨道/并发线路名称")
    blocks: list[TimelineBlock] = Field(default_factory=list, description="该轨道下的时间块列表")


class TimelinePayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    axis_label: str = Field(default="", description="时间轴标签，如时间单位(ms, s)或阶段描述")
    tracks: list[TimelineTrack] = Field(default_factory=list, description="时间线轨道列表")


# ---- graph_type → Payload 映射 ----

PAYLOAD_TYPE_MAP: dict[str, type[BaseModel]] = {
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
}


def _auto_fix_visual_content(graph_type: str, visual_content: dict[str, Any]) -> dict[str, Any]:
    """自动修复 LLM 常见的 visual_content 格式错误。

    已知问题：
    - hierarchy 的 root 被输出为嵌套对象（应为 string）
    - grid 的 index 被输出为 string（应为 int）
    - flowchart/sequence 的 from 字段被输出为 from_（Pydantic alias 问题）
    - comparison 的 dimensions 中可能混入多余字段
    """
    vc = dict(visual_content)  # 浅拷贝，不修改原始数据

    if graph_type == "hierarchy":
        # LLM 经常把 hierarchy.root 输出为嵌套对象而非 string
        root = vc.get("root")
        if isinstance(root, dict):
            # 提取最合理的文本标签
            vc["root"] = (
                root.get("label")
                or root.get("title")
                or root.get("name")
                or root.get("content")
                or str(root)
            )
            logger.info("[_auto_fix] hierarchy.root 从 dict 转为 string: %s", vc["root"])

        # LLM 可能把 hierarchy.branches[].children 输出为嵌套对象列表而非 string 列表
        branches = vc.get("branches")
        if isinstance(branches, list):
            fixed_branches = []
            for branch in branches:
                if not isinstance(branch, dict):
                    continue
                children = branch.get("children", [])
                fixed_children = []
                for child in children:
                    if isinstance(child, str):
                        fixed_children.append(child)
                    elif isinstance(child, dict):
                        fixed_children.append(
                            child.get("label")
                            or child.get("title")
                            or child.get("name")
                            or child.get("content")
                            or str(child)
                        )
                    else:
                        fixed_children.append(str(child))
                fixed_branches.append({**branch, "children": fixed_children})
            vc["branches"] = fixed_branches

    elif graph_type == "grid":
        # LLM 可能把 grid.cells[].index 输出为 string
        cells = vc.get("cells")
        if isinstance(cells, list):
            fixed_cells = []
            for cell in cells:
                if not isinstance(cell, dict):
                    continue
                idx = cell.get("index")
                if isinstance(idx, str) and idx.isdigit():
                    cell = {**cell, "index": int(idx)}
                fixed_cells.append(cell)
            vc["cells"] = fixed_cells

    elif graph_type == "flowchart":
        # LLM 可能用 from_ 而非 from（Pydantic alias 问题）
        edges = vc.get("edges")
        if isinstance(edges, list):
            fixed_edges = []
            for edge in edges:
                if not isinstance(edge, dict):
                    continue
                if "from_" in edge and "from" not in edge:
                    edge = {**edge, "from": edge.pop("from_")}
                fixed_edges.append(edge)
            vc["edges"] = fixed_edges

    elif graph_type == "sequence":
        # 同上，from_ → from
        messages = vc.get("messages")
        if isinstance(messages, list):
            fixed_messages = []
            for msg in messages:
                if not isinstance(msg, dict):
                    continue
                if "from_" in msg and "from" not in msg:
                    msg = {**msg, "from": msg.pop("from_")}
                fixed_messages.append(msg)
            vc["messages"] = fixed_messages

    return vc


def validate_visual(graph_type: str, visual_content: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """服务端二次校验：确保 graph_type 与 visual_content 结构匹配。

    返回 (校验后的 visual_content dict, 错误信息)。
    校验成功时错误信息为空字符串；校验失败时返回原始 dict 和错误描述。
    """
    payload_cls = PAYLOAD_TYPE_MAP.get(graph_type)
    if payload_cls is None:
        warning = f"未知 graph_type={graph_type}，跳过校验"
        logger.warning("[validate_visual] %s", warning)
        return visual_content, warning

    # 先尝试自动修复常见格式错误
    fixed_vc = _auto_fix_visual_content(graph_type, visual_content)

    try:
        validated = payload_cls.model_validate(fixed_vc)
        return validated.model_dump(mode="json", by_alias=True), ""
    except Exception as exc:
        error_msg = str(exc)
        logger.warning("[validate_visual] visual_content 校验失败: graph_type=%s error=%s", graph_type, exc)
        return visual_content, error_msg


# ---- 顶层 TeachingDiagram ----

class TeachingDiagram(BaseModel):
    """一次答疑对应的一张结构化教学图解。"""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    graph_type: TeachingDiagramType
    title: str = Field(default="", description="主标题")
    subtitle: Optional[str] = Field(default=None, description="副标题")
    teaching_goal: str = Field(default="", description="教学目标")
    course: Optional[str] = Field(default=None, description="课程名称")
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
        expected_type = PAYLOAD_TYPE_MAP[self.graph_type]
        if not isinstance(self.visual_content, expected_type):
            raise ValueError("visual_content must match graph_type")
        return self


def validate_diagram_json(raw: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    """校验从 <diagram> 标签提取的 JSON，返回 (校验后的 dict, 错误信息)。

    校验步骤：
    1. graph_type 合法性
    2. 必填字段存在
    3. visual_content 结构匹配
    4. teaching_content 结构合法

    返回 (None, error_msg) 表示校验失败，error_msg 可用于修复提示。
    返回 (validated_dict, "") 表示校验成功。
    """
    if not isinstance(raw, dict):
        return None, "图解 JSON 不是有效的对象"

    graph_type = raw.get("graph_type", "")
    if graph_type not in PAYLOAD_TYPE_MAP:
        error = f"非法 graph_type={graph_type}，允许值: {', '.join(PAYLOAD_TYPE_MAP.keys())}"
        logger.warning("[validate_diagram_json] %s", error)
        return None, error

    # 必填字段检查
    if not raw.get("title"):
        return None, "缺少必填字段 title"
    if not raw.get("teaching_goal"):
        return None, "缺少必填字段 teaching_goal"

    visual_content = raw.get("visual_content")
    if not isinstance(visual_content, dict):
        return None, "visual_content 不是有效的对象"

    teaching_content = raw.get("teaching_content")
    if not isinstance(teaching_content, dict):
        return None, "teaching_content 不是有效的对象"

    # 校验 visual_content（含自动修复）
    validated_visual, visual_error = validate_visual(graph_type, visual_content)

    # 校验 teaching_content
    validated_tc: dict[str, Any] | None = None
    try:
        tc = TeachingContent.model_validate(teaching_content)
        validated_tc = tc.model_dump(mode="json", by_alias=True)
    except Exception as exc:
        error = f"teaching_content 校验失败: {exc}"
        logger.warning("[validate_diagram_json] %s", error)
        return None, error

    # 组装校验后的结果
    result = {
        "graph_type": graph_type,
        "title": raw["title"],
        "subtitle": raw.get("subtitle"),
        "teaching_goal": raw["teaching_goal"],
        "course": raw.get("course"),
        "difficulty": raw.get("difficulty", "intermediate"),
        "visual_content": validated_visual,
        "teaching_content": validated_tc,
    }

    # 最终用 TeachingDiagram 做完整校验
    try:
        diagram = TeachingDiagram.model_validate(result)
        return diagram.model_dump(mode="json", by_alias=True), ""
    except Exception as exc:
        error = f"完整校验失败: {exc}"
        logger.warning("[validate_diagram_json] %s", error)
        return None, error
