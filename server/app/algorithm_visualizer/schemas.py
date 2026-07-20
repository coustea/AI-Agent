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
class TemplateSummaryResponse(BaseModel):
    """One registered algorithm template in the catalogue."""
    key: str
    name: str
    domain: str
    visualizerType: str = Field(..., alias="visualizer_type")
    difficulty: str

    model_config = ConfigDict(populate_by_name=True)


class TemplateDetailResponse(TemplateSummaryResponse):
    """The exact source and input contract of one registered template."""
    domain: str
    version: str
    templateCode: str = Field(..., alias="template_code")
    defaultInput: dict[str, JsonValue] = Field(default_factory=dict, alias="default_data")
    inputSchema: dict[str, JsonValue] = Field(default_factory=dict, alias="input_schema")

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class RunRequest(BaseModel):
    """Input for one registered template run."""
    inputData: dict[str, JsonValue] = Field(default_factory=dict, alias="input_data")

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class RunSuccessResponse(BaseModel):
    """A renderable execution trace produced by one template run."""
    templateKey: str
    templateVersion: str
    visualizerType: str
    events: list[dict[str, JsonValue]]
    result: JsonValue
    summary: str

    model_config = ConfigDict(extra="forbid")
