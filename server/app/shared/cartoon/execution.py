"""Compile compact execution programs into renderer-neutral Cartoon states."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.infra.logging import get_logger
from app.shared.cartoon.models import (
    EntityKind,
    EntityPlacement,
    ExecutionObject,
    ExecutionObjectRole,
    ExecutionOperation,
    ExecutionProgram,
    ExecutionVerb,
    Relation,
    SemanticRegion,
    TeachingBeat,
    Transition,
    TransitionKind,
    VisualEntity,
    VisualState,
)


logger = get_logger(__name__)


class _Draft(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExecutionObjectDraft(_Draft):
    name: str = Field(min_length=1, max_length=32)
    label: str = Field(min_length=1)
    role: ExecutionObjectRole
    value: str = ""
    capacity: int | None = Field(default=None, ge=0, le=12)

    @field_validator("value", mode="before")
    @classmethod
    def coerce_value_to_str(cls, v: Any) -> str:
        """LLM may output numeric values (e.g. 5 instead of '5'); coerce to str."""
        if v is None:
            return ""
        return str(v).strip()

    @field_validator("name", "label")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_structure(self) -> "ExecutionObjectDraft":
        if not self.name or not self.label:
            raise ValueError("execution object name and label cannot be blank")
        if self.role is ExecutionObjectRole.CONTAINER and self.capacity is None:
            raise ValueError("container requires capacity")
        if self.role is not ExecutionObjectRole.CONTAINER and self.capacity is not None:
            raise ValueError("only containers may declare capacity")
        return self


class ExecutionOperationDraft(_Draft):
    verb: ExecutionVerb
    subject: str = Field(min_length=1, max_length=32)
    target: str = Field(default="", max_length=32)
    slot: int | None = Field(default=None, ge=0, le=15)
    region: SemanticRegion | None = None
    value: str = ""

    @field_validator("value", mode="before")
    @classmethod
    def coerce_value_to_str(cls, v: Any) -> str:
        """LLM may output numeric values; coerce to str."""
        if v is None:
            return ""
        return str(v).strip()

    @field_validator("subject", "target")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_arguments(self) -> "ExecutionOperationDraft":
        target_required = {
            ExecutionVerb.PLACE,
            ExecutionVerb.POINT,
            ExecutionVerb.CONNECT,
            ExecutionVerb.DISCONNECT,
            ExecutionVerb.COMPARE,
        }
        if self.verb in target_required and not self.target:
            raise ValueError(f"{self.verb.value} requires target")
        if self.verb is ExecutionVerb.PLACE and self.slot is None:
            raise ValueError("place requires slot")
        if self.verb is ExecutionVerb.MOVE and not self.target and self.region is None:
            raise ValueError("move requires target container or region")
        if self.verb is ExecutionVerb.UPDATE and not self.value:
            raise ValueError("update requires value")
        if self.verb is not ExecutionVerb.MOVE and self.region is not None:
            raise ValueError("only move may declare region")
        return self


class ExecutionBeatDraft(_Draft):
    narration: str = Field(min_length=1)
    operation: ExecutionOperationDraft

    @field_validator("narration")
    @classmethod
    def normalize_narration(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("execution narration cannot be blank")
        return normalized


class ExecutionSceneDraft(_Draft):
    objects: list[ExecutionObjectDraft] = Field(min_length=2, max_length=16)
    beats: list[ExecutionBeatDraft] = Field(min_length=3, max_length=4)

    @model_validator(mode="after")
    def validate_object_names(self) -> "ExecutionSceneDraft":
        names = [item.name for item in self.objects]
        if len(names) != len(set(names)):
            raise ValueError("execution objects must have unique names")
        known = set(names)
        for beat in self.beats:
            operation = beat.operation
            if operation.subject not in known:
                raise ValueError(f"operation subject is unknown: {operation.subject}")
            if operation.target and operation.target not in known:
                raise ValueError(f"operation target is unknown: {operation.target}")
        return self


@dataclass(frozen=True)
class CompiledExecutionScene:
    program: ExecutionProgram
    entities: list[VisualEntity]
    states: list[VisualState]
    beats: list[TeachingBeat]


class ExecutionCompiler:
    """One interpreter for observable object, relation, and placement changes."""

    _TRANSITIONS = {
        ExecutionVerb.REVEAL: TransitionKind.REVEAL,
        ExecutionVerb.PLACE: TransitionKind.INSERT,
        ExecutionVerb.MOVE: TransitionKind.MOVE,
        ExecutionVerb.REMOVE: TransitionKind.REMOVE,
        ExecutionVerb.POINT: TransitionKind.MOVE,
        ExecutionVerb.UPDATE: TransitionKind.UPDATE,
        ExecutionVerb.CONNECT: TransitionKind.CONNECT,
        ExecutionVerb.DISCONNECT: TransitionKind.DISCONNECT,
        ExecutionVerb.COMPARE: TransitionKind.COMPARE,
        ExecutionVerb.HIGHLIGHT: TransitionKind.EXECUTE,
    }

    _KINDS = {
        ExecutionObjectRole.CONTAINER: EntityKind.CONTAINER,
        ExecutionObjectRole.TOKEN: EntityKind.TOKEN,
        ExecutionObjectRole.POINTER: EntityKind.POINTER,
        ExecutionObjectRole.NODE: EntityKind.TERM,
        ExecutionObjectRole.PORT: EntityKind.PORT,
        ExecutionObjectRole.MARKER: EntityKind.METRIC,
    }

    @classmethod
    def compile(cls, draft: ExecutionSceneDraft, *, scene_id: str) -> CompiledExecutionScene:
        logger.info(
            "[ExecutionCompiler] 编译执行场景: scene_id=%s objects=%d beats=%d",
            scene_id,
            len(draft.objects),
            len(draft.beats),
        )
        objects = [
            ExecutionObject(
                id=f"{scene_id}-object-{index:02d}",
                name=item.name,
                label=item.label,
                role=item.role,
                value=item.value,
                capacity=item.capacity,
            )
            for index, item in enumerate(draft.objects, start=1)
        ]
        program = ExecutionProgram(objects=objects)
        object_by_name = {item.name: item for item in objects}
        entities = [
            VisualEntity(id=item.id, label=item.label, kind=cls._KINDS[item.role])
            for item in objects
        ]
        placements = {
            item.name: cls._initial_placement(item)
            for item in objects
        }
        relations: list[Relation] = []
        states = [cls._state(scene_id, 1, placements, relations)]
        beats: list[TeachingBeat] = []
        for index, draft_beat in enumerate(draft.beats, start=1):
            before = states[-1]
            operation = cls._operation(draft_beat.operation)
            focus = cls._apply(
                operation,
                object_by_name=object_by_name,
                placements=placements,
                relations=relations,
            )
            after = cls._state(scene_id, index + 1, placements, relations)
            if not cls._state_changed(before, after):
                raise ValueError(f"operation {operation.verb.value} has no observable state delta")
            logger.debug(
                "[ExecutionCompiler] beat %d: verb=%s subject=%s target=%s",
                index,
                operation.verb.value,
                operation.subject,
                operation.target or "-",
            )
            states.append(after)
            focus_ids = [object_by_name[name].id for name in focus]
            beats.append(
                TeachingBeat(
                    id=f"{scene_id}-beat-{index:02d}",
                    narration=draft_beat.narration,
                    caption=cls._caption(operation),
                    before_state_id=before.id,
                    after_state_id=after.id,
                    transition=Transition(
                        kind=cls._TRANSITIONS[operation.verb],
                        entity_ids=focus_ids,
                    ),
                    focus_entity_ids=focus_ids,
                    operation=operation,
                )
            )
        logger.info(
            "[ExecutionCompiler] 编译完成: scene_id=%s states=%d beats=%d",
            scene_id,
            len(states),
            len(beats),
        )
        return CompiledExecutionScene(program=program, entities=entities, states=states, beats=beats)

    @staticmethod
    def _initial_placement(item: ExecutionObject) -> EntityPlacement:
        visible = item.role in {
            ExecutionObjectRole.CONTAINER,
            ExecutionObjectRole.NODE,
            ExecutionObjectRole.PORT,
            ExecutionObjectRole.MARKER,
        }
        region = SemanticRegion.MAIN
        if item.role is ExecutionObjectRole.TOKEN:
            region = SemanticRegion.INPUT
        if item.role is ExecutionObjectRole.POINTER:
            region = SemanticRegion.TOP
        return EntityPlacement(
            entity_id=item.id,
            region=region,
            visible=visible,
            value=item.value,
            status="idle",
        )

    @staticmethod
    def _operation(draft: ExecutionOperationDraft) -> ExecutionOperation:
        return ExecutionOperation(
            verb=draft.verb,
            subject=draft.subject,
            target=draft.target,
            slot=draft.slot,
            region=draft.region,
            value=draft.value,
        )

    @classmethod
    def _apply(
        cls,
        operation: ExecutionOperation,
        *,
        object_by_name: dict[str, ExecutionObject],
        placements: dict[str, EntityPlacement],
        relations: list[Relation],
    ) -> list[str]:
        subject = object_by_name[operation.subject]
        target = object_by_name.get(operation.target) if operation.target else None
        for placement in placements.values():
            if placement.status == "active":
                placement.status = "idle"

        def show(item: ExecutionObject, status: str = "active") -> None:
            placement = placements[item.name]
            if item.role is ExecutionObjectRole.POINTER and not placement.anchor_id:
                preferred = (
                    target
                    if target is not None and target.role is not ExecutionObjectRole.POINTER
                    else next(
                        (
                            candidate
                            for candidate in object_by_name.values()
                            if candidate.role is not ExecutionObjectRole.POINTER
                            and placements[candidate.name].visible
                        ),
                        next(
                            candidate
                            for candidate in object_by_name.values()
                            if candidate.role is not ExecutionObjectRole.POINTER
                        ),
                    )
                )
                placement.anchor_id = preferred.id
            placement.visible = True
            placement.status = status

        if operation.verb is ExecutionVerb.REVEAL:
            show(subject)
            return [subject.name]
        if operation.verb is ExecutionVerb.PLACE:
            assert target is not None and operation.slot is not None
            cls._place(subject, target, operation.slot, object_by_name, placements)
            show(target)
            return [subject.name, target.name]
        if operation.verb is ExecutionVerb.MOVE:
            if subject.role is ExecutionObjectRole.POINTER:
                placement = placements[subject.name]
                placement.container_id = ""
                placement.slot = None
                placement.anchor_id = target.id if target is not None else ""
                placement.region = (
                    placements[target.name].region
                    if target is not None
                    else operation.region or SemanticRegion.MAIN
                )
                show(subject)
                if target is not None:
                    show(target)
                    return [subject.name, target.name]
                return [subject.name]
            if target is not None:
                if target.role is not ExecutionObjectRole.CONTAINER:
                    raise ValueError("move target must be a container")
                # Stateless containers (capacity=0) accept move without slot;
                # the subject is placed into the container region but no slot
                # tracking is needed.
                if target.capacity and target.capacity > 0:
                    if operation.slot is None:
                        raise ValueError("move to a stateful container requires a slot")
                    cls._place(subject, target, operation.slot, object_by_name, placements)
                else:
                    # Stateless container: place subject inside without slot
                    placement = placements[subject.name]
                    placement.container_id = target.id
                    placement.slot = None
                    placement.anchor_id = ""
                    placement.region = SemanticRegion.MAIN
                    placement.visible = True
                    placement.status = "active"
                show(target)
                return [subject.name, target.name]
            placement = placements[subject.name]
            placement.container_id = ""
            placement.slot = None
            placement.anchor_id = ""
            placement.region = operation.region or SemanticRegion.MAIN
            show(subject)
            return [subject.name]
        if operation.verb is ExecutionVerb.REMOVE:
            placement = placements[subject.name]
            placement.container_id = ""
            placement.slot = None
            placement.anchor_id = ""
            placement.region = SemanticRegion.OUTPUT
            show(subject, "success")
            return [subject.name]
        if operation.verb is ExecutionVerb.POINT:
            assert target is not None
            if subject.role is not ExecutionObjectRole.POINTER:
                raise ValueError("point subject must be a pointer")
            target_placement = placements[target.name]
            placement = placements[subject.name]
            placement.anchor_id = target.id
            placement.container_id = target_placement.container_id
            placement.slot = target_placement.slot
            placement.region = target_placement.region
            show(subject)
            show(target)
            return [subject.name, target.name]
        if operation.verb is ExecutionVerb.UPDATE:
            placements[subject.name].value = operation.value
            show(subject)
            return [subject.name]
        if operation.verb in {ExecutionVerb.CONNECT, ExecutionVerb.DISCONNECT}:
            assert target is not None
            relation = Relation(source_id=subject.id, target_id=target.id)
            if operation.verb is ExecutionVerb.CONNECT:
                if relation in relations:
                    raise ValueError("connect relation already exists")
                relations.append(relation)
                show(subject)
                show(target)
            else:
                if relation not in relations:
                    raise ValueError("disconnect relation does not exist")
                relations.remove(relation)
                show(subject)
                show(target)
            return [subject.name, target.name]
        if operation.verb is ExecutionVerb.COMPARE:
            assert target is not None
            show(subject)
            show(target, "warning")
            return [subject.name, target.name]
        if operation.verb is ExecutionVerb.HIGHLIGHT:
            show(subject)
            return [subject.name]
        raise ValueError(f"unsupported execution verb: {operation.verb}")

    @staticmethod
    def _place(
        subject: ExecutionObject,
        target: ExecutionObject,
        slot: int,
        object_by_name: dict[str, ExecutionObject],
        placements: dict[str, EntityPlacement],
    ) -> None:
        if target.role is not ExecutionObjectRole.CONTAINER:
            raise ValueError("place target must be a container")
        # Stateless containers (capacity=0) do not track slots;
        # accept the placement without capacity or occupancy checks.
        if target.capacity and target.capacity > 0:
            if slot >= target.capacity:
                raise ValueError("place slot exceeds container capacity")
            occupied = next(
                (
                    name for name, placement in placements.items()
                    if name != subject.name
                    and placement.container_id == target.id
                    and placement.slot == slot
                    and placement.visible
                ),
                None,
            )
            if occupied is not None:
                raise ValueError(f"container slot is occupied by {occupied}")
        placement = placements[subject.name]
        placement.container_id = target.id
        placement.slot = slot
        placement.anchor_id = ""
        placement.region = SemanticRegion.MAIN
        placement.visible = True
        placement.status = "active"

    @staticmethod
    def _state(
        scene_id: str,
        number: int,
        placements: dict[str, EntityPlacement],
        relations: list[Relation],
    ) -> VisualState:
        return VisualState(
            id=f"{scene_id}-state-{number:02d}",
            placements=[item.model_copy(deep=True) for item in placements.values()],
            relations=[item.model_copy(deep=True) for item in relations],
        )

    @staticmethod
    def _state_changed(before: VisualState, after: VisualState) -> bool:
        return before.model_dump(mode="json", exclude={"id"}) != after.model_dump(
            mode="json", exclude={"id"}
        )

    @staticmethod
    def _caption(operation: ExecutionOperation) -> str:
        parts = [operation.subject]
        if operation.target:
            parts.append(operation.target)
        if operation.slot is not None:
            parts.append(f"槽位 {operation.slot}")
        if operation.value:
            parts.append(operation.value)
        return f"{operation.verb.value}({', '.join(parts)})"
