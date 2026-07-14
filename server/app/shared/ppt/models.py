from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.shared.ppt.contract import LayoutKind, SlideKind, VisualKind


class PPTModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PPTSource(PPTModel):
    agent_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    materials: list[str] = Field(default_factory=list, max_length=12)


class PPTPreferences(PPTModel):
    """内容偏好，不再选择视觉模板。"""

    narrative_style: Literal["concept", "case_driven", "problem_led", "review"] = "concept"
    density: Literal["concise", "standard", "detailed"] = "standard"
    emphasis: list[Literal["core_concepts", "cases", "pitfalls", "derivation"]] = Field(
        default_factory=lambda: ["core_concepts"], min_length=1, max_length=4
    )


class ResourcePPT(PPTModel):
    """独立资源入口的 PPT 请求。"""

    username: str = ""
    learning_need: str = Field(min_length=1)
    learning_scenario: str = "self_study"
    profile: dict[str, Any] | str = Field(default_factory=dict)
    # The resource workflow owns a structured control plan.  The shared PPT
    # engine receives its JSON-safe snapshot and is the sole place that turns
    # it into prompt material.
    resource_plan: dict[str, Any] = Field(min_length=1)
    artifacts: list[PPTSource] = Field(default_factory=list, max_length=16)
    preferences: PPTPreferences = Field(default_factory=PPTPreferences)


class PathPPT(PPTModel):
    """学习路径入口的 PPT 请求。"""

    username: str = ""
    profile: dict[str, Any] | str = Field(default_factory=dict)
    preferences: PPTPreferences = Field(default_factory=PPTPreferences)
    path_title: str = Field(min_length=1)
    path_goal: str = Field(min_length=1)
    node_title: str = Field(min_length=1)
    node_key: str = Field(min_length=1)
    difficulty: str = "beginner"
    knowledge_points: list[str] = Field(default_factory=list, max_length=24)
    weak_knowledge_points: list[str] = Field(default_factory=list, max_length=24)
    tutorial_title: str = Field(min_length=1)
    tutorial_summary: str = ""
    tutorial_knowledge_points: list[str] = Field(default_factory=list, max_length=24)
    tutorial_core_content: str = Field(min_length=1)


class PPTGenerationContext(PPTModel):
    """两个业务入口归一化后交给共享 PPT 引擎的唯一内部契约。"""

    source: Literal["resource", "path"]
    topic: str = Field(min_length=1, max_length=160)
    learner_profile: str = Field(default="", max_length=1_600)
    learning_goal: str = Field(min_length=1, max_length=1_200)
    prerequisites: list[str] = Field(default_factory=list, max_length=12)
    source_materials: list[str] = Field(default_factory=list, min_length=1, max_length=10)
    constraints: list[str] = Field(default_factory=list, max_length=8)
    preferences: PPTPreferences = Field(default_factory=PPTPreferences)


class SlideBrief(PPTModel):
    id: str = Field(pattern=r"^s[0-9]{2}$")
    kind: SlideKind
    title: str = Field(min_length=1, max_length=54)
    teaching_goal: str = Field(min_length=12, max_length=150)
    content_focus: str = Field(min_length=12, max_length=180)
    visual_kind: VisualKind
    layout: LayoutKind


class PPTStoryboard(PPTModel):
    title: str = Field(min_length=1, max_length=72)
    language: str = "zh-CN"
    visual_direction: str = Field(min_length=24, max_length=300)
    slides: list[SlideBrief] = Field(min_length=10, max_length=18)

    @model_validator(mode="after")
    def validate_story_arc(self) -> "PPTStoryboard":
        if self.slides[0].kind is not SlideKind.COVER or self.slides[-1].kind is not SlideKind.SUMMARY:
            raise ValueError("storyboard must start with cover and end with summary")
        if len({slide.id for slide in self.slides}) != len(self.slides):
            raise ValueError("storyboard slide ids must be unique")
        return self


class SlidePoint(PPTModel):
    label: str = Field(min_length=1, max_length=24)
    detail: str = Field(min_length=8, max_length=72)


class VisualMetric(PPTModel):
    label: str = Field(min_length=1, max_length=24)
    value: str = Field(min_length=1, max_length=32)
    detail: str = Field(default="", max_length=56)


class DiagramNode(PPTModel):
    id: str = Field(pattern=r"^n[0-9]{1,2}$")
    label: str = Field(min_length=1, max_length=24)
    detail: str = Field(default="", max_length=48)
    tone: Literal["primary", "secondary", "accent", "muted", "warning"] = "primary"


class DiagramEdge(PPTModel):
    source_id: str = Field(pattern=r"^n[0-9]{1,2}$")
    target_id: str = Field(pattern=r"^n[0-9]{1,2}$")
    label: str = Field(default="", max_length=24)


class DiagramModel(PPTModel):
    layout: Literal["hierarchy", "flow", "network", "comparison"] = "flow"
    nodes: list[DiagramNode] = Field(min_length=2, max_length=8)
    edges: list[DiagramEdge] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def validate_graph(self) -> "DiagramModel":
        node_ids = {node.id for node in self.nodes}
        if len(node_ids) != len(self.nodes):
            raise ValueError("diagram node ids must be unique")
        for edge in self.edges:
            if edge.source_id not in node_ids or edge.target_id not in node_ids:
                raise ValueError("diagram edge references an unknown node")
            if edge.source_id == edge.target_id:
                raise ValueError("diagram edges cannot loop to the same node")
        return self


class VisualSpec(PPTModel):
    kind: VisualKind
    title: str = Field(default="", max_length=48)
    caption: str = Field(default="", max_length=84)
    metrics: list[VisualMetric] = Field(default_factory=list, max_length=5)
    code_language: str = Field(default="", max_length=20)
    code: str = Field(default="", max_length=1_600)
    formula: str = Field(default="", max_length=300)
    formula_steps: list[str] = Field(default_factory=list, max_length=5)
    model: DiagramModel | None = None

    @model_validator(mode="after")
    def validate_visual_payload(self) -> "VisualSpec":
        if self.kind is VisualKind.MODEL and self.model is None:
            raise ValueError("model visual requires a structured diagram model")
        if self.kind is not VisualKind.MODEL and self.model is not None:
            raise ValueError("only model visuals may declare a diagram model")
        return self


class PPTSlide(PPTModel):
    id: str = Field(pattern=r"^s[0-9]{2}$")
    kind: SlideKind
    title: str = Field(min_length=1, max_length=54)
    eyebrow: str = Field(default="", max_length=28)
    subtitle: str = Field(default="", max_length=84)
    lead: str = Field(default="", max_length=96)
    points: list[SlidePoint] = Field(default_factory=list, max_length=4)
    visual: VisualSpec
    layout: LayoutKind
    takeaway: str = Field(default="", max_length=96)
    speaker_notes: str = Field(default="", max_length=600)

    @model_validator(mode="after")
    def validate_teaching_payload(self) -> "PPTSlide":
        if not self.lead and not self.points and not self.visual.code and not self.visual.formula and self.visual.model is None:
            raise ValueError("slide needs a teaching statement, points, code, formula, or diagram model")
        return self


class PPTSection(PPTModel):
    slides: list[PPTSlide] = Field(min_length=1, max_length=6)


class PPTDeck(PPTModel):
    title: str = Field(min_length=1, max_length=72)
    language: str = "zh-CN"
    visual_direction: str = Field(min_length=24, max_length=300)
    slides: list[PPTSlide] = Field(min_length=10, max_length=18)

    @model_validator(mode="after")
    def validate_story_arc(self) -> "PPTDeck":
        if self.slides[0].kind is not SlideKind.COVER or self.slides[-1].kind is not SlideKind.SUMMARY:
            raise ValueError("deck must start with cover and end with summary")
        if len({slide.id for slide in self.slides}) != len(self.slides):
            raise ValueError("deck slide ids must be unique")
        return self


class PPTArtifact(PPTModel):
    title: str = Field(min_length=1)
    path: Path
    generated_at: datetime
    template_id: str = "computer-teaching-studio"
    template_name: str = "计算机课程教学工作室"
    slide_count: int
    html_url: str = ""
