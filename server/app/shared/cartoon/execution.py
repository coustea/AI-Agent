"""Compile model-authored semantic steps into canonical replayable scenes."""

from __future__ import annotations

import re
from typing import Any, get_args

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.infra.logging import get_logger
from app.shared.cartoon.models import (
    ObjectPlacement,
    PlacementStatus,
    SceneMode,
    SceneProgram,
    SceneRelation,
    SceneState,
    SceneTopology,
    SemanticAction,
    SemanticActionVerb,
    SemanticObject,
    SemanticObjectRole,
    SemanticRegion,
    TeachingBeat,
    TeachingScene,
)


logger = get_logger(__name__)


_PLACEMENT_STATUSES = frozenset(get_args(PlacementStatus))
_STATUS_ALIASES = {
    "pending": "active",
    "processing": "active",
    "running": "active",
    "blocked": "warning",
    "failed": "error",
    "failure": "error",
    "done": "success",
    "complete": "success",
    "completed": "success",
}


def _normalize_status(value: Any) -> str:
    """Map model wording to the renderer's finite visual status vocabulary."""

    normalized = str(value or "").strip().lower()
    if not normalized:
        return ""
    if normalized in _PLACEMENT_STATUSES:
        return normalized
    return _STATUS_ALIASES.get(normalized, "")


class _Draft(BaseModel):
    model_config = ConfigDict(extra="ignore")


class SemanticObjectDraft(_Draft):
    """Model-authored object description without renderer-owned identity."""

    name: str = ""
    label: str = ""
    role: SemanticObjectRole | str = SemanticObjectRole.NODE
    value: str = ""
    capacity: int | None = None

    @field_validator("value", mode="before")
    @classmethod
    def coerce_value_to_str(cls, value: Any) -> str:
        return "" if value is None else str(value).strip()

    @field_validator("name", "label", mode="before")
    @classmethod
    def normalize_text(cls, value: Any) -> str:
        return str(value or "").strip()


class SemanticActionDraft(_Draft):
    """One model-authored action over object names, never canonical IDs."""

    verb: SemanticActionVerb | str = SemanticActionVerb.REVEAL
    subject: str = ""
    target: str = ""
    slot: int | None = None
    region: SemanticRegion | str | None = None
    value: str = ""
    state: str = ""

    @field_validator("value", mode="before")
    @classmethod
    def coerce_value_to_str(cls, value: Any) -> str:
        return "" if value is None else str(value).strip()

    @field_validator("subject", "target", mode="before")
    @classmethod
    def normalize_names(cls, value: Any) -> str:
        return str(value or "").strip()

    @field_validator("slot", mode="before")
    @classmethod
    def coerce_slot(cls, value: Any) -> int | None:
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @field_validator("state", mode="before")
    @classmethod
    def coerce_state(cls, value: Any) -> str:
        return _normalize_status(value)


class SemanticStepDraft(_Draft):
    narration: str = ""
    actions: list[SemanticActionDraft] = Field(default_factory=list)

    @field_validator("narration", mode="before")
    @classmethod
    def normalize_narration(cls, value: Any) -> str:
        normalized = str(value or "").strip()
        return normalized

    @field_validator("actions", mode="before")
    @classmethod
    def normalize_actions(cls, value: Any) -> Any:
        if value is None:
            return []
        return [value] if isinstance(value, dict) else value


class SemanticSceneDraft(_Draft):
    mode: SceneMode | str = SceneMode.CONCEPT
    topology: SceneTopology | str = SceneTopology.SPATIAL
    objects: list[SemanticObjectDraft] = Field(default_factory=list)
    steps: list[SemanticStepDraft] = Field(default_factory=list)

    @field_validator("objects", "steps", mode="before")
    @classmethod
    def normalize_collections(cls, value: Any) -> Any:
        if value is None:
            return []
        return [value] if isinstance(value, dict) else value

class SemanticCompiler:
    """Deterministically replay semantic actions into one canonical scene program."""

    @classmethod
    def compile(
        cls,
        draft: SemanticSceneDraft,
        *,
        scene_id: str,
        title: str,
    ) -> TeachingScene:
        prefix = cls._canonical_prefix(scene_id)
        objects: list[SemanticObject] = []
        aliases: dict[str, str] = {}
        used_names: set[str] = set()
        for index, item in enumerate(draft.objects, start=1):
            base_name = item.name.strip() or f"object-{index}"
            name = base_name
            suffix = 2
            while name in used_names:
                name = f"{base_name}-{suffix}"
                suffix += 1
            used_names.add(name)
            aliases.setdefault(base_name, name)
            try:
                role = SemanticObjectRole(item.role)
            except ValueError:
                role = SemanticObjectRole.NODE
            objects.append(
                SemanticObject(
                    id=f"{prefix}-object-{index:02d}",
                    name=name,
                    label=item.label.strip() or name,
                    role=role,
                    value=item.value,
                    capacity=max(0, item.capacity or 0) if role is SemanticObjectRole.CONTAINER else None,
                )
            )
        if not objects:
            # Keep a malformed-but-parseable empty scene renderable.
            objects.append(
                SemanticObject(
                    id=f"{prefix}-object-01",
                    name="subject",
                    label="Subject",
                    role=SemanticObjectRole.NODE,
                )
            )
            aliases["subject"] = "subject"
        object_by_name = {item.name: item for item in objects}
        fallback_name = objects[0].name
        placement_by_name = {
            item.name: cls._initial_placement(item)
            for item in objects
        }
        relations: list[SceneRelation] = []
        relation_ids: dict[tuple[str, str], str] = {}
        states = [cls._state(prefix, 0, placement_by_name, relations)]
        beats: list[TeachingBeat] = []

        logger.info(
            "[SemanticCompiler] 编译语义场景: scene_id=%s objects=%d steps=%d",
            scene_id,
            len(objects),
            len(draft.steps),
        )
        steps = draft.steps or [SemanticStepDraft(narration="继续演示当前主题。")]
        for step_index, step in enumerate(steps, start=1):
            before_step = states[-1]
            actions: list[SemanticAction] = []
            action_state_ids: list[str] = []
            action_drafts = step.actions or [
                SemanticActionDraft(verb=SemanticActionVerb.REVEAL, subject=fallback_name)
            ]
            for action_draft in action_drafts:
                normalized_action = cls._normalize_action(
                    action_draft,
                    aliases=aliases,
                    object_by_name=object_by_name,
                    fallback_name=fallback_name,
                )
                action = cls._action(normalized_action, object_by_name)
                cls._apply(
                    normalized_action,
                    object_by_name=object_by_name,
                    placements=placement_by_name,
                    relations=relations,
                    relation_ids=relation_ids,
                    prefix=prefix,
                )
                cls._validate_runtime(object_by_name, placement_by_name, relations)
                action_state = cls._state(
                    prefix,
                    len(states),
                    placement_by_name,
                    relations,
                )
                states.append(action_state)
                action_state_ids.append(action_state.id)
                actions.append(action)

            after_step = states[-1]
            beat = TeachingBeat(
                id=f"{prefix}-beat-{step_index:02d}",
                narration=step.narration or "继续演示当前状态。",
                before_state_id=before_step.id,
                after_state_id=after_step.id,
                actions=actions,
                action_state_ids=action_state_ids,
            )
            beats.append(beat)

        scene = TeachingScene(
            id=scene_id,
            title=title,
            mode=cls._coerce_mode(draft.mode),
            topology=cls._coerce_topology(draft.topology),
            program=SceneProgram(objects=objects, states=states, beats=beats),
        )
        logger.info(
            "[SemanticCompiler] 编译完成: scene_id=%s states=%d beats=%d",
            scene_id,
            len(states),
            len(beats),
        )
        return scene

    @staticmethod
    def _coerce_mode(value: SceneMode | str) -> SceneMode:
        try:
            return SceneMode(value)
        except (TypeError, ValueError):
            return SceneMode.CONCEPT

    @staticmethod
    def _coerce_topology(value: SceneTopology | str) -> SceneTopology:
        try:
            return SceneTopology(value)
        except (TypeError, ValueError):
            return SceneTopology.SPATIAL

    @staticmethod
    def _normalize_action(
        draft: SemanticActionDraft,
        *,
        aliases: dict[str, str],
        object_by_name: dict[str, SemanticObject],
        fallback_name: str,
    ) -> SemanticActionDraft:
        """Resolve model naming drift without rejecting an otherwise valid JSON payload."""

        subject = aliases.get(draft.subject, draft.subject)
        if subject not in object_by_name:
            subject = fallback_name
        target = aliases.get(draft.target, draft.target) if draft.target else ""
        if target not in object_by_name or target == subject:
            target = ""
        verb_aliases = {
            "point": SemanticActionVerb.MOVE,
            "highlight": SemanticActionVerb.FOCUS,
            "execute": SemanticActionVerb.SETTLE,
            "insert": SemanticActionVerb.PLACE,
        }
        try:
            verb = SemanticActionVerb(draft.verb)
        except ValueError:
            verb = verb_aliases.get(str(draft.verb).lower(), SemanticActionVerb.REVEAL)
        region = draft.region
        try:
            region = SemanticRegion(region) if region is not None else None
        except ValueError:
            region = None
        slot = draft.slot
        if slot is not None:
            slot = max(0, slot)
        return draft.model_copy(
            update={
                "verb": verb,
                "subject": subject,
                "target": target,
                "region": region,
                "slot": slot,
                "state": _normalize_status(draft.state),
            }
        )

    @staticmethod
    def _canonical_prefix(scene_id: str) -> str:
        normalized = re.sub(r"[^a-zA-Z0-9_-]+", "-", scene_id).strip("-_").lower()
        if not normalized or not normalized[0].isalnum():
            normalized = "scene"
        return normalized[:24]

    @staticmethod
    def _initial_placement(item: SemanticObject) -> ObjectPlacement:
        region = SemanticRegion.MAIN
        if item.role is SemanticObjectRole.TOKEN:
            region = SemanticRegion.INPUT
        elif item.role is SemanticObjectRole.POINTER:
            region = SemanticRegion.TOP
        return ObjectPlacement(
            object_id=item.id,
            region=region,
            visible=False,
            value=item.value,
        )

    @staticmethod
    def _action(
        draft: SemanticActionDraft,
        object_by_name: dict[str, SemanticObject],
    ) -> SemanticAction:
        subject = object_by_name[draft.subject]
        target_allowed = draft.verb in {
            SemanticActionVerb.REVEAL,
            SemanticActionVerb.PLACE,
            SemanticActionVerb.MOVE,
            SemanticActionVerb.CONNECT,
            SemanticActionVerb.DISCONNECT,
            SemanticActionVerb.COMPARE,
            SemanticActionVerb.TRAVERSE,
        }
        target_id = object_by_name[draft.target].id if draft.target and target_allowed else ""
        slot = draft.slot if draft.verb in {SemanticActionVerb.PLACE, SemanticActionVerb.MOVE} else None
        if subject.role is SemanticObjectRole.POINTER:
            slot = None
        region = draft.region if draft.verb is SemanticActionVerb.MOVE and not target_id else None
        value = draft.value if draft.verb is SemanticActionVerb.UPDATE else ""
        state = draft.state if draft.verb is SemanticActionVerb.UPDATE and draft.state in {
            "idle", "active", "success", "warning", "error",
        } else ""
        return SemanticAction(
            verb=draft.verb,
            subject_id=subject.id,
            target_id=target_id,
            slot=slot,
            region=region,
            value=value,
            state=state,
        )

    @classmethod
    def _apply(
        cls,
        action: SemanticActionDraft,
        *,
        object_by_name: dict[str, SemanticObject],
        placements: dict[str, ObjectPlacement],
        relations: list[SceneRelation],
        relation_ids: dict[tuple[str, str], str],
        prefix: str,
    ) -> None:
        subject = object_by_name[action.subject]
        target = object_by_name.get(action.target) if action.target else None
        subject_placement = placements[subject.name]

        def show(item: SemanticObject) -> None:
            placement = placements[item.name]
            # A pointer may be introduced before its target is known.  Treat it
            # as a standalone marker until a later move/reveal supplies an
            # anchor; keeping it hidden makes otherwise valid minimal scenes
            # fail the browser visibility gate.
            placement.visible = True

        if action.verb is SemanticActionVerb.REVEAL:
            if subject.role is SemanticObjectRole.POINTER and target is not None:
                cls._move(subject, target, action, placements)
            else:
                show(subject)
            return
        if action.verb is SemanticActionVerb.FOCUS:
            show(subject)
            subject_placement.status = "active"
            return
        if action.verb is SemanticActionVerb.SETTLE:
            show(subject)
            subject_placement.status = "success"
            return
        if action.verb in {SemanticActionVerb.PLACE, SemanticActionVerb.MOVE}:
            cls._move(subject, target, action, placements)
            return
        if action.verb is SemanticActionVerb.REMOVE:
            relations[:] = [
                relation
                for relation in relations
                if subject.id not in {relation.source_id, relation.target_id}
            ]
            if subject.role is SemanticObjectRole.POINTER:
                subject_placement.anchor_id = ""
                subject_placement.container_id = ""
                subject_placement.slot = None
                subject_placement.visible = False
                return
            if subject_placement.container_id or subject_placement.anchor_id:
                subject_placement.container_id = ""
                subject_placement.anchor_id = ""
                subject_placement.slot = None
                subject_placement.region = SemanticRegion.OUTPUT
                subject_placement.visible = True
                return
            subject_placement.visible = False
            return
        if action.verb in {
            SemanticActionVerb.CONNECT,
            SemanticActionVerb.DISCONNECT,
        }:
            if target is None:
                show(subject)
                return
            pair = (subject.id, target.id)
            existing = next(
                (
                    relation
                    for relation in relations
                    if (relation.source_id, relation.target_id) == pair
                ),
                None,
            )
            if action.verb is SemanticActionVerb.CONNECT:
                if existing is not None:
                    show(subject)
                    show(target)
                    return
                relation_id = relation_ids.setdefault(
                    pair,
                    f"{prefix}-relation-{len(relation_ids) + 1:02d}",
                )
                relations.append(
                    SceneRelation(
                        id=relation_id,
                        source_id=subject.id,
                        target_id=target.id,
                    )
                )
                show(subject)
                show(target)
                return
            if existing is None:
                return
            relations.remove(existing)
            return
        if action.verb is SemanticActionVerb.UPDATE:
            show(subject)
            if action.value:
                subject_placement.value = action.value
            if action.state:
                subject_placement.status = action.state
            return
        if action.verb is SemanticActionVerb.COMPARE:
            show(subject)
            subject_placement.status = "active"
            if target is None:
                return
            target_placement = placements[target.name]
            show(target)
            target_placement.status = "warning"
            return
        if action.verb is SemanticActionVerb.TRAVERSE:
            show(subject)
            subject_placement.status = "active"
            if target is None:
                return
            target_placement = placements[target.name]
            show(target)
            target_placement.status = "success"
            return
        raise ValueError(f"unsupported semantic action: {action.verb.value}")

    @classmethod
    def _move(
        cls,
        subject: SemanticObject,
        target: SemanticObject | None,
        action: SemanticActionDraft,
        placements: dict[str, ObjectPlacement],
    ) -> None:
        placement = placements[subject.name]
        if subject.role is SemanticObjectRole.POINTER:
            if target is None or target.role is SemanticObjectRole.POINTER:
                placement.visible = False
                placement.anchor_id = ""
                return
            placement.anchor_id = target.id
            placement.container_id = ""
            placement.slot = None
            placement.region = placements[target.name].region
            placement.visible = True
            placements[target.name].visible = True
            return

        placement.anchor_id = ""
        placement.visible = True
        if target is None:
            placement.container_id = ""
            placement.slot = None
            placement.region = action.region or SemanticRegion.MAIN
            return
        if target.role is not SemanticObjectRole.CONTAINER:
            placement.container_id = ""
            placement.anchor_id = target.id
            placement.slot = None
            placement.region = placements[target.name].region
            target_placement = placements[target.name]
            if target.role is not SemanticObjectRole.POINTER or target_placement.anchor_id:
                target_placement.visible = True
            return
        placements[target.name].visible = True
        used_slots = {
            current.slot
            for name, current in placements.items()
            if name != subject.name
            and current.visible
            and current.container_id == target.id
            and current.slot is not None
        }
        destination_slot = action.slot
        if destination_slot is None and (target.capacity or used_slots):
            destination_slot = next(
                slot for slot in range(len(used_slots) + 1) if slot not in used_slots
            )
        elif destination_slot in used_slots:
            destination_slot = next(
                slot for slot in range(len(used_slots) + 1) if slot not in used_slots
            )
        if destination_slot is not None:
            target.capacity = max(target.capacity or 0, destination_slot + 1)
        placement.container_id = target.id
        placement.slot = destination_slot
        placement.region = SemanticRegion.MAIN

    @staticmethod
    def _validate_runtime(
        object_by_name: dict[str, SemanticObject],
        placements: dict[str, ObjectPlacement],
        relations: list[SceneRelation],
    ) -> None:
        object_by_id = {item.id: item for item in object_by_name.values()}
        placement_by_id = {
            object_by_name[name].id: placement
            for name, placement in placements.items()
        }
        occupied: set[tuple[str, int]] = set()
        for name, placement in placements.items():
            item = object_by_name[name]
            if placement.container_id:
                container = object_by_id.get(placement.container_id)
                if container is None or container.role is not SemanticObjectRole.CONTAINER:
                    raise ValueError("invalid container destination")
                if placement.visible and not placement_by_id[container.id].visible:
                    raise ValueError("visible object has a hidden container destination")
            if placement.visible and placement.slot is not None:
                occupancy = (placement.container_id, placement.slot)
                if occupancy in occupied:
                    raise ValueError("duplicate occupied slot")
                occupied.add(occupancy)
            if item.role is SemanticObjectRole.POINTER and placement.visible:
                target = object_by_id.get(placement.anchor_id)
                if (
                    placement.anchor_id
                    and (
                        target is None
                        or target.role is SemanticObjectRole.POINTER
                        or not placement_by_id[target.id].visible
                    )
                ):
                    raise ValueError("dangling pointer")

        relation_pairs: set[tuple[str, str]] = set()
        for relation in relations:
            pair = (relation.source_id, relation.target_id)
            if pair in relation_pairs:
                raise ValueError("duplicate directed relation")
            relation_pairs.add(pair)
            if set(pair) - object_by_id.keys():
                raise ValueError("relation references an unknown object")

    @staticmethod
    def _state(
        prefix: str,
        number: int,
        placements: dict[str, ObjectPlacement],
        relations: list[SceneRelation],
    ) -> SceneState:
        return SceneState(
            id=f"{prefix}-state-{number:02d}",
            placements=[item.model_copy(deep=True) for item in placements.values()],
            relations=[item.model_copy(deep=True) for item in relations],
        )
