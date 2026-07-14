"""Semantic contract and typed scene recipes for HyperFrames teaching videos."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, create_model, field_validator, model_validator


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


class TeachingFunction(StrEnum):
    """The teaching job of a scene in an undergraduate CS explainer."""

    ORIENT = "orient"
    MODEL = "model"
    TRACE = "trace"
    COMPARE = "compare"
    CONSOLIDATE = "consolidate"


class AnimationMode(StrEnum):
    """Whether a scene is a static explanation or a replayable state change."""

    STATIC = "static"
    DYNAMIC = "dynamic"


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


_CONNECTED_VISUAL_KINDS = (
    VisualKind.MODEL,
    VisualKind.TREE,
    VisualKind.FLOW,
    VisualKind.STATE,
    VisualKind.MEMORY,
    VisualKind.NETWORK,
)
_STATIC_ONLY_VISUAL_KINDS = tuple(
    kind for kind in VisualKind if kind not in _CONNECTED_VISUAL_KINDS
)

_STORYBOARD_SCENE_JSON_SCHEMA = {
    "allOf": [
        {
            "if": {
                "properties": {"animation_mode": {"const": "dynamic"}},
                "required": ["animation_mode"],
            },
            "then": {
                "properties": {
                    "visual_kind": {
                        "enum": [kind.value for kind in _CONNECTED_VISUAL_KINDS]
                    }
                }
            },
        }
    ]
}


_FIRST_STORYBOARD_SCENE_SCHEMA = {
    "properties": {
        "layout": {"const": SceneLayout.HERO.value},
        "teaching_function": {"const": TeachingFunction.ORIENT.value},
    },
    "required": ["layout", "teaching_function"],
}
_LAST_STORYBOARD_SCENE_SCHEMA = {
    "properties": {
        "layout": {"const": SceneLayout.RECAP.value},
        "teaching_function": {"const": TeachingFunction.CONSOLIDATE.value},
    },
    "required": ["layout", "teaching_function"],
}


def _storyboard_length_schema(scene_count: int) -> dict[str, Any]:
    return {
        "properties": {
            "scenes": {
                "minItems": scene_count,
                "maxItems": scene_count,
                "prefixItems": [
                    _FIRST_STORYBOARD_SCENE_SCHEMA,
                    *({} for _index in range(scene_count - 2)),
                    _LAST_STORYBOARD_SCENE_SCHEMA,
                ],
            }
        }
    }


_STORYBOARD_JSON_SCHEMA = {
    "allOf": [
        {
            "anyOf": [
                _storyboard_length_schema(5),
                _storyboard_length_schema(6),
            ]
        },
        {
            "properties": {
                "scenes": {
                    "contains": {
                        "properties": {"animation_mode": {"const": "dynamic"}},
                        "required": ["animation_mode"],
                    },
                    "minContains": 3,
                }
            }
        },
        *[
            {
                "properties": {
                    "scenes": {
                        "contains": {
                            "properties": {"teaching_function": {"const": function.value}},
                            "required": ["teaching_function"],
                        }
                    }
                }
            }
            for function in (
                TeachingFunction.MODEL,
                TeachingFunction.TRACE,
                TeachingFunction.COMPARE,
            )
        ],
    ]
}


class MotionKind(StrEnum):
    REVEAL = "reveal"
    FOCUS = "focus"
    TRAVERSE = "traverse"
    TRANSFER = "transfer"
    TRANSFORM = "transform"
    COMPARE = "compare"
    EMPHASIZE = "emphasize"


_PATH_MOTION_KINDS = (MotionKind.TRAVERSE, MotionKind.TRANSFER)
_DIRECT_MOTION_KINDS = tuple(kind for kind in MotionKind if kind not in _PATH_MOTION_KINDS)
_MOTION_JSON_SCHEMA = {
    "allOf": [
        {
            "if": {
                "properties": {"kind": {"enum": [kind.value for kind in _PATH_MOTION_KINDS]}},
                "required": ["kind"],
            },
            "then": {
                "properties": {"path_ids": {"minItems": 2}},
                "required": ["path_ids"],
            },
        },
        {
            "if": {
                "properties": {"kind": {"enum": [kind.value for kind in _DIRECT_MOTION_KINDS]}},
                "required": ["kind"],
            },
            "then": {"properties": {"path_ids": {"maxItems": 0}}},
        },
    ]
}


class VisualRole(StrEnum):
    """The semantic job of an object inside a knowledge model.

    Roles give the renderer useful visual hierarchy without naming any specific
    discipline. Domain objects are supplied by the model as ordinary visual
    items instead of being hard-coded into the rendering contract.
    """

    ENTITY = "entity"
    VALUE = "value"
    OPERATION = "operation"
    STATE = "state"
    CONTAINER = "container"
    SIGNAL = "signal"
    TERM = "term"


LAYOUT_GUIDANCE: dict[SceneLayout, str] = {
    SceneLayout.HERO: "章节开场：一个核心命题配少量关键概念，画面留白。",
    SceneLayout.CONCEPT_MAP: "概念关系：中心概念和 3 到 6 个关系节点，强调层次。",
    SceneLayout.PROCESS_LANE: "过程推演：按时间或数据方向逐步推进，避免长段文字。",
    SceneLayout.STATE_LAB: "状态演化：展示前后状态差异和一次关键变换。",
    SceneLayout.SYSTEM_MAP: "系统组成：组件、边界和消息/数据流。",
    SceneLayout.COMPARISON_BOARD: "对比辨析：只比较两个对象，并给出明确判断维度。",
    SceneLayout.CODE_STUDIO: "代码讲解：短代码片段配执行轨迹；不展示冗长源码。",
    SceneLayout.FORMULA_LAB: "公式推导：一个公式、变量含义和一个代入/变化过程。",
    SceneLayout.RECAP: "收束总结：回顾 3 个以内可迁移结论，不新增知识。",
}

if set(LAYOUT_GUIDANCE) != set(SceneLayout):
    raise RuntimeError("Cartoon layout registry is not exhaustive")


VISUAL_GUIDANCE: dict[VisualKind, str] = {
    VisualKind.NODES: "彼此独立或弱关联的概念节点；不要伪造连线。",
    VisualKind.MODEL: "领域对象与真实关系组成的通用心智模型；对象必须来自教学素材。",
    VisualKind.TREE: "每个 item 都是一个实际树节点，edge 只能表示父子关系；禁止把序列、面板、整棵树或操作指针当成树节点。",
    VisualKind.FLOW: "每个 item 是一个真实步骤、事件或处理阶段，edge 表示执行或数据方向。",
    VisualKind.STATE: "每个 item 是参与状态变化的实体，states 展示同一批实体如何迁移。",
    VisualKind.MEMORY: "每个 item 是真实内存单元、变量、地址或指针，edge 表示引用或寻址关系。",
    VisualKind.NETWORK: "每个 item 是端点、组件、链路节点或报文，edge 表示真实通信方向。",
    VisualKind.CODE: "用短代码和少量变量/执行焦点配合讲解；必须输出 code。",
    VisualKind.FORMULA: "用一个核心公式和变量/项配合推导；必须输出 formula。",
    VisualKind.COMPARISON: "只组织两个待比较对象及清晰判断维度，不输出无关第三方卡片。",
    VisualKind.METRICS: "每个 item 是有明确含义的指标、数值或结论，不使用装饰数字。",
}

if set(VISUAL_GUIDANCE) != set(VisualKind):
    raise RuntimeError("Cartoon visual registry is not exhaustive")


def motion_values(kind: VisualKind) -> str:
    available = (
        tuple(MotionKind)
        if kind in _CONNECTED_VISUAL_KINDS
        else _DIRECT_MOTION_KINDS
    )
    return ", ".join(item.value for item in available)


def scene_motion_guidance(kind: VisualKind) -> str:
    direct_example = (
        '{"kind":"emphasize","target_ids":["item-a"],"duration_ms":700}'
    )
    if kind not in _CONNECTED_VISUAL_KINDS:
        return (
            f"当前 `{kind.value}` 没有可遍历的关系路径，只能使用非路径动作。"
            f"合法动作示例：{direct_example}。禁止 transfer、traverse 和 path_ids。"
        )
    path_example = (
        '{"kind":"traverse","target_ids":["item-a","item-b"],'
        '"path_ids":["item-a","item-b"],"duration_ms":800}'
    )
    return (
        "每个 motion 都必须有 target_ids。非路径动作示例："
        f"{direct_example}。transfer/traverse 还必须有 path_ids，且 target_ids "
        f"也不能省略；路径动作示例：{path_example}。示例 id 必须替换为当前 visual.items 的真实 id。"
    )


def scene_relationship_guidance(
    kind: VisualKind,
    animation_mode: AnimationMode,
) -> str:
    if animation_mode == AnimationMode.DYNAMIC:
        return (
            "输出 visual.states，所有关系边放在各 state.edges；"
            "禁止输出顶层 visual.edges。"
        )
    if kind in _CONNECTED_VISUAL_KINDS:
        return (
            "禁止输出 visual.states；当可见对象多于一个时，"
            "在顶层 visual.edges 输出真实关系。"
        )
    return (
        f"当前 `{kind.value}` 是非关系图形：禁止输出 visual.states 和 "
        "visual.edges，使用位置、内容和直接动作组织画面。"
    )


def connected_visual_kind_values() -> str:
    return "、".join(f"`{kind.value}`" for kind in _CONNECTED_VISUAL_KINDS)


def static_only_visual_kind_values() -> str:
    return "、".join(f"`{kind.value}`" for kind in _STATIC_ONLY_VISUAL_KINDS)


def role_values() -> str:
    return "、".join(f"`{role.value}`" for role in VisualRole)


def visual_kind_values() -> str:
    return "、".join(f"`{kind.value}`" for kind in VisualKind)


def visual_kind_guidance() -> str:
    return "\n".join(f"- `{kind.value}`：{instruction}" for kind, instruction in VISUAL_GUIDANCE.items())


def scene_visual_guidance(kind: VisualKind) -> str:
    return VISUAL_GUIDANCE[kind]


def layout_kind_values() -> str:
    return "、".join(f"`{layout.value}`" for layout in SceneLayout)


def layout_guidance() -> str:
    return "\n".join(f"- `{layout.value}`：{instruction}" for layout, instruction in LAYOUT_GUIDANCE.items())


def _id(value: str, fallback: str) -> str:
    normalized = "".join(char if char.isalnum() or char in "-_" else "-" for char in value.strip().lower())
    return normalized.strip("-_") or fallback


class CartoonGenerationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pace: Literal["calm", "balanced", "fast"] = "balanced"
    visual_density: Literal["moderate", "rich", "intensive"] = "rich"
    target_duration_seconds: int = Field(default=180, ge=90, le=600)
    voice: Literal["teacher", "coach"] = "teacher"


class CartoonResourceMetadata(BaseModel):
    """Single persisted and frontend-visible contract for a cartoon resource."""

    model_config = ConfigDict(extra="forbid")
    agent_id: Literal["cartoon"] = "cartoon"
    schema_version: Literal["cartoon/v7"] = "cartoon/v7"
    engine: Literal["hyperframes"] = "hyperframes"
    has_audio: Literal[True] = True
    video_url: str = Field(min_length=1)
    preview_url: str = Field(min_length=1)
    duration_seconds: float = Field(gt=0)
    scene_count: int = Field(ge=5, le=6)

    @field_validator("video_url")
    @classmethod
    def validate_video_url(cls, value: str) -> str:
        value = value.strip()
        if not value.endswith(".mp4"):
            raise ValueError("video_url must reference an MP4 file")
        return value

    @field_validator("preview_url")
    @classmethod
    def validate_preview_url(cls, value: str) -> str:
        value = value.strip()
        if not value.endswith(".html"):
            raise ValueError("preview_url must reference an HTML file")
        return value


class CartoonBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")
    learning_need: str = Field(min_length=1, max_length=500)
    instruction_context: dict[str, Any] = Field(default_factory=dict)
    source_materials: list[str] = Field(default_factory=list, max_length=12)
    knowledge_points: list[str] = Field(default_factory=list, max_length=30)
    weak_knowledge_points: list[str] = Field(default_factory=list, max_length=20)
    configuration: CartoonGenerationConfig = Field(default_factory=CartoonGenerationConfig)


class StoryboardScene(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra=_STORYBOARD_SCENE_JSON_SCHEMA)
    id: str = Field(min_length=1, max_length=48)
    title: str = Field(min_length=1, max_length=54)
    objective: str = Field(min_length=1, max_length=110)
    teaching_function: TeachingFunction
    layout: SceneLayout
    visual_kind: VisualKind
    animation_mode: AnimationMode

    @field_validator("id")
    @classmethod
    def normalize_id(cls, value: str) -> str:
        return _id(value, "scene")

class CartoonStoryboard(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra=_STORYBOARD_JSON_SCHEMA)
    title: str = Field(min_length=1, max_length=72)
    course: str = Field(default="计算机类本科课程", min_length=1, max_length=40)
    scenes: list[StoryboardScene] = Field(min_length=5, max_length=6)

    @model_validator(mode="after")
    def unique_scenes(self) -> "CartoonStoryboard":
        if len({scene.id for scene in self.scenes}) != len(self.scenes):
            raise ValueError("storyboard contains duplicate scene ids")
        if self.scenes[0].layout != SceneLayout.HERO or self.scenes[-1].layout != SceneLayout.RECAP:
            raise ValueError("storyboard must begin with hero and end with recap")
        if self.scenes[0].teaching_function != TeachingFunction.ORIENT:
            raise ValueError("storyboard must begin with an orient scene")
        if self.scenes[-1].teaching_function != TeachingFunction.CONSOLIDATE:
            raise ValueError("storyboard must end with a consolidate scene")
        required = {TeachingFunction.MODEL, TeachingFunction.TRACE, TeachingFunction.COMPARE}
        actual = {scene.teaching_function for scene in self.scenes}
        if not required <= actual:
            raise ValueError("storyboard must include model, trace, and compare scenes")
        if len({scene.layout for scene in self.scenes}) < 4:
            raise ValueError("storyboard needs at least four layouts")
        dynamic_scenes = [scene for scene in self.scenes if scene.animation_mode == AnimationMode.DYNAMIC]
        if len(dynamic_scenes) < 3:
            raise ValueError("storyboard needs at least three dynamic scenes")
        invalid_dynamic = [
            scene.id
            for scene in dynamic_scenes
            if scene.visual_kind not in _CONNECTED_VISUAL_KINDS
        ]
        if invalid_dynamic:
            raise ValueError(
                "dynamic scenes require a connected visual kind: "
                + ", ".join(invalid_dynamic)
            )
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
    source_id: str = Field(
        min_length=1,
        max_length=48,
        description=(
            "Must equal one visual.items[].id, must differ from target_id, and may not "
            "duplicate another edge's source_id/target_id pair; edge ids are invalid here."
        ),
    )
    target_id: str = Field(
        min_length=1,
        max_length=48,
        description=(
            "Must equal one visual.items[].id, must differ from source_id, and may not "
            "duplicate another edge's source_id/target_id pair; edge ids are invalid here."
        ),
    )
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
    annotation: str = Field(min_length=1, max_length=72)
    items: list[VisualStateItem] = Field(
        min_length=1,
        max_length=MAX_SCENE_VISUAL_ITEMS,
        description="All visual items visible in this state; every id must equal one visual.items[].id.",
    )
    edges: list[VisualEdge] = Field(
        default_factory=list,
        max_length=MAX_SCENE_VISUAL_ITEMS * 2,
        description=(
            "Relationships visible in this snapshot. Every source_id and target_id "
            "must also occur in this same state's items[].id list. Edge ids and ordered "
            "source_id/target_id pairs must be unique; self-edges are invalid."
        ),
    )
    focus_item_ids: list[str] = Field(
        min_length=1,
        max_length=MAX_SCENE_VISUAL_ITEMS,
        description="Visible visual.items[].id values only; never use an edge id or state id.",
    )

    @field_validator("id")
    @classmethod
    def normalize_id(cls, value: str) -> str:
        return _id(value, "state")

    @model_validator(mode="after")
    def unique_items(self) -> "VisualState":
        if len({item.id for item in self.items}) != len(self.items):
            raise ValueError("visual state contains duplicate item ids")
        item_ids = {item.id for item in self.items}
        if not set(self.focus_item_ids) <= item_ids:
            raise ValueError("visual state focus references an invisible item")
        return self


class SceneVisual(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: VisualKind
    items: list[VisualItem] = Field(
        min_length=1,
        max_length=MAX_SCENE_VISUAL_ITEMS,
        description=(
            "Complete stable scene-object registry with a hard maximum declared by this schema. "
            "Merge supporting facts into detail/value instead of adding excess objects. All state, "
            "edge, focus and motion references resolve to these unique ids."
        ),
    )
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
            if self.kind in _CONNECTED_VISUAL_KINDS and len(self.states) < 3:
                raise ValueError(f"dynamic {self.kind.value} visual requires initial, mechanism, and result states")
            for state in self.states:
                state_item_ids = {item.id for item in state.items}
                if not state_item_ids <= item_ids:
                    raise ValueError(f"visual state {state.id} references unknown items")
                self._validate_edges(state_item_ids, state.edges, require_relationship=False)
            if (
                self.kind in _CONNECTED_VISUAL_KINDS
                and len(item_ids) > 1
                and not any(state.edges for state in self.states)
            ):
                raise ValueError(f"dynamic {self.kind.value} visual requires relationships across its states")
            if self.kind == VisualKind.TREE:
                final_state = self.states[-1]
                self._validate_tree(
                    {item.id for item in final_state.items},
                    final_state.edges,
                    require_connected=True,
                )
        else:
            self._validate_edges(item_ids, self.edges, require_relationship=True)
        return self

    def _validate_edges(
        self,
        item_ids: set[str],
        edges: list[VisualEdge],
        *,
        require_relationship: bool,
    ) -> None:
        pairs = {(edge.source_id, edge.target_id) for edge in edges}
        if len(pairs) != len(edges):
            raise ValueError("visual contains duplicate edge endpoints")
        invalid_edges = [edge.id for edge in edges if edge.source_id not in item_ids or edge.target_id not in item_ids or edge.source_id == edge.target_id]
        if invalid_edges:
            raise ValueError(f"visual contains invalid edges: {sorted(invalid_edges)}")
        if require_relationship and self.kind in _CONNECTED_VISUAL_KINDS and len(item_ids) > 1 and not edges:
            raise ValueError(f"{self.kind.value} visual requires edges")
        if self.kind == VisualKind.TREE:
            self._validate_tree(item_ids, edges, require_connected=require_relationship)

    @staticmethod
    def _validate_tree(
        item_ids: set[str],
        edges: list[VisualEdge],
        *,
        require_connected: bool,
    ) -> None:
        if len(edges) > len(item_ids) - 1:
            raise ValueError("tree visual has too many parent edges")
        parents = {edge.target_id for edge in edges}
        if len(parents) != len(edges):
            raise ValueError("tree visual contains a node with multiple parents")
        roots = item_ids - parents
        if require_connected and (len(edges) != len(item_ids) - 1 or len(roots) != 1):
            raise ValueError("tree visual requires exactly one connected root")
        if not roots:
            raise ValueError("tree visual contains a cycle")
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
            raise ValueError("tree visual contains a cycle")


class _MotionFields(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: MotionKind
    # A motion can address the whole visual. This must stay aligned with
    # SceneVisual.items because the compiler accepts every referenced target.
    target_ids: list[str] = Field(
        min_length=1,
        max_length=MAX_SCENE_VISUAL_ITEMS,
        description=(
            "Required for every motion, including transfer and traverse. Must contain "
            "unique visual.items[].id values only; never target an edge id or state id."
        ),
    )
    path_ids: list[str] = Field(
        default_factory=list,
        max_length=MAX_SCENE_VISUAL_ITEMS,
        description="Ordered visual.items[].id route. Required only for transfer/traverse and must contain at least two ids.",
    )
    duration_ms: int = Field(default=700, ge=240, le=2200)

    @field_validator("target_ids")
    @classmethod
    def normalize_targets(cls, values: list[str]) -> list[str]:
        normalized = [_id(value, "item") for value in values]
        if len(normalized) != len(set(normalized)):
            raise ValueError("motion beat contains duplicate targets")
        return normalized

    @field_validator("path_ids")
    @classmethod
    def normalize_path(cls, values: list[str]) -> list[str]:
        return [_id(value, "item") for value in values]


class MotionBeat(_MotionFields):
    model_config = ConfigDict(extra="forbid", json_schema_extra=_MOTION_JSON_SCHEMA)

    @model_validator(mode="after")
    def validate_path(self) -> "MotionBeat":
        if self.kind in _PATH_MOTION_KINDS:
            if len(self.path_ids) < 2:
                raise ValueError(f"{self.kind.value} motion requires a path with at least two objects")
        elif self.path_ids:
            raise ValueError("only transfer and traverse motions may declare path_ids")
        return self


class DirectMotionBeat(MotionBeat):
    """A motion for visuals without a traversable relationship graph."""

    model_config = ConfigDict(extra="forbid", json_schema_extra=None)
    kind: Literal[
        MotionKind.REVEAL,
        MotionKind.FOCUS,
        MotionKind.TRANSFORM,
        MotionKind.COMPARE,
        MotionKind.EMPHASIZE,
    ]
    target_ids: list[str] = Field(
        min_length=1,
        max_length=MAX_SCENE_VISUAL_ITEMS,
        description=(
            "Required visual.items[].id values only; never target an edge id or state id."
        ),
    )
    path_ids: list[str] = Field(default_factory=list, max_length=0)


class TeachingStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=48)
    narration: str = Field(min_length=8, max_length=150)
    focus: str = Field(min_length=1, max_length=64)
    state_id: str = Field(
        default="",
        max_length=48,
        description="For dynamic scenes, must equal one visual.states[].id. Omit for static scenes.",
    )
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
    teaching_function: TeachingFunction
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
        unknown_paths = {
            target
            for step in self.steps
            for motion in step.motions
            for target in motion.path_ids
            if target not in known
        }
        if unknown_paths:
            raise ValueError(f"motion path references unknown items: {sorted(unknown_paths)}")
        state_ids = {state.id for state in self.visual.states}
        referenced_states = {step.state_id for step in self.steps if step.state_id}
        if referenced_states - state_ids:
            raise ValueError(f"steps reference unknown visual states: {sorted(referenced_states - state_ids)}")
        if state_ids and any(not step.state_id for step in self.steps):
            raise ValueError("dynamic visual requires every teaching step to declare state_id")
        if not state_ids and referenced_states:
            raise ValueError("static visual cannot declare state_id")
        if state_ids and len(self.steps) < 3:
            raise ValueError("dynamic visual requires at least three teaching steps")
        return self


def teaching_scene_contract(
    scene: StoryboardScene,
    *,
    max_visual_items: int = MAX_SCENE_VISUAL_ITEMS,
) -> type[TeachingScene]:
    """Build the exact schema for one storyboard scene composition call."""

    if not 1 <= max_visual_items <= MAX_SCENE_VISUAL_ITEMS:
        raise ValueError(
            f"max_visual_items must be between 1 and {MAX_SCENE_VISUAL_ITEMS}"
        )

    if scene.animation_mode == AnimationMode.DYNAMIC:
        states_field = (
            list[VisualState],
            Field(min_length=3, max_length=4),
        )
        edges_field = (
            list[VisualEdge],
            Field(default_factory=list, max_length=0),
        )
        state_id_field = (
            str,
            Field(min_length=1, max_length=48),
        )
        steps_field = Field(min_length=3, max_length=4)
    else:
        states_field = (
            list[VisualState],
            Field(default_factory=list, max_length=0),
        )
        edge_limit = (
            max_visual_items * 2
            if scene.visual_kind in _CONNECTED_VISUAL_KINDS
            else 0
        )
        edges_field = (
            list[VisualEdge],
            Field(default_factory=list, max_length=edge_limit),
        )
        state_id_field = (
            Literal[""],
            "",
        )
        steps_field = Field(min_length=2, max_length=4)

    visual_contract = create_model(
        "SceneVisualContract",
        __base__=SceneVisual,
        __module__=__name__,
        kind=(Literal[scene.visual_kind], ...),
        items=(
            list[VisualItem],
            Field(
                min_length=1,
                max_length=max_visual_items,
                description=(
                    f"Hard limit: at most {max_visual_items} stable scene objects. "
                    "Merge supporting facts into detail/value; never exceed this list."
                ),
            ),
        ),
        edges=edges_field,
        states=states_field,
    )
    motion_base = (
        MotionBeat
        if scene.visual_kind in _CONNECTED_VISUAL_KINDS
        else DirectMotionBeat
    )
    motion_contract = create_model(
        f"SceneMotionContract_{scene.id.replace('-', '_')}",
        __base__=motion_base,
        __module__=__name__,
        target_ids=(
            list[str],
            Field(
                min_length=1,
                max_length=max_visual_items,
                description=(
                    "Required for every motion. Use unique visual.items[].id values only; "
                    "never target an edge id or state id."
                ),
            ),
        ),
    )
    step_contract = create_model(
        "TeachingStepContract",
        __base__=TeachingStep,
        __module__=__name__,
        state_id=state_id_field,
        motions=(list[motion_contract], Field(min_length=1, max_length=4)),
    )
    return create_model(
        f"TeachingSceneContract_{scene.id.replace('-', '_')}",
        __base__=TeachingScene,
        __module__=__name__,
        id=(Literal[scene.id], ...),
        title=(Literal[scene.title], ...),
        objective=(Literal[scene.objective], ...),
        teaching_function=(Literal[scene.teaching_function], ...),
        layout=(Literal[scene.layout], ...),
        visual=(visual_contract, ...),
        steps=(list[step_contract], steps_field),
    )


def teaching_scene_example(scene: StoryboardScene) -> dict[str, Any]:
    """Return a grammar-only example that is valid for one exact scene contract."""

    example_objects: dict[VisualKind, list[tuple[str, str]]] = {
        VisualKind.NODES: [("item-a", "素材对象甲"), ("item-b", "素材对象乙"), ("item-c", "素材对象丙")],
        VisualKind.MODEL: [("entity-a", "领域对象甲"), ("relation-core", "关系载体"), ("entity-b", "领域对象乙")],
        VisualKind.TREE: [("parent", "父级对象"), ("child-a", "子级对象甲"), ("child-b", "子级对象乙")],
        VisualKind.FLOW: [("stage-a", "阶段甲"), ("stage-b", "阶段乙"), ("stage-c", "阶段丙")],
        VisualKind.STATE: [("entity-a", "状态对象甲"), ("entity-b", "状态对象乙"), ("entity-c", "状态对象丙")],
        VisualKind.MEMORY: [("cell-a", "存储对象甲"), ("reference", "引用关系"), ("cell-b", "存储对象乙")],
        VisualKind.NETWORK: [("endpoint-a", "通信对象甲"), ("link", "通信媒介"), ("endpoint-b", "通信对象乙")],
        VisualKind.CODE: [("symbol-a", "代码对象甲"), ("operation", "执行位置"), ("symbol-b", "代码对象乙")],
        VisualKind.FORMULA: [("term-a", "公式项甲"), ("operator", "运算关系"), ("term-b", "公式项乙")],
        VisualKind.COMPARISON: [("subject-a", "比较对象甲"), ("subject-b", "比较对象乙")],
        VisualKind.METRICS: [("evidence-a", "素材结论甲"), ("evidence-b", "素材结论乙"), ("evidence-c", "素材结论丙")],
    }
    objects = example_objects[scene.visual_kind]
    items = [{"id": item_id, "label": label} for item_id, label in objects]
    item_ids = [item_id for item_id, _label in objects]
    first_id = item_ids[0]
    middle_id = item_ids[1]
    result_id = item_ids[-1]

    if scene.visual_kind == VisualKind.TREE:
        completed_edges = [
            {"id": "parent-to-a", "source_id": "parent", "target_id": "child-a"},
            {"id": "parent-to-b", "source_id": "parent", "target_id": "child-b"},
        ]
    else:
        completed_edges = [
            {"id": "first-to-middle", "source_id": first_id, "target_id": middle_id},
            {"id": "middle-to-result", "source_id": middle_id, "target_id": result_id},
        ]
    base: dict[str, Any] = {
        "id": scene.id,
        "title": scene.title,
        "objective": scene.objective,
        "teaching_function": scene.teaching_function.value,
        "layout": scene.layout.value,
        "visual": {
            "kind": scene.visual_kind.value,
            "items": items,
        },
        "takeaway": "此处必须改写为素材支持的可迁移结论。",
    }

    if scene.animation_mode == AnimationMode.DYNAMIC:
        base["visual"]["states"] = [
            {
                "id": "initial",
                "annotation": "此处改写为素材中的初始条件",
                "items": [{"id": first_id}],
                "edges": [],
                "focus_item_ids": [first_id],
            },
            {
                "id": "running",
                "annotation": "此处改写为素材中的关键变化",
                "items": [{"id": first_id}, {"id": middle_id}],
                "edges": [
                    {"id": "first-to-middle", "source_id": first_id, "target_id": middle_id}
                ],
                "focus_item_ids": [first_id, middle_id],
            },
            {
                "id": "completed",
                "annotation": "此处改写为素材中的结果状态",
                "items": [{"id": item_id} for item_id in item_ids],
                "edges": completed_edges,
                "focus_item_ids": [middle_id, result_id],
            },
        ]
        base["steps"] = [
            {
                "id": "step-initial",
                "narration": "此处必须使用素材术语讲清本幕开始时可观察的对象与条件。",
                "focus": "素材中的初始条件",
                "state_id": "initial",
                "motions": [
                    {"kind": "reveal", "target_ids": [first_id], "duration_ms": 700}
                ],
            },
            {
                "id": "step-running",
                "narration": "此处必须使用素材术语讲清对象沿真实关系发生的关键变化。",
                "focus": "素材中的关键变化",
                "state_id": "running",
                "motions": [
                    {
                        "kind": "transfer",
                        "target_ids": [first_id, middle_id],
                        "path_ids": [first_id, middle_id],
                        "duration_ms": 800,
                    }
                ],
            },
            {
                "id": "step-completed",
                "narration": "此处必须使用素材术语解释变化结果以及它支持的教学结论。",
                "focus": "素材中的结果状态",
                "state_id": "completed",
                "motions": [
                    {"kind": "transform", "target_ids": [result_id], "duration_ms": 700}
                ],
            },
        ]
    else:
        if scene.visual_kind in _CONNECTED_VISUAL_KINDS:
            base["visual"]["edges"] = completed_edges
        if scene.visual_kind == VisualKind.CODE:
            base["visual"]["code"] = "result = transform(input)"
        if scene.visual_kind == VisualKind.FORMULA:
            base["visual"]["formula"] = "result = f(input)"
        base["steps"] = [
            {
                "id": "step-structure",
                "narration": "此处必须使用素材术语介绍本幕真实存在的对象及其结构。",
                "focus": "素材中的对象结构",
                "motions": [
                    {"kind": "reveal", "target_ids": [first_id, middle_id], "duration_ms": 700}
                ],
            },
            {
                "id": "step-conclusion",
                "narration": "此处必须根据素材中的对象关系提炼本幕需要掌握的结论。",
                "focus": "素材中的教学结论",
                "motions": [
                    {"kind": "emphasize", "target_ids": [result_id], "duration_ms": 700}
                ],
            },
        ]

    teaching_scene_contract(scene).model_validate(base)
    return base


class TeachingLesson(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=72)
    course: str = Field(default="计算机类本科课程", min_length=1, max_length=40)
    scenes: list[TeachingScene] = Field(min_length=5, max_length=6)

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
        if len(animated_models) < 3:
            raise ValueError("lesson needs at least three animated knowledge-model scenes")
        functions = {scene.teaching_function for scene in self.scenes}
        required = {TeachingFunction.ORIENT, TeachingFunction.MODEL, TeachingFunction.TRACE, TeachingFunction.COMPARE, TeachingFunction.CONSOLIDATE}
        if not required <= functions:
            raise ValueError("lesson must cover orient, model, trace, compare, and consolidate teaching functions")
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
