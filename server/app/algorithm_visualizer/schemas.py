"""算法可视化模块的双执行链路请求/响应契约。"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


# 支持的语言信息响应模型
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
    supportedLanguages: List[str] = Field(..., alias="supported_languages")

    class Config:
        populate_by_name = True


class TemplateResponse(BaseModel):
    """代码模板响应。"""

    domain: str
    algorithm: str
    visualizerType: str = Field(..., alias="visualizer_type")
    language: str
    templateCode: str = Field(..., alias="template_code")
    requiredEvents: List[str] = Field(default_factory=list, alias="required_events")
    supportedLanguages: List[str] = Field(default_factory=list, alias="supported_languages")
    defaultInput: Dict[str, Any] = Field(default_factory=dict, alias="default_data")
    inputSchema: Dict[str, Any] = Field(default_factory=dict, alias="input_schema")

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class RunRequest(BaseModel):
    """Run either an official template or LLM-instrumented custom Python code."""

    mode: Literal["official", "custom"] = "official"
    algorithm: str | None = None
    language: str
    inputData: Dict[str, Any] = Field(default_factory=dict, alias="input_data")
    code: str | None = None
    visualizerType: Optional[Literal["array", "stack-queue", "linked-list", "tree", "graph", "dp-table"]] = None
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


class CustomContractRequest(BaseModel):
    """Request a deterministic, form-friendly input contract for custom code."""

    code: str
    entryFunction: str | None = None

    model_config = ConfigDict(extra="forbid")


class CustomFunctionResponse(BaseModel):
    name: str
    parameters: List[str]


class CustomContractResponse(BaseModel):
    entryFunction: str
    functions: List[CustomFunctionResponse]
    inputSchema: Dict[str, Any]
    defaultInput: Dict[str, Any]


class TraceEventResponse(BaseModel):
    """TraceEvent 事件响应。"""

    id: str
    step: int
    domain: str
    visualizerType: Optional[str] = None
    type: str
    line: Optional[int] = None
    state: Dict[str, Any]
    targets: Optional[List[Any]] = None
    message: Optional[str] = None
    formula: Optional[str] = None


class RunSuccessResponse(BaseModel):
    """运行成功响应。"""

    domain: str
    algorithm: str
    visualizerType: str
    language: str
    executionMode: Literal["official", "custom"]
    events: List[TraceEventResponse]
    result: Any
    summary: str
    stdout: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class RunErrorResponse(BaseModel):
    """运行失败响应。"""

    errorType: str = Field(..., alias="error_type")
    message: str
    details: Optional[str] = None

    class Config:
        populate_by_name = True
