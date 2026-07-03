"""Structured contracts for deterministic animated teaching videos."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceArtifact(StrictModel):
    agent_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    materials: list[str] = Field(default_factory=list, max_length=12)


class CartoonVideoRequest(StrictModel):
    learning_need: str = Field(min_length=1)
    profile: dict[str, Any] | str
    video_length_seconds: int = Field(default=30, ge=10, le=180)
    voice: str = "teacher"
    style: Literal["diagram", "minimal", "dark_tech"] = "diagram"
    focus: Literal["concept", "process", "comparison", "practice"] = "concept"
    output_dir: Path
    artifacts: list[SourceArtifact] = Field(default_factory=list)


class CaptionWord(StrictModel):
    text: str = Field(min_length=1)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)


SceneRole = Literal[
    "hook",
    "concept",
    "process",
    "compare",
    "architecture",
    "code_trace",
    "recap",
]
SceneLayout = Literal[
    "hero",
    "flow",
    "compare",
    "stack",
    "tree",
    "code",
    "grid",
    "recap",
]
VisualKind = Literal[
    "node",
    "label",
    "code",
    "array",
    "stack",
    "queue",
    "state",
    "metric",
    "formula",
    "packet",
]
AnimationAction = Literal[
    "reveal",
    "focus",
    "transfer",
    "compare",
    "swap",
    "traverse",
    "branch",
    "state_change",
    "count",
]


class VisualElement(StrictModel):
    """A semantic teaching object rendered by the deterministic compiler."""

    id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,31}$")
    kind: VisualKind
    label: str = Field(min_length=1, max_length=80)
    detail: str = Field(default="", max_length=160)
    items: list[str] = Field(default_factory=list, max_length=8)
    value: str = Field(default="", max_length=40)


class VisualConnection(StrictModel):
    source: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,31}$")
    target: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,31}$")
    label: str = Field(default="", max_length=30)


class AnimationCue(StrictModel):
    """A semantic action anchored to a spoken keyword, never to guessed seconds."""

    action: AnimationAction
    targets: list[str] = Field(min_length=1, max_length=6)
    keyword: str = Field(default="", max_length=24)


class SceneBrief(StrictModel):
    role: SceneRole
    title: str = Field(min_length=1, max_length=48)
    narration: str = Field(min_length=1, max_length=360)
    layout: SceneLayout
    elements: list[VisualElement] = Field(min_length=1, max_length=10)
    connections: list[VisualConnection] = Field(default_factory=list, max_length=12)
    cues: list[AnimationCue] = Field(default_factory=list, max_length=12)
    callout: str = Field(default="", max_length=80)

    # Runtime-only fields populated from Edge TTS.
    start_time: float = Field(default=0.0, ge=0.0)
    duration: float = Field(default=1.0, gt=0.0)
    audio_path: str | None = None
    words: list[CaptionWord] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_references(self) -> "SceneBrief":
        element_ids = {element.id for element in self.elements}
        self.connections = [
            connection
            for connection in self.connections
            if connection.source in element_ids and connection.target in element_ids
        ]
        for cue in self.cues:
            cue.targets = [target for target in cue.targets if target in element_ids]
        self.cues = [cue for cue in self.cues if cue.targets]
        return self


class VideoBrief(StrictModel):
    title: str = Field(min_length=1, max_length=60)
    subject: str = Field(min_length=1, max_length=40)
    summary: str = Field(min_length=1, max_length=140)
    scenes: list[SceneBrief] = Field(min_length=3, max_length=16)
    total_duration: float = Field(default=0.0, ge=0.0)

    @model_validator(mode="after")
    def validate_story_arc(self) -> "VideoBrief":
        if self.scenes[0].role != "hook":
            raise ValueError("第一个场景必须是 hook")
        if self.scenes[-1].role != "recap":
            raise ValueError("最后一个场景必须是 recap")
        return self


class StaticAudit(StrictModel):
    passed: bool
    problems: list[str] = Field(default_factory=list)
    scene_count: int = Field(ge=0)
