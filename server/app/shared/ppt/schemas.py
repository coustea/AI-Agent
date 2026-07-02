from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


DensityMode = Literal["speaker_led", "reading_first"]
StyleSource = Literal["preset", "bold_template", "custom"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DeckBrief(StrictModel):
    purpose: str = Field(min_length=1)
    audience: str = Field(min_length=1)
    density: DensityMode
    target_slide_count: int = Field(ge=3, le=40)
    narrative: str = Field(min_length=1)
    required_points: list[str] = Field(default_factory=list)
    language: str = "zh-CN"
    mood: str = Field(min_length=1)


class SourceArtifact(StrictModel):
    agent_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    materials: list[str] = Field(default_factory=list, max_length=12)


class ResourcePPTRequest(StrictModel):
    learning_need: str = Field(min_length=1)
    learning_scenario: str = Field(min_length=1)
    profile: dict[str, Any] | str
    teaching_plan: dict[str, Any] | None
    artifacts: list[SourceArtifact] = Field(default_factory=list)


class PathPPTRequest(StrictModel):
    learning_need: str = Field(min_length=1)
    profile: dict[str, Any] | str
    artifacts: list[SourceArtifact] = Field(default_factory=list)
    path_title: str = Field(min_length=1)
    path_goal: str = Field(min_length=1)
    node_title: str = Field(min_length=1)
    node_key: str = Field(min_length=1)
    difficulty: str = Field(min_length=1)
    knowledge_points: list[str] = Field(default_factory=list)
    weak_knowledge_points: list[str] = Field(default_factory=list)
    generation_focus: list[str] = Field(default_factory=list)
    tutorial_title: str = Field(min_length=1)
    tutorial_summary: str = Field(min_length=1)
    tutorial_markdown: str = Field(min_length=1)


class StyleCandidate(StrictModel):
    name: str = Field(min_length=1)
    source: StyleSource
    rationale: str = Field(min_length=1)
    design_recipe: str = Field(min_length=1)
    font_urls: list[str] = Field(default_factory=list)


class StyleDecision(StrictModel):
    candidates: list[StyleCandidate] = Field(min_length=3, max_length=3)
    selected_index: int = Field(ge=0, le=2)
    density: DensityMode

    @model_validator(mode="after")
    def validate_candidate_mix(self) -> "StyleDecision":
        sources = [candidate.source for candidate in self.candidates]
        if sources != ["preset", "bold_template", "custom"]:
            raise ValueError(
                "style candidates must be ordered as preset, bold_template, custom"
            )
        return self

    @property
    def selected(self) -> StyleCandidate:
        return self.candidates[self.selected_index]


class StaticAudit(StrictModel):
    passed: bool
    problems: list[str] = Field(default_factory=list)
    slide_count: int = Field(ge=0)


class VisualQAProblem(StrictModel):
    slide_index: int = Field(ge=0)
    viewport: Literal["desktop", "mobile"]
    problem_type: Literal[
        "overflow",
        "overlap",
        "empty",
        "script_error",
        "stage_geometry",
        "font_size",
        "navigation",
        "other",
    ]
    element_summary: str = Field(min_length=1)
    severity: Literal["warning", "critical"]


class VisualAudit(StrictModel):
    passed: bool
    problems: list[VisualQAProblem] = Field(default_factory=list)
