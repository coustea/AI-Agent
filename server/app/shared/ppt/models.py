from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.shared.ppt.contract import (
    LayoutKind,
    LogicNodeRole,
    LogicRelation,
    SlideKind,
    VisualKind,
    layout_supports_relation,
)


class PPTModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PPTSource(PPTModel):
    agent_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    materials: list[str] = Field(default_factory=list, max_length=12)


class PPTPreferences(PPTModel):
    """内容偏好，不再选择视觉模板。"""

    narrative_style: Literal["concept", "case_driven", "problem_led", "review"] = "concept"
    density: Literal["concise", "standard", "detailed"] = "standard"
    emphasis: list[Literal["core_concepts", "cases", "pitfalls", "derivation"]] = Field(
        default_factory=lambda: ["core_concepts"], min_length=1, max_length=4
    )
    include_speaker_notes: bool = True


class ResourcePPT(PPTModel):
    """独立资源入口的 PPT 请求。"""

    username: str = ""
    learning_need: str = Field(min_length=1)
    learning_scenario: str = "self_study"
    profile: dict[str, Any] | str = Field(default_factory=dict)
    # The resource workflow owns a structured control plan.  The shared PPT
    # engine receives its JSON-safe snapshot and is the sole place that turns
    # it into prompt material.
    resource_plan: dict[str, Any] = Field(min_length=1)
    artifacts: list[PPTSource] = Field(default_factory=list, max_length=16)
    preferences: PPTPreferences = Field(default_factory=PPTPreferences)


class PathPPT(PPTModel):
    """学习路径入口的 PPT 请求。"""

    username: str = ""
    profile: dict[str, Any] | str = Field(default_factory=dict)
    preferences: PPTPreferences = Field(default_factory=PPTPreferences)
    path_title: str = Field(min_length=1)
    path_goal: str = Field(min_length=1)
    node_title: str = Field(min_length=1)
    node_key: str = Field(min_length=1)
    difficulty: str = "beginner"
    knowledge_points: list[str] = Field(default_factory=list, max_length=24)
    weak_knowledge_points: list[str] = Field(default_factory=list, max_length=24)
    tutorial_title: str = Field(min_length=1)
    tutorial_summary: str = ""
    tutorial_knowledge_points: list[str] = Field(default_factory=list, max_length=24)
    tutorial_core_content: str = Field(min_length=1)


class PPTGenerationContext(PPTModel):
    """两个业务入口归一化后交给共享 PPT 引擎的唯一内部契约。"""

    source: Literal["resource", "path"]
    topic: str = Field(min_length=1, max_length=160)
    learner_profile: str = Field(default="", max_length=1_600)
    learning_goal: str = Field(min_length=1, max_length=1_200)
    prerequisites: list[str] = Field(default_factory=list, max_length=12)
    source_materials: list[str] = Field(default_factory=list, min_length=1, max_length=10)
    constraints: list[str] = Field(default_factory=list, max_length=8)
    preferences: PPTPreferences = Field(default_factory=PPTPreferences)


class LogicChapter(PPTModel):
    id: str = Field(pattern=r"^c[0-9]{2}$")
    title: str = Field(min_length=2, max_length=32)
    question: str = Field(min_length=8, max_length=96)
    outcome: str = Field(min_length=8, max_length=120)
    node_ids: list[str] = Field(min_length=1, max_length=8)


class LogicNode(PPTModel):
    id: str = Field(pattern=r"^l[0-9]{2}$")
    chapter_id: str = Field(pattern=r"^c[0-9]{2}$")
    role: LogicNodeRole
    question: str = Field(min_length=8, max_length=96)
    claim: str = Field(min_length=8, max_length=120)
    evidence: list[str] = Field(default_factory=list, max_length=4)
    output: str = Field(min_length=8, max_length=120)
    importance: Literal["core", "supporting", "example"] = "core"


class LogicEdge(PPTModel):
    source_id: str = Field(pattern=r"^l[0-9]{2}$")
    target_id: str = Field(pattern=r"^l[0-9]{2}$")
    relation: LogicRelation
    bridge: str = Field(min_length=4, max_length=96)


class DeckLogicModel(PPTModel):
    central_question: str = Field(min_length=8, max_length=120)
    thesis: str = Field(min_length=8, max_length=160)
    learner_before: list[str] = Field(default_factory=list, max_length=6)
    learner_after: list[str] = Field(min_length=1, max_length=6)
    chapters: list[LogicChapter] = Field(min_length=2, max_length=5)
    nodes: list[LogicNode] = Field(min_length=5, max_length=16)
    edges: list[LogicEdge] = Field(min_length=4, max_length=24)

    @model_validator(mode="after")
    def validate_logic_graph(self) -> "DeckLogicModel":
        chapter_ids = [chapter.id for chapter in self.chapters]
        node_ids = [node.id for node in self.nodes]
        if len(set(chapter_ids)) != len(chapter_ids):
            raise ValueError("logic chapter ids must be unique")
        if len(set(node_ids)) != len(node_ids):
            raise ValueError("logic node ids must be unique")

        known_chapters = set(chapter_ids)
        known_nodes = set(node_ids)
        declared_nodes: list[str] = []
        for chapter in self.chapters:
            if len(set(chapter.node_ids)) != len(chapter.node_ids):
                raise ValueError(f"logic chapter {chapter.id} contains duplicate node ids")
            declared_nodes.extend(chapter.node_ids)
        if set(declared_nodes) != known_nodes or len(declared_nodes) != len(known_nodes):
            raise ValueError("logic chapters must contain every node exactly once")

        chapter_by_node = {node_id: chapter.id for chapter in self.chapters for node_id in chapter.node_ids}
        for node in self.nodes:
            if node.chapter_id not in known_chapters:
                raise ValueError(f"logic node {node.id} references an unknown chapter")
            if chapter_by_node[node.id] != node.chapter_id:
                raise ValueError(f"logic node {node.id} is assigned to the wrong chapter")
            if node.importance == "core" and not node.evidence and node.role not in {
                LogicNodeRole.QUESTION,
                LogicNodeRole.CONCLUSION,
            }:
                raise ValueError(f"core logic node {node.id} needs evidence")

        adjacency: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
        undirected: dict[str, set[str]] = {node_id: set() for node_id in node_ids}
        connected: set[str] = set()
        for edge in self.edges:
            if edge.source_id not in known_nodes or edge.target_id not in known_nodes:
                raise ValueError("logic edge references an unknown node")
            if edge.source_id == edge.target_id:
                raise ValueError("logic edges cannot loop to the same node")
            adjacency[edge.source_id].append(edge.target_id)
            undirected[edge.source_id].add(edge.target_id)
            undirected[edge.target_id].add(edge.source_id)
            connected.update((edge.source_id, edge.target_id))
        isolated = known_nodes - connected
        if isolated:
            raise ValueError(f"logic graph contains isolated nodes: {sorted(isolated)}")

        reachable: set[str] = set()
        pending = [node_ids[0]]
        while pending:
            node_id = pending.pop()
            if node_id in reachable:
                continue
            reachable.add(node_id)
            pending.extend(undirected[node_id] - reachable)
        if reachable != known_nodes:
            raise ValueError("logic graph must form one connected component")

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str) -> None:
            if node_id in visiting:
                raise ValueError("logic graph must be acyclic")
            if node_id in visited:
                return
            visiting.add(node_id)
            for target_id in adjacency[node_id]:
                visit(target_id)
            visiting.remove(node_id)
            visited.add(node_id)

        for node_id in node_ids:
            visit(node_id)
        return self


class SlideBrief(PPTModel):
    id: str = Field(pattern=r"^s[0-9]{2}$")
    kind: SlideKind
    title: str = Field(min_length=1, max_length=54)
    teaching_goal: str = Field(min_length=12, max_length=150)
    content_focus: str = Field(min_length=12, max_length=180)
    chapter_id: str | None = Field(default=None, pattern=r"^c[0-9]{2}$")
    logic_node_ids: list[str] = Field(default_factory=list, max_length=3)
    question: str = Field(default="", max_length=96)
    claim: str = Field(default="", max_length=120)
    bridge: str = Field(default="", max_length=96)
    logic_relation: LogicRelation | None = None
    visual_kind: VisualKind
    layout: LayoutKind

    @model_validator(mode="after")
    def validate_logic_mapping(self) -> "SlideBrief":
        if self.kind not in {SlideKind.COVER, SlideKind.ROADMAP, SlideKind.SUMMARY}:
            if not self.chapter_id or not self.logic_node_ids or not self.question or not self.claim:
                raise ValueError("content slide needs chapter, logic nodes, question, and claim")
            if self.logic_relation is None:
                raise ValueError("content slide needs a primary logic relation")
        if self.logic_relation is not None and not layout_supports_relation(self.layout, self.logic_relation):
            raise ValueError(
                f"layout {self.layout.value} does not support relation {self.logic_relation.value}"
            )
        return self


class PPTStoryboard(PPTModel):
    title: str = Field(min_length=1, max_length=72)
    language: str = "zh-CN"
    visual_direction: str = Field(min_length=24, max_length=300)
    slides: list[SlideBrief] = Field(min_length=10, max_length=18)

    @model_validator(mode="after")
    def validate_story_arc(self) -> "PPTStoryboard":
        if self.slides[0].kind is not SlideKind.COVER or self.slides[-1].kind is not SlideKind.SUMMARY:
            raise ValueError("storyboard must start with cover and end with summary")
        if len({slide.id for slide in self.slides}) != len(self.slides):
            raise ValueError("storyboard slide ids must be unique")
        return self


class SlidePoint(PPTModel):
    label: str = Field(min_length=1, max_length=24)
    detail: str = Field(min_length=8, max_length=72)


class VisualMetric(PPTModel):
    label: str = Field(min_length=1, max_length=24)
    value: str = Field(min_length=1, max_length=32)
    detail: str = Field(default="", max_length=56)


class DiagramNode(PPTModel):
    id: str = Field(pattern=r"^n[0-9]{1,2}$")
    label: str = Field(min_length=1, max_length=24)
    detail: str = Field(default="", max_length=48)
    tone: Literal["primary", "secondary", "accent", "muted", "warning"] = "primary"


class DiagramEdge(PPTModel):
    source_id: str = Field(pattern=r"^n[0-9]{1,2}$")
    target_id: str = Field(pattern=r"^n[0-9]{1,2}$")
    label: str = Field(default="", max_length=24)


class DiagramModel(PPTModel):
    layout: Literal["hierarchy", "flow", "network", "comparison"] = "flow"
    nodes: list[DiagramNode] = Field(min_length=2, max_length=8)
    edges: list[DiagramEdge] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def validate_graph(self) -> "DiagramModel":
        node_ids = {node.id for node in self.nodes}
        if len(node_ids) != len(self.nodes):
            raise ValueError("diagram node ids must be unique")
        for edge in self.edges:
            if edge.source_id not in node_ids or edge.target_id not in node_ids:
                raise ValueError("diagram edge references an unknown node")
            if edge.source_id == edge.target_id:
                raise ValueError("diagram edges cannot loop to the same node")
        return self


class VisualSpec(PPTModel):
    kind: VisualKind
    title: str = Field(default="", max_length=48)
    caption: str = Field(default="", max_length=84)
    metrics: list[VisualMetric] = Field(default_factory=list, max_length=5)
    code_language: str = Field(default="", max_length=20)
    code: str = Field(default="", max_length=1_600)
    formula: str = Field(default="", max_length=300)
    formula_steps: list[str] = Field(default_factory=list, max_length=5)
    model: DiagramModel | None = None

    @model_validator(mode="after")
    def validate_visual_payload(self) -> "VisualSpec":
        if self.kind is VisualKind.MODEL and self.model is None:
            raise ValueError("model visual requires a structured diagram model")
        if self.kind is not VisualKind.MODEL and self.model is not None:
            raise ValueError("only model visuals may declare a diagram model")
        return self


class PPTSlide(PPTModel):
    id: str = Field(pattern=r"^s[0-9]{2}$")
    kind: SlideKind
    title: str = Field(min_length=1, max_length=54)
    eyebrow: str = Field(default="", max_length=28)
    subtitle: str = Field(default="", max_length=84)
    lead: str = Field(default="", max_length=96)
    chapter_id: str | None = Field(default=None, pattern=r"^c[0-9]{2}$")
    logic_node_ids: list[str] = Field(default_factory=list, max_length=3)
    question: str = Field(default="", max_length=96)
    claim: str = Field(default="", max_length=120)
    bridge: str = Field(default="", max_length=96)
    logic_relation: LogicRelation | None = None
    points: list[SlidePoint] = Field(default_factory=list, max_length=4)
    visual: VisualSpec
    layout: LayoutKind
    takeaway: str = Field(default="", max_length=96)
    speaker_notes: str = Field(default="", max_length=600)

    @model_validator(mode="after")
    def validate_teaching_payload(self) -> "PPTSlide":
        if not self.lead and not self.points and not self.visual.code and not self.visual.formula and self.visual.model is None:
            raise ValueError("slide needs a teaching statement, points, code, formula, or diagram model")
        if self.kind not in {SlideKind.COVER, SlideKind.ROADMAP, SlideKind.SUMMARY}:
            if not self.chapter_id or not self.logic_node_ids or not self.question or not self.claim:
                raise ValueError("content slide needs its assigned logic mapping")
            if self.logic_relation is None:
                raise ValueError("content slide needs a primary logic relation")
        if self.logic_relation is not None and not layout_supports_relation(self.layout, self.logic_relation):
            raise ValueError(
                f"layout {self.layout.value} does not support relation {self.logic_relation.value}"
            )
        return self


class PPTSection(PPTModel):
    slides: list[PPTSlide] = Field(min_length=1, max_length=6)


class PPTDeck(PPTModel):
    title: str = Field(min_length=1, max_length=72)
    language: str = "zh-CN"
    visual_direction: str = Field(min_length=24, max_length=300)
    logic_model: DeckLogicModel
    slides: list[PPTSlide] = Field(min_length=10, max_length=18)

    @model_validator(mode="after")
    def validate_story_arc(self) -> "PPTDeck":
        if self.slides[0].kind is not SlideKind.COVER or self.slides[-1].kind is not SlideKind.SUMMARY:
            raise ValueError("deck must start with cover and end with summary")
        if len({slide.id for slide in self.slides}) != len(self.slides):
            raise ValueError("deck slide ids must be unique")
        known_chapters = {chapter.id for chapter in self.logic_model.chapters}
        known_nodes = {node.id for node in self.logic_model.nodes}
        covered_nodes: set[str] = set()
        completed_chapters: set[str] = set()
        active_chapter: str | None = None
        for slide in self.slides:
            if slide.chapter_id is not None:
                if slide.chapter_id not in known_chapters:
                    raise ValueError(f"slide {slide.id} references an unknown chapter")
                if slide.chapter_id != active_chapter:
                    if slide.chapter_id in completed_chapters:
                        raise ValueError("slides for each logic chapter must be contiguous")
                    if active_chapter is not None:
                        completed_chapters.add(active_chapter)
                    active_chapter = slide.chapter_id
            unknown_nodes = set(slide.logic_node_ids) - known_nodes
            if unknown_nodes:
                raise ValueError(f"slide {slide.id} references unknown logic nodes")
            if slide.kind not in {SlideKind.COVER, SlideKind.ROADMAP, SlideKind.SUMMARY}:
                covered_nodes.update(slide.logic_node_ids)
        if covered_nodes != known_nodes:
            raise ValueError("content slides must cover every logic node")
        return self


class PPTArtifact(PPTModel):
    title: str = Field(min_length=1)
    path: Path
    generated_at: datetime
    template_id: str = "computer-teaching-studio"
    template_name: str = "计算机课程教学工作室"
    slide_count: int
    html_url: str = ""
