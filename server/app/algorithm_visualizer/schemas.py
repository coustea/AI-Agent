"""HTTP DTOs for official algorithm visualization endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue


OfficialVisualizerType = Literal[
    "array",
    "stack-queue",
    "linked-list",
    "tree",
    "graph",
    "dp-table",
]
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
    """Run a registered official template."""
    algorithm: str
    language: str
    inputData: dict[str, JsonValue] = Field(default_factory=dict, alias="input_data")

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class RunSuccessResponse(BaseModel):
    """运行成功响应。"""
    domain: str
    algorithm: str
    visualizerType: str
    language: str
    executionMode: Literal["official"]
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
