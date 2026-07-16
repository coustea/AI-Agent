"""Plan a lesson as semantic entities, state transitions and teaching beats."""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

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
    title: str = Field(min_length=1, max_length=54)
    teaching_goal: str = Field(min_length=1, max_length=100)
    grammar: VisualGrammar


class _StoryboardDraft(_Draft):
    title: str = Field(min_length=1, max_length=72)
    course: str = Field(default="计算机类本科课程", min_length=1, max_length=40)
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
    detail: str = Field(default="", max_length=72)
    initial_value: str = Field(default="", max_length=200)
    orientation: str = Field(default="vertical", pattern=r"^(vertical|horizontal|radial)$")
    tone: str = Field(default="primary", pattern=r"^(primary|secondary|accent|warning)$")


class _PlacementDraft(_Draft):
    entity_index: int = Field(ge=0, le=8)
    container_index: int | None = Field(default=None, ge=0, le=8)
    slot: int | None = Field(default=None, ge=0, le=15)
    region: SemanticRegion = SemanticRegion.MAIN
    visible: bool = True
    value: str = Field(default="", max_length=200)
    status: str = Field(default="idle", pattern=r"^(idle|active|success|warning|error)$")

    @model_validator(mode="after")
    def validate_slot(self) -> "_PlacementDraft":
        if self.slot is not None and self.container_index is None:
            raise ValueError("slot requires container_index")
        if self.container_index == self.entity_index:
            raise ValueError("entity cannot be placed inside itself")
        return self


class _RelationDraft(_Draft):
    source_index: int = Field(ge=0, le=8)
    target_index: int = Field(ge=0, le=8)
    label: str = Field(default="", max_length=30)
    directed: bool = True
    tone: str = Field(default="primary", pattern=r"^(primary|secondary|accent|warning)$")


class _StateDraft(_Draft):
    label: str = Field(min_length=1, max_length=42)
    annotation: str = Field(default="", max_length=72)
    placements: list[_PlacementDraft] = Field(min_length=2, max_length=9)
    relations: list[_RelationDraft] = Field(default_factory=list, max_length=18)


class _TransitionDraft(_Draft):
    kind: TransitionKind
    entity_indexes: list[int] = Field(min_length=1, max_length=6)
    relation_label: str = Field(default="", max_length=30)


class _BeatDraft(_Draft):
    claim: str = Field(min_length=1, max_length=72)
    narration: str = Field(min_length=16, max_length=60)
    caption: str = Field(min_length=1, max_length=30)
    before_state_index: int = Field(ge=0, le=4)
    after_state_index: int = Field(ge=1, le=5)
    transition: _TransitionDraft
    focus_entity_indexes: list[int] = Field(min_length=1, max_length=6)


class _SceneDraft(_Draft):
    entities: list[_EntityDraft] = Field(min_length=2, max_length=9)
    states: list[_StateDraft] = Field(min_length=4, max_length=5)
    beats: list[_BeatDraft] = Field(min_length=3, max_length=4)

    @model_validator(mode="after")
    def validate_references(self) -> "_SceneDraft":
        entity_count = len(self.entities)
        expected_indexes = set(range(entity_count))
        container_indexes = {
            index for index, entity in enumerate(self.entities)
            if entity.kind == EntityKind.CONTAINER
        }
        for state in self.states:
            placement_indexes = [item.entity_index for item in state.placements]
            if set(placement_indexes) != expected_indexes or len(placement_indexes) != entity_count:
                raise ValueError("every state must place every entity exactly once")
            for placement in state.placements:
                if placement.container_index is not None and placement.container_index not in container_indexes:
                    raise ValueError("container_index must reference a container entity")
            for relation in state.relations:
                if relation.source_index >= entity_count or relation.target_index >= entity_count:
                    raise ValueError("relation references an entity outside entities")
                if relation.source_index == relation.target_index:
                    raise ValueError("relation cannot point to the same entity")

        if len(self.states) != len(self.beats) + 1:
            raise ValueError("scene requires one initial state plus one result state per beat")
        for index, beat in enumerate(self.beats):
            if (beat.before_state_index, beat.after_state_index) != (index, index + 1):
                raise ValueError("beats must form a sequential before/after state chain")
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
                course=storyboard.course,
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
                "state_count": profile.beats_per_scene + 1,
                "entity_limit": profile.entity_limit,
                "density": brief.configuration.visual_density,
            }
        )
        context = {
            "lesson_title": storyboard.title,
            "course": storyboard.course,
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
                max_tokens=8_192,
            )
        draft = response if isinstance(response, _SceneDraft) else _SceneDraft.model_validate(response)
        if len(draft.entities) > profile.entity_limit:
            raise CartoonPlanningError(f"scene exceeds entity limit {profile.entity_limit}")
        if len(draft.beats) != profile.beats_per_scene:
            raise CartoonPlanningError(f"scene requires exactly {profile.beats_per_scene} beats")
        draft = self._repair_grammar_entities(outline.grammar, draft)
        draft = self._repair_container_references(draft)
        return self._materialize_scene(outline, draft, scene_index)

    @staticmethod
    def _repair_grammar_entities(grammar: VisualGrammar, draft: _SceneDraft) -> _SceneDraft:
        """Auto-fix entity kinds so the draft satisfies grammar constraints.

        When the LLM omits required entity kinds for a grammar, promote the
        least-structural entities (those not referenced as containers by any
        placement) to the required kind.  This is a best-effort repair; if
        the draft is fundamentally incompatible the downstream
        ``TeachingScene`` validator will still reject it.
        """
        kinds = [entity.kind for entity in draft.entities]
        container_indexes = {
            index for index, entity in enumerate(draft.entities)
            if entity.kind == EntityKind.CONTAINER
        }
        # Collect indexes of entities that are not structural (not containers
        # and not referenced as containers by placements).
        structural = container_indexes.copy()
        for state in draft.states:
            for placement in state.placements:
                if placement.container_index is not None:
                    structural.add(placement.container_index)
        non_structural = [
            i for i in range(len(draft.entities)) if i not in structural
        ]

        def _promote(target_kind: EntityKind, count: int) -> None:
            """Promote up to *count* non-structural entities to *target_kind*."""
            promoted = 0
            for idx in non_structural:
                if promoted >= count:
                    break
                if draft.entities[idx].kind != target_kind:
                    draft.entities[idx] = draft.entities[idx].model_copy(
                        update={"kind": target_kind}
                    )
                    promoted += 1

        if grammar == VisualGrammar.CONCEPT and kinds.count(EntityKind.TERM) < 2:
            _promote(EntityKind.TERM, 2 - kinds.count(EntityKind.TERM))

        elif grammar == VisualGrammar.MODEL:
            if EntityKind.CONTAINER not in kinds:
                _promote(EntityKind.CONTAINER, 1)
            # Re-read kinds after possible container promotion
            kinds = [entity.kind for entity in draft.entities]
            if not {EntityKind.SLOT, EntityKind.POINTER, EntityKind.PORT} & set(kinds):
                _promote(EntityKind.SLOT, 1)

        elif grammar == VisualGrammar.TRACE:
            if EntityKind.CONTAINER not in kinds:
                _promote(EntityKind.CONTAINER, 1)
            kinds = [entity.kind for entity in draft.entities]
            if EntityKind.TOKEN not in kinds:
                _promote(EntityKind.TOKEN, 1)

        elif grammar == VisualGrammar.EVIDENCE:
            if EntityKind.CODE not in kinds and kinds.count(EntityKind.METRIC) < 2:
                _promote(EntityKind.CODE, 1)

        return draft

    @staticmethod
    def _repair_container_references(draft: _SceneDraft) -> _SceneDraft:
        """Auto-fix container_index values that reference non-container entities.

        When the LLM sets container_index to an entity whose kind is not
        CONTAINER, redirect it to the first actual container (or clear it if
        no container exists).
        """
        container_indexes = [
            i for i, entity in enumerate(draft.entities)
            if entity.kind == EntityKind.CONTAINER
        ]
        if not container_indexes:
            # No containers at all — strip all container_index and slot values
            for state in draft.states:
                for pi, placement in enumerate(state.placements):
                    if placement.container_index is not None:
                        state.placements[pi] = placement.model_copy(
                            update={"container_index": None, "slot": None}
                        )
            return draft

        first_container = container_indexes[0]
        for state in draft.states:
            for pi, placement in enumerate(state.placements):
                if (
                    placement.container_index is not None
                    and placement.container_index not in container_indexes
                ):
                    state.placements[pi] = placement.model_copy(
                        update={"container_index": first_container}
                    )
        return draft

    @staticmethod
    def _materialize_scene(
        outline: _StoryboardSceneDraft,
        draft: _SceneDraft,
        scene_index: int,
    ) -> TeachingScene:
        scene_id = f"scene-{scene_index:02d}"
        entity_ids = [
            f"{scene_id}-entity-{index:02d}"
            for index in range(1, len(draft.entities) + 1)
        ]
        state_ids = [
            f"{scene_id}-state-{index:02d}"
            for index in range(1, len(draft.states) + 1)
        ]
        entities = [
            VisualEntity(id=entity_id, **entity.model_dump(mode="python"))
            for entity_id, entity in zip(entity_ids, draft.entities, strict=True)
        ]
        states = [
            VisualState(
                id=state_id,
                label=state.label,
                annotation=state.annotation,
                placements=[
                    EntityPlacement(
                        entity_id=entity_ids[item.entity_index],
                        container_id=(
                            entity_ids[item.container_index]
                            if item.container_index is not None
                            else ""
                        ),
                        slot=item.slot,
                        region=item.region,
                        visible=item.visible,
                        value=item.value,
                        status=item.status,
                    )
                    for item in state.placements
                ],
                relations=[
                    Relation(
                        source_id=entity_ids[item.source_index],
                        target_id=entity_ids[item.target_index],
                        label=item.label,
                        directed=item.directed,
                        tone=item.tone,
                    )
                    for item in state.relations
                ],
            )
            for state_id, state in zip(state_ids, draft.states, strict=True)
        ]
        beats = [
            TeachingBeat(
                id=f"{scene_id}-beat-{index:02d}",
                claim=beat.claim,
                narration=beat.narration,
                caption=beat.caption,
                before_state_id=state_ids[beat.before_state_index],
                after_state_id=state_ids[beat.after_state_index],
                transition=Transition(
                    kind=beat.transition.kind,
                    entity_ids=[entity_ids[value] for value in beat.transition.entity_indexes],
                    relation_label=beat.transition.relation_label,
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

    async def _invoke(
        self,
        schema: type[BaseModel],
        messages: list[SystemMessage | HumanMessage],
        *,
        temperature: float,
        max_tokens: int,
    ) -> Any:
        return await get_llm().ainvoke_json(
            schema,
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
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
