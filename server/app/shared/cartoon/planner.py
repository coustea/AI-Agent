"""Plan a lesson as semantic entities, state transitions and teaching beats."""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.shared.cartoon.models import (
    CartoonBrief,
    EntityKind,
    EntityPlacement,
    Lesson,
    LessonDepth,
    Relation,
    SemanticRegion,
    TeachingBeat,
    TeachingScene,
    Transition,
    TransitionKind,
    VisualEntity,
    VisualGrammar,
    VisualState,
)


logger = get_logger(__name__)
_PROMPT_VARIABLE = re.compile(r"\{\{(?P<name>[a-z_][a-z0-9_]*)\}\}")
_PROMPT_DIR = Path(__file__).parent


class CartoonPlanningError(RuntimeError):
    pass


@dataclass(frozen=True)
class _Profile:
    scene_count: int
    beats_per_scene: int
    entity_limit: int
    label: str


def _profile(brief: CartoonBrief) -> _Profile:
    density_limit = {
        "moderate": 5,
        "rich": 7,
        "intensive": 9,
    }[brief.configuration.visual_density]
    return {
        LessonDepth.FOCUSED: _Profile(5, 3, density_limit, "聚焦讲解"),
        LessonDepth.STANDARD: _Profile(5, 3, density_limit, "标准讲解"),
        LessonDepth.DEEP: _Profile(6, 4, density_limit, "深入讲解"),
    }[brief.configuration.lesson_depth]


@dataclass(frozen=True)
class _PromptDocument:
    name: str
    content: str
    variables: frozenset[str]

    @classmethod
    def load(cls, path: Path) -> "_PromptDocument":
        content = path.read_text(encoding="utf-8")
        variables = frozenset(match.group("name") for match in _PROMPT_VARIABLE.finditer(content))
        remaining = _PROMPT_VARIABLE.sub("", content)
        if "{{" in remaining or "}}" in remaining:
            raise CartoonPlanningError(f"提示词 {path.name} 包含未闭合变量")
        return cls(path.name, content, variables)

    def render(self, values: Mapping[str, object]) -> str:
        provided = frozenset(values)
        if provided != self.variables:
            raise CartoonPlanningError(
                f"提示词 {self.name} 变量不一致: "
                f"missing={sorted(self.variables - provided)} "
                f"unexpected={sorted(provided - self.variables)}"
            )
        return _PROMPT_VARIABLE.sub(lambda match: str(values[match.group("name")]), self.content)


class _Draft(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _StoryboardSceneDraft(_Draft):
    title: str = Field(min_length=1, max_length=28)
    teaching_goal: str = Field(min_length=1, max_length=100)
    grammar: VisualGrammar


class _StoryboardDraft(_Draft):
    title: str = Field(min_length=1, max_length=72)
    scenes: list[_StoryboardSceneDraft] = Field(min_length=5, max_length=6)

    @model_validator(mode="after")
    def validate_arc(self) -> "_StoryboardDraft":
        grammars = {scene.grammar for scene in self.scenes}
        required = {VisualGrammar.CONCEPT, VisualGrammar.MODEL, VisualGrammar.TRACE, VisualGrammar.EVIDENCE}
        if not required <= grammars:
            raise ValueError("storyboard must use concept, model, trace, and evidence grammars")
        if self.scenes[0].grammar != VisualGrammar.CONCEPT:
            raise ValueError("storyboard must begin with a concept scene")
        if self.scenes[-1].grammar not in {VisualGrammar.CONCEPT, VisualGrammar.MODEL}:
            raise ValueError("storyboard must end with concept or model consolidation")
        return self


class _EntityDraft(_Draft):
    label: str = Field(min_length=1, max_length=28)
    kind: EntityKind


class _TransitionDraft(_Draft):
    kind: TransitionKind
    entity_indexes: list[int] = Field(min_length=1, max_length=6)

    @field_validator("entity_indexes")
    @classmethod
    def unique_entity_indexes(cls, values: list[int]) -> list[int]:
        if len(values) != len(set(values)):
            raise ValueError("transition entity indexes must be unique")
        return values


class _BeatDraft(_Draft):
    narration: str = Field(min_length=16, max_length=40)
    caption: str = Field(min_length=1, max_length=30)
    transition: _TransitionDraft
    focus_entity_indexes: list[int] = Field(min_length=1, max_length=6)

    @field_validator("focus_entity_indexes")
    @classmethod
    def unique_focus_entity_indexes(cls, values: list[int]) -> list[int]:
        if len(values) != len(set(values)):
            raise ValueError("focus entity indexes must be unique")
        return values


class _SceneDraft(_Draft):
    entities: list[_EntityDraft] = Field(min_length=2, max_length=9)
    beats: list[_BeatDraft] = Field(min_length=3, max_length=4)

    @model_validator(mode="after")
    def validate_references(self) -> "_SceneDraft":
        entity_count = len(self.entities)
        for beat in self.beats:
            references = set(beat.transition.entity_indexes) | set(beat.focus_entity_indexes)
            if any(value < 0 or value >= entity_count for value in references):
                raise ValueError("beat references an entity outside entities")
        return self


class CartoonPlanner:
    """Generate one validated lesson while keeping renderer details private."""

    def __init__(self, *, max_parallel_scenes: int = 3) -> None:
        self._parallelism = max(1, max_parallel_scenes)
        self._prompts = {
            name: _PromptDocument.load(_PROMPT_DIR / name)
            for name in ("storyboard.md", "scene_compose.md")
        }

    def prompt_variables(self, name: str) -> frozenset[str]:
        return self._prompts[name].variables

    async def plan(self, brief: CartoonBrief) -> Lesson:
        try:
            storyboard = await self._create_storyboard(brief)
            profile = _profile(brief)
            semaphore = asyncio.Semaphore(self._parallelism)
            async with asyncio.TaskGroup() as group:
                tasks = [
                    group.create_task(
                        self._compose_scene(
                            brief,
                            storyboard,
                            scene,
                            scene_index,
                            profile,
                            semaphore,
                        )
                    )
                    for scene_index, scene in enumerate(storyboard.scenes, start=1)
                ]
            return Lesson(
                title=storyboard.title,
                scenes=[task.result() for task in tasks],
            )
        except Exception as exc:
            if isinstance(exc, CartoonPlanningError):
                raise
            details = self._exception_details(exc)
            raise CartoonPlanningError("无法生成可渲染的语义动画分镜: " + " | ".join(details)) from exc

    async def _create_storyboard(self, brief: CartoonBrief) -> _StoryboardDraft:
        profile = _profile(brief)
        prompt = self._prompts["storyboard.md"].render(
            {
                "scene_count": profile.scene_count,
                "lesson_depth": profile.label,
                "density": brief.configuration.visual_density,
            }
        )
        response = await self._invoke(
            _StoryboardDraft,
            [
                SystemMessage(content=prompt),
                self._material_message(
                    brief,
                    task="规划整套动画的教学推进顺序",
                    limit=8_000,
                ),
            ],
            temperature=0.1,
            max_tokens=2_200,
        )
        storyboard = response if isinstance(response, _StoryboardDraft) else _StoryboardDraft.model_validate(response)
        if len(storyboard.scenes) != profile.scene_count:
            raise CartoonPlanningError(f"storyboard requires exactly {profile.scene_count} scenes")
        return storyboard

    async def _compose_scene(
        self,
        brief: CartoonBrief,
        storyboard: _StoryboardDraft,
        outline: _StoryboardSceneDraft,
        scene_index: int,
        profile: _Profile,
        semaphore: asyncio.Semaphore,
    ) -> TeachingScene:
        prompt = self._prompts["scene_compose.md"].render(
            {
                "grammar": outline.grammar.value,
                "beat_count": profile.beats_per_scene,
                "entity_limit": profile.entity_limit,
                "density": brief.configuration.visual_density,
            }
        )
        context = {
            "lesson_title": storyboard.title,
            "scene_title": outline.title,
            "teaching_goal": outline.teaching_goal,
            "grammar": outline.grammar.value,
        }
        async with semaphore:
            response = await self._invoke(
                _SceneDraft,
                [
                    SystemMessage(content=prompt),
                    self._material_message(
                        brief,
                        task="只生成当前场景的实体、状态和教学节拍",
                        limit=5_000,
                        context=context,
                    ),
                ],
                temperature=0.12,
                max_tokens=2_800,
                validator=lambda value: self._validate_scene_draft(
                    value,
                    grammar=outline.grammar,
                    profile=profile,
                ),
            )
        draft = response if isinstance(response, _SceneDraft) else _SceneDraft.model_validate(response)
        self._validate_scene_draft(draft, grammar=outline.grammar, profile=profile)
        return self._materialize_scene(outline, draft, scene_index)

    @staticmethod
    def _validate_scene_draft(
        value: BaseModel,
        *,
        grammar: VisualGrammar,
        profile: _Profile,
    ) -> None:
        if not isinstance(value, _SceneDraft):
            raise ValueError("scene payload must validate as _SceneDraft")
        if len(value.entities) > profile.entity_limit:
            raise ValueError(f"scene exceeds entity limit {profile.entity_limit}")
        if len(value.beats) != profile.beats_per_scene:
            raise ValueError(f"scene requires exactly {profile.beats_per_scene} beats")

        kinds = [entity.kind for entity in value.entities]
        if grammar is VisualGrammar.CONCEPT and kinds.count(EntityKind.TERM) < 2:
            raise ValueError("concept grammar requires at least two term entities")
        if grammar is VisualGrammar.MODEL and (
            EntityKind.CONTAINER not in kinds
            or not {EntityKind.SLOT, EntityKind.POINTER, EntityKind.PORT} & set(kinds)
        ):
            raise ValueError("model grammar requires a container and a slot, pointer, or port")
        if grammar is VisualGrammar.TRACE and (
            EntityKind.CONTAINER not in kinds or EntityKind.TOKEN not in kinds
        ):
            raise ValueError("trace grammar requires a container and token entity")
        if grammar is VisualGrammar.EVIDENCE and not (
            EntityKind.CODE in kinds or kinds.count(EntityKind.METRIC) >= 2
        ):
            raise ValueError("evidence grammar requires code or at least two metric entities")
        if grammar is VisualGrammar.TRACE and not any(
            beat.transition.kind
            in {
                TransitionKind.MOVE,
                TransitionKind.INSERT,
                TransitionKind.REMOVE,
                TransitionKind.UPDATE,
                TransitionKind.EXECUTE,
            }
            for beat in value.beats
        ):
            raise ValueError("trace grammar requires an operational transition")

    @classmethod
    def _materialize_scene(
        cls,
        outline: _StoryboardSceneDraft,
        draft: _SceneDraft,
        scene_index: int,
    ) -> TeachingScene:
        scene_id = f"scene-{scene_index:02d}"
        entity_ids = [
            f"{scene_id}-entity-{index:02d}"
            for index in range(1, len(draft.entities) + 1)
        ]
        entities = [
            VisualEntity(id=entity_id, **entity.model_dump(mode="python"))
            for entity_id, entity in zip(entity_ids, draft.entities, strict=True)
        ]
        states = cls._compile_states(scene_id, entities, draft.beats)
        beats = [
            TeachingBeat(
                id=f"{scene_id}-beat-{index:02d}",
                narration=beat.narration,
                caption=beat.caption,
                before_state_id=states[index - 1].id,
                after_state_id=states[index].id,
                transition=Transition(
                    kind=beat.transition.kind,
                    entity_ids=[entity_ids[value] for value in beat.transition.entity_indexes],
                ),
                focus_entity_ids=[entity_ids[value] for value in beat.focus_entity_indexes],
            )
            for index, beat in enumerate(draft.beats, start=1)
        ]
        return TeachingScene(
            id=scene_id,
            title=outline.title,
            grammar=outline.grammar,
            entities=entities,
            states=states,
            beats=beats,
        )

    @classmethod
    def _compile_states(
        cls,
        scene_id: str,
        entities: list[VisualEntity],
        beats: list[_BeatDraft],
    ) -> list[VisualState]:
        container_id = next(
            (entity.id for entity in entities if entity.kind is EntityKind.CONTAINER),
            "",
        )
        regions = (
            SemanticRegion.LEFT,
            SemanticRegion.RIGHT,
            SemanticRegion.TOP,
            SemanticRegion.BOTTOM,
            SemanticRegion.INPUT,
            SemanticRegion.OUTPUT,
            SemanticRegion.RESULT,
            SemanticRegion.CODE,
        )
        placements = [
            EntityPlacement(
                entity_id=entity.id,
                container_id=(container_id if container_id and entity.id != container_id else ""),
                slot=(index if container_id and entity.id != container_id else None),
                region=(SemanticRegion.MAIN if entity.id == container_id else regions[index % len(regions)]),
                visible=(entity.id == container_id or index == 0),
                status=("active" if entity.id == container_id or index == 0 else "idle"),
            )
            for index, entity in enumerate(entities)
        ]
        states = [
            VisualState(
                id=f"{scene_id}-state-01",
                placements=placements,
                relations=[],
            )
        ]
        for index, beat in enumerate(beats, start=1):
            states.append(
                cls._advance_state(
                    state=states[-1],
                    state_id=f"{scene_id}-state-{index + 1:02d}",
                    entity_ids=[entity.id for entity in entities],
                    container_id=container_id,
                    beat=beat,
                    step=index,
                )
            )
        return states

    @staticmethod
    def _advance_state(
        *,
        state: VisualState,
        state_id: str,
        entity_ids: list[str],
        container_id: str,
        beat: _BeatDraft,
        step: int,
    ) -> VisualState:
        placements = [item.model_copy(deep=True) for item in state.placements]
        relations = [item.model_copy(deep=True) for item in state.relations]
        by_id = {item.entity_id: item for item in placements}
        targets = [entity_ids[index] for index in beat.transition.entity_indexes]
        changed = False

        def mark_value(entity_id: str, status: str = "active") -> None:
            nonlocal changed
            placement = by_id[entity_id]
            value = f"{beat.caption} {step}"[:200]
            if placement.value != value or placement.status != status:
                placement.value = value
                placement.status = status
                changed = True

        if beat.transition.kind is TransitionKind.REVEAL:
            for entity_id in targets:
                placement = by_id[entity_id]
                if not placement.visible or placement.status != "active":
                    placement.visible = True
                    placement.status = "active"
                    changed = True
        elif beat.transition.kind is TransitionKind.MOVE:
            regions = list(SemanticRegion)
            for entity_id in targets:
                placement = by_id[entity_id]
                if placement.container_id:
                    placement.slot = ((placement.slot or 0) + 1) % 16
                else:
                    placement.region = regions[(regions.index(placement.region) + 1) % len(regions)]
                placement.visible = True
                placement.status = "active"
                changed = True
        elif beat.transition.kind is TransitionKind.INSERT:
            for entity_id in targets:
                placement = by_id[entity_id]
                if container_id and entity_id != container_id:
                    previous = (placement.container_id, placement.slot, placement.visible, placement.status)
                    placement.container_id = container_id
                    placement.slot = ((placement.slot or 0) + 1) % 16
                    placement.visible = True
                    placement.status = "active"
                    if previous != (
                        placement.container_id,
                        placement.slot,
                        placement.visible,
                        placement.status,
                    ):
                        changed = True
                else:
                    mark_value(entity_id)
        elif beat.transition.kind is TransitionKind.REMOVE:
            for entity_id in targets:
                placement = by_id[entity_id]
                if placement.visible or placement.status != "warning":
                    placement.visible = False
                    placement.status = "warning"
                    changed = True
        elif beat.transition.kind is TransitionKind.CONNECT:
            source_id = targets[0]
            target_id = next((value for value in targets[1:] if value != source_id), None)
            if target_id is None:
                target_id = next(value for value in entity_ids if value != source_id)
            relation = Relation(source_id=source_id, target_id=target_id, label=beat.caption)
            if relation not in relations:
                relations.append(relation)
                changed = True
        elif beat.transition.kind is TransitionKind.DISCONNECT:
            target_set = set(targets)
            for index, relation in enumerate(relations):
                if relation.source_id in target_set or relation.target_id in target_set:
                    relations.pop(index)
                    changed = True
                    break
        else:
            for entity_id in targets:
                mark_value(
                    entity_id,
                    status="success" if beat.transition.kind is TransitionKind.EXECUTE else "active",
                )

        if not changed:
            mark_value(targets[0], status="success")
        return VisualState(id=state_id, placements=placements, relations=relations)

    async def _invoke(
        self,
        schema: type[BaseModel],
        messages: list[SystemMessage | HumanMessage],
        *,
        temperature: float,
        max_tokens: int,
        validator: Callable[[BaseModel], None] | None = None,
    ) -> Any:
        return await get_llm().ainvoke_json(
            schema,
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            validator=validator,
        )

    @classmethod
    def _material_message(
        cls,
        brief: CartoonBrief,
        *,
        task: str,
        limit: int,
        context: dict[str, object] | None = None,
    ) -> HumanMessage:
        payload = {
            "task": task,
            "context": context or {},
            "teaching_material": cls._source(brief, limit),
        }
        return HumanMessage(
            content=json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        )

    @staticmethod
    def _source(brief: CartoonBrief, limit: int) -> str:
        sections = [
            f"学习主题：{brief.learning_need}",
            "教学上下文：" + json.dumps(brief.instruction_context, ensure_ascii=False),
            "知识点：" + "、".join(brief.knowledge_points),
            "薄弱点：" + "、".join(brief.weak_knowledge_points),
            *brief.source_materials,
        ]
        output: list[str] = []
        remaining = limit
        for section in sections:
            normalized = str(section).strip()
            if not normalized or remaining <= 0:
                continue
            value = normalized[:remaining]
            output.append(value)
            remaining -= len(value) + 2
        return "\n\n".join(output)

    @classmethod
    def _exception_details(cls, exc: BaseException) -> list[str]:
        if isinstance(exc, BaseExceptionGroup):
            details = [detail for nested in exc.exceptions for detail in cls._exception_details(nested)]
            return details[:8]
        return [f"{type(exc).__name__}: {str(exc).strip() or type(exc).__name__}"]
