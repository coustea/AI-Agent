"""Chat 模块核心数据模式 — TutorAgent 输入、工具上下文、证据模型、教学图解 Schema。

所有 DTO 集中在此文件，打破原分散文件间的循环依赖。
按职责分为四组：

  1. 证据与上传 — Evidence / EvidenceSet / UploadResponse
  2. 工具上下文 — TutorToolCall / TutorTurnContext
  3. TutorAgent 合约 — TutorAgentInput / ChatStreamEvent / ClassificationResult
  4. 教学图解 Schema — TeachingDiagram 及 6 种 payload（comparison/flowchart/sequence/framework/summary/hierarchy）
"""

from __future__ import annotations  # 延迟求值注解，允许前向引用（如字符串形式的类型标注）

from typing import Any, Literal, Optional, Union  # Any: 动态类型; Literal: 限定枚举值

from pydantic import BaseModel, ConfigDict, Field, model_validator  # Pydantic v2 核心基类和校验器


# ===================================================================
# 证据与上传
# ===================================================================


# 证据类型枚举 — 覆盖所有流水线阶段的产出物
# attachment: 附件分析(图片OCR/文档解析)
# web_search: 联网搜索结果
# knowledge_base: 本地知识库检索结果
# learner_profile: 学习者画像
# long_term_memory: 长期记忆
# recent_evaluation: 近期测验评估
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
    evidence_type: EvidenceType  # 证据来源类型，决定下游如何消费
    summary: str  # 人类可读的摘要文本，直接嵌入推理 prompt
    details: dict[str, Any] = Field(default_factory=dict)  # 结构化详情，供持久化和前端展示（如 sources、urls）
    confidence: float = 0.7  # 证据置信度，0~1，默认中等（用于未来排序或过滤）
    freshness: str = "turn"  # 时效性标记：turn(当前轮)/session(会话级)/persistent(跨会话)
    scope: str = "turn"  # 生命周期：turn 级证据每轮重置
    usable_for_answer: bool = True  # 是否注入推理 prompt（控制该证据能否影响最终回答）
    usable_for_diagram: bool = True  # 是否注入教学图解生成


class EvidenceSet(BaseModel):
    """证据集合 — 编排流水线中各阶段产出的证据汇总容器。

    for_answer() / for_diagram() 分别过滤出对应下游可用的证据。
    这是流转于 orchestrator 各阶段之间的共享状态。
    """
    items: list[Evidence] = Field(default_factory=list)

    # 过滤出可用于推理回答的证据（usable_for_answer=True）
    def for_answer(self) -> list[Evidence]:
        return [item for item in self.items if item.usable_for_answer]

    # 过滤出可用于教学图解的证据（usable_for_diagram=True）
    def for_diagram(self) -> list[Evidence]:
        return [item for item in self.items if item.usable_for_diagram]

    # 批量追加新证据到集合
    def extend(self, items: list[Evidence]) -> None:
        self.items.extend(items)


class UploadResponse(BaseModel):
    """文件上传成功后的响应 DTO — 前端拿到后用于构建 attachments 参数传入对话接口。"""
    url: str = Field(..., description="文件访问 URL")  # 完整的 API 路径，如 /api/v1/ai/chat/uploads/{uid}/{sid}/{file}
    file_type: str = Field(default="document", description="image / document")  # 文件大类，前端据此决定显示图标
    original_name: str = Field(default="", description="原始文件名")  # 用户上传时的原始文件名
    size_bytes: int = Field(default=0, ge=0, description="文件大小")  # 字节数，前端用于显示大小
    storage_key: str | None = Field(default=None, description="存储键")  # 相对路径 key，用于内部寻址
    mime_type: str | None = Field(default=None, description="MIME 类型")  # 如 image/png, application/pdf
    extension: str | None = Field(default=None, description="文件扩展名")  # 如 .pdf, .png


# ===================================================================
# 工具上下文
# ===================================================================


class TutorToolCall(BaseModel):
    """TutorAgent 节点选择出的工具调用。"""
    tool_name: str  # 工具名：get_learner_profile / get_long_term_memory / search_knowledge_base / web_search / get_recent_evaluation
    payload: dict[str, Any] = Field(default_factory=dict)  # 工具参数，如 {"query": "TCP三次握手"} 或 {"category": "stable_weaknesses"}


class TutorTurnContext(BaseModel):
    """单轮辅导上下文 — 绑定工具和图解生成所需的最小请求信息。"""
    user_id: int
    session_id: str
    user_input: str = ""
    attachments: list[str] = Field(default_factory=list)
    enable_web_search: bool = False
    need_teaching_diagram: bool = False


# ===================================================================
# TutorAgent 合约 — TutorAgent ↔ ChatService 的接口
# ===================================================================

class TutorAgentInput(BaseModel):
    """TutorAgent 的输入 — ChatService 构建，传入 TutorAgent.chat()。"""
    user_id: int
    session_id: str
    turn_id: int
    user_message_id: int | None = None
    question: str
    attachments: list[str] = Field(default_factory=list)
    history_messages: list[Any] = Field(default_factory=list)
    session_summary: str = ""
    enable_web_search: bool = False
    need_teaching_diagram: bool = False


class ClassificationResult(BaseModel):
    """classify 节点的输出 — 意图分类和路由决策。"""
    intent: str = "general_qa"
    subject: str = ""
    difficulty: str = "intermediate"
    needs_file_analysis: bool = False
    needs_knowledge_search: bool = False
    needs_web_search: bool = False
    needs_profile: bool = False
    needs_long_term_memory: bool = False
    needs_recent_evaluation: bool = False
    needs_diagram: bool = False
    safety_risk: str = "none"
    answer_style: str = "explain"


ChatStreamEventType = Literal[
    "message_start", "classify_done",
    "file_analysis_start", "file_analysis_done",
    "tool_start", "tool_done",
    "answer_token", "answer_done",
    "diagram_start", "diagram_done",
    "memory_update_start", "memory_update_done",
    "final", "error",
]


class ChatStreamEvent(BaseModel):
    """TutorAgent 流式事件 — 内部事件形状，ChatService 转换为 SSE。"""
    type: ChatStreamEventType
    payload: dict[str, Any] = Field(default_factory=dict)
    sequence: int = 0
    timestamp: float = 0.0


# ===================================================================
# 教学图解 Schema（6 类图型：comparison / flowchart / sequence / framework / summary / hierarchy）
#
# 数据流：TeachingDiagramGenerator → LLM ainvoke_json(TeachingDiagram) → 前端渲染
# 每个 Payload 使用 extra="forbid" 严格约束字段，防止 LLM 输出多余内容。
# TeachingDiagram.validate_payload_type 确保 graph_type 与 visual_content 类型一致。
# ===================================================================

TeachingDiagramType = Literal["comparison", "flowchart", "sequence", "framework", "summary", "hierarchy"]


# ---- 辅助文字（每种图解共用的文本描述部分） ----
class TeachingContent(BaseModel):
    """教学图解的文本内容 — 所有图型共享此结构，提供核心解释、要点、误区、示例。"""
    model_config = ConfigDict(extra="forbid")  # 严格模式：禁止 LLM 输出未定义的多余字段
    core_explanation: str = Field(max_length=400, description="核心解释")  # 对知识点的核心讲解
    key_points: list[str] = Field(default_factory=list, max_length=5, description="要点列表")  # 3~5 个关键要点
    common_mistakes: list[str] = Field(default_factory=list, max_length=3, description="常见误区")  # 学生容易犯的错
    examples: list[str] = Field(default_factory=list, max_length=3, description="示例")  # 辅助理解的例子
    summary: str = Field(max_length=240, description="一句话总结")  # 高度概括的一句话


# ---- 1. 对比图（comparison）—— 用于比较两个概念的异同 ----
class ComparisonEntity(BaseModel):
    """对比实体 — 对比图中的一个参与方（如 TCP vs UDP 中的 TCP）。"""
    model_config = ConfigDict(extra="forbid")
    name: str = Field(max_length=20, description="实体名称")  # 如 "TCP"
    core_label: str = Field(max_length=30, description="核心标签")  # 如 "可靠传输协议"
    short_desc: str = Field(max_length=60, description="简短描述")  # 一句话概括该实体特征


class ComparisonDimension(BaseModel):
    """对比维度 — 两个实体在某一方面的对比项。"""
    model_config = ConfigDict(extra="forbid")
    name: str = Field(max_length=20, description="维度名称")  # 如 "连接方式"
    left: str = Field(max_length=60, description="左侧内容")  # 左实体在该维度的描述
    right: str = Field(max_length=60, description="右侧内容")  # 右实体在该维度的描述
    highlight: Optional[str] = Field(default=None, max_length=60, description="重点标注")  # 可选的差异高亮


class VisualSummary(BaseModel):
    """对比图底部的可视化总结。"""
    model_config = ConfigDict(extra="forbid")
    left_keyword: str = Field(max_length=10, description="左侧关键词")  # 左实体的关键词标签
    right_keyword: str = Field(max_length=10, description="右侧关键词")  # 右实体的关键词标签
    center_conclusion: str = Field(max_length=60, description="居中结论")  # 底部总结性结论


class ComparisonPayload(BaseModel):
    """对比图的完整数据 — 包含两个实体、多个对比维度和总结。"""
    model_config = ConfigDict(extra="forbid")
    left_entity: ComparisonEntity  # 左侧对比实体
    right_entity: ComparisonEntity  # 右侧对比实体
    dimensions: list[ComparisonDimension] = Field(min_length=2, max_length=8, description="对比维度列表")  # 至少 2 个维度
    visual_summary: VisualSummary  # 底部总结


# ---- 2. 流程图（flowchart）—— 用于展示步骤、决策、流程 ----
FlowchartNodeType = Literal["start", "process", "decision", "end", "danger"]  # 节点类型枚举


class FlowchartNode(BaseModel):
    """流程图节点 — 每个节点有唯一 ID、标题和类型。"""
    model_config = ConfigDict(extra="forbid")
    id: str = Field(description="节点ID")  # 唯一标识，用于 edge 引用
    title: str = Field(max_length=35, description="节点标题")  # 节点显示文字
    short_desc: str = Field(default="", max_length=60, description="简短描述")  # 可选的详细描述
    type: FlowchartNodeType = Field(default="process", description="节点类型")  # 决定节点颜色和形状


class FlowchartEdge(BaseModel):
    """流程图有向边 — 连接两个节点，可带标签。"""
    model_config = ConfigDict(populate_by_name=True, extra="forbid")  # populate_by_name: 允许用 from_ 或 from 访问
    from_: str = Field(alias="from", description="起始节点ID")  # Python 中 from 是关键字，用 from_ + alias
    to: str = Field(description="目标节点ID")  # 目标节点
    label: Optional[str] = Field(default=None, max_length=20, description="边标签")  # 可选的条件/动作标签


class FlowchartPayload(BaseModel):
    """流程图完整数据 — 节点列表 + 有向边列表 + 流向方向。"""
    model_config = ConfigDict(populate_by_name=True, extra="forbid")
    direction: Literal["vertical", "horizontal"] = Field(default="vertical", description="流向方向")  # 竖向或横向
    nodes: list[FlowchartNode] = Field(min_length=2, max_length=20)  # 至少 start + end 两个节点
    edges: list[FlowchartEdge] = Field(min_length=1)  # 至少一条边


# ---- 3. 时序图（sequence）—— 用于展示参与者间的交互时序 ----
class SequenceMessage(BaseModel):
    """时序图消息 — 两个参与者之间的一次交互。"""
    model_config = ConfigDict(populate_by_name=True, extra="forbid")
    from_: str = Field(alias="from", description="发送方")  # 发起方名称
    to: str = Field(description="接收方")  # 接收方名称
    label: str = Field(max_length=30, description="消息标签")  # 消息内容简述
    detail: Optional[str] = Field(default=None, max_length=60, description="详细说明")  # 可选补充


class SequencePayload(BaseModel):
    """时序图完整数据 — 参与者列表 + 交互消息列表。"""
    model_config = ConfigDict(extra="forbid")
    actors: list[str] = Field(min_length=2, max_length=6, description="参与者列表")  # 如 ["客户端", "服务端", "数据库"]
    messages: list[SequenceMessage] = Field(min_length=1, max_length=20, description="交互消息列表")  # 按时间排列的消息


# ---- 4. 知识框架图（framework）—— 用于展示知识体系结构 ----
class FrameworkModule(BaseModel):
    """知识框架模块 — 中心主题下的一个子模块。"""
    model_config = ConfigDict(extra="forbid")
    title: str = Field(max_length=20, description="模块标题")  # 如 "传输层"
    items: list[str] = Field(min_length=1, max_length=8, description="知识点列表")  # 模块下的知识点


class FrameworkPayload(BaseModel):
    """知识框架图完整数据 — 中心主题 + 多个模块。"""
    model_config = ConfigDict(extra="forbid")
    center: str = Field(max_length=20, description="中心主题")  # 如 "计算机网络"
    modules: list[FrameworkModule] = Field(min_length=2, max_length=8, description="模块列表")  # 至少 2 个模块


# ---- 5. 总结卡片图（summary）—— 用于关键信息卡片式展示 ----
class SummaryCard(BaseModel):
    """总结卡片 — 一条精炼的知识点。"""
    model_config = ConfigDict(extra="forbid")
    title: str = Field(max_length=20, description="卡片标题")  # 卡片主标题
    short_desc: str = Field(max_length=60, description="卡片描述")  # 卡片描述文字


class SummaryPayload(BaseModel):
    """总结卡片图完整数据 — 多张卡片的列表。"""
    model_config = ConfigDict(extra="forbid")
    cards: list[SummaryCard] = Field(min_length=2, max_length=8, description="卡片列表")  # 至少 2 张卡片


# ---- 6. 层级概括图（hierarchy）—— 用于展示树状层级关系 ----
class HierarchyBranch(BaseModel):
    """层级图分支 — 根节点下的一个子分支。"""
    model_config = ConfigDict(extra="forbid")
    title: str = Field(max_length=20, description="分支标题")  # 如 "应用层"
    children: list[str] = Field(min_length=1, max_length=8, description="子项列表")  # 分支下的子项


class HierarchyPayload(BaseModel):
    """层级概括图完整数据 — 根节点 + 多个分支。"""
    model_config = ConfigDict(extra="forbid")
    root: str = Field(max_length=20, description="根节点名称")  # 如 "TCP/IP 协议栈"
    branches: list[HierarchyBranch] = Field(min_length=2, max_length=8, description="分支列表")  # 至少 2 个分支


# ---- 顶层 TeachingDiagram ----
class TeachingDiagram(BaseModel):
    """一次答疑对应的一张结构化教学图解 — LLM 生成后通过 ainvoke_json 输出。

    graph_type 决定 visual_content 的具体类型（Union 中的哪个 Payload），
    validate_payload_type 校验器确保两者一致。
    """
    model_config = ConfigDict(populate_by_name=True, extra="forbid")  # 严格模式，LLM 不可输出多余字段

    graph_type: TeachingDiagramType  # 图解类型：comparison/flowchart/sequence/framework/summary/hierarchy
    title: str = Field(min_length=1, max_length=80, description="主标题")  # 图解主标题
    subtitle: Optional[str] = Field(default=None, max_length=60, description="副标题")  # 可选副标题
    teaching_goal: str = Field(max_length=60, description="教学目标")  # 本图解要达到的教学目标
    course: Optional[str] = Field(default=None, max_length=30, description="课程名称")  # 可选课程名
    difficulty: Literal["beginner", "intermediate", "advanced"] = Field(default="intermediate", description="难度等级")
    # 根据 graph_type 选择对应的 Payload 类型 — Union 让 Pydantic 按 graph_type 校验
    visual_content: Union[
        ComparisonPayload, FlowchartPayload, SequencePayload,
        FrameworkPayload, SummaryPayload, HierarchyPayload,
    ]
    teaching_content: TeachingContent  # 所有图型共用的文本内容

    @model_validator(mode="after")  # Pydantic v2 的 model 级校验器，在所有字段验证后执行
    def validate_payload_type(self) -> "TeachingDiagram":
        """确保 graph_type 与 visual_content 的实际类型匹配。"""
        expected_type = {  # graph_type → 对应的 Payload 类
            "comparison": ComparisonPayload,
            "flowchart": FlowchartPayload,
            "sequence": SequencePayload,
            "framework": FrameworkPayload,
            "summary": SummaryPayload,
            "hierarchy": HierarchyPayload,
        }[self.graph_type]
        if not isinstance(self.visual_content, expected_type):  # 类型不匹配则报错
            raise ValueError("visual_content must match graph_type")
        return self
