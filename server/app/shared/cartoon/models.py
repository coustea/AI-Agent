"""Domain model for stateful, captioned teaching videos.

The planner describes semantic entities and state changes. Pixel geometry,
selectors and animation implementation belong to the composer.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LessonDepth(StrEnum):
    FOCUSED = "focused"
    STANDARD = "standard"
    DEEP = "deep"


class SceneMode(StrEnum):
    CONCEPT = "concept"
    MECHANISM = "mechanism"
    EXECUTION = "execution"
    COMPARISON = "comparison"
    EVIDENCE = "evidence"


class SceneTopology(StrEnum):
    HIERARCHICAL = "hierarchical"
    NETWORK = "network"
    FLOW = "flow"
    SEQUENCE = "sequence"
    GRID = "grid"
    SPATIAL = "spatial"


class SemanticObjectRole(StrEnum):
    CONTAINER = "container"
    NODE = "node"
    PROCESS = "process"
    TOKEN = "token"
    POINTER = "pointer"
    PORT = "port"
    MARKER = "marker"


class SemanticActionVerb(StrEnum):
    REVEAL = "reveal"
    FOCUS = "focus"
    PLACE = "place"
    MOVE = "move"
    REMOVE = "remove"
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    UPDATE = "update"
    COMPARE = "compare"
    TRAVERSE = "traverse"
    SETTLE = "settle"


class SemanticRegion(StrEnum):
    MAIN = "main"
    INPUT = "input"
    OUTPUT = "output"
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"
    CODE = "code"
    RESULT = "result"


PlacementStatus = Literal["idle", "active", "success", "warning", "error"]


class SemanticObject(_Model):
    """One stable, renderer-neutral object in a semantic scene program."""

    id: str = Field(min_length=1, max_length=48, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")
    name: str = Field(min_length=1)
    label: str = Field(min_length=1)
    role: SemanticObjectRole
    value: str = ""
    capacity: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_structure(self) -> "SemanticObject":
        if self.role is SemanticObjectRole.CONTAINER and self.capacity is None:
            raise ValueError("semantic container requires capacity")
        if self.role is not SemanticObjectRole.CONTAINER and self.capacity is not None:
            raise ValueError("only semantic containers may declare capacity")
        return self


class SemanticAction(_Model):
    """One atomic, geometry-free action over named semantic objects."""

    verb: SemanticActionVerb
    subject_id: str = Field(min_length=1, max_length=48)
    target_id: str = Field(default="", max_length=48)
    slot: int | None = Field(default=None, ge=0)
    region: SemanticRegion | None = None
    value: str = ""
    state: PlacementStatus | Literal[""] = ""

class CartoonGenerationConfig(_Model):
    lesson_depth: LessonDepth = LessonDepth.STANDARD
    visual_density: Literal["moderate", "rich", "intensive"] = "rich"
    pace: Literal["fast", "balanced", "calm"] = "balanced"
    voice: Literal["teacher", "coach"] = "teacher"


class CartoonBrief(_Model):
    learning_need: str = Field(min_length=1)
    instruction_context: dict[str, Any] = Field(default_factory=dict)
    source_materials: list[str] = Field(default_factory=list)
    knowledge_points: list[str] = Field(default_factory=list)
    weak_knowledge_points: list[str] = Field(default_factory=list)
    configuration: CartoonGenerationConfig = Field(default_factory=CartoonGenerationConfig)


class ObjectPlacement(_Model):
    object_id: str = Field(min_length=1, max_length=48)
    container_id: str = Field(default="", max_length=48)
    anchor_id: str = Field(default="", max_length=48)
    slot: int | None = Field(default=None, ge=0)
    region: SemanticRegion = SemanticRegion.MAIN
    visible: bool = True
    value: str = ""
    status: PlacementStatus = "idle"

    @model_validator(mode="after")
    def validate_slot(self) -> "ObjectPlacement":
        if self.slot is not None and not self.container_id:
            raise ValueError("slot placement requires container_id")
        if self.anchor_id == self.object_id:
            raise ValueError("object cannot anchor to itself")
        return self


class SceneRelation(_Model):
    id: str = Field(min_length=1, max_length=48)
    source_id: str = Field(min_length=1, max_length=48)
    target_id: str = Field(min_length=1, max_length=48)

    @model_validator(mode="after")
    def reject_self_relation(self) -> "SceneRelation":
        if self.source_id == self.target_id:
            raise ValueError("relation cannot point to the same object")
        return self


class SceneState(_Model):
    id: str = Field(min_length=1, max_length=48)
    placements: list[ObjectPlacement] = Field(min_length=1)
    relations: list[SceneRelation] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_members(self) -> "SceneState":
        object_ids = [item.object_id for item in self.placements]
        if len(object_ids) != len(set(object_ids)):
            raise ValueError("state contains duplicate object placements")
        relation_ids = [item.id for item in self.relations]
        if len(relation_ids) != len(set(relation_ids)):
            raise ValueError("state contains duplicate relations")
        return self


class TeachingBeat(_Model):
    id: str = Field(min_length=1, max_length=48)
    narration: str = Field(min_length=1)
    before_state_id: str = Field(min_length=1, max_length=48)
    after_state_id: str = Field(min_length=1, max_length=48)
    actions: list[SemanticAction] = Field(min_length=1)
    action_state_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_action_state_count(self) -> "TeachingBeat":
        if len(self.action_state_ids) != len(self.actions):
            raise ValueError("every semantic action requires one resulting state")
        if self.action_state_ids[-1] != self.after_state_id:
            raise ValueError("the final action state must equal after_state_id")
        return self


class SceneProgram(_Model):
    objects: list[SemanticObject] = Field(min_length=1)
    states: list[SceneState] = Field(min_length=2)
    beats: list[TeachingBeat] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_references(self) -> "SceneProgram":
        object_ids = [item.id for item in self.objects]
        if len(object_ids) != len(set(object_ids)):
            raise ValueError("scene program contains duplicate object ids")
        object_names = [item.name for item in self.objects]
        if len(object_names) != len(set(object_names)):
            raise ValueError("scene program contains duplicate object names")
        known_objects = set(object_ids)
        container_ids = {
            item.id for item in self.objects if item.role is SemanticObjectRole.CONTAINER
        }
        state_ids = [state.id for state in self.states]
        if len(state_ids) != len(set(state_ids)):
            raise ValueError("scene contains duplicate state ids")
        known_states = set(state_ids)
        relation_endpoints_by_id: dict[str, tuple[str, str]] = {}
        for state in self.states:
            placed = {item.object_id for item in state.placements}
            if placed != known_objects:
                missing = sorted(known_objects - placed)
                unknown = sorted(placed - known_objects)
                raise ValueError(
                    f"state placements must cover every scene object; missing={missing}, unknown={unknown}"
                )
            for placement in state.placements:
                if placement.container_id and placement.container_id not in container_ids:
                    raise ValueError("placement container_id must reference a container object")
                if placement.container_id == placement.object_id:
                    raise ValueError("object cannot be placed inside itself")
                if placement.anchor_id and placement.anchor_id not in known_objects:
                    raise ValueError("placement anchor_id must reference a scene object")
            for relation in state.relations:
                if {relation.source_id, relation.target_id} - known_objects:
                    raise ValueError("relation references an unknown object")
                endpoints = (relation.source_id, relation.target_id)
                known_endpoints = relation_endpoints_by_id.setdefault(
                    relation.id,
                    endpoints,
                )
                if known_endpoints != endpoints:
                    raise ValueError("relation identity cannot change endpoints")

        beat_ids = [beat.id for beat in self.beats]
        if len(beat_ids) != len(set(beat_ids)):
            raise ValueError("scene contains duplicate beat ids")
        for beat in self.beats:
            if beat.before_state_id not in known_states or beat.after_state_id not in known_states:
                raise ValueError("beat references an unknown scene state")
            if beat.before_state_id == beat.after_state_id:
                raise ValueError("beat must reference distinct before and after states")
            referenced: set[str] = set()
            for action in beat.actions:
                referenced.add(action.subject_id)
                if action.target_id:
                    referenced.add(action.target_id)
            if referenced - known_objects:
                raise ValueError("beat action references an unknown object")
        expected_state_ids = [self.states[0].id]
        previous_state_id = self.states[0].id
        for beat in self.beats:
            if beat.before_state_id != previous_state_id:
                raise ValueError("beats must form one ordered continuous replay chain")
            expected_state_ids.extend(beat.action_state_ids)
            previous_state_id = beat.after_state_id
        actual_state_ids = [state.id for state in self.states]
        if actual_state_ids != expected_state_ids:
            raise ValueError("states must contain every action result in replay order")
        return self

class TeachingScene(_Model):
    id: str = Field(min_length=1, max_length=48)
    title: str = Field(min_length=1)
    mode: SceneMode
    topology: SceneTopology
    program: SceneProgram

class Lesson(_Model):
    title: str = Field(min_length=1)
    scenes: list[TeachingScene] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_contract(self) -> "Lesson":
        scene_ids = [scene.id for scene in self.scenes]
        if len(scene_ids) != len(set(scene_ids)):
            raise ValueError("lesson contains duplicate scene ids")
        beat_ids = [
            beat.id
            for scene in self.scenes
            for beat in scene.program.beats
        ]
        if len(beat_ids) != len(set(beat_ids)):
            raise ValueError("lesson contains duplicate beat ids")
        return self


class SpeechClip(_Model):
    beat_id: str
    path: Path
    duration_ms: int = Field(gt=0)
    provider: str = Field(min_length=1)
    voice: str = Field(min_length=1)


class CaptionCue(_Model):
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    text: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_cue(self) -> "CaptionCue":
        duration = self.end_ms - self.start_ms
        if duration <= 0:
            raise ValueError("caption cue must end after it starts")
        return self


class TimedBeat(_Model):
    scene_id: str
    beat_id: str
    start_ms: int = Field(ge=0)
    duration_ms: int = Field(gt=0)
    audio_duration_ms: int | None = Field(default=None, gt=0)
    audio_src: str = Field(min_length=1)

    @property
    def end_ms(self) -> int:
        return self.start_ms + self.duration_ms


class Timeline(_Model):
    duration_ms: int = Field(gt=0)
    beats: list[TimedBeat] = Field(min_length=1)
    captions: list[CaptionCue] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_timeline(self) -> "Timeline":
        ordered_beats = sorted(self.beats, key=lambda item: item.start_ms)
        if ordered_beats != self.beats:
            raise ValueError("timeline beats must be ordered")
        if ordered_beats[-1].end_ms > self.duration_ms:
            raise ValueError("timeline beat exceeds total duration")
        ordered_captions = sorted(self.captions, key=lambda item: item.start_ms)
        if ordered_captions != self.captions:
            raise ValueError("caption cues must be ordered")
        for beat in ordered_beats:
            midpoint = beat.start_ms + beat.duration_ms // 2
            if not any(cue.start_ms <= midpoint <= cue.end_ms for cue in ordered_captions):
                raise ValueError("every narration beat requires a visible caption at its midpoint")
        return self


class CartoonBundle(_Model):
    html_path: Path
    caption_path: Path


class CartoonArtifact(_Model):
    schema_version: Literal["cartoon/artifact-v8"] = "cartoon/artifact-v8"
    title: str
    duration_ms: int = Field(gt=0)
    scene_count: int = Field(ge=1)
    has_audio: Literal[True] = True
    output_dir: Path
    html_path: Path
    video_path: Path
    caption_path: Path
    lesson_path: Path
    timeline_path: Path
    audit_path: Path


class CartoonResourceMetadata(_Model):
    agent_id: Literal["cartoon"] = "cartoon"
    schema_version: Literal["cartoon/v8"] = "cartoon/v8"
    engine: Literal["hyperframes"] = "hyperframes"
    has_audio: Literal[True] = True
    quality_passed: Literal[True] = True
    video_url: str = Field(min_length=1)
    preview_url: str = Field(min_length=1)
    captions_url: str = Field(min_length=1)
    duration_seconds: float = Field(gt=0)
    scene_count: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_urls(self) -> "CartoonResourceMetadata":
        expected = {
            "video_url": ".mp4",
            "preview_url": ".html",
            "captions_url": ".vtt",
        }
        for field, suffix in expected.items():
            if not str(getattr(self, field)).strip().endswith(suffix):
                raise ValueError(f"{field} must reference a {suffix} file")
        return self


class CartoonGenerationError(RuntimeError):
    def __init__(self, message: str, *, stage: str, problems: list[str] | None = None) -> None:
        super().__init__(message)
        self.stage = stage
        self.problems = list(problems or [])
