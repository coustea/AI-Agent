"""Chat 模块核心数据模式 — 重新导出所有公共类型。

保持 from app.chat.schemas import X 的兼容性。
"""

from app.chat.schemas.evidence import (
    EvidenceType,
    Evidence,
    EvidenceSet,
    SourceItem,
    AgentError,
    ToolInvocation,
    AttachmentAnalysis,
    NormalizedToolResult,
    normalize_tool_result,
    UploadResponse,
    ChatMessageItem,
)

from app.chat.schemas.agent import (
    TutorToolCall,
    TutorRequestContext,
    TutorAgentInput,
    TutorRuntimeEventType,
    TutorRuntimeEvent,
)

from app.chat.schemas.diagram import (
    TeachingDiagramType,
    TeachingContent,
    ComparisonEntity,
    ComparisonDimension,
    VisualSummary,
    ComparisonPayload,
    FlowchartNodeType,
    FlowchartNode,
    FlowchartEdge,
    FlowchartPayload,
    SequenceMessage,
    SequencePayload,
    FrameworkModule,
    FrameworkPayload,
    SummaryCard,
    SummaryPayload,
    HierarchyBranch,
    HierarchyPayload,
    TreeDiagramNode,
    TreePayload,
    GridCell,
    GridPayload,
    ProtocolField,
    ProtocolPayload,
    TimelineBlock,
    TimelineTrack,
    TimelinePayload,
    TeachingDiagram,
    TeachingDiagramGenerator,
)

__all__ = [
    "EvidenceType", "Evidence", "EvidenceSet", "UploadResponse",
    "SourceItem", "AgentError", "ToolInvocation", "AttachmentAnalysis",
    "NormalizedToolResult", "normalize_tool_result", "ChatMessageItem",
    "TutorToolCall", "TutorRequestContext", "TutorAgentInput",
    "TutorRuntimeEventType", "TutorRuntimeEvent",
    "TeachingDiagramType", "TeachingContent", "TeachingDiagramGenerator",
    "ComparisonEntity", "ComparisonDimension", "VisualSummary", "ComparisonPayload",
    "FlowchartNodeType", "FlowchartNode", "FlowchartEdge", "FlowchartPayload",
    "SequenceMessage", "SequencePayload",
    "FrameworkModule", "FrameworkPayload",
    "SummaryCard", "SummaryPayload",
    "HierarchyBranch", "HierarchyPayload",
    "TreeDiagramNode", "TreePayload",
    "GridCell", "GridPayload",
    "ProtocolField", "ProtocolPayload",
    "TimelineBlock", "TimelineTrack",
    "TimelinePayload",
    "TeachingDiagram",
]
