"""Semantic contract and typed scene recipes for HyperFrames teaching videos."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


MAX_SCENE_VISUAL_ITEMS = 8


class SceneLayout(StrEnum):
    HERO = "hero"
    CONCEPT_MAP = "concept_map"
    PROCESS_LANE = "process_lane"
    STATE_LAB = "state_lab"
    SYSTEM_MAP = "system_map"
    COMPARISON_BOARD = "comparison_board"
    CODE_STUDIO = "code_studio"
    FORMULA_LAB = "formula_lab"
    RECAP = "recap"


class VisualKind(StrEnum):
    """A compact vocabulary of rendering grammars, not course-specific templates."""

    NODES = "nodes"
    MODEL = "model"
    TREE = "tree"
    FLOW = "flow"
    STATE = "state"
    MEMORY = "memory"
    NETWORK = "network"
    CODE = "code"
    FORMULA = "formula"
    COMPARISON = "comparison"
    METRICS = "metrics"


_CONNECTED_VISUAL_KINDS = frozenset({
    VisualKind.MODEL,
    VisualKind.TREE,
    VisualKind.FLOW,
    VisualKind.STATE,
    VisualKind.MEMORY,
    VisualKind.NETWORK,
})


class MotionKind(StrEnum):
    REVEAL = "reveal"
    FOCUS = "focus"
    TRAVERSE = "traverse"
    TRANSFER = "transfer"
    TRANSFORM = "transform"
    COMPARE = "compare"
    EMPHASIZE = "emphasize"


class VisualRole(StrEnum):
    """The semantic job of an object inside a knowledge model.

    Roles give the renderer useful visual hierarchy without naming any specific
    discipline.  A red-black-tree key, a network packet, a memory cell and a
    formula term are all supplied by the model as ordinary visual items.
    """

    ENTITY = "entity"
    VALUE = "value"
    OPERATION = "operation"
    STATE = "state"
    CONTAINER = "container"
    SIGNAL = "signal"
    TERM = "term"


@dataclass(frozen=True)
class LayoutSpec:
    visual_kinds: frozenset[VisualKind]
    instruction: str


LAYOUTS: dict[SceneLayout, LayoutSpec] = {
    SceneLayout.HERO: LayoutSpec(frozenset({VisualKind.NODES, VisualKind.MODEL, VisualKind.METRICS}), "章节开场：一个核心命题配少量关键概念，画面留白。"),
    SceneLayout.CONCEPT_MAP: LayoutSpec(frozenset({VisualKind.NODES, VisualKind.MODEL, VisualKind.TREE, VisualKind.FLOW}), "概念关系：中心概念和 3 到 6 个关系节点，强调层次。"),
    SceneLayout.PROCESS_LANE: LayoutSpec(frozenset({VisualKind.MODEL, VisualKind.FLOW, VisualKind.NETWORK}), "过程推演：按时间或数据方向逐步推进，避免长段文字。"),
    SceneLayout.STATE_LAB: LayoutSpec(frozenset({VisualKind.MODEL, VisualKind.STATE, VisualKind.MEMORY, VisualKind.TREE}), "状态演化：展示前后状态差异和一次关键变换。"),
    SceneLayout.SYSTEM_MAP: LayoutSpec(frozenset({VisualKind.MODEL, VisualKind.NETWORK, VisualKind.NODES, VisualKind.MEMORY, VisualKind.TREE}), "系统组成：组件、边界和消息/数据流。"),
    SceneLayout.COMPARISON_BOARD: LayoutSpec(frozenset({VisualKind.MODEL, VisualKind.COMPARISON, VisualKind.METRICS}), "对比辨析：只比较两个对象，并给出明确判断维度。"),
    SceneLayout.CODE_STUDIO: LayoutSpec(frozenset({VisualKind.MODEL, VisualKind.CODE, VisualKind.FLOW}), "代码讲解：短代码片段配执行轨迹；不展示冗长源码。"),
    SceneLayout.FORMULA_LAB: LayoutSpec(frozenset({VisualKind.MODEL, VisualKind.FORMULA, VisualKind.METRICS}), "公式推导：一个公式、变量含义和一个代入/变化过程。"),
    SceneLayout.RECAP: LayoutSpec(frozenset({VisualKind.MODEL, VisualKind.METRICS, VisualKind.NODES}), "收束总结：回顾 3 个以内可迁移结论，不新增知识。"),
}

if set(LAYOUTS) != set(SceneLayout):
    raise RuntimeError("Cartoon layout registry is not exhaustive")


def motion_values() -> str:
    return ", ".join(item.value for item in MotionKind)


def connected_visual_kind_values() -> str:
    return "、".join(f"`{kind.value}`" for kind in _CONNECTED_VISUAL_KINDS)


def role_values() -> str:
    return "、".join(f"`{role.value}`" for role in VisualRole)


def layout_guidance() -> str:
    return "\n".join(f"- `{layout.value}`：{spec.instruction}" for layout, spec in LAYOUTS.items())


def _id(value: str, fallback: str) -> str:
    normalized = "".join(char if char.isalnum() or char in "-_" else "-" for char in value.strip().lower())
    return normalized.strip("-_") or fallback


class CartoonGenerationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pace: Literal["calm", "balanced", "fast"] = "balanced"
    visual_density: Literal["moderate", "rich", "intensive"] = "rich"
    target_duration_seconds: int = Field(default=90, ge=90, le=600)
    voice: Literal["teacher", "coach"] = "teacher"


class CartoonBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")
    learning_need: str = Field(min_length=1, max_length=500)
    teaching_plan: str = Field(default="", max_length=12000)
    tutorial_markdown: str = Field(default="", max_length=30000)
    knowledge_points: list[str] = Field(default_factory=list, max_length=30)
    weak_knowledge_points: list[str] = Field(default_factory=list, max_length=20)
    configuration: CartoonGenerationConfig = Field(default_factory=CartoonGenerationConfig)


class StoryboardScene(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=48)
    title: str = Field(min_length=1, max_length=54)
    objective: str = Field(min_length=1, max_length=110)
    layout: SceneLayout
    visual_kind: VisualKind

    @field_validator("id")
    @classmethod
    def normalize_id(cls, value: str) -> str:
        return _id(value, "scene")

    @model_validator(mode="after")
    def validate_layout_visual_pair(self) -> "StoryboardScene":
        if self.visual_kind not in LAYOUTS[self.layout].visual_kinds:
            raise ValueError(f"layout {self.layout.value} does not support visual kind {self.visual_kind.value}")
        return self


class CartoonStoryboard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=72)
    course: str = Field(default="计算机科学", min_length=1, max_length=40)
    scenes: list[StoryboardScene] = Field(min_length=4, max_length=6)

    @model_validator(mode="after")
    def unique_scenes(self) -> "CartoonStoryboard":
        if len({scene.id for scene in self.scenes}) != len(self.scenes):
            raise ValueError("storyboard contains duplicate scene ids")
        if self.scenes[0].layout != SceneLayout.HERO or self.scenes[-1].layout != SceneLayout.RECAP:
            raise ValueError("storyboard must begin with hero and end with recap")
        return self


class VisualItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=48)
    label: str = Field(min_length=1, max_length=30)
    detail: str = Field(default="", max_length=64)
    value: str = Field(default="", max_length=36)
    role: VisualRole = VisualRole.ENTITY
    tone: Literal["ink", "mint", "blue", "amber", "violet", "coral"] = "blue"

    @field_validator("id")
    @classmethod
    def normalize_id(cls, value: str) -> str:
        return _id(value, "item")


class VisualEdge(BaseModel):
    """One rendered relationship between two visual items.

    The edge is deliberately part of the compact LLM contract: it is used to
    build SVG connectors and to derive semantic layouts such as a tree.  It is
    not a decorative, unused graph field.
    """

    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=48)
    source_id: str = Field(min_length=1, max_length=48)
    target_id: str = Field(min_length=1, max_length=48)
    label: str = Field(default="", max_length=30)
    tone: Literal["ink", "mint", "blue", "amber", "violet", "coral"] = "blue"

    @field_validator("id", "source_id", "target_id")
    @classmethod
    def normalize_id(cls, value: str) -> str:
        return _id(value, "edge")


class VisualStateItem(BaseModel):
    """One object as it appears in a particular teaching-time model snapshot.

    The id always points to the scene's stable object.  Optional values are
    state-specific overrides, so an insertion, recolouring, pointer update or
    value substitution is represented as data rather than a one-off renderer
    rule.
    """

    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=48)
    label: str | None = Field(default=None, min_length=1, max_length=30)
    detail: str | None = Field(default=None, max_length=64)
    value: str | None = Field(default=None, max_length=36)
    role: VisualRole | None = None
    tone: Literal["ink", "mint", "blue", "amber", "violet", "coral"] | None = None

    @field_validator("id")
    @classmethod
    def normalize_id(cls, value: str) -> str:
        return _id(value, "item")


class VisualState(BaseModel):
    """A replayable snapshot of the knowledge model at one teaching step."""

    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=48)
    items: list[VisualStateItem] = Field(min_length=1, max_length=MAX_SCENE_VISUAL_ITEMS)
    edges: list[VisualEdge] = Field(default_factory=list, max_length=MAX_SCENE_VISUAL_ITEMS * 2)

    @field_validator("id")
    @classmethod
    def normalize_id(cls, value: str) -> str:
        return _id(value, "state")

    @model_validator(mode="after")
    def unique_items(self) -> "VisualState":
        if len({item.id for item in self.items}) != len(self.items):
            raise ValueError("visual state contains duplicate item ids")
        return self


class SceneVisual(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: VisualKind
    items: list[VisualItem] = Field(min_length=1, max_length=MAX_SCENE_VISUAL_ITEMS)
    edges: list[VisualEdge] = Field(default_factory=list, max_length=MAX_SCENE_VISUAL_ITEMS * 2)
    states: list[VisualState] = Field(default_factory=list, max_length=4)
    code: str = Field(default="", max_length=540)
    formula: str = Field(default="", max_length=160)
    caption: str = Field(default="", max_length=90)

    @model_validator(mode="after")
    def validate_payload(self) -> "SceneVisual":
        item_ids = {item.id for item in self.items}
        if len(item_ids) != len(self.items):
            raise ValueError("visual contains duplicate item ids")
        edge_ids = {edge.id for edge in self.edges}
        if len(edge_ids) != len(self.edges):
            raise ValueError("visual contains duplicate edge ids")
        state_ids = {state.id for state in self.states}
        if len(state_ids) != len(self.states):
            raise ValueError("visual contains duplicate state ids")
        if self.kind == VisualKind.CODE and not self.code:
            raise ValueError("code visual requires code")
        if self.kind == VisualKind.FORMULA and not self.formula:
            raise ValueError("formula visual requires formula")
        if self.kind in {VisualKind.CODE, VisualKind.FORMULA} and self.states:
            raise ValueError(f"{self.kind.value} visual cannot contain visual states")
        if self.states and self.edges:
            raise ValueError("dynamic visual must define edges only inside states")
        if self.states:
            for state in self.states:
                state_item_ids = {item.id for item in state.items}
                if not state_item_ids <= item_ids:
                    raise ValueError(f"visual state {state.id} references unknown items")
                self._validate_edges(state_item_ids, state.edges)
        else:
            self._validate_edges(item_ids, self.edges)
        return self

    def _validate_edges(self, item_ids: set[str], edges: list[VisualEdge]) -> None:
        pairs = {(edge.source_id, edge.target_id) for edge in edges}
        if len(pairs) != len(edges):
            raise ValueError("visual contains duplicate edge endpoints")
        invalid_edges = [edge.id for edge in edges if edge.source_id not in item_ids or edge.target_id not in item_ids or edge.source_id == edge.target_id]
        if invalid_edges:
            raise ValueError(f"visual contains invalid edges: {sorted(invalid_edges)}")
        if self.kind in {VisualKind.MODEL, VisualKind.TREE, VisualKind.FLOW, VisualKind.STATE, VisualKind.NETWORK} and len(item_ids) > 1 and not edges:
            raise ValueError(f"{self.kind.value} visual requires edges")
        if self.kind == VisualKind.TREE:
            self._validate_tree(item_ids, edges)

    @staticmethod
    def _validate_tree(item_ids: set[str], edges: list[VisualEdge]) -> None:
        if len(edges) != len(item_ids) - 1:
            raise ValueError("tree visual requires exactly one parent edge for every non-root node")
        parents = {edge.target_id for edge in edges}
        if len(parents) != len(edges):
            raise ValueError("tree visual contains a node with multiple parents")
        roots = item_ids - parents
        if len(roots) != 1:
            raise ValueError("tree visual requires exactly one root")
        children: dict[str, list[str]] = {item_id: [] for item_id in item_ids}
        for edge in edges:
            children[edge.source_id].append(edge.target_id)
        seen: set[str] = set()
        pending = list(roots)
        while pending:
            node = pending.pop()
            if node in seen:
                continue
            seen.add(node)
            pending.extend(children[node])
        if seen != item_ids:
            raise ValueError("tree visual must be connected and acyclic")


class MotionBeat(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: MotionKind
    # A motion can address the whole visual. This must stay aligned with
    # SceneVisual.items because the compiler accepts every referenced target.
    target_ids: list[str] = Field(min_length=1, max_length=MAX_SCENE_VISUAL_ITEMS)
    duration_ms: int = Field(default=700, ge=240, le=2200)

    @field_validator("target_ids")
    @classmethod
    def normalize_targets(cls, values: list[str]) -> list[str]:
        normalized = [_id(value, "item") for value in values]
        if len(normalized) != len(set(normalized)):
            raise ValueError("motion beat contains duplicate targets")
        return normalized


class TeachingStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=48)
    narration: str = Field(min_length=8, max_length=150)
    focus: str = Field(min_length=1, max_length=64)
    state_id: str = Field(default="", max_length=48)
    motions: list[MotionBeat] = Field(min_length=1, max_length=4)

    @field_validator("id")
    @classmethod
    def normalize_id(cls, value: str) -> str:
        return _id(value, "step")

    @field_validator("state_id")
    @classmethod
    def normalize_state_id(cls, value: str) -> str:
        return _id(value, "") if value else ""


class TeachingScene(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=48)
    title: str = Field(min_length=1, max_length=54)
    objective: str = Field(min_length=1, max_length=110)
    layout: SceneLayout
    visual: SceneVisual
    steps: list[TeachingStep] = Field(min_length=2, max_length=4)
    takeaway: str = Field(min_length=1, max_length=96)

    @field_validator("id")
    @classmethod
    def normalize_id(cls, value: str) -> str:
        return _id(value, "scene")

    @model_validator(mode="after")
    def validate_scene(self) -> "TeachingScene":
        if len({step.id for step in self.steps}) != len(self.steps):
            raise ValueError("scene contains duplicate step ids")
        known = {item.id for item in self.visual.items}
        unknown = {target for step in self.steps for motion in step.motions for target in motion.target_ids if target not in known}
        if unknown:
            raise ValueError(f"motion references unknown items: {sorted(unknown)}")
        state_ids = {state.id for state in self.visual.states}
        referenced_states = {step.state_id for step in self.steps if step.state_id}
        if referenced_states - state_ids:
            raise ValueError(f"steps reference unknown visual states: {sorted(referenced_states - state_ids)}")
        if state_ids and any(not step.state_id for step in self.steps):
            raise ValueError("dynamic visual requires every teaching step to declare state_id")
        if not state_ids and referenced_states:
            raise ValueError("static visual cannot declare state_id")
        return self


class TeachingLesson(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=72)
    course: str = Field(default="计算机科学", min_length=1, max_length=40)
    scenes: list[TeachingScene] = Field(min_length=4, max_length=6)

    @model_validator(mode="after")
    def validate_lesson(self) -> "TeachingLesson":
        if len({scene.id for scene in self.scenes}) != len(self.scenes):
            raise ValueError("lesson contains duplicate scene ids")
        if len({scene.layout for scene in self.scenes}) < 4:
            raise ValueError("lesson needs at least four layouts")
        animated_models = [
            scene
            for scene in self.scenes
            if scene.visual.kind in _CONNECTED_VISUAL_KINDS and scene.visual.states
        ]
        if len(animated_models) < 2:
            raise ValueError("lesson needs at least two animated knowledge-model scenes")
        return self


class AudioSynthesis(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    path: Path
    duration_ms: int = Field(gt=0)
    text: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    voice: str = Field(min_length=1)


class TimedMotion(BaseModel):
    motion: MotionBeat
    start_ms: int = Field(ge=0)
    duration_ms: int = Field(gt=0)


class TimedStep(BaseModel):
    scene_id: str
    step: TeachingStep
    start_ms: int = Field(ge=0)
    duration_ms: int = Field(gt=0)
    audio_src: str
    audio_duration_ms: int = Field(gt=0)
    motions: list[TimedMotion]


class TimedScene(BaseModel):
    index: int = Field(ge=0)
    scene: TeachingScene
    start_ms: int = Field(ge=0)
    duration_ms: int = Field(gt=0)
    steps: list[TimedStep] = Field(min_length=1)


class CompositionPlan(BaseModel):
    total_duration_ms: int = Field(gt=0)
    scenes: list[TimedScene] = Field(min_length=4)
