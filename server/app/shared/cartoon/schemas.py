"""Structured, replayable contract for HyperFrames teaching videos."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


TeachingMode = Literal["concept", "algorithm", "protocol", "state-machine", "architecture", "comparison"]
VisualKind = Literal["tree", "array", "graph", "flow", "state-machine", "memory", "network", "comparison"]
ActionKind = Literal["reveal", "focus", "compare", "traverse", "transfer", "mutate", "insert", "remove", "connect", "highlight"]
PatchKind = Literal["add_node", "remove_node", "set_label", "set_state", "add_edge", "remove_edge", "set_value"]


def _token(value: str, fallback: str = "item") -> str:
    normalized = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in value.strip().lower())
    return normalized.strip("-_") or fallback


class CartoonGenerationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    depth: Literal["overview", "standard", "deep"] = "standard"
    pace: Literal["calm", "balanced", "fast"] = "balanced"
    visual_density: Literal["moderate", "rich", "intensive"] = "rich"
    target_duration_seconds: int = Field(default=90, ge=35, le=180)
    voice: Literal["teacher", "coach"] = "teacher"
    template_id: str = "white-teaching-v1"

    @field_validator("template_id")
    @classmethod
    def normalize_template_id(cls, value: str) -> str:
        return _token(value, "white-teaching-v1")


class CartoonBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")

    learning_need: str = Field(min_length=1, max_length=500)
    teaching_plan: str = ""
    tutorial_markdown: str = ""
    prerequisites: list[str] = Field(default_factory=list)
    knowledge_points: list[str] = Field(default_factory=list)
    weak_knowledge_points: list[str] = Field(default_factory=list)
    learner_profile: dict[str, Any] = Field(default_factory=dict)
    upstream_handoffs: dict[str, Any] = Field(default_factory=dict)
    configuration: CartoonGenerationConfig = Field(default_factory=CartoonGenerationConfig)


class VisualNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=48)
    label: str = Field(min_length=1, max_length=72)
    detail: str = Field(default="", max_length=120)
    state: str = Field(default="idle", max_length=24)
    parent_id: str | None = None
    value: str | int | float | None = None

    @field_validator("id", "parent_id")
    @classmethod
    def normalize_id(cls, value: str | None) -> str | None:
        return _token(value) if value else value


class VisualEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    target_id: str
    label: str = Field(default="", max_length=48)
    kind: Literal["directed", "undirected", "left", "right", "transition"] = "directed"

    @field_validator("source_id", "target_id")
    @classmethod
    def normalize_id(cls, value: str) -> str:
        return _token(value)


class VisualModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: VisualKind
    label: str = Field(default="", max_length=80)
    nodes: list[VisualNode] = Field(default_factory=list, max_length=36)
    edges: list[VisualEdge] = Field(default_factory=list, max_length=64)

    @model_validator(mode="after")
    def validate_links(self) -> "VisualModel":
        ids = [node.id for node in self.nodes]
        if len(ids) != len(set(ids)):
            raise ValueError("visual model contains duplicate node ids")
        known = set(ids)
        for node in self.nodes:
            if node.parent_id and node.parent_id not in known:
                raise ValueError(f"node {node.id} references unknown parent {node.parent_id}")
        for edge in self.edges:
            if edge.source_id not in known or edge.target_id not in known:
                raise ValueError("visual edge references an unknown node")
        return self


class TeachingAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: ActionKind
    target_ids: list[str] = Field(default_factory=list, max_length=4)
    source_id: str | None = None
    destination_id: str | None = None
    note: str = Field(default="", max_length=72)
    duration_ms: int = Field(default=700, ge=160, le=4000)

    @field_validator("target_ids")
    @classmethod
    def normalize_targets(cls, values: list[str]) -> list[str]:
        return [_token(value) for value in values if value.strip()]

    @field_validator("source_id", "destination_id")
    @classmethod
    def normalize_optional_id(cls, value: str | None) -> str | None:
        return _token(value) if value else value


class StatePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: PatchKind
    target_id: str | None = None
    node: VisualNode | None = None
    edge: VisualEdge | None = None
    value: str | int | float | None = None

    @field_validator("target_id")
    @classmethod
    def normalize_target(cls, value: str | None) -> str | None:
        return _token(value) if value else value

    @model_validator(mode="after")
    def require_payload(self) -> "StatePatch":
        if self.op == "add_node" and self.node is None:
            raise ValueError("add_node requires node")
        if self.op in {"add_edge", "remove_edge"} and self.edge is None:
            raise ValueError(f"{self.op} requires edge")
        if self.op in {"remove_node", "set_label", "set_state", "set_value"} and not self.target_id:
            raise ValueError(f"{self.op} requires target_id")
        return self


class TeachingStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=48)
    narration: str = Field(min_length=4, max_length=180)
    focus_ids: list[str] = Field(default_factory=list, max_length=4)
    actions: list[TeachingAction] = Field(min_length=1, max_length=5)
    patches: list[StatePatch] = Field(default_factory=list, max_length=4)

    @field_validator("id")
    @classmethod
    def normalize_id(cls, value: str) -> str:
        return _token(value, "step")

    @field_validator("focus_ids")
    @classmethod
    def normalize_focus(cls, values: list[str]) -> list[str]:
        return [_token(value) for value in values if value.strip()]


class TeachingScene(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=48)
    title: str = Field(min_length=1, max_length=72)
    objective: str = Field(min_length=1, max_length=140)
    mode: TeachingMode
    tag: str = Field(default="", max_length=36)
    visual_model: VisualModel
    steps: list[TeachingStep] = Field(min_length=1, max_length=10)

    @field_validator("id")
    @classmethod
    def normalize_id(cls, value: str) -> str:
        return _token(value, "scene")

    @model_validator(mode="after")
    def validate_replay(self) -> "TeachingScene":
        replay_scene(self)
        return self


class TeachingLesson(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=80)
    course: str = Field(default="计算机科学", max_length=40)
    topic: str = Field(min_length=1, max_length=60)
    scenes: list[TeachingScene] = Field(min_length=2, max_length=8)

    @model_validator(mode="after")
    def unique_scene_ids(self) -> "TeachingLesson":
        ids = [scene.id for scene in self.scenes]
        if len(ids) != len(set(ids)):
            raise ValueError("lesson contains duplicate scene ids")
        return self


def replay_scene(scene: TeachingScene) -> VisualModel:
    """Return the final state while validating all references and transitions."""
    state = scene.visual_model.model_copy(deep=True)
    nodes = {node.id: node for node in state.nodes}
    edges = list(state.edges)

    def require_node(node_id: str) -> None:
        if node_id not in nodes:
            raise ValueError(f"scene {scene.id} references unknown node {node_id}")

    for step in scene.steps:
        pending_nodes = {
            patch.node.id
            for patch in step.patches
            if patch.op == "add_node" and patch.node is not None
        }
        for node_id in step.focus_ids:
            if node_id not in pending_nodes:
                require_node(node_id)
        for action in step.actions:
            for node_id in action.target_ids:
                if node_id not in pending_nodes:
                    require_node(node_id)
            if action.source_id and action.source_id not in pending_nodes:
                require_node(action.source_id)
            if action.destination_id and action.destination_id not in pending_nodes:
                require_node(action.destination_id)
        for patch in step.patches:
            if patch.op == "add_node":
                assert patch.node is not None
                if patch.node.id in nodes:
                    raise ValueError(f"scene {scene.id} adds duplicate node {patch.node.id}")
                if patch.node.parent_id:
                    require_node(patch.node.parent_id)
                nodes[patch.node.id] = patch.node
            elif patch.op == "remove_node":
                assert patch.target_id is not None
                require_node(patch.target_id)
                nodes.pop(patch.target_id)
                edges = [edge for edge in edges if edge.source_id != patch.target_id and edge.target_id != patch.target_id]
            elif patch.op in {"set_label", "set_state", "set_value"}:
                assert patch.target_id is not None
                require_node(patch.target_id)
                node = nodes[patch.target_id]
                if patch.op == "set_label":
                    node.label = str(patch.value or "")
                elif patch.op == "set_state":
                    node.state = str(patch.value or "idle")
                else:
                    node.value = patch.value
            else:
                assert patch.edge is not None
                require_node(patch.edge.source_id)
                require_node(patch.edge.target_id)
                if patch.op == "add_edge":
                    edges.append(patch.edge)
                else:
                    edges = [edge for edge in edges if edge != patch.edge]
    return VisualModel(kind=state.kind, label=state.label, nodes=list(nodes.values()), edges=edges)


class AudioSynthesis(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    path: Path
    duration_ms: int = Field(gt=0)
    text: str
    provider: str
    voice: str


class TimedStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scene_id: str
    step: TeachingStep
    start_ms: int = Field(ge=0)
    duration_ms: int = Field(gt=0)
    audio_src: str
    audio_duration_ms: int = Field(gt=0)


class TimedScene(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int = Field(ge=0)
    scene: TeachingScene
    start_ms: int = Field(ge=0)
    duration_ms: int = Field(gt=0)
    steps: list[TimedStep] = Field(min_length=1)


class CompositionPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_duration_ms: int = Field(gt=0)
    scenes: list[TimedScene] = Field(min_length=1)
