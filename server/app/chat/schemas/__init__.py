"""Chat 模块核心数据模式 — 重新导出所有公共类型。

保持 from app.chat.schemas import X 的兼容性。
"""

from app.chat.schemas.evidence import (
    EvidenceType,
    Evidence,
    EvidenceSet,
    UploadResponse,
)

from app.chat.schemas.agent import (
    TutorToolCall,
    TutorTurnContext,
    TutorAgentInput,
    ClassificationResult,
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
)

__all__ = [
    "EvidenceType", "Evidence", "EvidenceSet", "UploadResponse",
    "TutorToolCall", "TutorTurnContext", "TutorAgentInput",
    "ClassificationResult", "TutorRuntimeEventType", "TutorRuntimeEvent",
    "TeachingDiagramType", "TeachingContent",
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
