"""Domain model for stateful, captioned teaching videos.

The planner describes semantic entities and state changes. Pixel geometry,
selectors and animation implementation belong to the composer.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LessonDepth(StrEnum):
    FOCUSED = "focused"
    STANDARD = "standard"
    DEEP = "deep"


class VisualGrammar(StrEnum):
    CONCEPT = "concept"
    MODEL = "model"
    TRACE = "trace"
    EVIDENCE = "evidence"


class EntityKind(StrEnum):
    CONTAINER = "container"
    SLOT = "slot"
    TOKEN = "token"
    POINTER = "pointer"
    PORT = "port"
    TERM = "term"
    CODE = "code"
    METRIC = "metric"


class TransitionKind(StrEnum):
    REVEAL = "reveal"
    MOVE = "move"
    INSERT = "insert"
    REMOVE = "remove"
    UPDATE = "update"
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    EXECUTE = "execute"
    COMPARE = "compare"


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


class ExecutionObjectRole(StrEnum):
    CONTAINER = "container"
    TOKEN = "token"
    POINTER = "pointer"
    NODE = "node"
    PORT = "port"
    MARKER = "marker"


class ExecutionVerb(StrEnum):
    REVEAL = "reveal"
    PLACE = "place"
    MOVE = "move"
    REMOVE = "remove"
    POINT = "point"
    UPDATE = "update"
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    COMPARE = "compare"
    HIGHLIGHT = "highlight"


class ExecutionObject(_Model):
    """One server-identified object in a renderer-neutral execution program."""

    id: str = Field(min_length=1, max_length=48, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")
    name: str = Field(min_length=1, max_length=32)
    label: str = Field(min_length=1)
    role: ExecutionObjectRole
    value: str = ""
    capacity: int | None = Field(default=None, ge=0, le=12)

    @model_validator(mode="after")
    def validate_structure(self) -> "ExecutionObject":
        if self.role is ExecutionObjectRole.CONTAINER and self.capacity is None:
            raise ValueError("execution container requires capacity")
        if self.role is not ExecutionObjectRole.CONTAINER and self.capacity is not None:
            raise ValueError("only execution containers may declare capacity")
        return self


class ExecutionOperation(_Model):
    """One atomic, geometry-free change in an executable teaching trace."""

    verb: ExecutionVerb
    subject: str = Field(min_length=1, max_length=32)
    target: str = Field(default="", max_length=32)
    slot: int | None = Field(default=None, ge=0, le=15)
    region: SemanticRegion | None = None
    value: str = ""


class ExecutionProgram(_Model):
    objects: list[ExecutionObject] = Field(min_length=2, max_length=16)

    @model_validator(mode="after")
    def validate_object_names(self) -> "ExecutionProgram":
        names = [item.name for item in self.objects]
        if len(names) != len(set(names)):
            raise ValueError("execution program contains duplicate object names")
        return self


class CartoonGenerationConfig(_Model):
    lesson_depth: LessonDepth = LessonDepth.STANDARD
    visual_density: Literal["moderate", "rich", "intensive"] = "rich"
    pace: Literal["fast", "balanced", "calm"] = "balanced"
    voice: Literal["teacher", "coach"] = "teacher"


class CartoonBrief(_Model):
    learning_need: str = Field(min_length=1)
    instruction_context: dict[str, Any] = Field(default_factory=dict)
    source_materials: list[str] = Field(default_factory=list, max_length=12)
    knowledge_points: list[str] = Field(default_factory=list, max_length=30)
    weak_knowledge_points: list[str] = Field(default_factory=list, max_length=20)
    configuration: CartoonGenerationConfig = Field(default_factory=CartoonGenerationConfig)


class VisualEntity(_Model):
    id: str = Field(min_length=1, max_length=48, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")
    label: str = Field(min_length=1)
    kind: EntityKind


class EntityPlacement(_Model):
    entity_id: str = Field(min_length=1, max_length=48)
    container_id: str = Field(default="", max_length=48)
    anchor_id: str = Field(default="", max_length=48)
    slot: int | None = Field(default=None, ge=0, le=15)
    region: SemanticRegion = SemanticRegion.MAIN
    visible: bool = True
    value: str = ""
    status: Literal["idle", "active", "success", "warning", "error"] = "idle"

    @model_validator(mode="after")
    def validate_slot(self) -> "EntityPlacement":
        if self.slot is not None and not self.container_id:
            raise ValueError("slot placement requires container_id")
        if self.anchor_id == self.entity_id:
            raise ValueError("entity cannot anchor to itself")
        return self


class Relation(_Model):
    source_id: str = Field(min_length=1, max_length=48)
    target_id: str = Field(min_length=1, max_length=48)
    label: str = ""

    @model_validator(mode="after")
    def reject_self_relation(self) -> "Relation":
        if self.source_id == self.target_id:
            raise ValueError("relation cannot point to the same entity")
        return self


class VisualState(_Model):
    id: str = Field(min_length=1, max_length=48)
    placements: list[EntityPlacement] = Field(min_length=1, max_length=16)
    relations: list[Relation] = Field(default_factory=list, max_length=24)

    @model_validator(mode="after")
    def unique_placements(self) -> "VisualState":
        entity_ids = [item.entity_id for item in self.placements]
        if len(entity_ids) != len(set(entity_ids)):
            raise ValueError("state contains duplicate entity placements")
        relation_keys = [
            (item.source_id, item.target_id, item.label)
            for item in self.relations
        ]
        if len(relation_keys) != len(set(relation_keys)):
            raise ValueError("state contains duplicate relations")
        return self


class Transition(_Model):
    kind: TransitionKind
    entity_ids: list[str] = Field(min_length=1, max_length=8)

    @field_validator("entity_ids")
    @classmethod
    def unique_entities(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("transition contains duplicate entity ids")
        return values


class TeachingBeat(_Model):
    id: str = Field(min_length=1, max_length=48)
    narration: str = Field(min_length=1)
    caption: str = Field(min_length=1)
    before_state_id: str = Field(min_length=1, max_length=48)
    after_state_id: str = Field(min_length=1, max_length=48)
    transition: Transition
    focus_entity_ids: list[str] = Field(min_length=1, max_length=8)
    operation: ExecutionOperation | None = None

    @field_validator("focus_entity_ids")
    @classmethod
    def unique_focus_entities(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("beat contains duplicate focus entity ids")
        return values


@dataclass(frozen=True)
class StateChanges:
    moved_entity_ids: frozenset[str]
    visibility_changed_entity_ids: frozenset[str]
    value_changed_entity_ids: frozenset[str]
    status_changed_entity_ids: frozenset[str]
    relations_changed: bool

    @property
    def has_semantic_change(self) -> bool:
        return bool(
            self.moved_entity_ids
            or self.visibility_changed_entity_ids
            or self.value_changed_entity_ids
            or self.status_changed_entity_ids
            or self.relations_changed
        )


class TeachingScene(_Model):
    id: str = Field(min_length=1, max_length=48)
    title: str = Field(min_length=1)
    grammar: VisualGrammar
    execution_program: ExecutionProgram | None = None
    entities: list[VisualEntity] = Field(min_length=2, max_length=16)
    states: list[VisualState] = Field(min_length=2, max_length=8)
    beats: list[TeachingBeat] = Field(min_length=1, max_length=5)

    @model_validator(mode="after")
    def validate_scene_contract(self) -> "TeachingScene":
        if self.grammar is VisualGrammar.TRACE and self.execution_program is None:
            raise ValueError("trace scenes require an execution_program")
        if self.grammar is not VisualGrammar.TRACE and self.execution_program is not None:
            raise ValueError("only trace scenes may declare an execution_program")
        entity_ids = [entity.id for entity in self.entities]
        if len(entity_ids) != len(set(entity_ids)):
            raise ValueError("scene contains duplicate entity ids")
        known_entities = set(entity_ids)
        container_ids = {
            entity.id for entity in self.entities if entity.kind == EntityKind.CONTAINER
        }

        state_ids = [state.id for state in self.states]
        if len(state_ids) != len(set(state_ids)):
            raise ValueError("scene contains duplicate state ids")
        known_states = set(state_ids)
        for state in self.states:
            placed = {item.entity_id for item in state.placements}
            if placed != known_entities:
                missing = sorted(known_entities - placed)
                unknown = sorted(placed - known_entities)
                raise ValueError(
                    f"state placements must cover every scene entity; missing={missing}, unknown={unknown}"
                )
            for placement in state.placements:
                if placement.container_id and placement.container_id not in container_ids:
                    raise ValueError("placement container_id must reference a container entity")
                if placement.container_id == placement.entity_id:
                    raise ValueError("entity cannot be placed inside itself")
                if placement.anchor_id and placement.anchor_id not in known_entities:
                    raise ValueError("placement anchor_id must reference a scene entity")
            for relation in state.relations:
                if {relation.source_id, relation.target_id} - known_entities:
                    raise ValueError("relation references an unknown entity")

            if self.execution_program is not None:
                self._validate_execution_state(state, container_ids)

        beat_ids = [beat.id for beat in self.beats]
        if len(beat_ids) != len(set(beat_ids)):
            raise ValueError("scene contains duplicate beat ids")
        for beat in self.beats:
            if beat.before_state_id not in known_states or beat.after_state_id not in known_states:
                raise ValueError("beat references an unknown visual state")
            if beat.before_state_id == beat.after_state_id:
                raise ValueError("beat must reference distinct before and after states")
            referenced = set(beat.focus_entity_ids) | set(beat.transition.entity_ids)
            if referenced - known_entities:
                raise ValueError("beat references an unknown entity")
            if not self.state_changes(beat).has_semantic_change:
                raise ValueError(
                    "every teaching beat requires a semantic state change; focus-only animation is invalid"
                )
            if self.grammar is VisualGrammar.TRACE and beat.operation is None:
                raise ValueError("trace beats require an execution operation")
            if self.grammar is VisualGrammar.TRACE and beat.operation is not None:
                assert self.execution_program is not None
                execution_by_name = {
                    item.name: item for item in self.execution_program.objects
                }
                operation = beat.operation
                subject = execution_by_name.get(operation.subject)
                target = execution_by_name.get(operation.target) if operation.target else None
                if subject is None or (operation.target and target is None):
                    raise ValueError("execution operation references an unknown object")
                after = self.state(beat.after_state_id)
                after_items = {item.entity_id: item for item in after.placements}
                subject_placement = after_items[subject.id]
                if operation.verb is ExecutionVerb.PLACE:
                    if target is None or subject_placement.container_id != target.id or subject_placement.slot != operation.slot:
                        raise ValueError("place operation must occupy its declared container slot")
                if operation.verb is ExecutionVerb.REMOVE and (
                    subject_placement.region is not SemanticRegion.OUTPUT
                    or not subject_placement.visible
                ):
                    raise ValueError("remove operation must produce visible output")
                if operation.verb is ExecutionVerb.POINT and (
                    target is None or subject_placement.anchor_id != target.id
                ):
                    raise ValueError("point operation must attach to its declared target")
        return self

    def _validate_execution_state(self, state: VisualState, container_ids: set[str]) -> None:
        assert self.execution_program is not None
        execution_ids = {item.id for item in self.execution_program.objects}
        if execution_ids != {entity.id for entity in self.entities}:
            raise ValueError("execution program objects must match scene entities")
        placements = {item.entity_id: item for item in state.placements}
        containers = {
            item.id: item
            for item in self.execution_program.objects
            if item.role is ExecutionObjectRole.CONTAINER
        }
        if containers and not any(placements[container_id].visible for container_id in containers):
            raise ValueError("execution trace must keep a visible container")
        occupied_slots: set[tuple[str, int]] = set()
        execution_by_id = {item.id: item for item in self.execution_program.objects}
        for entity in self.entities:
            placement = placements[entity.id]
            if placement.container_id:
                if placement.container_id not in containers:
                    raise ValueError("execution placement must use a valid container")
                if not placement.visible:
                    raise ValueError("occupied execution object must be visible")
                container = containers[placement.container_id]
                # Stateless containers (capacity=0) do not enforce slot capacity
                if container.capacity and container.capacity > 0:
                    if placement.slot is None:
                        raise ValueError("stateful execution container requires a slot")
                    if placement.slot >= container.capacity:
                        raise ValueError("execution object exceeds container capacity")
                    if execution_by_id[entity.id].role is not ExecutionObjectRole.POINTER:
                        key = (placement.container_id, placement.slot)
                        if key in occupied_slots:
                            raise ValueError("execution trace cannot place two objects in one slot")
                        occupied_slots.add(key)
                elif placement.slot is not None:
                    raise ValueError("stateless execution container cannot use a slot")
            if entity.kind is EntityKind.POINTER and placement.visible and not placement.anchor_id:
                raise ValueError("visible execution pointer must attach to an object")

    def state(self, state_id: str) -> VisualState:
        return next(state for state in self.states if state.id == state_id)

    def state_changes(self, beat: TeachingBeat) -> StateChanges:
        before = self.state(beat.before_state_id)
        after = self.state(beat.after_state_id)
        before_items = {item.entity_id: item for item in before.placements}
        after_items = {item.entity_id: item for item in after.placements}

        moved: set[str] = set()
        visibility: set[str] = set()
        values: set[str] = set()
        statuses: set[str] = set()
        for entity_id in before_items.keys() | after_items.keys():
            left = before_items.get(entity_id)
            right = after_items.get(entity_id)
            if left is None or right is None:
                visibility.add(entity_id)
                continue
            if (left.container_id, left.slot, left.region, left.anchor_id) != (
                right.container_id,
                right.slot,
                right.region,
                right.anchor_id,
            ):
                moved.add(entity_id)
            if left.visible != right.visible:
                visibility.add(entity_id)
            if left.value != right.value:
                values.add(entity_id)
            if left.status != right.status:
                statuses.add(entity_id)

        before_relations = {
            (item.source_id, item.target_id, item.label)
            for item in before.relations
        }
        after_relations = {
            (item.source_id, item.target_id, item.label)
            for item in after.relations
        }
        return StateChanges(
            moved_entity_ids=frozenset(moved),
            visibility_changed_entity_ids=frozenset(visibility),
            value_changed_entity_ids=frozenset(values),
            status_changed_entity_ids=frozenset(statuses),
            relations_changed=before_relations != after_relations,
        )


class Lesson(_Model):
    title: str = Field(min_length=1)
    scenes: list[TeachingScene] = Field(min_length=3, max_length=6)

    @model_validator(mode="after")
    def validate_contract(self) -> "Lesson":
        if len({scene.grammar for scene in self.scenes}) < 2:
            raise ValueError("lesson requires at least two visual grammars")
        scene_ids = [scene.id for scene in self.scenes]
        if len(scene_ids) != len(set(scene_ids)):
            raise ValueError("lesson contains duplicate scene ids")
        beat_ids = [beat.id for scene in self.scenes for beat in scene.beats]
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
    output_dir: Path
    html_path: Path
    scene_data_path: Path
    caption_path: Path
    scene_paths: list[Path] = Field(min_length=3, max_length=6)


class CartoonArtifact(_Model):
    schema_version: Literal["cartoon/artifact-v8"] = "cartoon/artifact-v8"
    title: str
    duration_ms: int = Field(gt=0)
    scene_count: int = Field(ge=3, le=6)
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
    scene_count: int = Field(ge=3, le=6)

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
