"""Strict, replayable contracts for HyperFrames teaching videos."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


TeachingMode = Literal[
    "concept",
    "algorithm",
    "protocol",
    "state-machine",
    "architecture",
    "comparison",
]
VisualKind = Literal[
    "tree",
    "array",
    "graph",
    "flow",
    "state-machine",
    "memory",
    "network",
    "comparison",
]
MechanismKind = Literal[
    "structure",
    "sequence",
    "state_transition",
    "data_flow",
    "message_exchange",
    "container_operation",
    "tree_growth",
    "graph_traversal",
    "timeline",
    "memory_change",
    "pipeline",
    "comparison",
]
VisualElementKind = Literal[
    "concept",
    "process",
    "state",
    "data",
    "packet",
    "array_cell",
    "tree_node",
    "graph_node",
    "queue_item",
    "stack_frame",
    "memory_block",
    "page_frame",
    "register",
    "instruction",
    "pipeline_stage",
    "table_row",
    "code_line",
    "formula",
    "pointer",
    "timer",
    "window",
    "annotation",
]
ActionKind = Literal[
    "reveal",
    "focus",
    "compare",
    "traverse",
    "transfer",
    "mutate",
    "insert",
    "remove",
    "connect",
    "highlight",
]
PatchKind = Literal[
    "add_node",
    "remove_node",
    "set_label",
    "set_state",
    "add_edge",
    "remove_edge",
    "set_value",
]
EdgeKind = Literal[
    "directed",
    "undirected",
    "left",
    "right",
    "transition",
]


TEACHING_MODES = tuple(get_args(TeachingMode))
VISUAL_KINDS = tuple(get_args(VisualKind))
MECHANISM_KINDS = tuple(get_args(MechanismKind))
VISUAL_ELEMENT_KINDS = tuple(get_args(VisualElementKind))
ACTION_KINDS = tuple(get_args(ActionKind))
PATCH_KINDS = tuple(get_args(PatchKind))
EDGE_KINDS = tuple(get_args(EdgeKind))


_DYNAMIC_ACTIONS = frozenset(
    {
        "compare",
        "traverse",
        "transfer",
        "mutate",
        "insert",
        "remove",
        "connect",
    }
)

_MECHANISM_ACTIONS: dict[str, frozenset[str]] = {
    "sequence": frozenset(
        {
            "transfer",
            "traverse",
            "mutate",
            "insert",
            "remove",
            "connect",
        }
    ),
    "state_transition": frozenset(
        {
            "mutate",
            "transfer",
        }
    ),
    "data_flow": frozenset(
        {
            "transfer",
            "traverse",
        }
    ),
    "message_exchange": frozenset(
        {
            "transfer",
        }
    ),
    "container_operation": frozenset(
        {
            "insert",
            "remove",
            "transfer",
            "mutate",
        }
    ),
    "tree_growth": frozenset(
        {
            "insert",
            "connect",
        }
    ),
    "graph_traversal": frozenset(
        {
            "traverse",
        }
    ),
    "timeline": frozenset(
        {
            "traverse",
            "transfer",
            "mutate",
        }
    ),
    "memory_change": frozenset(
        {
            "mutate",
            "transfer",
            "insert",
            "remove",
        }
    ),
    "pipeline": frozenset(
        {
            "transfer",
            "mutate",
        }
    ),
    "comparison": frozenset(
        {
            "compare",
        }
    ),
}


def _token(
    value: str,
    fallback: str = "item",
) -> str:
    normalized = "".join(
        char
        if char.isalnum() or char in {"-", "_"}
        else "-"
        for char in value.strip().lower()
    )
    return normalized.strip("-_") or fallback


def _unique_tokens(
    values: list[str],
    *,
    field_name: str,
) -> list[str]:
    normalized = [
        _token(value)
        for value in values
        if value.strip()
    ]

    if len(normalized) != len(set(normalized)):
        raise ValueError(
            f"{field_name} contains duplicate ids"
        )

    return normalized


def _edge_key(
    edge: "VisualEdge",
) -> tuple[str, str, str, str]:
    return (
        edge.source_id,
        edge.target_id,
        edge.kind,
        edge.label,
    )


class CartoonGenerationConfig(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    depth: Literal[
        "overview",
        "standard",
        "deep",
    ] = "standard"

    pace: Literal[
        "calm",
        "balanced",
        "fast",
    ] = "balanced"

    visual_density: Literal[
        "moderate",
        "rich",
        "intensive",
    ] = "rich"

    target_duration_seconds: int = Field(
        default=90,
        ge=35,
        le=180,
    )

    voice: Literal[
        "teacher",
        "coach",
    ] = "teacher"

    template_id: str = "white-teaching-v1"

    @field_validator("template_id")
    @classmethod
    def normalize_template_id(
        cls,
        value: str,
    ) -> str:
        return _token(
            value,
            "white-teaching-v1",
        )


class CartoonBrief(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    learning_need: str = Field(
        min_length=1,
        max_length=500,
    )

    teaching_plan: str = Field(
        default="",
        max_length=12000,
    )

    tutorial_markdown: str = Field(
        default="",
        max_length=30000,
    )

    prerequisites: list[str] = Field(
        default_factory=list,
        max_length=20,
    )

    knowledge_points: list[str] = Field(
        default_factory=list,
        max_length=30,
    )

    weak_knowledge_points: list[str] = Field(
        default_factory=list,
        max_length=20,
    )

    learner_profile: dict[str, Any] = Field(
        default_factory=dict,
    )

    upstream_handoffs: dict[str, Any] = Field(
        default_factory=dict,
    )

    configuration: CartoonGenerationConfig = Field(
        default_factory=CartoonGenerationConfig,
    )


class SceneOutline(BaseModel):
    """Compact scene contract produced by the global planning pass."""

    model_config = ConfigDict(
        extra="forbid",
    )

    id: str = Field(
        min_length=1,
        max_length=48,
    )

    title: str = Field(
        min_length=1,
        max_length=72,
    )

    objective: str = Field(
        min_length=1,
        max_length=140,
    )

    mechanism: MechanismKind

    key_points: list[str] = Field(
        min_length=1,
        max_length=6,
    )

    process_beats: list[str] = Field(
        min_length=2,
        max_length=6,
    )

    entry_state: str = Field(
        min_length=1,
        max_length=180,
    )

    exit_state: str = Field(
        min_length=1,
        max_length=180,
    )

    estimated_seconds: int = Field(
        default=18,
        ge=6,
        le=50,
    )

    @field_validator("id")
    @classmethod
    def normalize_id(
        cls,
        value: str,
    ) -> str:
        return _token(
            value,
            "scene",
        )


class LessonOutline(BaseModel):
    """Global teaching plan. Detailed scenes are generated in parallel."""

    model_config = ConfigDict(
        extra="forbid",
    )

    title: str = Field(
        min_length=1,
        max_length=80,
    )

    course: str = Field(
        default="计算机科学",
        min_length=1,
        max_length=40,
    )

    topic: str = Field(
        min_length=1,
        max_length=60,
    )

    terminology: dict[str, str] = Field(
        default_factory=dict,
        max_length=24,
    )

    scenes: list[SceneOutline] = Field(
        min_length=2,
        max_length=6,
    )

    @model_validator(mode="after")
    def validate_outline(
        self,
    ) -> "LessonOutline":
        ids = [
            scene.id
            for scene in self.scenes
        ]

        if len(ids) != len(set(ids)):
            raise ValueError(
                "outline contains duplicate scene ids"
            )

        if not any(
            scene.mechanism != "structure"
            for scene in self.scenes
        ):
            raise ValueError(
                "outline must contain at least one process scene"
            )

        return self


class VisualNode(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    id: str = Field(
        min_length=1,
        max_length=48,
    )

    label: str = Field(
        min_length=1,
        max_length=72,
    )

    detail: str = Field(
        default="",
        max_length=120,
    )

    state: str = Field(
        default="idle",
        min_length=1,
        max_length=24,
    )

    parent_id: str | None = None

    value: str | int | float | None = None

    kind: VisualElementKind = "concept"

    group_id: str | None = None

    initially_visible: bool = True

    @field_validator(
        "id",
        "parent_id",
        "group_id",
    )
    @classmethod
    def normalize_id(
        cls,
        value: str | None,
    ) -> str | None:
        return (
            _token(value)
            if value
            else value
        )


class VisualEdge(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    source_id: str = Field(
        min_length=1,
        max_length=48,
    )

    target_id: str = Field(
        min_length=1,
        max_length=48,
    )

    label: str = Field(
        default="",
        max_length=48,
    )

    kind: EdgeKind = "directed"

    @field_validator(
        "source_id",
        "target_id",
    )
    @classmethod
    def normalize_id(
        cls,
        value: str,
    ) -> str:
        return _token(value)

    @model_validator(mode="after")
    def validate_endpoints(
        self,
    ) -> "VisualEdge":
        if self.source_id == self.target_id:
            raise ValueError(
                "visual edge cannot connect a node to itself"
            )

        return self


class VisualModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    kind: VisualKind

    label: str = Field(
        default="",
        max_length=80,
    )

    nodes: list[VisualNode] = Field(
        min_length=1,
        max_length=36,
    )

    edges: list[VisualEdge] = Field(
        default_factory=list,
        max_length=64,
    )

    @model_validator(mode="after")
    def validate_links(
        self,
    ) -> "VisualModel":
        ids = [
            node.id
            for node in self.nodes
        ]

        if len(ids) != len(set(ids)):
            raise ValueError(
                "visual model contains duplicate node ids"
            )

        known = set(ids)
        for node in self.nodes:
            if (
                node.parent_id
                and node.parent_id not in known
            ):
                raise ValueError(
                    f"node {node.id} references "
                    f"unknown parent {node.parent_id}"
                )

        edge_keys: set[
            tuple[str, str, str, str]
        ] = set()

        for edge in self.edges:
            if (
                edge.source_id not in known
                or edge.target_id not in known
            ):
                raise ValueError(
                    f"visual edge "
                    f"{edge.source_id}->{edge.target_id} "
                    "references an unknown node"
                )

            key = _edge_key(edge)
            if key in edge_keys:
                raise ValueError(
                    "visual model contains duplicate edge "
                    f"{edge.source_id}->{edge.target_id}"
                )

            edge_keys.add(key)

        return self


class TeachingAction(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    kind: ActionKind

    target_ids: list[str] = Field(
        default_factory=list,
        max_length=6,
    )

    source_id: str | None = None

    destination_id: str | None = None

    note: str = Field(
        default="",
        max_length=72,
    )

    duration_ms: int = Field(
        default=700,
        ge=160,
        le=4000,
    )

    intensity: Literal[
        "subtle",
        "normal",
        "strong",
    ] = "normal"

    @field_validator("target_ids")
    @classmethod
    def normalize_targets(
        cls,
        values: list[str],
    ) -> list[str]:
        return _unique_tokens(
            values,
            field_name="target_ids",
        )

    @field_validator(
        "source_id",
        "destination_id",
    )
    @classmethod
    def normalize_optional_id(
        cls,
        value: str | None,
    ) -> str | None:
        return (
            _token(value)
            if value
            else value
        )

    @model_validator(mode="after")
    def validate_action_shape(
        self,
    ) -> "TeachingAction":
        target_count = len(
            self.target_ids
        )

        if (
            self.kind
            in {
                "reveal",
                "focus",
                "mutate",
                "insert",
                "remove",
                "highlight",
            }
            and target_count < 1
        ):
            raise ValueError(
                f"action {self.kind} requires "
                "at least one target_id"
            )

        if (
            self.kind
            in {
                "compare",
                "traverse",
            }
            and target_count < 2
        ):
            raise ValueError(
                f"action {self.kind} requires "
                "at least two target_ids"
            )

        if self.kind in {
            "transfer",
            "connect",
        }:
            if (
                not self.source_id
                or not self.destination_id
            ):
                raise ValueError(
                    f"action {self.kind} requires "
                    "source_id and destination_id"
                )

            if (
                self.source_id
                == self.destination_id
            ):
                raise ValueError(
                    f"action {self.kind} requires "
                    "two different nodes"
                )

            if (
                self.source_id
                not in self.target_ids
                or self.destination_id
                not in self.target_ids
            ):
                raise ValueError(
                    f"action {self.kind} target_ids "
                    "must contain source_id "
                    "and destination_id"
                )

        elif (
            self.source_id is not None
            or self.destination_id is not None
        ):
            raise ValueError(
                f"action {self.kind} must not define "
                "source_id or destination_id"
            )

        return self


class StatePatch(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    op: PatchKind

    after_action_index: int = Field(
        ge=0,
        le=5,
    )

    target_id: str | None = None

    node: VisualNode | None = None

    edge: VisualEdge | None = None

    value: str | int | float | None = None

    @field_validator("target_id")
    @classmethod
    def normalize_target(
        cls,
        value: str | None,
    ) -> str | None:
        return (
            _token(value)
            if value
            else value
        )

    @model_validator(mode="after")
    def validate_payload(
        self,
    ) -> "StatePatch":
        if self.op == "add_node":
            if (
                self.node is None
                or self.target_id is not None
                or self.edge is not None
                or self.value is not None
            ):
                raise ValueError(
                    "add_node requires only node"
                )

        elif self.op in {
            "add_edge",
            "remove_edge",
        }:
            if (
                self.edge is None
                or self.target_id is not None
                or self.node is not None
                or self.value is not None
            ):
                raise ValueError(
                    f"{self.op} requires only edge"
                )

        elif self.op in {
            "remove_node",
            "set_label",
            "set_state",
            "set_value",
        }:
            if (
                not self.target_id
                or self.node is not None
                or self.edge is not None
            ):
                raise ValueError(
                    f"{self.op} requires target_id "
                    "and no node/edge"
                )

            if (
                self.op == "remove_node"
                and self.value is not None
            ):
                raise ValueError(
                    "remove_node must not define value"
                )

            if (
                self.op
                in {
                    "set_label",
                    "set_state",
                }
                and not isinstance(
                    self.value,
                    str,
                )
            ):
                raise ValueError(
                    f"{self.op} requires a string value"
                )

        return self


class TeachingStep(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    id: str = Field(
        min_length=1,
        max_length=48,
    )

    narration: str = Field(
        min_length=4,
        max_length=180,
    )

    focus_ids: list[str] = Field(
        default_factory=list,
        max_length=8,
    )

    actions: list[TeachingAction] = Field(
        min_length=1,
        max_length=6,
    )

    patches: list[StatePatch] = Field(
        default_factory=list,
        max_length=8,
    )

    @field_validator("id")
    @classmethod
    def normalize_id(
        cls,
        value: str,
    ) -> str:
        return _token(
            value,
            "step",
        )

    @field_validator("focus_ids")
    @classmethod
    def normalize_focus(
        cls,
        values: list[str],
    ) -> list[str]:
        return _unique_tokens(
            values,
            field_name="focus_ids",
        )

    @model_validator(mode="after")
    def validate_patch_timing(
        self,
    ) -> "TeachingStep":
        indexes = [
            patch.after_action_index
            for patch in self.patches
        ]

        if indexes != sorted(indexes):
            raise ValueError(
                "patches must be ordered "
                "by after_action_index"
            )

        if any(
            index >= len(self.actions)
            for index in indexes
        ):
            raise ValueError(
                "patch after_action_index "
                "exceeds the action list"
            )

        return self


class TeachingScene(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    id: str = Field(
        min_length=1,
        max_length=48,
    )

    title: str = Field(
        min_length=1,
        max_length=72,
    )

    objective: str = Field(
        min_length=1,
        max_length=140,
    )

    mode: TeachingMode

    mechanism: MechanismKind

    tag: str = Field(
        default="",
        max_length=36,
    )

    visual_model: VisualModel

    steps: list[TeachingStep] = Field(
        min_length=2,
        max_length=6,
    )

    @field_validator("id")
    @classmethod
    def normalize_id(
        cls,
        value: str,
    ) -> str:
        return _token(
            value,
            "scene",
        )

    @model_validator(mode="after")
    def validate_scene(
        self,
    ) -> "TeachingScene":
        step_ids = [
            step.id
            for step in self.steps
        ]

        if len(step_ids) != len(set(step_ids)):
            raise ValueError(
                f"scene {self.id} contains "
                "duplicate step ids"
            )

        replay_scene(self)

        problems = scene_motion_problems(
            self
        )

        if problems:
            raise ValueError(
                "; ".join(problems)
            )

        return self


class TeachingLesson(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    title: str = Field(
        min_length=1,
        max_length=80,
    )

    course: str = Field(
        default="计算机科学",
        min_length=1,
        max_length=40,
    )

    topic: str = Field(
        min_length=1,
        max_length=60,
    )

    scenes: list[TeachingScene] = Field(
        min_length=2,
        max_length=8,
    )

    @model_validator(mode="after")
    def validate_lesson(
        self,
    ) -> "TeachingLesson":
        ids = [
            scene.id
            for scene in self.scenes
        ]

        if len(ids) != len(set(ids)):
            raise ValueError(
                "lesson contains duplicate scene ids"
            )

        if not any(
            action.kind in _DYNAMIC_ACTIONS
            for scene in self.scenes
            for step in scene.steps
            for action in step.actions
        ):
            raise ValueError(
                "lesson does not contain "
                "any dynamic teaching process"
            )

        return self


def scene_motion_problems(
    scene: TeachingScene,
) -> list[str]:
    """Return mechanism-level motion problems without changing the scene."""

    required = _MECHANISM_ACTIONS.get(
        scene.mechanism
    )

    if not required:
        return []

    kinds = {
        action.kind
        for step in scene.steps
        for action in step.actions
    }

    if kinds & required:
        return []

    expected = "/".join(
        sorted(required)
    )

    return [
        f"scene {scene.id} mechanism "
        f"{scene.mechanism} requires one of: "
        f"{expected}"
    ]


def collect_lesson_motion_problems(
    lesson: TeachingLesson,
) -> list[str]:
    return [
        problem
        for scene in lesson.scenes
        for problem in scene_motion_problems(
            scene
        )
    ]


def replay_scene(
    scene: TeachingScene,
) -> VisualModel:
    """Replay actions and patches in timeline order and return the final state."""

    state = scene.visual_model.model_copy(
        deep=True
    )

    nodes = {
        node.id: node
        for node in state.nodes
    }

    edges = {
        _edge_key(edge): edge
        for edge in state.edges
    }

    def require_node(
        node_id: str,
    ) -> None:
        if node_id not in nodes:
            raise ValueError(
                f"scene {scene.id} references "
                f"unknown node {node_id}"
            )

    def apply_patch(
        patch: StatePatch,
    ) -> None:
        if patch.op == "add_node":
            assert patch.node is not None

            if patch.node.id in nodes:
                raise ValueError(
                    f"scene {scene.id} adds "
                    f"duplicate node {patch.node.id}"
                )

            if patch.node.parent_id:
                require_node(
                    patch.node.parent_id
                )

            nodes[patch.node.id] = (
                patch.node.model_copy(
                    deep=True
                )
            )
            return

        if patch.op == "remove_node":
            assert patch.target_id is not None

            require_node(
                patch.target_id
            )

            nodes.pop(
                patch.target_id
            )

            for key, edge in list(
                edges.items()
            ):
                if (
                    edge.source_id
                    == patch.target_id
                    or edge.target_id
                    == patch.target_id
                ):
                    edges.pop(key)

            return

        if patch.op in {
            "set_label",
            "set_state",
            "set_value",
        }:
            assert patch.target_id is not None

            require_node(
                patch.target_id
            )

            node = nodes[
                patch.target_id
            ]

            if patch.op == "set_label":
                node.label = str(
                    patch.value
                )

            elif patch.op == "set_state":
                node.state = str(
                    patch.value
                )

            else:
                node.value = patch.value

            return

        assert patch.edge is not None

        require_node(
            patch.edge.source_id
        )
        require_node(
            patch.edge.target_id
        )

        key = _edge_key(
            patch.edge
        )

        if patch.op == "add_edge":
            if key in edges:
                raise ValueError(
                    f"scene {scene.id} adds "
                    "duplicate edge "
                    f"{patch.edge.source_id}->"
                    f"{patch.edge.target_id}"
                )

            edges[key] = (
                patch.edge.model_copy(
                    deep=True
                )
            )

        else:
            if key not in edges:
                raise ValueError(
                    f"scene {scene.id} removes "
                    "unknown edge "
                    f"{patch.edge.source_id}->"
                    f"{patch.edge.target_id}"
                )

            edges.pop(key)

    for step in scene.steps:
        for focus_id in step.focus_ids:
            require_node(
                focus_id
            )

        patches_by_action: dict[
            int,
            list[StatePatch],
        ] = {}

        for patch in step.patches:
            patches_by_action.setdefault(
                patch.after_action_index,
                [],
            ).append(patch)

        for (
            action_index,
            action,
        ) in enumerate(
            step.actions
        ):
            pending_nodes = {
                patch.node.id
                for patch in patches_by_action.get(
                    action_index,
                    [],
                )
                if (
                    patch.op == "add_node"
                    and patch.node is not None
                )
            }

            action_ids = [
                *action.target_ids
            ]

            if action.source_id:
                action_ids.append(
                    action.source_id
                )

            if action.destination_id:
                action_ids.append(
                    action.destination_id
                )

            for node_id in action_ids:
                if node_id not in pending_nodes:
                    require_node(
                        node_id
                    )

            related_patches = (
                patches_by_action.get(
                    action_index,
                    [],
                )
            )

            if action.kind == "mutate":
                changed = {
                    patch.target_id
                    for patch in related_patches
                    if patch.op
                    in {
                        "set_label",
                        "set_state",
                        "set_value",
                    }
                }

                if not changed.intersection(
                    action.target_ids
                ):
                    raise ValueError(
                        f"scene {scene.id} "
                        f"step {step.id} "
                        "mutate action requires "
                        "a matching state patch"
                    )

            elif action.kind == "remove":
                removed = {
                    patch.target_id
                    for patch in related_patches
                    if patch.op
                    == "remove_node"
                }

                if not removed.intersection(
                    action.target_ids
                ):
                    raise ValueError(
                        f"scene {scene.id} "
                        f"step {step.id} "
                        "remove action requires "
                        "a matching remove_node patch"
                    )

            elif action.kind == "insert":
                inserted = {
                    patch.node.id
                    for patch in related_patches
                    if (
                        patch.op == "add_node"
                        and patch.node is not None
                    )
                }

                hidden_existing = {
                    node_id
                    for node_id
                    in action.target_ids
                    if (
                        node_id in nodes
                        and not nodes[
                            node_id
                        ].initially_visible
                    )
                }

                if (
                    not inserted.intersection(
                        action.target_ids
                    )
                    and not hidden_existing
                ):
                    raise ValueError(
                        f"scene {scene.id} "
                        f"step {step.id} "
                        "insert action must add "
                        "or reveal a target node"
                    )

            elif action.kind == "connect":
                assert (
                    action.source_id
                    is not None
                    and action.destination_id
                    is not None
                )

                staged_edges = [
                    *edges.values(),
                    *(
                        patch.edge
                        for patch
                        in related_patches
                        if (
                            patch.op == "add_edge"
                            and patch.edge
                            is not None
                        )
                    ),
                ]

                if not any(
                    {
                        edge.source_id,
                        edge.target_id,
                    }
                    == {
                        action.source_id,
                        action.destination_id,
                    }
                    for edge in staged_edges
                ):
                    raise ValueError(
                        f"scene {scene.id} "
                        f"step {step.id} "
                        "connect action has no "
                        "matching visual edge"
                    )

            for patch in related_patches:
                apply_patch(
                    patch
                )

    return VisualModel(
        kind=state.kind,
        label=state.label,
        nodes=list(
            nodes.values()
        ),
        edges=list(
            edges.values()
        ),
    )


def stage_visual_model(
    scene: TeachingScene,
) -> VisualModel:
    """Return every node and edge that can appear at any point in the scene."""

    nodes = {
        node.id: node.model_copy(
            deep=True
        )
        for node in scene.visual_model.nodes
    }

    edges = {
        _edge_key(edge): edge.model_copy(
            deep=True
        )
        for edge in scene.visual_model.edges
    }

    for step in scene.steps:
        for patch in step.patches:
            if (
                patch.op == "add_node"
                and patch.node is not None
            ):
                if patch.node.id in nodes:
                    raise ValueError(
                        f"scene {scene.id} "
                        "stages duplicate node "
                        f"{patch.node.id}"
                    )

                nodes[patch.node.id] = (
                    patch.node.model_copy(
                        deep=True
                    )
                )

            if patch.edge is not None:
                edges.setdefault(
                    _edge_key(
                        patch.edge
                    ),
                    patch.edge.model_copy(
                        deep=True
                    ),
                )

    return VisualModel(
        kind=scene.visual_model.kind,
        label=scene.visual_model.label,
        nodes=list(
            nodes.values()
        ),
        edges=list(
            edges.values()
        ),
    )


class AudioSynthesis(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="forbid",
    )

    path: Path

    duration_ms: int = Field(
        gt=0,
    )

    text: str = Field(
        min_length=1,
    )

    provider: str = Field(
        min_length=1,
    )

    voice: str = Field(
        min_length=1,
    )


class TimedAction(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    action_index: int = Field(
        ge=0,
    )

    action: TeachingAction

    start_ms: int = Field(
        ge=0,
    )

    duration_ms: int = Field(
        gt=0,
    )

    synthetic: bool = False


class TimedPatch(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    patch_index: int = Field(
        ge=0,
    )

    patch: StatePatch

    start_ms: int = Field(
        ge=0,
    )


class TimedStep(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    scene_id: str

    step: TeachingStep

    start_ms: int = Field(
        ge=0,
    )

    duration_ms: int = Field(
        gt=0,
    )

    audio_src: str = Field(
        min_length=1,
    )

    audio_duration_ms: int = Field(
        gt=0,
    )

    actions: list[TimedAction] = Field(
        min_length=1,
    )

    patches: list[TimedPatch] = Field(
        default_factory=list,
    )


class TimedScene(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    index: int = Field(
        ge=0,
    )

    scene: TeachingScene

    start_ms: int = Field(
        ge=0,
    )

    duration_ms: int = Field(
        gt=0,
    )

    steps: list[TimedStep] = Field(
        min_length=1,
    )


class CompositionPlan(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    total_duration_ms: int = Field(
        gt=0,
    )

    scenes: list[TimedScene] = Field(
        min_length=1,
    )