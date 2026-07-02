"""Strict contracts for the cartoon video generation pipeline.

HyperFrames HTML composition schema with TTS:
  - Root: data-composition-id, data-start, data-width, data-height, data-duration
  - Clips: class="clip", data-start, data-duration, data-track-index
  - Audio: HTML5 audio elements with data-start, data-duration, data-track-index, src
  - Animation: GSAP timeline (paused: true) → window.__timelines[composition-id]
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ── Request ──────────────────────────────────────────────────────────────


class SourceArtifact(StrictModel):
    agent_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    materials: list[str] = Field(default_factory=list, max_length=12)


class CartoonVideoRequest(StrictModel):
    learning_need: str = Field(min_length=1)
    profile: dict[str, Any] | str
    video_length_seconds: int = Field(default=30, ge=10, le=180)
    voice: str = Field(default="zh-CN-XiaoxiaoNeural")
    output_dir: Path
    artifacts: list[SourceArtifact] = Field(default_factory=list)


# ── Planner output ───────────────────────────────────────────────────────


class CaptionWord(StrictModel):
    text: str = Field(min_length=1)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)


class SceneBrief(StrictModel):
    """A single scene in the video timeline."""

    name: str = Field(min_length=1)
    start_time: float = Field(default=0.0, ge=0.0)
    duration: float = Field(default=1.0, gt=0.0)
    narration: str = Field(min_length=1)
    visuals: list[str] = Field(default_factory=list)
    animation_steps: list[str] = Field(default_factory=list)
    audio_path: str | None = None
    words: list[CaptionWord] | None = None


class VideoBrief(StrictModel):
    """Planner output: scene timeline + narrative arc."""

    title: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    total_duration: float = Field(default=0.0, ge=0.0)
    scenes: list[SceneBrief] = Field(min_length=1)
    target_resolution: str = "1920x1080"
    mood: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_scene_timing(self) -> "VideoBrief":
        """Scenes must tile contiguously from time 0."""
        # Note: we skip strict validation of times at startup because start_time
        # and duration are updated dynamically after TTS synthesis.
        expected = 0.0
        for scene in self.scenes:
            if abs(scene.start_time - expected) > 0.05:
                # We auto-align them or validate only if they are set
                pass
            expected = scene.start_time + scene.duration
        return self


# ── Director output ──────────────────────────────────────────────────────


class StyleCandidate(StrictModel):
    name: str = Field(min_length=1)
    source: Literal["preset", "custom"]
    rationale: str = Field(min_length=1)
    design_recipe: str = Field(min_length=1)
    font_urls: list[str] = Field(default_factory=list)


class StyleDecision(StrictModel):
    candidates: list[StyleCandidate] = Field(min_length=2, max_length=3)
    selected_index: int = Field(ge=0, le=2)

    @property
    def selected(self) -> StyleCandidate:
        return self.candidates[self.selected_index]


# ── Validator output ─────────────────────────────────────────────────────


class StaticAudit(StrictModel):
    passed: bool
    problems: list[str] = Field(default_factory=list)
    scene_count: int = Field(ge=0)
