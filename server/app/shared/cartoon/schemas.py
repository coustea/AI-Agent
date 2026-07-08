"""Structured contracts for deterministic animated teaching videos.

面向计算机理论知识的动画演示 — 通用可视化原语体系。
支持数据结构、算法、数学、数据库、编译原理、操作系统、离散数学等
所有计算机本科理论课程的动态演示。

核心设计：不按学科分类，按可视化模式分类。
LLM 根据 learning_need 自动选择合适的可视化模式组合。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _coerce_enum(
    value: Any,
    valid: tuple[str, ...],
    default: str,
    mapping: dict[str, str] | None = None,
) -> str:
    """枚举容错归一化：映射已知别名，未知值回落到默认值，绝不抛 Literal 校验错误。

    生成可靠性优先于枚举完美——LLM 偶发产出 schema 外的枚举值时，强制归一化到
    语义最通用的默认值，保证只要结构正确就能通过校验，避免整个分镜生成失败。
    """
    if value is None:
        return default
    s = str(value).strip().lower()
    if mapping and s in mapping:
        return mapping[s]
    if s in valid:
        return s
    return default


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceArtifact(StrictModel):
    agent_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    materials: list[str] = Field(default_factory=list, max_length=12)


# ===================== Visual Kind — 通用可视化原语 =====================

VisualKind = Literal[
    "node",
    "label",
    "code",
    "metric",
    "formula",
    "packet",
    "cell",
    "state",
    "step",
    "array",
    "stack",
    "queue",
    "table",
]


# ===================== Animation Action — 通用操作型动画 =====================

AnimationAction = Literal[
    "reveal",
    "focus",
    "transfer",
    "compare",
    "swap",
    "traverse",
    "branch",
    "state_change",
    "count",
    "insert",
    "remove",
    "highlight_path",
    "value_change",
    "shift",
    "highlight_code",
    "derive",
    "transform",
]


# ===================== Scene Layout & Role =====================

SceneRole = Literal[
    "hook",
    "concept",
    "process",
    "compare",
    "architecture",
    "code_trace",
    "derivation",
    "recap",
]

SceneLayout = Literal[
    "hero",
    "flow",
    "compare",
    "stack",
    "tree",
    "graph",
    "state_diagram",
    "code",
    "array_view",
    "queue_view",
    "table_view",
    "derivation",
    "grid",
    "recap",
]

_VISUAL_KINDS = get_args(VisualKind)
_ANIMATION_ACTIONS = get_args(AnimationAction)
_SCENE_ROLES = get_args(SceneRole)
_SCENE_LAYOUTS = get_args(SceneLayout)


class CaptionWord(StrictModel):
    text: str = Field(min_length=1)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)


class VisualElement(StrictModel):
    """A semantic teaching object rendered by the deterministic compiler."""

    id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,31}$")
    kind: VisualKind
    label: str = Field(default="", max_length=80)
    detail: str = Field(default="", max_length=1000)
    items: list[str] = Field(default_factory=list, max_length=30)
    value: str = Field(default="", max_length=1000)

    @field_validator("id", mode="before")
    @classmethod
    def normalize_id(cls, value: Any) -> str:
        if value is None:
            return ""
        s = str(value).strip().lower()
        if s and not s[0].isalpha():
            s = "n" + s
        import re

        s = re.sub(r"[^a-z0-9_-]", "_", s)
        return s[:32]

    @field_validator("kind", mode="before")
    @classmethod
    def normalize_kind(cls, value: str) -> str:
        mapping = {
            "text": "label",
            "header": "label",
            "list_item": "step",
            "array_view": "array",
            "array_cell": "cell",
            "list": "array",
            "box": "node",
            "rect": "node",
            "circle": "node",
            "block": "node",
            "pointer": "node",
            "card": "node",
        }
        return _coerce_enum(value, _VISUAL_KINDS, "node", mapping)

    @field_validator("items", mode="before")
    @classmethod
    def normalize_items(cls, value: Any) -> Any:
        if isinstance(value, list):
            return [str(x) for x in value]
        if isinstance(value, str):
            if value.startswith("[") and value.endswith("]"):
                try:
                    import ast

                    parsed = ast.literal_eval(value)
                    if isinstance(parsed, list):
                        return [str(x) for x in parsed]
                except Exception:
                    pass
            if "," in value:
                return [x.strip() for x in value.split(",")]
        return value


class VisualConnection(StrictModel):
    source: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,31}$")
    target: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,31}$")
    label: str = Field(default="", max_length=30)
    kind: Literal["edge", "pointer", "arrow", "transition"] = "edge"
    condition: str = Field(default="", max_length=30)

    @field_validator("kind", mode="before")
    @classmethod
    def normalize_conn_kind(cls, value: Any) -> str:
        return _coerce_enum(value, ("edge", "pointer", "arrow", "transition"), "edge")

    @field_validator("source", "target", mode="before")
    @classmethod
    def normalize_conn_id(cls, value: Any) -> str:
        if value is None:
            return ""
        s = str(value).strip().lower()
        if s and not s[0].isalpha():
            s = "n" + s
        import re

        s = re.sub(r"[^a-z0-9_-]", "_", s)
        return s[:32]


class AnimationCue(StrictModel):
    """A semantic action anchored to a spoken keyword."""

    action: AnimationAction
    targets: list[str] = Field(min_length=1, max_length=6)
    keyword: str = Field(default="", max_length=24)
    direction: Literal["left", "right", "top", "bottom"] = "top"
    path: list[str] = Field(default_factory=list, max_length=8)
    new_value: str = Field(default="", max_length=40)
    result: str = Field(default="", max_length=32)

    @field_validator("action", mode="before")
    @classmethod
    def normalize_action(cls, value: str) -> str:
        mapping = {
            "highlight": "focus",
            "select": "focus",
            "fade_in": "reveal",
            "animate": "reveal",
            "move": "reveal",
            "connect": "reveal",
            "highlight_line": "highlight_code",
            "highlight_lines": "highlight_code",
        }
        return _coerce_enum(value, _ANIMATION_ACTIONS, "reveal", mapping)

    @field_validator("direction", mode="before")
    @classmethod
    def normalize_direction(cls, value: Any) -> Any:
        return _coerce_enum(value, ("left", "right", "top", "bottom"), "top")

    @field_validator("targets", "path", mode="before")
    @classmethod
    def normalize_cue_ids(cls, value: Any) -> Any:
        if isinstance(value, list):
            res = []
            for item in value:
                s = str(item).strip().lower()
                if s and not s[0].isalpha():
                    s = "n" + s
                import re

                s = re.sub(r"[^a-z0-9_-]", "_", s)
                res.append(s[:32])
            return res
        return value


class SceneBrief(StrictModel):
    role: SceneRole
    title: str = Field(min_length=1, max_length=48)
    narration: str = Field(min_length=1, max_length=360)
    layout: SceneLayout
    elements: list[VisualElement] = Field(min_length=1, max_length=24)
    connections: list[VisualConnection] = Field(default_factory=list, max_length=24)
    cues: list[AnimationCue] = Field(default_factory=list, max_length=24)
    callout: str = Field(default="", max_length=80)

    start_time: float = Field(default=0.0, ge=0.0)
    duration: float = Field(default=1.0, gt=0.0)
    audio_path: str | None = None
    words: list[CaptionWord] = Field(default_factory=list)

    @field_validator("role", mode="before")
    @classmethod
    def normalize_role(cls, value: Any) -> Any:
        return _coerce_enum(value, _SCENE_ROLES, "concept")

    @field_validator("layout", mode="before")
    @classmethod
    def normalize_layout(cls, value: Any) -> Any:
        return _coerce_enum(value, _SCENE_LAYOUTS, "flow")

    @model_validator(mode="after")
    def validate_references(self) -> "SceneBrief":
        element_ids = {element.id for element in self.elements}

        self.connections = [
            connection
            for connection in self.connections
            if connection.source in element_ids and connection.target in element_ids
        ]

        for cue in self.cues:
            cue.targets = [target for target in cue.targets if target in element_ids]
            if cue.path:
                cue.path = [node for node in cue.path if node in element_ids]

        self.cues = [cue for cue in self.cues if cue.targets]
        return self


class VideoBrief(StrictModel):
    title: str = Field(min_length=1, max_length=60)
    subject: str = Field(min_length=1, max_length=40)
    summary: str = Field(min_length=1, max_length=140)
    scenes: list[SceneBrief] = Field(min_length=3, max_length=16)
    total_duration: float = Field(default=0.0, ge=0.0)

    @model_validator(mode="after")
    def validate_story_arc(self) -> "VideoBrief":
        if self.scenes[0].role != "hook":
            raise ValueError("第一个场景必须是 hook")
        if self.scenes[-1].role != "recap":
            raise ValueError("最后一个场景必须是 recap")
        return self


class StaticAudit(StrictModel):
    passed: bool
    problems: list[str] = Field(default_factory=list)
    scene_count: int = Field(ge=0)


class CartoonVideoRequest(StrictModel):
    """动画视频生成请求 — 4 个参数全部影响 HTML 输出。"""

    learning_need: str = Field(min_length=1)
    profile: dict[str, Any] | str
    teaching_plan: str | None = None

    style: Literal["diagram", "minimal", "dark_tech", "chalkboard"] = "diagram"
    depth: Literal["overview", "standard", "deep"] = "standard"
    pace: Literal["fast", "normal", "slow"] = "normal"
    visuals: Literal["clean", "balanced", "detailed"] = "balanced"

    output_dir: Path
    artifacts: list[SourceArtifact] = Field(default_factory=list)


# ============================================================================
# THEORY ANIMATION SCHEMA — 面向高校计算机本科理论课程的机制演示层
# ============================================================================

TheoryAnimationType = Literal[
    "structure_build",
    "state_transition",
    "data_flow",
    "table_transform",
    "timeline_schedule",
    "mapping_transform",
    "formula_derivation",
    "concept_compare",
]

TheoryStepAction = Literal[
    "create",
    "compare",
    "move",
    "transfer",
    "highlight",
    "insert",
    "remove",
    "swap",
    "split",
    "merge",
    "lookup",
    "state_change",
    "filter",
    "project",
    "join",
    "schedule",
    "map",
    "derive",
    "transform",
    "update_metric",
]

_THEORY_ANIMATION_TYPES = get_args(TheoryAnimationType)
_THEORY_STEP_ACTIONS = get_args(TheoryStepAction)


class TheoryObject(StrictModel):
    """理论机制中的对象，由桥接层映射为视觉元素。"""

    id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,31}$")
    label: str = Field(default="", max_length=80)
    value: str = Field(default="", max_length=200)
    detail: str = Field(default="", max_length=300)
    visual_kind: VisualKind = "node"
    items: list[str] = Field(default_factory=list, max_length=30)

    @field_validator("id", mode="before")
    @classmethod
    def normalize_id(cls, value: Any) -> str:
        if value is None:
            return ""
        s = str(value).strip().lower()
        if s and not s[0].isalpha():
            s = "n" + s
        import re

        s = re.sub(r"[^a-z0-9_-]", "_", s)
        return s[:32]

    @field_validator("visual_kind", mode="before")
    @classmethod
    def normalize_visual_kind(cls, value: Any) -> str:
        mapping = {
            "box": "node",
            "rect": "node",
            "circle": "node",
            "message": "packet",
            "request": "packet",
            "response": "packet",
            "page": "cell",
            "frame": "cell",
            "row": "table",
            "formula_text": "formula",
        }
        return _coerce_enum(value, _VISUAL_KINDS, "node", mapping)


class TheoryRelation(StrictModel):
    """理论对象之间的关系。"""

    source: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,31}$")
    target: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,31}$")
    label: str = Field(default="", max_length=40)
    relation_type: Literal[
        "edge",
        "left",
        "right",
        "transition",
        "flow",
        "mapping",
        "dependency",
        "parent_child",
    ] = "edge"
    condition: str = Field(default="", max_length=40)

    @field_validator("source", "target", mode="before")
    @classmethod
    def normalize_relation_id(cls, value: Any) -> str:
        if value is None:
            return ""
        s = str(value).strip().lower()
        if s and not s[0].isalpha():
            s = "n" + s
        import re

        s = re.sub(r"[^a-z0-9_-]", "_", s)
        return s[:32]


class TheoryStep(StrictModel):
    """理论机制中的一个动态步骤。"""

    id: str = Field(default="", max_length=32)
    action: TheoryStepAction
    keyword: str = Field(default="", max_length=32)
    target: str = Field(default="", max_length=32)
    source: str = Field(default="", max_length=32)
    destination: str = Field(default="", max_length=32)
    path: list[str] = Field(default_factory=list, max_length=10)
    condition: str = Field(default="", max_length=80)
    result: str = Field(default="", max_length=80)
    value: str = Field(default="", max_length=80)
    direction: Literal["left", "right", "top", "bottom"] = "top"
    metric_updates: dict[str, str] = Field(default_factory=dict, max_length=6)
    explanation: str = Field(default="", max_length=160)

    @field_validator("action", mode="before")
    @classmethod
    def normalize_step_action(cls, value: Any) -> str:
        mapping = {
            "show": "create",
            "appear": "create",
            "add": "insert",
            "send": "transfer",
            "receive": "transfer",
            "lookup_table": "lookup",
            "state": "state_change",
            "update": "update_metric",
        }
        return _coerce_enum(value, _THEORY_STEP_ACTIONS, "highlight", mapping)

    @field_validator("target", "source", "destination", mode="before")
    @classmethod
    def normalize_optional_id(cls, value: Any) -> str:
        if value is None:
            return ""
        s = str(value).strip().lower()
        if not s:
            return ""
        if not s[0].isalpha():
            s = "n" + s
        import re

        s = re.sub(r"[^a-z0-9_-]", "_", s)
        return s[:32]

    @field_validator("path", mode="before")
    @classmethod
    def normalize_path_ids(cls, value: Any) -> Any:
        if isinstance(value, list):
            normalized: list[str] = []
            for item in value:
                s = str(item).strip().lower()
                if not s:
                    continue
                if not s[0].isalpha():
                    s = "n" + s
                import re

                normalized.append(re.sub(r"[^a-z0-9_-]", "_", s)[:32])
            return normalized
        return value


class TheoryScene(StrictModel):
    """理论机制演示场景。"""

    role: SceneRole
    template: TheoryAnimationType
    title: str = Field(min_length=1, max_length=56)
    narration: str = Field(min_length=1, max_length=420)
    objects: list[TheoryObject] = Field(min_length=1, max_length=28)
    relations: list[TheoryRelation] = Field(default_factory=list, max_length=32)
    steps: list[TheoryStep] = Field(default_factory=list, max_length=32)
    key_rule: str = Field(default="", max_length=100)
    common_misconception: str = Field(default="", max_length=140)
    callout: str = Field(default="", max_length=100)

    @field_validator("role", mode="before")
    @classmethod
    def normalize_role(cls, value: Any) -> Any:
        mapping = {
            "mechanism": "process",
            "operation": "process",
            "summary": "recap",
            "intro": "hook",
        }
        return _coerce_enum(value, _SCENE_ROLES, "process", mapping)

    @field_validator("template", mode="before")
    @classmethod
    def normalize_template(cls, value: Any) -> str:
        mapping = {
            "tree_build": "structure_build",
            "graph_build": "structure_build",
            "automata_transition": "state_transition",
            "protocol_flow": "data_flow",
            "relational_algebra": "table_transform",
            "cpu_scheduling": "timeline_schedule",
            "page_replacement": "timeline_schedule",
            "address_translation": "mapping_transform",
            "complexity_derivation": "formula_derivation",
            "compare": "concept_compare",
        }
        return _coerce_enum(value, _THEORY_ANIMATION_TYPES, "data_flow", mapping)

    @model_validator(mode="after")
    def validate_scene_references(self) -> "TheoryScene":
        object_ids = {obj.id for obj in self.objects}
        self.relations = [
            rel
            for rel in self.relations
            if rel.source in object_ids and rel.target in object_ids
        ]
        for step in self.steps:
            step.path = [node for node in step.path if node in object_ids]
        return self


class TheoryAnimationBrief(StrictModel):
    """LLM 输出的高校计算机理论知识动画分镜。"""

    title: str = Field(min_length=1, max_length=60)
    subject: str = Field(min_length=1, max_length=40)
    course: str = Field(default="计算机基础", max_length=40)
    knowledge_point: str = Field(default="", max_length=80)
    animation_type: TheoryAnimationType
    learning_goal: str = Field(default="", max_length=160)
    summary: str = Field(min_length=1, max_length=160)
    scenes: list[TheoryScene] = Field(min_length=3, max_length=16)

    @field_validator("animation_type", mode="before")
    @classmethod
    def normalize_animation_type(cls, value: Any) -> str:
        return _coerce_enum(value, _THEORY_ANIMATION_TYPES, "data_flow")

    @model_validator(mode="after")
    def validate_story_arc(self) -> "TheoryAnimationBrief":
        if self.scenes[0].role != "hook":
            self.scenes[0].role = "hook"
        if self.scenes[-1].role != "recap":
            self.scenes[-1].role = "recap"
        return self


def _layout_for_theory_template(
    template: str,
    relations: list[TheoryRelation],
) -> str:
    if template == "structure_build":
        return "tree" if relations else "flow"
    if template == "state_transition":
        return "state_diagram" if relations else "flow"
    if template == "data_flow":
        return "flow"
    if template == "table_transform":
        return "table_view"
    if template == "timeline_schedule":
        return "flow"
    if template == "mapping_transform":
        return "flow"
    if template == "formula_derivation":
        return "derivation"
    if template == "concept_compare":
        return "compare"
    return "flow"


def _connection_kind_for_theory(
    template: str,
    relation: TheoryRelation,
) -> str:
    if template == "state_transition" or relation.relation_type == "transition":
        return "transition"
    if template in {"data_flow", "mapping_transform", "timeline_schedule"}:
        return "arrow"
    return "edge"


def _relation_label(relation: TheoryRelation) -> str:
    if relation.relation_type == "left" and not relation.label:
        return "左"
    if relation.relation_type == "right" and not relation.label:
        return "右"
    return relation.label


def _theory_step_to_cues(
    step: TheoryStep,
    object_ids: set[str],
) -> list[AnimationCue]:
    cues: list[AnimationCue] = []
    keyword = step.keyword or step.condition or step.result or step.action

    def add(action: str, targets: list[str], **extra: Any) -> None:
        filtered = [target for target in targets if target in object_ids]
        if not filtered:
            return
        payload: dict[str, Any] = {
            "action": action,
            "targets": filtered,
            "keyword": keyword,
            "direction": step.direction,
        }
        payload.update(extra)
        cues.append(AnimationCue(**payload))

    if step.action in {"create", "insert", "push"}:
        add("insert", [step.target], new_value=step.value or step.result)

    elif step.action in {"remove", "pop"}:
        add("remove", [step.target])

    elif step.action == "compare":
        targets = [step.source, step.target] if step.source else [step.target]
        real_targets = [t for t in targets if t]
        add("compare" if len(real_targets) >= 2 else "focus", real_targets)

    elif step.action == "highlight":
        if step.path:
            add("highlight_path", step.path, path=step.path)
        else:
            add("focus", [step.target])

    elif step.action == "move":
        if step.path:
            add("highlight_path", step.path, path=step.path)
        elif step.source and step.destination:
            add("transfer", [step.source, step.destination])
        else:
            add("focus", [step.target])

    elif step.action == "transfer":
        if step.target and step.source and step.destination:
            add("transfer", [step.target, step.source, step.destination])
        elif step.source and step.destination:
            add("transfer", [step.source, step.destination])
        else:
            add("insert", [step.target])

    elif step.action == "state_change":
        add("state_change", [step.target], new_value=step.value or step.result)

    elif step.action == "update_metric":
        if step.metric_updates:
            for metric_id, value in step.metric_updates.items():
                if metric_id in object_ids:
                    add("value_change", [metric_id], new_value=value)
        else:
            add("value_change", [step.target], new_value=step.value or step.result)

    elif step.action == "swap":
        if step.source and step.destination:
            add("swap", [step.source, step.destination])
        else:
            add("swap", [step.target])

    elif step.action in {"split", "merge", "transform"}:
        add("transform", [step.target], result=step.destination or step.result)

    elif step.action in {"derive", "filter", "project", "join", "map"}:
        add(
            "derive" if step.action == "derive" else "transform",
            [step.target],
            result=step.destination or step.result,
        )

    elif step.action in {"lookup", "schedule"}:
        if step.path:
            add("highlight_path", step.path, path=step.path)
        else:
            add("focus", [step.target])

    return cues


def bridge_theory_to_brief(theory: TheoryAnimationBrief) -> VideoBrief:
    """将理论机制分镜映射为现有 HyperFrames 编译器可消费的 VideoBrief。"""
    scenes: list[SceneBrief] = []

    for scene in theory.scenes:
        layout = _layout_for_theory_template(scene.template, scene.relations)
        object_ids = {obj.id for obj in scene.objects}

        elements = [
            VisualElement(
                id=obj.id,
                kind=obj.visual_kind,
                label=obj.label,
                value=obj.value,
                detail=obj.detail,
                items=obj.items,
            )
            for obj in scene.objects
        ]

        connections = [
            VisualConnection(
                source=rel.source,
                target=rel.target,
                label=_relation_label(rel),
                kind=_connection_kind_for_theory(scene.template, rel),
                condition=rel.condition or _relation_label(rel),
            )
            for rel in scene.relations
        ]

        cues: list[AnimationCue] = []
        for step in scene.steps:
            cues.extend(_theory_step_to_cues(step, object_ids))

        if not cues:
            cues = [
                AnimationCue(
                    action="reveal",
                    targets=[element.id for element in elements[:6]],
                    keyword="展示",
                )
            ]

        role = scene.role
        if scene is theory.scenes[0]:
            role = "hook"
        if scene is theory.scenes[-1]:
            role = "recap"

        callout = scene.callout or scene.key_rule or scene.common_misconception

        scenes.append(
            SceneBrief(
                role=role,
                title=scene.title,
                narration=scene.narration,
                layout=layout,
                elements=elements,
                connections=connections,
                cues=cues,
                callout=callout[:80] if callout else "",
            )
        )

    return VideoBrief(
        title=theory.title,
        subject=theory.subject or theory.course,
        summary=theory.summary,
        scenes=scenes,
    )


# ============================================================================
# SIMPLE FALLBACK SCHEMA — 旧结构保留为兜底
# ============================================================================

SimpleKind = Literal["node", "label", "metric"]
SimpleAction = Literal["reveal", "focus", "insert"]
SimpleLayout = Literal["tree", "flow", "recap"]
SimpleRole = Literal["hook", "process", "compare", "recap"]

_SIMPLE_KINDS = get_args(SimpleKind)
_SIMPLE_ACTIONS = get_args(SimpleAction)
_SIMPLE_LAYOUTS = get_args(SimpleLayout)
_SIMPLE_ROLES = get_args(SimpleRole)


class SimpleElement(StrictModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,31}$")
    kind: SimpleKind
    label: str = Field(default="", max_length=80)
    value: str = Field(default="", max_length=200)
    items: list[str] = Field(default_factory=list, max_length=30)

    @field_validator("id", mode="before")
    @classmethod
    def normalize_id(cls, value: Any) -> str:
        if value is None:
            return ""
        s = str(value).strip().lower()
        if s and not s[0].isalpha():
            s = "n" + s
        import re

        s = re.sub(r"[^a-z0-9_-]", "_", s)
        return s[:32]

    @field_validator("kind", mode="before")
    @classmethod
    def normalize_kind(cls, value: Any) -> str:
        mapping = {
            "text": "label",
            "header": "label",
            "step": "label",
            "cell": "node",
            "state": "node",
            "box": "node",
            "array": "node",
            "stack": "node",
            "queue": "node",
            "table": "node",
            "code": "label",
            "formula": "label",
            "packet": "node",
            "pointer": "node",
        }
        return _coerce_enum(value, _SIMPLE_KINDS, "node", mapping)

    @field_validator("items", mode="before")
    @classmethod
    def normalize_items(cls, value: Any) -> Any:
        if isinstance(value, list):
            return [str(x) for x in value]
        if isinstance(value, str):
            if value.startswith("[") and value.endswith("]"):
                try:
                    import ast

                    parsed = ast.literal_eval(value)
                    if isinstance(parsed, list):
                        return [str(x) for x in parsed]
                except Exception:
                    pass
            if "," in value:
                return [x.strip() for x in value.split(",")]
        return value


class SimpleConnection(StrictModel):
    source: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,31}$")
    target: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,31}$")
    label: str = Field(default="", max_length=30)

    @field_validator("source", "target", mode="before")
    @classmethod
    def normalize_conn_id(cls, value: Any) -> str:
        if value is None:
            return ""
        s = str(value).strip().lower()
        if s and not s[0].isalpha():
            s = "n" + s
        import re

        s = re.sub(r"[^a-z0-9_-]", "_", s)
        return s[:32]


class SimpleCue(StrictModel):
    action: SimpleAction
    targets: list[str] = Field(min_length=1, max_length=6)
    keyword: str = Field(default="", max_length=24)
    direction: Literal["left", "right", "top", "bottom"] = "top"
    new_value: str = Field(default="", max_length=80)

    @field_validator("action", mode="before")
    @classmethod
    def normalize_action(cls, value: Any) -> str:
        mapping = {
            "highlight": "focus",
            "select": "focus",
            "emphasize": "focus",
            "fade_in": "reveal",
            "animate": "reveal",
            "move": "reveal",
            "show": "reveal",
            "appear": "reveal",
            "add": "insert",
            "push": "insert",
            "slide_in": "insert",
            "swap": "insert",
            "remove": "insert",
            "shift": "insert",
            "transfer": "insert",
            "traverse": "focus",
            "highlight_path": "focus",
            "value_change": "insert",
            "state_change": "insert",
            "branch": "insert",
            "derive": "insert",
            "transform": "insert",
            "count": "insert",
            "highlight_code": "focus",
        }
        return _coerce_enum(value, _SIMPLE_ACTIONS, "reveal", mapping)

    @field_validator("direction", mode="before")
    @classmethod
    def normalize_direction(cls, value: Any) -> Any:
        return _coerce_enum(value, ("left", "right", "top", "bottom"), "top")

    @field_validator("targets", mode="before")
    @classmethod
    def normalize_cue_ids(cls, value: Any) -> Any:
        if isinstance(value, list):
            res = []
            for item in value:
                s = str(item).strip().lower()
                if s and not s[0].isalpha():
                    s = "n" + s
                import re

                s = re.sub(r"[^a-z0-9_-]", "_", s)
                res.append(s[:32])
            return res
        return value


class SimpleScene(StrictModel):
    role: SimpleRole
    title: str = Field(min_length=1, max_length=48)
    narration: str = Field(min_length=1, max_length=360)
    layout: SimpleLayout
    elements: list[SimpleElement] = Field(min_length=1, max_length=24)
    connections: list[SimpleConnection] = Field(default_factory=list, max_length=24)
    cues: list[SimpleCue] = Field(default_factory=list, max_length=24)
    callout: str = Field(default="", max_length=80)

    @field_validator("role", mode="before")
    @classmethod
    def normalize_role(cls, value: Any) -> Any:
        mapping = {
            "concept": "process",
            "architecture": "process",
            "code_trace": "process",
            "derivation": "process",
        }
        return _coerce_enum(value, _SIMPLE_ROLES, "process", mapping)

    @field_validator("layout", mode="before")
    @classmethod
    def normalize_layout(cls, value: Any) -> str:
        mapping = {
            "hero": "flow",
            "graph": "tree",
            "state_diagram": "tree",
            "array_view": "flow",
            "queue_view": "flow",
            "table_view": "flow",
            "derivation": "flow",
            "stack": "flow",
            "code": "flow",
            "grid": "flow",
            "compare": "flow",
        }
        return _coerce_enum(value, _SIMPLE_LAYOUTS, "flow", mapping)

    @model_validator(mode="after")
    def validate_references(self) -> "SimpleScene":
        element_ids = {element.id for element in self.elements}
        self.connections = [
            conn
            for conn in self.connections
            if conn.source in element_ids and conn.target in element_ids
        ]
        for cue in self.cues:
            cue.targets = [t for t in cue.targets if t in element_ids]
        self.cues = [cue for cue in self.cues if cue.targets]
        return self


class SimpleVideoBrief(StrictModel):
    title: str = Field(min_length=1, max_length=60)
    subject: str = Field(min_length=1, max_length=40)
    summary: str = Field(min_length=1, max_length=140)
    scenes: list[SimpleScene] = Field(min_length=3, max_length=16)

    @model_validator(mode="after")
    def validate_story_arc(self) -> "SimpleVideoBrief":
        if self.scenes[0].role != "hook":
            raise ValueError("第一个场景必须是 hook")
        if self.scenes[-1].role != "recap":
            raise ValueError("最后一个场景必须是 recap")
        return self


def _infer_layout(scene: SimpleScene) -> str:
    if scene.layout == "tree":
        node_values = [e.value for e in scene.elements if e.kind == "node" and e.value]
        has_cycle = False
        if scene.connections:
            source_set = {c.source for c in scene.connections}
            target_set = {c.target for c in scene.connections}
            has_cycle = bool(source_set & target_set)
        has_condition_labels = any(c.label for c in scene.connections)

        if (
            node_values
            and len(node_values) >= 2
            and all(len(v) <= 6 for v in node_values)
            and has_cycle
            and has_condition_labels
        ):
            return "state_diagram"
        return "tree"

    if scene.layout == "recap":
        return "recap"

    if scene.role == "compare":
        return "compare"

    has_container = any(e.kind == "node" and e.items for e in scene.elements)
    if has_container and not scene.connections:
        title_lower = scene.title.lower()
        if any(kw in title_lower for kw in ("栈", "入栈", "出栈", "递归", "stack")):
            return "stack"
        if any(kw in title_lower for kw in ("队列", "入队", "出队", "queue")):
            return "queue_view"
        if any(kw in title_lower for kw in ("表", "table", "真值")):
            return "table_view"
        return "array_view"

    if scene.connections and scene.role != "compare":
        source_set = {c.source for c in scene.connections}
        target_set = {c.target for c in scene.connections}
        if source_set & target_set:
            return "graph"

    return "flow"


def _infer_kind(element: SimpleElement, layout: str) -> str:
    if element.kind == "metric":
        return "metric"

    if element.kind == "label":
        if element.value:
            return "step"
        if element.label and any(
            ch in element.label
            for ch in ("=", "→", "≤", "≥", "∈", "∪", "∩", "∧", "∨", "¬")
        ):
            return "formula"
        return "label"

    if element.items:
        return "array"

    if layout in ("flow", "compare"):
        protocol_keywords = (
            "SYN",
            "ACK",
            "FIN",
            "REQ",
            "RES",
            "GET",
            "POST",
            "seq",
            "ack",
        )
        if element.value and any(kw in element.value for kw in protocol_keywords):
            return "packet"
        if element.value and len(element.value) <= 4 and element.value.isdigit():
            return "cell"

    if layout == "state_diagram":
        if element.value and len(element.value) <= 6:
            return "state"

    return "node"


def _infer_action(
    cue: SimpleCue,
    scene: SimpleScene,
    layout: str,
    element_map: dict[str, SimpleElement],
) -> tuple[str, dict[str, Any]]:
    extra: dict[str, Any] = {}

    if cue.action == "reveal":
        return ("reveal", extra)

    if cue.action == "focus":
        if len(cue.targets) >= 2 and layout in ("tree", "graph", "state_diagram"):
            path_nodes: list[str] = []
            visited: set[str] = set()

            for t in cue.targets:
                if t not in visited:
                    path_nodes.append(t)
                    visited.add(t)

            if len(path_nodes) >= 2:
                return ("highlight_path", {"path": path_nodes})

        if len(cue.targets) == 2 and layout == "compare":
            return ("compare", extra)

        return ("focus", extra)

    if getattr(cue, "new_value", ""):
        extra["new_value"] = cue.new_value
        return ("value_change", extra)

    if all(
        element_map.get(t, SimpleElement(id=t, kind="node")).kind == "metric"
        for t in cue.targets
    ):
        return ("count", extra)

    if layout in ("tree", "graph", "state_diagram"):
        return ("insert", extra)

    if layout == "flow" and cue.direction in ("left", "right") and scene.connections:
        for t in cue.targets:
            for conn in scene.connections:
                if conn.target == t or conn.source == t:
                    return ("transfer", extra)

    if layout in ("flow", "compare") and not scene.connections:
        if len(cue.targets) >= 2:
            return ("branch", extra)

    return ("insert", extra)


def _infer_conn_kind(
    layout: str,
    source_elem: SimpleElement | None,
    target_elem: SimpleElement | None,
) -> str:
    if layout == "tree":
        return "edge"
    if layout == "state_diagram":
        return "transition"
    if layout == "graph":
        return "edge"
    return "arrow"


def bridge_simple_to_brief(simple: SimpleVideoBrief) -> VideoBrief:
    full_scenes: list[SceneBrief] = []

    for s in simple.scenes:
        layout = _infer_layout(s)
        element_map = {e.id: e for e in s.elements}

        elements = [
            VisualElement(
                id=e.id,
                kind=_infer_kind(e, layout),
                label=e.label,
                value=e.value,
                items=e.items,
                detail="",
            )
            for e in s.elements
        ]

        connections = [
            VisualConnection(
                source=conn.source,
                target=conn.target,
                kind=_infer_conn_kind(
                    layout,
                    element_map.get(conn.source),
                    element_map.get(conn.target),
                ),
                label=conn.label,
                condition=conn.label if layout == "state_diagram" else "",
            )
            for conn in s.connections
        ]

        cues: list[AnimationCue] = []
        for c in s.cues:
            action, extra = _infer_action(c, s, layout, element_map)
            cue_kwargs: dict[str, Any] = {
                "action": action,
                "targets": c.targets,
                "keyword": c.keyword,
                "direction": c.direction,
            }
            cue_kwargs.update(extra)
            cues.append(AnimationCue(**cue_kwargs))

        role = s.role
        if s.role == "process" and layout == "state_diagram":
            if any(kw in s.title for kw in ("推导", "证明", "变换", "归约")):
                role = "derivation"

        full_scenes.append(
            SceneBrief(
                role=role,
                title=s.title,
                narration=s.narration,
                layout=layout,
                elements=elements,
                connections=connections,
                cues=cues,
                callout=s.callout,
            )
        )

    return VideoBrief(
        title=simple.title,
        subject=simple.subject,
        summary=simple.summary,
        scenes=full_scenes,
    )