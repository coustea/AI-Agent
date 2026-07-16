"""Strict HTTP DTOs and semantic trace models for algorithm visualization."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator


OfficialVisualizerType = Literal[
    "array",
    "stack-queue",
    "linked-list",
    "tree",
    "graph",
    "dp-table",
]
Difficulty = Literal["easy", "medium", "hard"]
Sha256Version = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
NonNegativeInt = Annotated[int, Field(ge=0)]
PositiveLine = Annotated[int, Field(ge=1)]


class _StrictDto(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        serialize_by_alias=True,
    )


class TemplateSummaryResponse(_StrictDto):
    key: str
    domain: str
    name: str
    visualizerType: OfficialVisualizerType
    difficulty: Difficulty
    version: str


class TemplateDetailResponse(TemplateSummaryResponse):
    templateCode: str
    defaultInput: dict[str, JsonValue]
    inputSchema: dict[str, JsonValue]


class OfficialRunRequest(_StrictDto):
    inputData: dict[str, JsonValue]


class AnalyzeCustomCodeRequest(_StrictDto):
    code: str
    entryFunction: str | None = None


class CustomParameterResponse(_StrictDto):
    name: str
    kind: Literal["positional_or_keyword"]
    required: bool
    schema_: dict[str, JsonValue] = Field(alias="schema")
    defaultValue: JsonValue = None


class CustomFunctionResponse(_StrictDto):
    name: str
    line: PositiveLine
    parameters: list[CustomParameterResponse]


class ObservableVariableResponse(_StrictDto):
    name: str
    scope: Literal["parameter", "local"]
    line: PositiveLine


class CustomCodeContractResponse(_StrictDto):
    sourceHash: Sha256Version
    entryFunction: str
    functions: list[CustomFunctionResponse]
    observableVariables: list[ObservableVariableResponse]
    inputSchema: dict[str, JsonValue]
    defaultInput: dict[str, JsonValue]


class MachineErrorResponse(_StrictDto):
    errorType: Literal[
        "TEMPLATE_NOT_FOUND",
        "INVALID_TEMPLATE_INPUT",
        "INVALID_CUSTOM_CODE",
        "ENTRY_FUNCTION_NOT_FOUND",
        "OFFICIAL_BUSY",
        "OFFICIAL_EXECUTION_FAILED",
        "INVALID_OFFICIAL_TRACE",
    ]


class ArrayStructureResponse(_StrictDto):
    array: list[JsonValue]


class ArrayStateResponse(_StrictDto):
    structure: ArrayStructureResponse


class StackQueueItemResponse(_StrictDto):
    id: str
    label: str
    tone: str | None = None


class StackQueuePointerResponse(_StrictDto):
    label: str
    itemIndex: NonNegativeInt
    tone: str | None = None


class StackQueueStructureResponse(_StrictDto):
    mode: Literal["stack", "queue"]
    items: list[StackQueueItemResponse]
    pointers: list[StackQueuePointerResponse]
    currentValue: JsonValue = None


class StackQueueStateResponse(_StrictDto):
    structure: StackQueueStructureResponse


class LinkedListNodeResponse(_StrictDto):
    id: str
    label: str
    next: str | None
    tone: str | None = None


class LinkedListPointerResponse(_StrictDto):
    label: str
    nodeId: str | None
    tone: str | None = None


class LinkedListStructureResponse(_StrictDto):
    nodes: list[LinkedListNodeResponse]
    pointers: list[LinkedListPointerResponse]


class LinkedListStateResponse(_StrictDto):
    structure: LinkedListStructureResponse


class TreeNodeResponse(_StrictDto):
    id: str
    label: str
    left: str | None = None
    right: str | None = None
    children: list[str] | None = None
    tone: str | None = None


class TreeStructureResponse(_StrictDto):
    nodes: list[TreeNodeResponse]


class TreeStateResponse(_StrictDto):
    structure: TreeStructureResponse


class GraphEdgeResponse(_StrictDto):
    to: str
    weight: float | None = None


class GraphNodeResponse(_StrictDto):
    id: str
    label: str
    distance: float | None = None
    tone: str | None = None
    edges: list[GraphEdgeResponse]


class GraphStructureResponse(_StrictDto):
    nodes: list[GraphNodeResponse]
    directed: bool


class GraphStateResponse(_StrictDto):
    structure: GraphStructureResponse


class DpTableCellResponse(_StrictDto):
    row: NonNegativeInt
    col: NonNegativeInt


class DpTableHighlightResponse(DpTableCellResponse):
    tone: str


class DpTableStructureResponse(_StrictDto):
    headers: list[str]
    rowHeaders: list[str]
    values: list[list[JsonValue]]
    highlighted: list[DpTableHighlightResponse]


class DpTableStateResponse(_StrictDto):
    structure: DpTableStructureResponse


class _TraceEventBase(_StrictDto):
    id: str
    step: NonNegativeInt
    type: str
    line: PositiveLine | None = None
    message: str | None = None


class ArrayTraceEventResponse(_TraceEventBase):
    visualizerType: Literal["array"]
    state: ArrayStateResponse
    targets: list[NonNegativeInt]


class StackQueueTraceEventResponse(_TraceEventBase):
    visualizerType: Literal["stack-queue"]
    state: StackQueueStateResponse
    targets: list[NonNegativeInt]


class LinkedListTraceEventResponse(_TraceEventBase):
    visualizerType: Literal["linked-list"]
    state: LinkedListStateResponse
    targets: list[str]


class TreeTraceEventResponse(_TraceEventBase):
    visualizerType: Literal["tree"]
    state: TreeStateResponse
    targets: list[str]


class GraphTraceEventResponse(_TraceEventBase):
    visualizerType: Literal["graph"]
    state: GraphStateResponse
    targets: list[str]


class DpTableTraceEventResponse(_TraceEventBase):
    visualizerType: Literal["dp-table"]
    state: DpTableStateResponse
    targets: list[DpTableCellResponse]


TraceEventResponse = Annotated[
    ArrayTraceEventResponse
    | StackQueueTraceEventResponse
    | LinkedListTraceEventResponse
    | TreeTraceEventResponse
    | GraphTraceEventResponse
    | DpTableTraceEventResponse,
    Field(discriminator="visualizerType"),
]


class OfficialRunResponse(_StrictDto):
    templateKey: str
    templateVersion: str
    visualizerType: OfficialVisualizerType
    events: list[TraceEventResponse]
    result: JsonValue
    summary: str


# ---------------------------------------------------------------------------
# Legacy DTOs kept for backward compatibility with api.py during migration
# ---------------------------------------------------------------------------

class LanguageResponse(BaseModel):
    """语言信息响应。"""
    key: str
    label: str
    extension: str


class AlgorithmResponse(BaseModel):
    """算法信息响应。"""
    key: str
    name: str
    domain: str
    visualizerType: str = Field(..., alias="visualizer_type")
    difficulty: str
    supportedLanguages: list[str] = Field(..., alias="supported_languages")

    class Config:
        populate_by_name = True


class TemplateResponse(BaseModel):
    """代码模板响应。"""
    domain: str
    algorithm: str
    visualizerType: str = Field(..., alias="visualizer_type")
    language: str
    templateCode: str = Field(..., alias="template_code")
    requiredEvents: list[str] = Field(default_factory=list, alias="required_events")
    supportedLanguages: list[str] = Field(default_factory=list, alias="supported_languages")
    defaultInput: dict[str, JsonValue] = Field(default_factory=dict, alias="default_data")
    inputSchema: dict[str, JsonValue] = Field(default_factory=dict, alias="input_schema")

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class RunRequest(BaseModel):
    """Run either an official template or LLM-instrumented custom Python code."""
    mode: Literal["official", "custom"] = "official"
    algorithm: str | None = None
    language: str
    inputData: dict[str, JsonValue] = Field(default_factory=dict, alias="input_data")
    code: str | None = None
    visualizerType: OfficialVisualizerType | None = None
    entryFunction: str | None = None

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @model_validator(mode="after")
    def validate_mode_payload(self) -> "RunRequest":
        if self.mode == "official":
            if not self.algorithm:
                raise ValueError("官方模板模式必须指定 algorithm")
            if self.code is not None or self.visualizerType is not None or self.entryFunction is not None:
                raise ValueError("官方模板模式不接受 code、visualizerType 或 entryFunction")
        elif not self.code or not self.visualizerType:
            raise ValueError("自定义代码模式必须提供 code 和 visualizerType")
        return self


class RunSuccessResponse(BaseModel):
    """运行成功响应。"""
    domain: str
    algorithm: str
    visualizerType: str
    language: str
    executionMode: Literal["official", "custom"]
    events: list[dict[str, JsonValue]]
    result: JsonValue
    summary: str
    stdout: str | None = None

    model_config = ConfigDict(extra="forbid")


class RunErrorResponse(BaseModel):
    """运行失败响应。"""
    errorType: str = Field(..., alias="error_type")
    message: str
    details: str | None = None

    class Config:
        populate_by_name = True
