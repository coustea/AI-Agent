"""Strict contracts for the shared teaching-video pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

VideoStyleId = Literal[
    "precision_light",
    "systems_dark",
    "editorial_classroom",
]
AspectRatio = Literal["16:9", "9:16", "1:1"]
SceneRole = Literal[
    "hook",
    "concept",
    "example",
    "process",
    "misconception",
    "practice",
    "recap",
]
VisualType = Literal[
    "title_intro",
    "concept_explain",
    "process_flow",
    "state_machine",
    "data_structure",
    "algorithm_trace",
    "memory_layout",
    "cpu_architecture",
    "network_protocol",
    "layered_architecture",
    "code_execution",
    "compare_summary",
    "knowledge_check",
    "array_linked_list",
    "stack_queue",
    "process_state",
    "storage_hierarchy",
]
VisualCueKind = Literal[
    "define",
    "example",
    "trace_step",
    "compare",
    "misconception",
    "checkpoint",
    "recap",
]


class SourceMaterial(BaseModel):
    source_id: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    title: str = ""
    content: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VideoRequest(BaseModel):
    topic: str = Field(min_length=1)
    audience: str = ""
    learning_goal: str = ""
    duration_seconds: int = Field(default=180, ge=60, le=600)
    scene_count: int = Field(default=6, ge=3, le=12)
    aspect_ratio: AspectRatio = "16:9"
    language: str = "zh-CN"
    voice: str = "teacher"
    include_captions: bool = True
    style_hint: VideoStyleId | None = None
    narrative_focus: Literal["concept", "process", "comparison", "practice"] | None = None
    materials: list[SourceMaterial] = Field(min_length=1)
    output_dir: Path
    metadata: dict[str, Any] = Field(default_factory=dict)


class VideoStyleDecision(BaseModel):
    id: VideoStyleId
    rationale: str = Field(min_length=1)


class VideoMaterialDigest(BaseModel):
    topic: str = Field(min_length=1)
    audience: str = ""
    learning_goal: str = ""
    core_concepts: list[str] = Field(default_factory=list)
    facts: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    process_steps: list[str] = Field(default_factory=list)
    misconceptions: list[str] = Field(default_factory=list)
    practice_prompts: list[str] = Field(default_factory=list)
    visual_opportunities: list[str] = Field(default_factory=list)
    source_map: dict[str, list[str]] = Field(default_factory=dict)


class SceneContract(BaseModel):
    scene_id: str = Field(min_length=1)
    index: int = Field(ge=1)
    role: SceneRole
    title: str = Field(min_length=1)
    learning_objective: str = Field(min_length=1)
    visual_type: VisualType
    content_hint: str = Field(min_length=1)
    source_ids: list[str] = Field(min_length=1)


class VideoOutline(BaseModel):
    title: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    narrative: str = Field(min_length=1)
    style: VideoStyleDecision
    scenes: list[SceneContract] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_scenes(self) -> "VideoOutline":
        indexes = [scene.index for scene in self.scenes]
        if indexes != list(range(1, len(self.scenes) + 1)):
            raise ValueError("outline scene indexes must be contiguous")
        if self.scenes[0].role != "hook":
            raise ValueError("outline must begin with a hook")
        if self.scenes[-1].role != "recap":
            raise ValueError("outline must end with a recap")
        return self


class VisualBeatDraft(BaseModel):
    id: str = Field(min_length=1)
    kind: VisualCueKind
    target: str = ""
    text_anchor: str = Field(min_length=1)
    summary: str = ""


class SceneDraft(BaseModel):
    scene_id: str = Field(min_length=1)
    index: int = Field(ge=1)
    title: str = Field(min_length=1)
    narration: str = Field(min_length=1)
    visual_type: VisualType
    visual: Any = Field(min_length=1)
    visual_beats: list[VisualBeatDraft] = Field(default_factory=list)


class RenderSettings(BaseModel):
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    fps: int = Field(default=30, ge=24, le=60)
    video_codec: Literal["h264"] = "h264"
    audio_codec: Literal["aac"] = "aac"
    format: Literal["mp4"] = "mp4"


class CaptionWord(BaseModel):
    text: str = Field(min_length=1)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_timing(self) -> "CaptionWord":
        if self.end_ms <= self.start_ms:
            raise ValueError("caption word end_ms must be greater than start_ms")
        return self


class AudioSynthesis(BaseModel):
    path: Path
    duration_ms: int = Field(gt=0)
    words: list[CaptionWord] = Field(default_factory=list)


class CaptionChunk(BaseModel):
    text: str = Field(min_length=1)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_timing(self) -> "CaptionChunk":
        if self.end_ms <= self.start_ms:
            raise ValueError("caption chunk end_ms must be greater than start_ms")
        return self


class VisualCue(BaseModel):
    id: str = Field(min_length=1)
    kind: VisualCueKind
    target: str = ""
    summary: str = ""
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    caption_text: str | None = None

    @model_validator(mode="after")
    def validate_timing(self) -> "VisualCue":
        if self.end_ms <= self.start_ms:
            raise ValueError("visual cue end_ms must be greater than start_ms")
        return self


class VideoScene(BaseModel):
    scene_id: str = Field(min_length=1)
    index: int = Field(ge=1)
    role: SceneRole
    title: str = Field(min_length=1)
    learning_objective: str = Field(min_length=1)
    visual_type: VisualType
    visual: Any = Field(min_length=1)
    narration: str = Field(min_length=1)
    audio_src: str = Field(min_length=1)
    start_ms: int = Field(ge=0)
    duration_ms: int = Field(gt=0)
    audio_duration_ms: int = Field(gt=0)
    caption_words: list[CaptionWord] = Field(default_factory=list)
    captions: list[CaptionChunk] = Field(default_factory=list)
    visual_cues: list[VisualCue] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_timeline(self) -> "VideoScene":
        if self.audio_duration_ms > self.duration_ms:
            raise ValueError("audio duration exceeds scene duration")
        if any(word.end_ms > self.audio_duration_ms for word in self.caption_words):
            raise ValueError("caption word timing exceeds measured audio")
        if any(chunk.end_ms > self.audio_duration_ms for chunk in self.captions):
            raise ValueError("caption timing exceeds measured audio")
        if any(cue.end_ms > self.audio_duration_ms for cue in self.visual_cues):
            raise ValueError("visual cue timing exceeds measured audio")
        return self


class VideoPlan(BaseModel):
    schema_version: Literal["video/v2"] = "video/v2"
    title: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    language: str = "zh-CN"
    aspect_ratio: AspectRatio
    style: VideoStyleDecision
    render: RenderSettings
    scenes: list[VideoScene] = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_scene_sequence(self) -> "VideoPlan":
        expected_start = 0
        for expected_index, scene in enumerate(self.scenes, start=1):
            if scene.index != expected_index:
                raise ValueError("scene indexes must be contiguous")
            if scene.start_ms != expected_start:
                raise ValueError("scene starts must be contiguous")
            expected_start += scene.duration_ms
        return self

    @property
    def duration_ms(self) -> int:
        return sum(scene.duration_ms for scene in self.scenes)


class VideoArtifact(BaseModel):
    plan: VideoPlan
    mp4_path: Path
    public_url: str = Field(min_length=1)
    duration_ms: int = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    size_bytes: int = Field(gt=0)
    metadata: dict[str, Any] = Field(default_factory=dict)
