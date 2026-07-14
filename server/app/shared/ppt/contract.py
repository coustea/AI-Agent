"""PPT 生成的唯一语义契约。

页面角色、视觉组件、提示词约束和 HTML 渲染都必须从本模块读取，
禁止在调用方复制组件名称或视觉能力列表。
"""

from dataclasses import dataclass
from enum import StrEnum


class SlideKind(StrEnum):
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


class VisualKind(StrEnum):
    CODE = "code"
    FORMULA = "formula"
    METRICS = "metrics"
    MODEL = "model"


class VisualRenderMode(StrEnum):
    CODE = "code"
    FORMULA = "formula"
    METRICS = "metrics"
    MODEL = "model"


class LayoutKind(StrEnum):
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
    QUESTION = "question"
    PREMISE = "premise"
    CONCEPT = "concept"
    MECHANISM = "mechanism"
    METHOD = "method"
    EVIDENCE = "evidence"
    CASE = "case"
    CONCLUSION = "conclusion"


class LogicRelation(StrEnum):
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
class VisualComponent:
    kind: VisualKind
    render_mode: VisualRenderMode
    prompt_instruction: str


@dataclass(frozen=True)
class LayoutSpec:
    kind: LayoutKind
    prompt_instruction: str


VISUAL_COMPONENTS: dict[VisualKind, VisualComponent] = {
    VisualKind.CODE: VisualComponent(VisualKind.CODE, VisualRenderMode.CODE, "给出短小、可读且与教学目标直接相关的代码。"),
    VisualKind.FORMULA: VisualComponent(VisualKind.FORMULA, VisualRenderMode.FORMULA, "给出关键公式及不超过五步的推导或使用步骤。"),
    VisualKind.METRICS: VisualComponent(VisualKind.METRICS, VisualRenderMode.METRICS, "用少量有明确含义的指标或量级支撑结论。"),
    VisualKind.MODEL: VisualComponent(VisualKind.MODEL, VisualRenderMode.MODEL, "对于任何计算机理论（如数据结构、内存布局、OS 架构、网络拓扑、设计模式、ER 图、时序流转等），必须输出受控的 model.nodes / model.edges 具象化建模，绝不能只使用文字。"),
}


LAYOUTS: dict[LayoutKind, LayoutSpec] = {
    LayoutKind.HERO: LayoutSpec(LayoutKind.HERO, "封面或章节开场：一句主张、最多三张关键词卡片，视觉作为大面积锚点。"),
    LayoutKind.ROUTE: LayoutSpec(LayoutKind.ROUTE, "课程路线：用横向全宽路线或知识地图承载顺序，文字只解释阶段价值。"),
    LayoutKind.STATEMENT: LayoutSpec(LayoutKind.STATEMENT, "核心主张：用一条短结论主导画面，辅以少量证据或概念图，不重复解释。"),
    LayoutKind.DIAGRAM: LayoutSpec(LayoutKind.DIAGRAM, "图解讲解：左侧放简短结论与最多三项提示，右侧放较大的关系图。"),
    LayoutKind.SEQUENCE: LayoutSpec(LayoutKind.SEQUENCE, "机制或步骤：让流程、时序或推导横向铺开；正文只保留必要条件和关键节点。"),
    LayoutKind.COMPARISON: LayoutSpec(LayoutKind.COMPARISON, "比较决策：使用平衡的双侧或矩阵构图，逐维呈现差异与适用条件。"),
    LayoutKind.STUDIO: LayoutSpec(LayoutKind.STUDIO, "代码或公式实验台：代码/公式占主要面积，旁侧只放运行解释、变量含义或推导提示。"),
    LayoutKind.MOSAIC: LayoutSpec(LayoutKind.MOSAIC, "多要点讲解：使用均衡的卡片矩阵，每张卡片只保留一个短结论和一行解释。"),
    LayoutKind.RECAP: LayoutSpec(LayoutKind.RECAP, "收束复盘：知识地图、速查要点和迁移任务构成总结，不再重复课程导语。"),
}


LOGIC_RELATION_LAYOUTS: dict[LogicRelation, frozenset[LayoutKind]] = {
    LogicRelation.PREREQUISITE: frozenset({LayoutKind.ROUTE, LayoutKind.DIAGRAM, LayoutKind.SEQUENCE}),
    LogicRelation.DECOMPOSES: frozenset({LayoutKind.ROUTE, LayoutKind.DIAGRAM, LayoutKind.RECAP}),
    LogicRelation.SUPPORTS: frozenset({LayoutKind.STATEMENT, LayoutKind.DIAGRAM, LayoutKind.MOSAIC}),
    LogicRelation.DERIVES: frozenset({LayoutKind.SEQUENCE, LayoutKind.STUDIO}),
    LogicRelation.CAUSES: frozenset({LayoutKind.SEQUENCE, LayoutKind.DIAGRAM}),
    LogicRelation.CONTRASTS: frozenset({LayoutKind.COMPARISON}),
    LogicRelation.APPLIES: frozenset({LayoutKind.STUDIO, LayoutKind.DIAGRAM, LayoutKind.MOSAIC}),
    LogicRelation.VERIFIES: frozenset({LayoutKind.STUDIO, LayoutKind.STATEMENT, LayoutKind.MOSAIC}),
    LogicRelation.SUMMARIZES: frozenset({LayoutKind.RECAP, LayoutKind.ROUTE}),
}


def _validate_contract() -> None:
    declared = set(VisualKind)
    registered = set(VISUAL_COMPONENTS)
    if declared != registered:
        missing = ", ".join(kind.value for kind in declared - registered)
        extra = ", ".join(kind.value for kind in registered - declared)
        raise RuntimeError(f"PPT visual contract mismatch: missing=[{missing}] extra=[{extra}]")
    if any(component.kind != kind for kind, component in VISUAL_COMPONENTS.items()):
        raise RuntimeError("PPT visual contract contains a mismatched component key")
    if set(LayoutKind) != set(LAYOUTS):
        raise RuntimeError("PPT layout contract is incomplete")
    if set(LogicRelation) != set(LOGIC_RELATION_LAYOUTS):
        raise RuntimeError("PPT logic relation layout contract is incomplete")


_validate_contract()


def slide_kind_values() -> str:
    return "、".join(f"`{kind.value}`" for kind in SlideKind)


def visual_kind_values() -> str:
    return "、".join(f"`{kind.value}`" for kind in VisualKind)


def layout_kind_values() -> str:
    return "、".join(f"`{kind.value}`" for kind in LayoutKind)


def logic_node_role_values() -> str:
    return "、".join(f"`{role.value}`" for role in LogicNodeRole)


def logic_relation_values() -> str:
    return "、".join(f"`{relation.value}`" for relation in LogicRelation)


def visual_component_guidance() -> str:
    return "\n".join(
        f"- `{component.kind.value}`：{component.prompt_instruction}"
        for component in VISUAL_COMPONENTS.values()
    )


def layout_guidance() -> str:
    return "\n".join(
        f"- `{layout.kind.value}`：{layout.prompt_instruction}"
        for layout in LAYOUTS.values()
    )


def logic_layout_guidance() -> str:
    return "\n".join(
        f"- `{relation.value}` -> "
        + "、".join(f"`{layout.value}`" for layout in sorted(layouts, key=lambda item: item.value))
        for relation, layouts in LOGIC_RELATION_LAYOUTS.items()
    )


def layout_supports_relation(layout: LayoutKind, relation: LogicRelation) -> bool:
    return layout in LOGIC_RELATION_LAYOUTS[relation]


def visual_component(kind: VisualKind) -> VisualComponent:
    return VISUAL_COMPONENTS[kind]
