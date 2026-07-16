"""Closed semantic vocabularies shared by the PPT generation pipeline.

The teaching graph, storyboard, visual planner, and renderer read their enums
from this module. Visual selection happens after storyboard compilation, so a
provisional layout may depend only on slide semantics and graph relation.
"""

from dataclasses import dataclass
from enum import StrEnum


class CourseDomain(StrEnum):
    """Supported computer-science course families."""

    ALGORITHMS = "algorithms"
    OPERATING_SYSTEMS = "operating_systems"
    NETWORKS = "networks"
    COMPUTER_ARCHITECTURE = "computer_architecture"
    DATABASES = "databases"
    COMPILERS = "compilers"
    DISCRETE_THEORY = "discrete_theory"
    SOFTWARE_DISTRIBUTED = "software_distributed"
    GENERAL_CS = "general_cs"


class SlideKind(StrEnum):
    """Semantic roles available to storyboard slides."""

    COVER = "cover"
    ROADMAP = "roadmap"
    OBJECTIVE = "objective"
    QUESTION = "question"
    CONCEPT = "concept"
    PROCESS = "process"
    EXPLANATION = "explanation"
    COMPARISON = "comparison"
    CORRECTION = "correction"
    MAP = "map"
    SUMMARY = "summary"


class VisualFamily(StrEnum):
    """Closed set of renderer-neutral visual IR discriminators."""

    HIERARCHY = "hierarchy"
    GRAPH = "graph"
    STATE_MACHINE = "state_machine"
    TIMELINE = "timeline"
    MEMORY_LAYOUT = "memory_layout"
    DATA_FLOW = "data_flow"
    MAPPING = "mapping"
    TABLE_MATRIX = "table_matrix"
    ALGORITHM_FRAMES = "algorithm_frames"
    CIRCUIT = "circuit"
    QUANTITATIVE = "quantitative"
    CODE = "code"
    FORMULA = "formula"
    COMPOSITE = "composite"


class LayoutKind(StrEnum):
    """Renderer-owned composition layouts."""

    HERO = "hero"
    ROUTE = "route"
    STATEMENT = "statement"
    DIAGRAM = "diagram"
    SEQUENCE = "sequence"
    COMPARISON = "comparison"
    STUDIO = "studio"
    MOSAIC = "mosaic"
    RECAP = "recap"


class LogicNodeRole(StrEnum):
    """Teaching role played by one logic graph node."""

    QUESTION = "question"
    PREMISE = "premise"
    CONCEPT = "concept"
    MECHANISM = "mechanism"
    METHOD = "method"
    EVIDENCE = "evidence"
    CASE = "case"
    CONCLUSION = "conclusion"


class LogicRelation(StrEnum):
    """Directed teaching relations between logic graph nodes."""

    PREREQUISITE = "prerequisite"
    DECOMPOSES = "decomposes"
    SUPPORTS = "supports"
    DERIVES = "derives"
    CAUSES = "causes"
    CONTRASTS = "contrasts"
    APPLIES = "applies"
    VERIFIES = "verifies"
    SUMMARIZES = "summarizes"


@dataclass(frozen=True)
class LayoutSpec:
    """Prompt guidance for one renderer layout."""

    kind: LayoutKind
    prompt_instruction: str


SLIDE_KIND_LABELS: dict[SlideKind, str] = {
    SlideKind.COVER: "封面",
    SlideKind.ROADMAP: "学习路线",
    SlideKind.OBJECTIVE: "学习目标",
    SlideKind.QUESTION: "核心问题",
    SlideKind.CONCEPT: "概念",
    SlideKind.PROCESS: "过程",
    SlideKind.EXPLANATION: "讲解",
    SlideKind.COMPARISON: "对比",
    SlideKind.CORRECTION: "纠偏",
    SlideKind.MAP: "知识地图",
    SlideKind.SUMMARY: "总结",
}

LAYOUTS: dict[LayoutKind, LayoutSpec] = {
    LayoutKind.HERO: LayoutSpec(
        LayoutKind.HERO,
        "封面开场：一句主张，视觉作为大面积锚点。",
    ),
    LayoutKind.ROUTE: LayoutSpec(
        LayoutKind.ROUTE,
        "课程路线：用全宽路线承载阶段顺序。",
    ),
    LayoutKind.STATEMENT: LayoutSpec(
        LayoutKind.STATEMENT,
        "核心主张：短结论主导画面，辅以少量证据。",
    ),
    LayoutKind.DIAGRAM: LayoutSpec(
        LayoutKind.DIAGRAM,
        "图解讲解：简短结论配合较大的关系图。",
    ),
    LayoutKind.SEQUENCE: LayoutSpec(
        LayoutKind.SEQUENCE,
        "机制或步骤：让流程、时序或推导横向铺开。",
    ),
    LayoutKind.COMPARISON: LayoutSpec(
        LayoutKind.COMPARISON,
        "比较决策：用双侧或矩阵逐维呈现差异。",
    ),
    LayoutKind.STUDIO: LayoutSpec(
        LayoutKind.STUDIO,
        "实验台：代码、公式或结构主体占主要面积。",
    ),
    LayoutKind.MOSAIC: LayoutSpec(
        LayoutKind.MOSAIC,
        "多要点讲解：用均衡矩阵承载互补信息。",
    ),
    LayoutKind.RECAP: LayoutSpec(
        LayoutKind.RECAP,
        "收束复盘：用知识关系与迁移任务结束课程。",
    ),
}

LOGIC_RELATION_LAYOUTS: dict[LogicRelation, frozenset[LayoutKind]] = {
    LogicRelation.PREREQUISITE: frozenset(
        {LayoutKind.DIAGRAM, LayoutKind.SEQUENCE, LayoutKind.STATEMENT}
    ),
    LogicRelation.DECOMPOSES: frozenset(
        {LayoutKind.DIAGRAM, LayoutKind.MOSAIC, LayoutKind.RECAP}
    ),
    LogicRelation.SUPPORTS: frozenset(
        {LayoutKind.STATEMENT, LayoutKind.DIAGRAM, LayoutKind.MOSAIC}
    ),
    LogicRelation.DERIVES: frozenset({LayoutKind.SEQUENCE, LayoutKind.STUDIO}),
    LogicRelation.CAUSES: frozenset({LayoutKind.SEQUENCE, LayoutKind.DIAGRAM}),
    LogicRelation.CONTRASTS: frozenset({LayoutKind.COMPARISON}),
    LogicRelation.APPLIES: frozenset(
        {LayoutKind.STUDIO, LayoutKind.DIAGRAM, LayoutKind.MOSAIC}
    ),
    LogicRelation.VERIFIES: frozenset(
        {LayoutKind.STUDIO, LayoutKind.STATEMENT, LayoutKind.MOSAIC}
    ),
    LogicRelation.SUMMARIZES: frozenset({LayoutKind.RECAP, LayoutKind.DIAGRAM}),
}

ROLE_LABELS: dict[LogicNodeRole, str] = {
    LogicNodeRole.QUESTION: "问题",
    LogicNodeRole.PREMISE: "前提",
    LogicNodeRole.CONCEPT: "概念",
    LogicNodeRole.MECHANISM: "机制",
    LogicNodeRole.METHOD: "方法",
    LogicNodeRole.EVIDENCE: "证据",
    LogicNodeRole.CASE: "案例",
    LogicNodeRole.CONCLUSION: "结论",
}

RELATION_LABELS: dict[LogicRelation, str] = {
    LogicRelation.PREREQUISITE: "前置",
    LogicRelation.DECOMPOSES: "拆解",
    LogicRelation.SUPPORTS: "支撑",
    LogicRelation.DERIVES: "推导",
    LogicRelation.CAUSES: "因果",
    LogicRelation.CONTRASTS: "对比",
    LogicRelation.APPLIES: "应用",
    LogicRelation.VERIFIES: "验证",
    LogicRelation.SUMMARIZES: "收束",
}

_CONTENT_LAYOUTS: tuple[LayoutKind, ...] = (
    LayoutKind.DIAGRAM,
    LayoutKind.SEQUENCE,
    LayoutKind.STATEMENT,
    LayoutKind.COMPARISON,
    LayoutKind.STUDIO,
    LayoutKind.MOSAIC,
    LayoutKind.RECAP,
)


def _layout_ranking(*preferred: LayoutKind) -> tuple[LayoutKind, ...]:
    remaining = tuple(
        layout for layout in _CONTENT_LAYOUTS if layout not in preferred
    )
    return (*preferred, *remaining)


_VISUAL_LAYOUT_PREFERENCE: dict[VisualFamily, tuple[LayoutKind, ...]] = {
    VisualFamily.HIERARCHY: _layout_ranking(
        LayoutKind.DIAGRAM,
        LayoutKind.MOSAIC,
        LayoutKind.RECAP,
    ),
    VisualFamily.GRAPH: _layout_ranking(
        LayoutKind.DIAGRAM,
        LayoutKind.SEQUENCE,
        LayoutKind.COMPARISON,
    ),
    VisualFamily.STATE_MACHINE: _layout_ranking(
        LayoutKind.SEQUENCE,
        LayoutKind.DIAGRAM,
        LayoutKind.STUDIO,
    ),
    VisualFamily.TIMELINE: _layout_ranking(
        LayoutKind.SEQUENCE,
        LayoutKind.DIAGRAM,
        LayoutKind.COMPARISON,
    ),
    VisualFamily.MEMORY_LAYOUT: _layout_ranking(
        LayoutKind.DIAGRAM,
        LayoutKind.STUDIO,
        LayoutKind.MOSAIC,
    ),
    VisualFamily.DATA_FLOW: _layout_ranking(
        LayoutKind.DIAGRAM,
        LayoutKind.SEQUENCE,
        LayoutKind.STUDIO,
    ),
    VisualFamily.MAPPING: _layout_ranking(
        LayoutKind.COMPARISON,
        LayoutKind.DIAGRAM,
        LayoutKind.MOSAIC,
    ),
    VisualFamily.TABLE_MATRIX: _layout_ranking(
        LayoutKind.COMPARISON,
        LayoutKind.MOSAIC,
        LayoutKind.STATEMENT,
    ),
    VisualFamily.ALGORITHM_FRAMES: _layout_ranking(
        LayoutKind.SEQUENCE,
        LayoutKind.STUDIO,
        LayoutKind.DIAGRAM,
    ),
    VisualFamily.CIRCUIT: _layout_ranking(
        LayoutKind.DIAGRAM,
        LayoutKind.SEQUENCE,
        LayoutKind.STUDIO,
    ),
    VisualFamily.QUANTITATIVE: _layout_ranking(
        LayoutKind.COMPARISON,
        LayoutKind.STATEMENT,
        LayoutKind.MOSAIC,
    ),
    VisualFamily.CODE: _layout_ranking(
        LayoutKind.STUDIO,
        LayoutKind.SEQUENCE,
        LayoutKind.DIAGRAM,
    ),
    VisualFamily.FORMULA: _layout_ranking(
        LayoutKind.STUDIO,
        LayoutKind.SEQUENCE,
        LayoutKind.STATEMENT,
    ),
    VisualFamily.COMPOSITE: _layout_ranking(
        LayoutKind.MOSAIC,
        LayoutKind.DIAGRAM,
        LayoutKind.COMPARISON,
    ),
}

_PROVISIONAL_RELATION_LAYOUTS: dict[LogicRelation, LayoutKind] = {
    LogicRelation.PREREQUISITE: LayoutKind.SEQUENCE,
    LogicRelation.DECOMPOSES: LayoutKind.DIAGRAM,
    LogicRelation.SUPPORTS: LayoutKind.STATEMENT,
    LogicRelation.DERIVES: LayoutKind.SEQUENCE,
    LogicRelation.CAUSES: LayoutKind.SEQUENCE,
    LogicRelation.CONTRASTS: LayoutKind.COMPARISON,
    LogicRelation.APPLIES: LayoutKind.STUDIO,
    LogicRelation.VERIFIES: LayoutKind.STATEMENT,
    LogicRelation.SUMMARIZES: LayoutKind.RECAP,
}

_META_LAYOUTS: dict[SlideKind, LayoutKind] = {
    SlideKind.COVER: LayoutKind.HERO,
    SlideKind.ROADMAP: LayoutKind.ROUTE,
    SlideKind.SUMMARY: LayoutKind.RECAP,
}


def _validate_contract() -> None:
    checks = (
        (set(SlideKind), set(SLIDE_KIND_LABELS), "slide kind labels"),
        (set(VisualFamily), set(_VISUAL_LAYOUT_PREFERENCE), "visual layouts"),
        (set(LayoutKind), set(LAYOUTS), "layout specs"),
        (set(LogicRelation), set(LOGIC_RELATION_LAYOUTS), "relation layouts"),
        (
            set(LogicRelation),
            set(_PROVISIONAL_RELATION_LAYOUTS),
            "provisional layouts",
        ),
    )
    for declared, registered, label in checks:
        if declared != registered:
            missing = sorted(item.value for item in declared - registered)
            extra = sorted(item.value for item in registered - declared)
            raise RuntimeError(
                f"PPT {label} contract mismatch: missing={missing} extra={extra}"
            )
    for relation, layout in _PROVISIONAL_RELATION_LAYOUTS.items():
        if layout not in LOGIC_RELATION_LAYOUTS[relation]:
            raise RuntimeError(
                f"provisional layout {layout.value} does not support {relation.value}"
            )


_validate_contract()


def course_domain_values() -> str:
    """Return prompt-ready values for the closed course-domain enum."""

    return "、".join(f"`{domain.value}`" for domain in CourseDomain)


def slide_kind_values() -> str:
    """Return prompt-ready slide kinds with Chinese semantic labels."""

    return "、".join(
        f"`{kind.value}`（{SLIDE_KIND_LABELS[kind]}）" for kind in SlideKind
    )


def visual_family_values() -> str:
    """Return prompt-ready values for every visual IR discriminator."""

    return "、".join(f"`{family.value}`" for family in VisualFamily)


def logic_node_role_values() -> str:
    """Return prompt-ready values for logic-node roles."""

    return "、".join(f"`{role.value}`" for role in LogicNodeRole)


def logic_relation_values() -> str:
    """Return prompt-ready values for logic relations."""

    return "、".join(f"`{relation.value}`" for relation in LogicRelation)


def layout_guidance() -> str:
    """Return prompt guidance for renderer layout choices."""

    return "\n".join(
        f"- `{layout.kind.value}`：{layout.prompt_instruction}"
        for layout in LAYOUTS.values()
    )


def layout_supports_relation(
    layout: LayoutKind,
    relation: LogicRelation,
) -> bool:
    """Return whether a layout can express the given teaching relation.

    Args:
        layout: Candidate renderer layout.
        relation: Teaching relation that must remain visible.

    Returns:
        True when the relation's layout contract includes the layout.
    """

    return layout in LOGIC_RELATION_LAYOUTS[relation]


def select_provisional_layout(
    kind: SlideKind,
    relation: LogicRelation | None,
) -> LayoutKind:
    """Choose a storyboard layout before a visual family has been planned.

    Args:
        kind: Semantic role of the slide.
        relation: Primary teaching relation for a content slide.

    Returns:
        A deterministic meta layout or relation-compatible content layout.

    Raises:
        ValueError: If a content slide has no teaching relation.
    """

    if kind in _META_LAYOUTS:
        return _META_LAYOUTS[kind]
    if relation is None:
        raise ValueError("content slide requires a logic relation")
    return _PROVISIONAL_RELATION_LAYOUTS[relation]


def select_layout(
    kind: SlideKind,
    visual_family: VisualFamily,
    relation: LogicRelation | None,
) -> LayoutKind:
    """Resolve the final layout from visual family and teaching relation.

    Args:
        kind: Semantic role of the slide.
        visual_family: Final renderer-neutral visual family.
        relation: Primary teaching relation for a content slide.

    Returns:
        A deterministic layout compatible with both semantic inputs.

    Raises:
        ValueError: If a content slide has no teaching relation.
    """

    if kind in _META_LAYOUTS:
        return _META_LAYOUTS[kind]
    if relation is None:
        raise ValueError("content slide requires a logic relation")

    supported = LOGIC_RELATION_LAYOUTS[relation]
    for preferred in _VISUAL_LAYOUT_PREFERENCE[visual_family]:
        if preferred in supported:
            return preferred
    raise RuntimeError(
        f"no layout supports {visual_family.value} with relation {relation.value}"
    )
