from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Protocol, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.shared.ppt.contract import (
    CourseDomain,
    LayoutKind,
    LogicNodeRole,
    LogicRelation,
    SlideKind,
    layout_supports_relation,
)
from app.shared.ppt.visual_ir import VisualModel


class PPTModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PPTSource(PPTModel):
    agent_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    materials: list[str] = Field(default_factory=list, max_length=12)


class PPTPreferences(PPTModel):
    """内容偏好 — 影响确定性编译的章节命名、页面分配和内容侧重。"""

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
    # The resource workflow owns a structured control plan. The shared PPT
    # engine projects its learner-facing fields into deterministic source copy.
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
    # ``topic`` is a display-ready lesson subject, not the user's complete
    # learning request.  The latter belongs to ``learning_goal`` and may be
    # much longer than a slide title.
    topic: str = Field(min_length=1)
    learner_profile: str = ""
    learning_goal: str = Field(min_length=1)
    prerequisites: list[str] = Field(default_factory=list, max_length=12)
    source_materials: list[str] = Field(default_factory=list, min_length=1, max_length=10)
    constraints: list[str] = Field(default_factory=list, max_length=8)
    preferences: PPTPreferences = Field(default_factory=PPTPreferences)


class LogicChapter(PPTModel):
    id: str = Field(pattern=r"^c[0-9]{2}$")
    title: str = Field(min_length=1)
    question: str = Field(min_length=1)
    outcome: str = Field(min_length=1)
    node_ids: list[str] = Field(min_length=1, max_length=8)


class LogicNode(PPTModel):
    id: str = Field(pattern=r"^l[0-9]{2}$")
    chapter_id: str | None = Field(default=None, pattern=r"^c[0-9]{2}$")
    title: str = Field(min_length=2)
    role: LogicNodeRole
    question: str = Field(min_length=1)
    claim: str = Field(min_length=1)
    evidence: list[str] = Field(default_factory=list, max_length=4)
    output: str = Field(min_length=1)


class LogicEdge(PPTModel):
    source_id: str = Field(pattern=r"^l[0-9]{2}$")
    target_id: str = Field(pattern=r"^l[0-9]{2}$")
    relation: LogicRelation
    bridge: str = Field(min_length=4)


class DeckLogicModel(PPTModel):
    """Canonical backend-owned teaching DAG for one presentation."""

    course_domain: CourseDomain
    central_question: str = Field(min_length=1)
    thesis: str = Field(min_length=1)
    chapters: list[LogicChapter] = Field(min_length=2, max_length=5)
    # Cover + roadmap + summary already occupy three pages. Four factual
    # teaching nodes therefore form the smallest complete seven-page lesson;
    # requiring a fifth node forced the compiler to invent a duplicate topic.
    nodes: list[LogicNode] = Field(min_length=4, max_length=16)
    edges: list[LogicEdge] = Field(min_length=3, max_length=24)

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
            # Auto-assign chapter_id from chapters if LLM omitted it
            if node.chapter_id is None:
                node.chapter_id = chapter_by_node.get(node.id)
            if node.chapter_id not in known_chapters:
                raise ValueError(f"logic node {node.id} references an unknown chapter")
            if chapter_by_node.get(node.id) != node.chapter_id:
                raise ValueError(f"logic node {node.id} is assigned to the wrong chapter")
            if not node.evidence:
                raise ValueError(f"logic node {node.id} needs evidence")

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
    """Renderer-neutral storyboard assignment for one slide."""

    id: str = Field(pattern=r"^s[0-9]{2}$")
    kind: SlideKind
    title: str = Field(min_length=1)
    teaching_goal: str = Field(min_length=1)
    content_focus: str = Field(min_length=1)
    chapter_id: str | None = Field(default=None, pattern=r"^c[0-9]{2}$")
    logic_node_ids: list[str] = Field(default_factory=list, max_length=8)
    question: str = ""
    claim: str = ""
    bridge: str = ""
    logic_relation: LogicRelation | None = None
    layout: LayoutKind
    density: Literal["concise", "standard", "detailed"] = "standard"

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


class _StoryArcSlide(Protocol):
    id: str
    kind: SlideKind


def _validate_canonical_story_arc(
    slides: Sequence[_StoryArcSlide],
    owner: str,
) -> None:
    meta_counts = {
        kind: sum(slide.kind is kind for slide in slides)
        for kind in (SlideKind.COVER, SlideKind.ROADMAP, SlideKind.SUMMARY)
    }
    if any(count != 1 for count in meta_counts.values()):
        raise ValueError(f"{owner} must contain exactly one cover, roadmap, and summary")
    if slides[0].kind is not SlideKind.COVER:
        raise ValueError(f"{owner} must start with cover")
    if slides[1].kind is not SlideKind.ROADMAP:
        raise ValueError(f"{owner} must place roadmap second")
    if slides[-1].kind is not SlideKind.SUMMARY:
        raise ValueError(f"{owner} must end with summary")
    if len({slide.id for slide in slides}) != len(slides):
        raise ValueError(f"{owner} slide ids must be unique")


class PPTStoryboard(PPTModel):
    """Canonical teaching arc compiled before visual planning."""

    title: str = Field(min_length=1)
    language: str = "zh-CN"
    visual_direction: str = Field(min_length=1)
    slides: list[SlideBrief] = Field(min_length=7, max_length=18)

    @model_validator(mode="after")
    def validate_story_arc(self) -> "PPTStoryboard":
        _validate_canonical_story_arc(self.slides, "storyboard")
        return self


class SlidePoint(PPTModel):
    """One bounded visible teaching point."""

    label: str = Field(min_length=1)
    detail: str = Field(min_length=1)


class PPTSlide(PPTModel):
    """Composed slide copy paired with optional renderer-neutral Visual IR."""

    id: str = Field(pattern=r"^s[0-9]{2}$")
    kind: SlideKind
    title: str = Field(min_length=1)
    subtitle: str = ""
    chapter_id: str | None = Field(default=None, pattern=r"^c[0-9]{2}$")
    logic_node_ids: list[str] = Field(default_factory=list, max_length=8)
    question: str = ""
    claim: str = ""
    bridge: str = ""
    logic_relation: LogicRelation | None = None
    layout: LayoutKind
    density: Literal["concise", "standard", "detailed"] = "standard"
    lead: str = ""
    points: list[SlidePoint] = Field(default_factory=list, max_length=3)
    speaker_notes: str = ""
    visual: VisualModel | None = None

    @model_validator(mode="after")
    def validate_logic_mapping(self) -> "PPTSlide":
        if self.kind not in {SlideKind.COVER, SlideKind.ROADMAP, SlideKind.SUMMARY}:
            if not self.chapter_id or not self.logic_node_ids or not self.question or not self.claim:
                raise ValueError("content slide needs its assigned logic mapping")
            if self.logic_relation is None:
                raise ValueError("content slide needs a primary logic relation")
        if self.logic_relation is not None and not layout_supports_relation(self.layout, self.logic_relation):
            raise ValueError(
                f"layout {self.layout.value} does not support relation {self.logic_relation.value}"
            )
        meta_kinds = {SlideKind.COVER, SlideKind.ROADMAP, SlideKind.SUMMARY}
        if self.kind in meta_kinds and self.visual is not None:
            raise ValueError("cover, roadmap and summary slides own their visual model in the renderer")
        if self.kind not in meta_kinds and self.visual is None:
            raise ValueError("non-meta slide requires a visual payload")
        return self


class PPTDeck(PPTModel):
    """Validated presentation whose content slides cover the teaching DAG."""

    title: str = Field(min_length=1)
    language: str = "zh-CN"
    visual_direction: str = Field(min_length=1)
    logic_model: DeckLogicModel
    slides: list[PPTSlide] = Field(min_length=7, max_length=18)

    @model_validator(mode="after")
    def validate_story_arc(self) -> "PPTDeck":
        _validate_canonical_story_arc(self.slides, "deck")
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
    slide_count: int
    html_url: str = ""
