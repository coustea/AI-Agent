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
from app.shared.cartoon.execution import ExecutionCompiler, ExecutionSceneDraft
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
    return {
        LessonDepth.FOCUSED: _Profile(5, 3, 10, "聚焦讲解"),
        LessonDepth.STANDARD: _Profile(5, 3, 10, "标准讲解"),
        LessonDepth.DEEP: _Profile(6, 4, 10, "深入讲解"),
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
    title: str = Field(min_length=1)
    teaching_goal: str = Field(min_length=1)
    grammar: VisualGrammar

    @field_validator("title", "teaching_goal")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("storyboard text cannot be blank")
        return normalized


class _StoryboardDraft(_Draft):
    title: str = Field(min_length=1)
    scenes: list[_StoryboardSceneDraft] = Field(min_length=5, max_length=6)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("storyboard title cannot be blank")
        return normalized

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


class _BeatDraft(_Draft):
    narration: str = Field(min_length=1)
    visual: str = Field(min_length=1)
    action: TransitionKind
    targets: list[str] = Field(min_length=1, max_length=10)

    @field_validator("narration", "visual")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("beat text cannot be blank")
        return normalized

    @field_validator("targets")
    @classmethod
    def normalize_unique_targets(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("beat targets cannot contain blank labels")
        if len(normalized) != len(set(normalized)):
            raise ValueError("beat contains duplicate targets")
        return normalized


class _EntityDraft(_Draft):
    """One stable visual object, expressed without renderer implementation details."""

    label: str = Field(min_length=1)
    detail: str = Field(min_length=1)

    @field_validator("label", "detail")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("entity text cannot be blank")
        return normalized


class _SceneDraft(_Draft):
    entities: list[_EntityDraft] = Field(min_length=2, max_length=10)
    beats: list[_BeatDraft] = Field(min_length=3, max_length=4)

    @field_validator("entities")
    @classmethod
    def unique_entity_labels(cls, values: list[_EntityDraft]) -> list[_EntityDraft]:
        labels = [value.label for value in values]
        if len(labels) != len(set(labels)):
            raise ValueError("scene contains duplicate entity labels")
        return values

    @model_validator(mode="after")
    def validate_references(self) -> "_SceneDraft":
        labels = [value.label for value in self.entities]
        if len(labels) != len(set(labels)):
            raise ValueError("scene contains duplicate entity labels")
        known = set(labels)
        for beat in self.beats:
            if set(beat.targets) - known:
                raise ValueError("beat target must exactly match an entity label")
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
            logger.info(
                "[CartoonPlanner] 开始规划: learning_need=%s depth=%s density=%s",
                brief.learning_need,
                brief.configuration.lesson_depth.value,
                brief.configuration.visual_density,
            )
            storyboard = await self._create_storyboard(brief)
            logger.info(
                "[CartoonPlanner] 分镜完成: title=%s scenes=%s grammars=%s",
                storyboard.title,
                len(storyboard.scenes),
                [s.grammar.value for s in storyboard.scenes],
            )
            profile = _profile(brief)
            logger.info(
                "[CartoonPlanner] 场景并行生成: max_parallel=%s profile=%s",
                self._parallelism,
                profile.label,
            )
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
            scenes = [task.result() for task in tasks]
            total_beats = sum(len(s.beats) for s in scenes)
            logger.info(
                "[CartoonPlanner] 规划完成: title=%s scenes=%s total_beats=%s",
                storyboard.title.strip(),
                len(scenes),
                total_beats,
            )
            return Lesson(
                title=storyboard.title.strip(),
                scenes=scenes,
            )
        except Exception as exc:
            if isinstance(exc, CartoonPlanningError):
                raise
            details = self._exception_details(exc)
            logger.error(
                "[CartoonPlanner] 规划失败: %s",
                " | ".join(details),
            )
            raise CartoonPlanningError("无法生成可渲染的语义动画分镜: " + " | ".join(details)) from exc

    async def _create_storyboard(self, brief: CartoonBrief) -> _StoryboardDraft:
        profile = _profile(brief)
        logger.info(
            "[CartoonPlanner] 生成分镜: scene_count=%s depth=%s density=%s",
            profile.scene_count,
            profile.label,
            brief.configuration.visual_density,
        )
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
        )
        storyboard = response if isinstance(response, _StoryboardDraft) else _StoryboardDraft.model_validate(response)
        if len(storyboard.scenes) != profile.scene_count:
            logger.error(
                "[CartoonPlanner] 分镜场景数不匹配: expected=%s got=%s",
                profile.scene_count,
                len(storyboard.scenes),
            )
            raise CartoonPlanningError(f"storyboard requires exactly {profile.scene_count} scenes")
        logger.info(
            "[CartoonPlanner] 分镜生成成功: title=%s scenes=%s",
            storyboard.title,
            [(i + 1, s.title, s.grammar.value) for i, s in enumerate(storyboard.scenes)],
        )
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
        logger.info(
            "[CartoonPlanner] 生成场景 %d/%d: title=%s grammar=%s",
            scene_index,
            len(storyboard.scenes),
            outline.title,
            outline.grammar.value,
        )
        t0 = asyncio.get_event_loop().time()
        prompt = self._prompts["scene_compose.md"].render(
            {
                "grammar": outline.grammar.value,
                "beat_count": profile.beats_per_scene,
                "density": brief.configuration.visual_density,
                "scene_contract": self._scene_contract(outline.grammar),
            }
        )
        context = {
            "lesson_title": storyboard.title,
            "scene_title": outline.title,
            "teaching_goal": outline.teaching_goal,
            "grammar": outline.grammar.value,
        }
        async with semaphore:
            schema: type[BaseModel] = (
                ExecutionSceneDraft if outline.grammar is VisualGrammar.TRACE else _SceneDraft
            )
            response = await self._invoke(
                schema,
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
                validator=lambda value: self._validate_scene_draft(
                    value, grammar=outline.grammar, profile=profile
                ),
            )
        scene_ms = round((asyncio.get_event_loop().time() - t0) * 1000)
        if outline.grammar is VisualGrammar.TRACE:
            draft = response if isinstance(response, ExecutionSceneDraft) else ExecutionSceneDraft.model_validate(response)
            self._validate_scene_draft(draft, grammar=outline.grammar, profile=profile)
            logger.info(
                "[CartoonPlanner] 场景 %d (trace) 生成完成: objects=%s beats=%s elapsed_ms=%d",
                scene_index,
                len(draft.objects),
                len(draft.beats),
                scene_ms,
            )
            return self._materialize_execution_scene(outline, draft, scene_index)
        draft = response if isinstance(response, _SceneDraft) else _SceneDraft.model_validate(response)
        self._validate_scene_draft(draft, grammar=outline.grammar, profile=profile)
        logger.info(
            "[CartoonPlanner] 场景 %d (%s) 生成完成: entities=%s beats=%s elapsed_ms=%d",
            scene_index,
            outline.grammar.value,
            len(draft.entities),
            len(draft.beats),
            scene_ms,
        )
        return self._materialize_scene(outline, draft, scene_index)

    @classmethod
    def _validate_scene_draft(
        cls,
        value: BaseModel,
        *,
        grammar: VisualGrammar,
        profile: _Profile,
    ) -> None:
        if grammar is VisualGrammar.TRACE:
            if not isinstance(value, ExecutionSceneDraft):
                raise ValueError("trace payload must validate as ExecutionSceneDraft")
            if len(value.beats) != profile.beats_per_scene:
                raise ValueError(f"trace scene requires exactly {profile.beats_per_scene} beats")
            if len(value.objects) > profile.entity_limit:
                raise ValueError(f"trace scene exceeds object capacity {profile.entity_limit}")
            ExecutionCompiler.compile(value, scene_id="validation-scene")
            return
        if not isinstance(value, _SceneDraft):
            raise ValueError("scene payload must validate as _SceneDraft")
        if len(value.entities) > profile.entity_limit:
            raise ValueError(f"scene exceeds entity capacity {profile.entity_limit}")
        if len(value.beats) != profile.beats_per_scene:
            raise ValueError(f"scene requires exactly {profile.beats_per_scene} beats")

    @staticmethod
    def _scene_contract(grammar: VisualGrammar) -> str:
        if grammar is VisualGrammar.TRACE:
            return """你正在生成算法或计算机过程的可执行场景。只输出以下 JSON，不得输出 entities、targets、visual、action、states、placements、ID、坐标或样式：
```json
{
  "objects":[
    {"name":"buffer","label":"缓冲区","role":"container","capacity":3},
    {"name":"packetA","label":"数据包 A","role":"token","value":"A"},
    {"name":"cursor","label":"读指针","role":"pointer"}
  ],
  "beats":[
    {"narration":"数据包进入缓冲区的第一个位置。","operation":{"verb":"place","subject":"packetA","target":"buffer","slot":0}},
    {"narration":"读指针指向即将处理的数据包。","operation":{"verb":"point","subject":"cursor","target":"packetA"}},
    {"narration":"处理完成后，数据包进入输出区。","operation":{"verb":"remove","subject":"packetA"}}
  ]
}
```
对象 `role` 只能是 `container`、`token`、`pointer`、`node`、`port`、`marker`；只有 `container` 声明 `capacity`（0 表示无状态容器，不分配槽位）。`value` 字段必须是字符串（如 "5" 而非 5）。操作 `verb` 只能是 `reveal`、`place`、`move`、`remove`、`point`、`update`、`connect`、`disconnect`、`compare`、`highlight`。`place` 必须有 container `target` 和 `slot`；`point/connect/disconnect/compare` 必须有 `target`；`update` 必须有 `value`；`move` 使用有状态 container 的 `target`+`slot`，或使用无状态 container（capacity=0）的 `target`（无需 slot），或使用 `region`（input/output/result/left/right/top/bottom/main/code）。每个 beat 只描述一个真实操作，不要用文字代替状态变化。"""
        return """只输出以下 JSON：
```json
{
  "entities":[{"label":"稳定对象名称","detail":"对象的实际公式、值或条件"}],
  "beats":[{"narration":"解释当前变化","visual":"画面上可见的知识表达","action":"reveal","targets":["稳定对象名称"]}]
}
```
不得输出 states、placements、relations、实体 ID、位置、容器、区域、颜色、样式或焦点字段。`targets` 必须精确引用已有实体。旁白不设字符上限；`visual` 必须是可静音理解的真实知识，不能只是“更新”或“执行”。"""

    @classmethod
    def _materialize_execution_scene(
        cls,
        outline: _StoryboardSceneDraft,
        draft: ExecutionSceneDraft,
        scene_index: int,
    ) -> TeachingScene:
        scene_id = f"scene-{scene_index:02d}"
        compiled = ExecutionCompiler.compile(draft, scene_id=scene_id)
        return TeachingScene(
            id=scene_id,
            title=outline.title,
            grammar=VisualGrammar.TRACE,
            execution_program=compiled.program,
            entities=compiled.entities,
            states=compiled.states,
            beats=compiled.beats,
        )

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
            VisualEntity(
                id=entity_id,
                label=entity.label,
                kind=cls._entity_kind(outline.grammar, index),
            )
            for index, (entity_id, entity) in enumerate(
                zip(entity_ids, draft.entities, strict=True)
            )
        ]
        entity_ids_by_label = {
            entity.label: entity.id
            for entity in entities
        }
        compiled_beats = [
            (beat, [entity_ids_by_label[label] for label in beat.targets])
            for beat in draft.beats
        ]
        initial_values = {
            entity_id: entity.detail
            for entity_id, entity in zip(entity_ids, draft.entities, strict=True)
        }
        states = cls._compile_states(scene_id, entities, compiled_beats, initial_values)
        beats = [
            TeachingBeat(
                id=f"{scene_id}-beat-{index:02d}",
                narration=beat.narration,
                caption=cls._action_caption(beat.action, beat.targets),
                before_state_id=states[index - 1].id,
                after_state_id=states[index].id,
                transition=Transition(
                    kind=beat.action,
                    entity_ids=target_ids,
                ),
                focus_entity_ids=target_ids,
            )
            for index, (beat, target_ids) in enumerate(compiled_beats, start=1)
        ]
        return TeachingScene(
            id=scene_id,
            title=outline.title,
            grammar=outline.grammar,
            entities=entities,
            states=states,
            beats=beats,
        )

    @staticmethod
    def _entity_kind(grammar: VisualGrammar, index: int) -> EntityKind:
        if grammar in {VisualGrammar.MODEL, VisualGrammar.TRACE} and index == 0:
            return EntityKind.CONTAINER
        if grammar is VisualGrammar.TRACE:
            return EntityKind.TOKEN
        if grammar is VisualGrammar.EVIDENCE:
            return EntityKind.CODE if index == 0 else EntityKind.METRIC
        return EntityKind.TERM

    @staticmethod
    def _action_caption(action: TransitionKind, targets: list[str]) -> str:
        labels = "、".join(targets)
        verbs = {
            TransitionKind.REVEAL: "显示",
            TransitionKind.MOVE: "推进",
            TransitionKind.INSERT: "加入",
            TransitionKind.REMOVE: "移除",
            TransitionKind.UPDATE: "更新",
            TransitionKind.CONNECT: "建立关联",
            TransitionKind.DISCONNECT: "解除关联",
            TransitionKind.EXECUTE: "执行",
            TransitionKind.COMPARE: "比较",
        }
        return f"{verbs[action]}：{labels}"

    @classmethod
    def _compile_states(
        cls,
        scene_id: str,
        entities: list[VisualEntity],
        beats: list[tuple[_BeatDraft, list[str]]],
        initial_values: dict[str, str],
    ) -> list[VisualState]:
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
                region=regions[index % len(regions)],
                visible=(index == 0),
                value=initial_values[entity.id],
                status=("active" if index == 0 else "idle"),
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
        for index, (beat, target_ids) in enumerate(beats, start=1):
            states.append(
                cls._advance_state(
                    state=states[-1],
                    state_id=f"{scene_id}-state-{index + 1:02d}",
                    entity_ids=[entity.id for entity in entities],
                    beat=beat,
                    target_ids=target_ids,
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
        beat: _BeatDraft,
        target_ids: list[str],
        step: int,
    ) -> VisualState:
        placements = [item.model_copy(deep=True) for item in state.placements]
        relations = [item.model_copy(deep=True) for item in state.relations]
        by_id = {item.entity_id: item for item in placements}
        targets = target_ids
        changed = False

        def mark_value(entity_id: str, status: str = "active") -> None:
            nonlocal changed
            placement = by_id[entity_id]
            # A beat may focus several stable objects, but its visual statement
            # belongs to one focal object.  Repeating it in every card turns a
            # diagram into a caption wall and loses the object-level meaning.
            value = beat.visual if entity_id == targets[0] else placement.value
            if (
                placement.value != value
                or placement.status != status
                or not placement.visible
            ):
                placement.value = value
                placement.status = status
                placement.visible = True
                changed = True

        if beat.action is TransitionKind.REVEAL:
            for entity_id in targets:
                placement = by_id[entity_id]
                if not placement.visible or placement.status != "active":
                    placement.visible = True
                    placement.status = "active"
                    changed = True
        elif beat.action is TransitionKind.MOVE:
            regions = list(SemanticRegion)
            for entity_id in targets:
                placement = by_id[entity_id]
                placement.region = regions[(regions.index(placement.region) + 1) % len(regions)]
                placement.visible = True
                placement.status = "active"
                changed = True
        elif beat.action is TransitionKind.INSERT:
            for entity_id in targets:
                placement = by_id[entity_id]
                if not placement.visible or placement.status != "active":
                    placement.visible = True
                    placement.status = "active"
                    changed = True
                mark_value(entity_id)
        elif beat.action is TransitionKind.REMOVE:
            for entity_id in targets:
                placement = by_id[entity_id]
                if placement.visible or placement.status != "warning":
                    placement.visible = False
                    placement.status = "warning"
                    changed = True
        elif beat.action is TransitionKind.CONNECT:
            source_id = targets[0]
            target_id = next((value for value in targets[1:] if value != source_id), None)
            if target_id is None:
                target_id = next(value for value in entity_ids if value != source_id)
            for entity_id in {source_id, target_id}:
                placement = by_id[entity_id]
                if not placement.visible or placement.status != "active":
                    placement.visible = True
                    placement.status = "active"
                    changed = True
            relation = Relation(source_id=source_id, target_id=target_id)
            if relation not in relations:
                relations.append(relation)
                changed = True
        elif beat.action is TransitionKind.DISCONNECT:
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
                    status="success" if beat.action is TransitionKind.EXECUTE else "active",
                )

        # Every beat carries one learner-visible statement.  Actions such as
        # reveal, connect and move used to mutate only presentation state, so
        # the renderer had no domain content to show for most of the narration.
        # Keep it on the first focus object; the remaining targets retain their
        # own stable details instead of becoming duplicate caption cards.
        if beat.action is not TransitionKind.REMOVE:
            focal = by_id[targets[0]]
            if focal.value != beat.visual:
                focal.value = beat.visual
                changed = True

        if not changed:
            mark_value(targets[0], status="success")
        return VisualState(id=state_id, placements=placements, relations=relations)

    async def _invoke(
        self,
        schema: type[BaseModel],
        messages: list[SystemMessage | HumanMessage],
        *,
        temperature: float,
        validator: Callable[[BaseModel], None] | None = None,
    ) -> Any:
        logger.info(
            "[CartoonPlanner] LLM 调用开始: schema=%s temperature=%.2f messages=%d",
            schema.__name__,
            temperature,
            len(messages),
        )
        t0 = asyncio.get_event_loop().time()
        try:
            result = await get_llm().ainvoke_json(
                schema,
                messages,
                temperature=temperature,
                validator=validator,
            )
            elapsed_ms = round((asyncio.get_event_loop().time() - t0) * 1000)
            logger.info(
                "[CartoonPlanner] LLM 调用成功: schema=%s elapsed_ms=%d",
                schema.__name__,
                elapsed_ms,
            )
            return result
        except Exception as exc:
            elapsed_ms = round((asyncio.get_event_loop().time() - t0) * 1000)
            logger.error(
                "[CartoonPlanner] LLM 调用失败: schema=%s elapsed_ms=%d error=%s",
                schema.__name__,
                elapsed_ms,
                exc,
            )
            raise

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
