from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


DensityMode = Literal["speaker_led", "reading_first"]
SlideRole = Literal[
    "cover",
    "section",
    "hook",
    "explain",
    "derive",
    "case",
    "practice",
    "summary",
    "closing",
]
ContentShape = Literal[
    "statement",
    "concept",
    "sequence",
    "comparison",
    "system",
    "code",
    "formula",
    "quiz",
]
AnimationKind = Literal["reveal", "focus", "trace", "compare", "build", "resolve"]
TemplateFamily = Literal["auto", "editorial", "technical"]
ColorScheme = Literal["auto", "light", "dark"]


class PPTModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PPTSource(PPTModel):
    agent_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    materials: list[str] = Field(default_factory=list, max_length=12)


class PPTPreferences(PPTModel):
    """用户可配置的 PPT 内容与视觉偏好。"""
    template: str = Field(
        default="auto",
        min_length=1,
        max_length=64,
        pattern=r"^(auto|[a-z0-9]+(?:-[a-z0-9]+)*)$",
    )
    explanation_style: Literal["concept", "case_driven", "problem_led", "review"] = "concept"
    density: Literal["concise", "standard", "detailed"] = "standard"
    focus: list[Literal["core_concepts", "cases", "pitfalls", "derivation"]] = Field(
        default_factory=lambda: ["core_concepts"],
        min_length=1,
    )


class ResourcePPTRequest(PPTModel):
    learning_need: str = Field(min_length=1)
    learning_scenario: str = Field(min_length=1)
    profile: dict[str, Any] | str
    teaching_plan: dict[str, Any] | None
    artifacts: list[PPTSource] = Field(default_factory=list)
    preferences: PPTPreferences = Field(
        default_factory=PPTPreferences
    )


class PathPPTRequest(PPTModel):
    learning_need: str = Field(min_length=1)
    profile: dict[str, Any] | str
    artifacts: list[PPTSource] = Field(default_factory=list)
    preferences: PPTPreferences = Field(default_factory=PPTPreferences)
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


class PPTTemplatePreference(PPTModel):
    family: TemplateFamily = "auto"
    scheme: ColorScheme = "auto"
    keywords: list[str] = Field(default_factory=list, max_length=6)


class KeyPoint(PPTModel):
    label: str = Field(min_length=1, max_length=28)
    detail: str = Field(min_length=1, max_length=120)


class ProcessStep(PPTModel):
    title: str = Field(min_length=1, max_length=32)
    detail: str = Field(min_length=1, max_length=100)


class ComparisonSide(PPTModel):
    title: str = Field(min_length=1, max_length=32)
    points: list[str] = Field(min_length=1, max_length=4)


class SystemNode(PPTModel):
    id: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_-]{0,23}$")
    label: str = Field(min_length=1, max_length=24)
    detail: str = Field(default="", max_length=70)
    layer: str = Field(default="", max_length=20)


class PPTSlide(PPTModel):
    role: SlideRole
    shape: ContentShape
    title: str = Field(min_length=1, max_length=54)
    subtitle: str = Field(default="", max_length=110)
    eyebrow: str = Field(default="", max_length=28)
    statement: str = Field(default="", max_length=150)
    points: list[KeyPoint] = Field(default_factory=list, max_length=6)
    steps: list[ProcessStep] = Field(default_factory=list, max_length=6)
    comparison: list[ComparisonSide] = Field(default_factory=list, max_length=2)
    nodes: list[SystemNode] = Field(default_factory=list, max_length=8)
    code: str = Field(default="", max_length=1800)
    code_language: str = Field(default="", max_length=20)
    formula: str = Field(default="", max_length=160)
    question: str = Field(default="", max_length=160)
    answer: str = Field(default="", max_length=180)
    takeaway: str = Field(default="", max_length=140)
    speaker_notes: str = Field(default="", max_length=500)
    animation: AnimationKind = "reveal"
    preferred_layout: str = Field(default="", max_length=40)

    @model_validator(mode="after")
    def validate_shape_content(self) -> "PPTSlide":
        requirements = {
            "sequence": bool(self.steps),
            "comparison": len(self.comparison) == 2,
            "system": bool(self.nodes),
            "code": bool(self.code),
            "formula": bool(self.formula),
            "quiz": bool(self.question and self.answer),
        }
        if self.shape in requirements and not requirements[self.shape]:
            raise ValueError(f"{self.shape} slide is missing its structured content")
        return self


class PPTPlan(PPTModel):
    title: str = Field(min_length=1, max_length=64)
    subtitle: str = Field(default="", max_length=120)
    purpose: str = Field(min_length=1, max_length=180)
    audience: str = Field(min_length=1, max_length=120)
    density: DensityMode
    narrative: str = Field(min_length=1, max_length=500)
    language: str = "zh-CN"
    template_preference: PPTTemplatePreference = Field(
        default_factory=PPTTemplatePreference
    )
    slides: list[PPTSlide] = Field(min_length=3, max_length=18)

    @model_validator(mode="after")
    def validate_deck_rhythm(self) -> "PPTPlan":
        if self.slides[0].role != "cover":
            raise ValueError("the first slide must use the cover role")
        if self.slides[-1].role not in {"summary", "closing"}:
            raise ValueError("the final slide must summarize or close the lesson")
        return self


class PPTArtifact(PPTModel):
    path: Path
    plan: PPTPlan
    template_id: str
    template_name: str
    slide_count: int
