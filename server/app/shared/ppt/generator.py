from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from app.shared.ppt.contract import (
    CourseDomain,
    LogicNodeRole,
    LogicRelation,
    SlideKind,
    VisualFamily,
    select_layout,
    select_provisional_layout,
)
from app.shared.ppt.html import PPTHTMLPublisher, PPTHTMLRenderer, PPTPublication
from app.shared.ppt.models import (
    DeckLogicModel,
    LogicChapter,
    LogicEdge,
    LogicNode,
    PPTArtifact,
    PPTDeck,
    PPTGenerationContext,
    PPTSlide,
    PPTStoryboard,
    PathPPT,
    ResourcePPT,
    SlideBrief,
    SlidePoint,
)
from app.shared.ppt.visual_ir import VisualModel
from app.shared.ppt.visual_planner import VisualPlanner


ProgressCallback = Callable[[str, int], Awaitable[None]]
_PRESENTATION_TIMEZONE = ZoneInfo("Asia/Shanghai")
PPT_PIPELINE_VERSION = "deterministic-html-v6"
PPT_PIPELINE_STAGES = (
    "assembling_context",
    "designing_logic",
    "designing_story",
    "compiling_visuals",
    "composing_slides",
    "rendering_html",
)
_MAX_SOURCE_MATERIALS = 10
_MARKDOWN_HEADING = re.compile(r"^\s{0,3}(?P<level>#{1,6})\s+(?P<title>.+?)\s*$")
_MARKDOWN_LIST_ITEM = re.compile(r"^\s{0,3}(?:[-*+]\s+|\d+[.)、]\s+)(?P<item>.+?)\s*$")
_SENTENCE_BOUNDARY = re.compile(r"[。！？!?；;]+|\n+")
_MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_MARKDOWN_EMPHASIS = re.compile(r"[`*_~]")
_LEADING_LABEL = re.compile(r"^(?P<label>[^：:]{1,12})[：:]\s*(?P<body>.+)$")
_GENERIC_HEADINGS = frozenset(
    {
        "概述",
        "核心概念",
        "概念精解",
        "应用场景",
        "总结",
        "复习建议",
        "高频考点",
        "复习策略",
        "关键解释",
        "案例目标",
    }
)
_NON_FACT_MARKERS = (
    "需要解决什么问题",
    "学习目标",
    "学习路线",
    "能够说明",
    "下一步",
    "形成清晰的学习路径",
)
_DOMAIN_KEYWORDS: dict[CourseDomain, tuple[str, ...]] = {
    CourseDomain.ALGORITHMS: ("算法", "排序", "树", "图", "复杂度", "递归", "动态规划"),
    CourseDomain.OPERATING_SYSTEMS: ("进程", "线程", "死锁", "内存", "调度", "操作系统"),
    CourseDomain.NETWORKS: ("tcp", "udp", "网络", "报文", "握手", "路由", "http"),
    CourseDomain.COMPUTER_ARCHITECTURE: ("cpu", "缓存", "指令", "流水线", "体系结构"),
    CourseDomain.DATABASES: ("数据库", "sql", "事务", "索引", "关系模型"),
    CourseDomain.COMPILERS: ("编译", "词法", "语法", "中间代码", "优化"),
    CourseDomain.DISCRETE_THEORY: ("离散", "集合", "逻辑", "图论", "组合"),
    CourseDomain.SOFTWARE_DISTRIBUTED: ("分布式", "一致性", "微服务", "并发", "系统设计"),
}


@dataclass
class _KnowledgeUnit:
    """One source-grounded teaching unit before it enters the lesson DAG."""

    title: str
    claim: str
    evidence: list[str] = field(default_factory=list)

    def add_evidence(self, fact: str) -> None:
        if fact != self.claim and fact not in self.evidence and len(self.evidence) < 3:
            self.evidence.append(fact)


def ppt_pipeline_metadata() -> dict[str, object]:
    """Expose the actual pipeline contract used by resource and path callers."""

    return {
        "version": PPT_PIPELINE_VERSION,
        "stages": list(PPT_PIPELINE_STAGES),
        "copy_compiler": "deterministic",
    }


class PPTGenerationError(RuntimeError):
    def __init__(self, stage: str, message: str) -> None:
        self.stage = stage
        super().__init__(f"{stage}: {message}")


class PPTContextAdapter:
    """让 resource/path 维持各自参数，仅共享内部生成语义。"""

    @classmethod
    def from_request(cls, request: ResourcePPT | PathPPT) -> PPTGenerationContext:
        if isinstance(request, ResourcePPT):
            # A resource plan is orchestration metadata.  It answers *why* a
            # deck is requested, not *what is true* in the lesson.  Treating
            # it as source material was the direct cause of slides that
            # repeated the learner goal instead of teaching the handoff.
            materials = cls._artifact_materials(request.artifacts)
            return PPTGenerationContext(
                source="resource",
                topic=cls._resource_topic(request),
                learner_profile=cls._profile_text(request.profile),
                learning_goal=cls._text(request.learning_need),
                prerequisites=[],
                source_materials=cls._clean_materials(materials),
                constraints=[f"学习场景：{cls._text(request.learning_scenario)}"],
                preferences=request.preferences,
            )

        # Path metadata is useful for the goal and prerequisite rails, but a
        # lesson's factual source is its authored tutorial body.  Mixing in a
        # summary and bare knowledge-point labels creates title-only slides.
        materials = [request.tutorial_core_content]
        return PPTGenerationContext(
            source="path",
            topic=cls._text(request.node_title),
            learner_profile=cls._profile_text(request.profile),
            learning_goal=cls._text(request.path_goal),
            prerequisites=[cls._text(item) for item in request.knowledge_points[:12]],
            source_materials=cls._clean_materials(materials),
            constraints=[
                f"路径：{cls._text(request.path_title)}",
                f"难度：{cls._text(request.difficulty)}",
                "薄弱点：" + "、".join(cls._text(item) for item in request.weak_knowledge_points[:8]),
            ],
            preferences=request.preferences,
        )

    @classmethod
    def _resource_topic(cls, request: ResourcePPT) -> str:
        """Select the display subject from the structured plan, never the raw need.

        ``learning_need`` describes the learner, their course, and desired
        outcome.  It is deliberately preserved in ``learning_goal``.  A deck
        title instead comes from the planner's scoped subject, with the PPT
        task and upstream artifact headings as progressively less-specific
        sources.  This keeps presentation text and prompt context separate.
        """

        plan = request.resource_plan
        candidates: list[object] = []
        scope = plan.get("scope")
        if isinstance(scope, list):
            candidates.extend(scope)

        tasks = plan.get("tasks")
        if isinstance(tasks, list):
            for task in tasks:
                if not isinstance(task, dict) or task.get("agent_id") != "ppt":
                    continue
                focus = task.get("focus")
                if isinstance(focus, list):
                    candidates.extend(focus)
                candidates.append(task.get("objective", ""))

        candidates.extend(source.title for source in request.artifacts)
        candidates.append(request.learning_need)

        for candidate in candidates:
            if not isinstance(candidate, str):
                continue
            title = cls._text(candidate)
            if title:
                return title
        raise ValueError("资源教学计划没有可用的课件主题")

    @staticmethod
    def _profile_text(profile: dict[str, Any] | str) -> str:
        value = profile if isinstance(profile, str) else " ".join(PPTContextAdapter._string_leaves(profile))
        return PPTContextAdapter._text(value)

    @classmethod
    def _artifact_materials(cls, artifacts: list[PPTSource]) -> list[str]:
        """Collect factual handoffs in an order suitable for a lesson compiler.

        The content handoff is prose-first and therefore the strongest source
        for claims.  Code and mind-map handoffs follow as supporting material.
        Titles and one-sentence summaries are deliberately excluded: they are
        labels for another artifact, not evidence for a teaching slide.
        """

        priority = {"content": 0, "code": 1, "mindmap": 2, "quiz": 3, "reading": 4}
        ordered = sorted(
            artifacts,
            key=lambda source: (priority.get(source.agent_id, 9), source.agent_id),
        )
        materials = [
            material
            for source in ordered
            for material in source.materials[:12]
            if material.strip()
        ]
        if not materials:
            raise ValueError("PPT 聚合生成缺少基础 Agent 提供的教学正文")
        return cls._clean_materials(materials)

    @staticmethod
    def _string_leaves(value: object) -> list[str]:
        if isinstance(value, str):
            return [value]
        if isinstance(value, dict):
            return [item for child in value.values() for item in PPTContextAdapter._string_leaves(child)]
        if isinstance(value, list):
            return [item for child in value for item in PPTContextAdapter._string_leaves(child)]
        return []

    @staticmethod
    def _clean_materials(values: list[str]) -> list[str]:
        """Normalize source material without discarding its factual content.

        The logic compiler and storyboard receive the same source context.
        Every downstream projection receives the same complete facts. Layout
        must adapt at render time rather than silently clipping source truth.
        """
        materials: list[str] = []
        for value in values:
            # Markdown headings and list items encode the author-provided
            # concept boundaries.  Preserve line breaks here; flattening them
            # made the fact compiler lose every heading before it began.
            text = "\n".join(
                " ".join(line.split())
                for line in value.replace("\r\n", "\n").replace("\r", "\n").split("\n")
                if line.strip()
            )
            if not text or len(materials) >= _MAX_SOURCE_MATERIALS:
                continue
            materials.append(text)
        return materials

    @staticmethod
    def _text(value: str) -> str:
        return " ".join(value.split())


class PPTGenerator:
    """Compile source material directly into a self-contained HTML lesson deck.

    The generator intentionally has no language-model dependency. Resource
    planning may use models upstream, but this delivery boundary only accepts
    normalized learning material and deterministically produces a valid deck.
    """

    def __init__(
        self,
        *,
        renderer: PPTHTMLRenderer | None = None,
        planner: VisualPlanner | None = None,
    ) -> None:
        self._renderer = renderer or PPTHTMLRenderer()
        self._planner = planner or VisualPlanner()

    @staticmethod
    def _text(value: str) -> str:
        """Normalize whitespace without applying a presentation text budget."""

        return " ".join(value.split())

    async def generate(
        self,
        request: ResourcePPT | PathPPT,
        *,
        output_dir: Path,
        progress: ProgressCallback | None = None,
    ) -> PPTArtifact:
        stage = "assembling_context"
        try:
            context = PPTContextAdapter.from_request(request)
            await self._progress(progress, "正在整理课程材料…", 8)

            stage = "designing_logic"
            await self._progress(progress, "教学逻辑架构师正在建立知识依赖模型…", 20)
            logic_model = self._generate_logic_model(context)

            stage = "designing_story"
            await self._progress(progress, "正在将知识链编译为教学故事板…", 34)
            storyboard = self._compile_storyboard(context, logic_model)
            self._validate_storyboard_logic(storyboard, logic_model)

            stage = "compiling_visuals"
            await self._progress(progress, "正在编译每页的教学图解…", 40)
            visuals = self._planner.plan(storyboard, logic_model)

            stage = "composing_slides"
            await self._progress(progress, "正在按全局逻辑确定性编排页面文案…", 48)
            deck = self._compose_deck(
                context,
                logic_model,
                storyboard,
                visuals,
            )

            stage = "rendering_html"
            await self._progress(progress, "正在将语义版式渲染为 HTML/SVG 课件…", 88)
            publication = PPTPublication(generated_at=datetime.now(_PRESENTATION_TIMEZONE))
            document = self._renderer.render(deck, publication)

            stage = "publishing"
            path = PPTHTMLPublisher(output_dir).publish("slides", document)
            await self._progress(progress, "课件生成完成", 100)
        except PPTGenerationError:
            raise
        except Exception as exc:
            raise PPTGenerationError(stage, str(exc)) from exc

        return PPTArtifact(
            title=deck.title,
            path=path,
            generated_at=publication.generated_at,
            slide_count=len(deck.slides),
        )

    _NARRATIVE_CHAPTER_TITLES: dict[str, tuple[str, str]] = {
        "concept": ("概念与结构", "方法与应用"),
        "case_driven": ("案例引入", "实践与迁移"),
        "problem_led": ("问题与线索", "推导与解决"),
        "review": ("核心回顾", "查漏与巩固"),
    }

    _NARRATIVE_QUESTIONS: dict[str, str] = {
        "concept": "如何理解并应用{topic}？",
        "case_driven": "{topic}在真实场景中如何发挥作用？",
        "problem_led": "关于{topic}的核心问题是什么？如何解决？",
        "review": "{topic}有哪些必须掌握的要点和常见误区？",
    }

    _EMPHASIS_ROLE_BOOST: dict[str, list[LogicNodeRole]] = {
        "core_concepts": [LogicNodeRole.CONCEPT, LogicNodeRole.MECHANISM],
        "cases": [LogicNodeRole.CASE, LogicNodeRole.EVIDENCE],
        "pitfalls": [LogicNodeRole.CONCLUSION],
        "derivation": [LogicNodeRole.METHOD, LogicNodeRole.MECHANISM],
    }

    @classmethod
    def _generate_logic_model(cls, context: PPTGenerationContext) -> DeckLogicModel:
        """Build a bounded teaching graph from human-readable source material."""

        units = cls._knowledge_units(context)
        chapter_break = max(2, min(3, len(units) // 2))
        narrative = context.preferences.narrative_style
        emphasis = set(context.preferences.emphasis)
        nodes: list[LogicNode] = []
        for index, unit in enumerate(units, start=1):
            role = cls._role_for_unit(unit, emphasis_boost=emphasis)
            chapter_id = "c01" if index <= chapter_break else "c02"
            nodes.append(
                LogicNode(
                    id=f"l{index:02d}",
                    chapter_id=chapter_id,
                    title=cls._text(unit.title),
                    role=role,
                    question=cls._question_for(unit.title, role),
                    claim=cls._text(unit.claim),
                    # The graph contract requires evidence for every node.  A
                    # standalone source fact is its own evidence; downstream
                    # copy/visual projections de-duplicate it before display.
                    evidence=[
                        cls._text(item)
                        for item in (unit.evidence or [unit.claim])
                    ],
                    output=cls._output_for(unit),
                )
            )

        c1_title, c2_title = cls._NARRATIVE_CHAPTER_TITLES.get(narrative, ("概念与结构", "方法与应用"))
        chapters: list[LogicChapter] = []
        for chapter_id, title, chapter_nodes in (
            ("c01", c1_title, [node for node in nodes if node.chapter_id == "c01"]),
            ("c02", c2_title, [node for node in nodes if node.chapter_id == "c02"]),
        ):
            if not chapter_nodes:
                continue
            chapters.append(
                LogicChapter(
                    id=chapter_id,
                    title=title,
                    question=chapter_nodes[0].question,
                    outcome=chapter_nodes[-1].output,
                    node_ids=[node.id for node in chapter_nodes],
                )
            )

        return DeckLogicModel(
            course_domain=cls._infer_course_domain(context),
            central_question=cls._text(cls._NARRATIVE_QUESTIONS.get(narrative, "如何理解并应用{topic}？").format(topic=context.topic)),
            thesis=cls._text("；".join(node.claim for node in nodes[-2:])),
            chapters=chapters,
            nodes=nodes,
            edges=[
                LogicEdge(
                    source_id=source.id,
                    target_id=target.id,
                    relation=cls._relation_for(target),
                    bridge=cls._bridge_for(source, target),
                )
                for source, target in zip(nodes, nodes[1:])
            ],
        )

    @classmethod
    def _knowledge_units(cls, context: PPTGenerationContext) -> list[_KnowledgeUnit]:
        """Compile headings and facts from handoffs, never from task metadata.

        A source heading owns the facts beneath it.  This preserves the
        author's concept boundaries (for example ``前序遍历``) instead of
        turning every sentence or user request into a slide title.
        """

        by_title: dict[str, _KnowledgeUnit] = {}
        seen_facts: set[str] = set()
        for material in context.source_materials:
            active_title = ""
            in_code_fence = False
            for raw_line in material.splitlines():
                line = raw_line.strip()
                if line.startswith("```"):
                    in_code_fence = not in_code_fence
                    continue
                if not line or in_code_fence:
                    continue

                heading = _MARKDOWN_HEADING.match(line)
                if heading:
                    candidate = cls._clean_source_text(heading.group("title"))
                    active_title = "" if candidate in _GENERIC_HEADINGS else candidate
                    continue

                item = _MARKDOWN_LIST_ITEM.match(line)
                if item:
                    line = item.group("item")
                line = cls._clean_source_text(line)
                if not line:
                    continue

                title_from_line, fact_line = cls._line_semantics(line)
                for fact in cls._sentences(fact_line):
                    if not cls._is_teaching_fact(fact):
                        continue
                    title = title_from_line or active_title or cls._unit_title(fact, context.topic)
                    title = cls._text(title)
                    normalized = cls._normalize_fact(fact)
                    if not title or not normalized or normalized in seen_facts:
                        continue
                    seen_facts.add(normalized)
                    unit = by_title.get(title)
                    if unit is None:
                        by_title[title] = _KnowledgeUnit(
                            title=title,
                            claim=fact,
                            evidence=cls._sequence_steps(fact),
                        )
                    else:
                        unit.add_evidence(fact)

        units = list(by_title.values())
        if len(units) < 4:
            raise PPTGenerationError(
                "designing_logic",
                "基础资源缺少足够的知识事实，无法生成教学课件；请确保至少提供 4 个含定义、步骤或案例的内容单元",
            )
        return units[:8]

    @staticmethod
    def _clean_source_text(value: str) -> str:
        plain = _MARKDOWN_LINK.sub(r"\1", value)
        plain = _MARKDOWN_EMPHASIS.sub("", plain)
        return " ".join(plain.split()).strip("：:，,。；;！!？? ")

    @classmethod
    def _line_semantics(cls, line: str) -> tuple[str, str]:
        """Split a labelled source line into a concept title and its fact."""

        match = _LEADING_LABEL.match(line)
        if not match:
            return "", line
        label = cls._clean_source_text(match.group("label"))
        body = cls._clean_source_text(match.group("body"))
        if label in {"定义", "作用", "特点", "说明", "步骤", "结论", "注意", "类比", "访问顺序"}:
            return "", body
        return label, body

    @classmethod
    def _sentences(cls, value: str) -> list[str]:
        return [
            cls._clean_source_text(part)
            for part in _SENTENCE_BOUNDARY.split(value)
            if len(cls._clean_source_text(part)) >= 2
        ]

    @staticmethod
    def _normalize_fact(value: str) -> str:
        return re.sub(r"[\s，,。；;：:！!？?]", "", value).lower()

    @classmethod
    def _is_teaching_fact(cls, value: str) -> bool:
        if len(value) < 2 or value.endswith(("？", "?")):
            return False
        return not any(marker in value for marker in _NON_FACT_MARKERS)

    @staticmethod
    def _sequence_steps(value: str) -> list[str]:
        """Extract explicit ordered steps without inventing a process."""

        matches = re.findall(r"(先|再|然后|最后)([^，,。；;]+)", value)
        steps = [f"{prefix}{body.strip()}" for prefix, body in matches if body.strip()]
        return list(dict.fromkeys(steps))[:3] if len(steps) >= 2 else []

    @classmethod
    def _unit_title(cls, value: str, fallback: str) -> str:
        text = " ".join(value.split()).strip("：:，,。；;！!？? ")
        if "：" in text:
            text = text.split("：", 1)[0]
        for token in ("是", "指", "通过", "包括", "用于"):
            if token in text:
                candidate = text.split(token, 1)[0].strip("的 ，。；：、 -—")
                if len(candidate) >= 2:
                    text = candidate
                    break
        return text if len(text) >= 2 else cls._text(fallback)

    @classmethod
    def _infer_course_domain(cls, context: PPTGenerationContext) -> CourseDomain:
        corpus = " ".join((context.topic, context.learning_goal, *context.source_materials)).lower()
        for domain, keywords in _DOMAIN_KEYWORDS.items():
            if any(keyword in corpus for keyword in keywords):
                return domain
        return CourseDomain.GENERAL_CS

    @classmethod
    def _role_for_unit(cls, unit: _KnowledgeUnit, *, emphasis_boost: set[str] | None = None) -> LogicNodeRole:
        corpus = f"{unit.title} {' '.join([unit.claim, *unit.evidence])}"
        # When emphasis includes pitfalls, boost conclusion detection
        boost_roles: set[LogicNodeRole] = set()
        if emphasis_boost:
            for emphasis_key in emphasis_boost:
                boost_roles.update(cls._EMPHASIS_ROLE_BOOST.get(emphasis_key, []))
        if any(token in corpus for token in ("对比", "区别", "差异", "联系")):
            return LogicNodeRole.CASE
        if any(token in corpus for token in ("步骤", "顺序", "遍历", "流程", "算法")):
            return LogicNodeRole.METHOD
        if any(token in corpus for token in ("机制", "原理", "结构", "线索", "指针")):
            return LogicNodeRole.MECHANISM
        if any(token in corpus for token in ("误区", "注意", "结论", "总结")):
            return LogicNodeRole.CONCLUSION
        # No keyword match — prefer a role that aligns with emphasis
        if boost_roles:
            return next(iter(boost_roles))
        return LogicNodeRole.CONCEPT

    @classmethod
    def _question_for(cls, title: str, role: LogicNodeRole) -> str:
        if role is LogicNodeRole.METHOD:
            return cls._text(f"如何正确执行{title}？")
        if role is LogicNodeRole.CASE:
            return cls._text(f"{title}之间有什么差异或联系？")
        if role is LogicNodeRole.MECHANISM:
            return cls._text(f"{title}为什么能发挥作用？")
        return cls._text(f"{title}的关键特征是什么？")

    @classmethod
    def _output_for(cls, unit: _KnowledgeUnit) -> str:
        evidence = "；".join(unit.evidence[:2])
        if evidence:
            return cls._text(f"结合{evidence}理解{unit.title}。")
        return cls._text(f"依据“{unit.claim}”理解{unit.title}。")

    @classmethod
    def _relation_for(cls, target: LogicNode) -> LogicRelation:
        """Choose a visual relation from available source structure.

        A node with one factual statement is evidence, not a fabricated flow.
        More specialised diagrams are reserved for source text that explicitly
        carries a sequence or comparison relation.
        """

        corpus = " ".join((target.title, target.claim, *target.evidence))
        if target.role is LogicNodeRole.CASE and any(
            token in corpus for token in ("对比", "区别", "差异", "联系")
        ):
            return LogicRelation.CONTRASTS
        if target.role is LogicNodeRole.METHOD and any(
            token in corpus for token in ("先", "再", "然后", "最后", "步骤", "顺序")
        ):
            return LogicRelation.DERIVES
        return LogicRelation.SUPPORTS

    @staticmethod
    def _bridge_for(source: LogicNode, target: LogicNode) -> str:
        return f"从{source.title}出发，继续理解{target.title}。"[:96]

    @staticmethod
    def _compile_storyboard(
        context: PPTGenerationContext,
        logic_model: DeckLogicModel,
    ) -> PPTStoryboard:
        """Compile a teaching DAG into the canonical cover-to-summary arc.

        The storyboard owns teaching sequence and provisional composition only.
        It deliberately makes no visual-family decision; the visual planner
        resolves that independent concern after this compiler has finished.

        Args:
            context: Normalized lesson request and copy preferences.
            logic_model: Validated teaching graph with canonical node identity.

        Returns:
            A seven-to-eighteen-slide storyboard covering every logic node.

        Raises:
            PPTGenerationError: If nodes cannot be grouped without crossing a
                chapter or exceeding the slide budget.
        """

        chapters_by_id = {chapter.id: chapter for chapter in logic_model.chapters}
        nodes_by_id = {node.id: node for node in logic_model.nodes}

        def relation_for(node_ids: list[str]) -> LogicEdge:
            primary_id = node_ids[0]
            for edge in logic_model.edges:
                if edge.target_id == primary_id:
                    return edge
            # The first knowledge node has no incoming edge.  It is presented
            # as a source-backed fact, not as a fabricated prerequisite flow.
            primary = nodes_by_id[primary_id]
            return LogicEdge(
                source_id=primary.id,
                target_id=logic_model.nodes[1].id,
                relation=LogicRelation.SUPPORTS,
                bridge="从第一个知识事实开始建立课程框架。",
            )

        def content_brief(
            *,
            kind: SlideKind,
            title: str,
            teaching_goal: str,
            content_focus: str,
            node_ids: list[str],
        ) -> SlideBrief:
            primary = nodes_by_id[node_ids[0]]
            chapter = chapters_by_id[primary.chapter_id]
            if any(nodes_by_id[node_id].chapter_id != chapter.id for node_id in node_ids):
                raise PPTGenerationError("designing_story", "一页知识内容不能跨章节合并")
            relation = relation_for(node_ids)
            return SlideBrief(
                id="s00",
                kind=kind,
                title=title[:54],
                teaching_goal=teaching_goal[:150],
                content_focus=content_focus[:180],
                chapter_id=chapter.id,
                logic_node_ids=node_ids,
                question=primary.question,
                claim=primary.claim,
                bridge=relation.bridge,
                logic_relation=relation.relation,
                layout=select_provisional_layout(kind, relation.relation),
                density=context.preferences.density,
            )

        groups: list[tuple[str, list[str]]] = [
            (chapter.id, [node_id])
            for chapter in logic_model.chapters
            for node_id in chapter.node_ids
        ]
        while len(groups) > 15:
            merge_at = next(
                (
                    index
                    for index in range(len(groups) - 1)
                    if (
                        groups[index][0] == groups[index + 1][0]
                        and len(groups[index][1]) + len(groups[index + 1][1]) <= 3
                    )
                ),
                None,
            )
            if merge_at is None:
                raise PPTGenerationError("designing_story", "知识章节无法在 18 页内连续编排")
            chapter_id, node_ids = groups[merge_at]
            groups[merge_at] = (chapter_id, node_ids + groups[merge_at + 1][1])
            del groups[merge_at + 1]

        briefs: list[SlideBrief] = [
            SlideBrief(
                id="s00",
                kind=SlideKind.COVER,
                title=context.topic,
                teaching_goal=logic_model.thesis,
                content_focus=logic_model.central_question,
                layout=select_provisional_layout(SlideKind.COVER, None),
                density=context.preferences.density,
            ),
            SlideBrief(
                id="s00",
                kind=SlideKind.ROADMAP,
                title="学习路线",
                teaching_goal="建立从问题到应用的完整学习路径",
                content_focus=" → ".join(chapter.title for chapter in logic_model.chapters)[:180],
                layout=select_provisional_layout(SlideKind.ROADMAP, None),
                density=context.preferences.density,
            ),
        ]

        for _chapter_id, node_ids in groups:
            primary = nodes_by_id[node_ids[0]]
            kind = PPTGenerator._slide_kind_for_role(primary.role)
            focus = primary.claim
            if len(node_ids) > 1:
                focus = "；".join(nodes_by_id[node_id].claim for node_id in node_ids)
            briefs.append(
                content_brief(
                    kind=kind,
                    title=primary.title,
                    teaching_goal=primary.output,
                    content_focus=focus,
                    node_ids=node_ids,
                )
            )

        briefs.append(
            SlideBrief(
                id="s00",
                kind=SlideKind.SUMMARY,
                title="课程总结",
                teaching_goal="回收核心问题并形成后续学习行动",
                content_focus=logic_model.central_question,
                layout=select_provisional_layout(SlideKind.SUMMARY, None),
                density=context.preferences.density,
            )
        )

        numbered = [
            brief.model_copy(update={"id": f"s{index:02d}"})
            for index, brief in enumerate(briefs, start=1)
        ]
        return PPTStoryboard(
            title=context.topic,
            visual_direction="现代教学课件：以关系模型、过程演示和关键对比组织信息，图解优先且适合课堂放映。",
            slides=numbered,
        )

    @staticmethod
    def _slide_kind_for_role(role: LogicNodeRole) -> SlideKind:
        """Map a teaching role to copy semantics without choosing visuals."""

        return {
            LogicNodeRole.QUESTION: SlideKind.QUESTION,
            LogicNodeRole.PREMISE: SlideKind.EXPLANATION,
            LogicNodeRole.CONCEPT: SlideKind.CONCEPT,
            LogicNodeRole.MECHANISM: SlideKind.PROCESS,
            LogicNodeRole.METHOD: SlideKind.EXPLANATION,
            LogicNodeRole.EVIDENCE: SlideKind.EXPLANATION,
            LogicNodeRole.CASE: SlideKind.COMPARISON,
            LogicNodeRole.CONCLUSION: SlideKind.CORRECTION,
        }[role]

    def _compose_deck(
        self,
        context: PPTGenerationContext,
        logic_model: DeckLogicModel,
        storyboard: PPTStoryboard,
        visuals: dict[str, VisualModel],
    ) -> PPTDeck:
        def compose(brief: SlideBrief) -> PPTSlide:
            visual = visuals.get(brief.id)
            layout = brief.layout
            if visual is not None:
                if brief.logic_relation is None:
                    raise PPTGenerationError(
                        "composing_slides",
                        f"内容页 {brief.id} 缺少教学关系",
                    )
                layout = select_layout(
                    brief.kind,
                    VisualFamily(visual.kind),
                    brief.logic_relation,
                )
            lead, points, notes = self._compose_copy(brief, logic_model, context)
            return PPTSlide(
                id=brief.id,
                kind=brief.kind,
                title=brief.title,
                chapter_id=brief.chapter_id,
                logic_node_ids=brief.logic_node_ids,
                question=brief.question,
                claim=brief.claim,
                bridge=brief.bridge,
                logic_relation=brief.logic_relation,
                layout=layout,
                density=brief.density,
                visual=visual,
                lead=lead,
                points=points,
                speaker_notes=notes,
            )

        ordered_slides = [compose(brief) for brief in storyboard.slides]

        return PPTDeck(
            title=storyboard.title,
            language=storyboard.language,
            visual_direction=storyboard.visual_direction,
            logic_model=logic_model,
            slides=ordered_slides,
        )

    @classmethod
    def _compose_copy(
        cls,
        brief: SlideBrief,
        logic_model: DeckLogicModel,
        context: PPTGenerationContext,
    ) -> tuple[str, list[SlidePoint], str]:
        """Compile renderer-safe copy from the same semantic brief as the visual.

        Copy is not a second model-generation problem. Keeping this projection
        local makes the text, diagram, speaker notes, and page identity agree
        by construction, while the model constraints remain the final layout
        guardrail.
        """

        if brief.kind is SlideKind.COVER:
            return (
                cls._text(logic_model.thesis),
                [cls._point("学习目标", context.learning_goal)],
                f"本课围绕{context.topic}展开，先建立问题框架，再进入机制与应用。",
            )
        if brief.kind is SlideKind.ROADMAP:
            points = [
                cls._point(chapter.title, chapter.question)
                for chapter in logic_model.chapters
            ]
            return (
                "从核心问题出发，依次完成基础认知、机制理解与应用迁移。",
                points,
                "先展示完整路线，帮助学习者建立每一部分之间的前后关系。",
            )
        if brief.kind is SlideKind.SUMMARY:
            points = [
                cls._point(chapter.title, chapter.outcome)
                for chapter in logic_model.chapters
            ]
            return (
                cls._text(logic_model.thesis),
                points,
                "回到开场问题，要求学习者用自己的话串起结论与应用条件。",
            )
        nodes_by_id = {node.id: node for node in logic_model.nodes}
        source_nodes = [nodes_by_id[node_id] for node_id in brief.logic_node_ids]
        supporting_facts = list(
            dict.fromkeys(
                evidence
                for node in source_nodes
                for evidence in node.evidence
                if evidence != brief.claim
            )
        )
        return (
            cls._text(brief.claim),
            [
                cls._point(cls._point_label(index), fact)
                for index, fact in enumerate(supporting_facts[:3], start=1)
            ],
            cls._text("；".join((brief.claim, *supporting_facts[:2]))),
        )

    @classmethod
    def _point(cls, label: str, detail: str) -> SlidePoint:
        return SlidePoint(
            label=cls._text(label),
            detail=cls._text(detail),
        )

    @staticmethod
    def _point_label(index: int) -> str:
        return ("补充事实", "应用提示", "关联线索")[min(index - 1, 2)]

    @staticmethod
    def _validate_storyboard_logic(
        storyboard: PPTStoryboard,
        logic_model: DeckLogicModel,
    ) -> None:
        if len(storyboard.slides) < 2 or storyboard.slides[1].kind.value != "roadmap":
            raise PPTGenerationError("designing_story", "第 2 页必须是全局逻辑路线页")

        known_chapters = {chapter.id for chapter in logic_model.chapters}
        known_nodes = {node.id for node in logic_model.nodes}
        covered_nodes: set[str] = set()
        completed_chapters: set[str] = set()
        active_chapter: str | None = None
        for brief in storyboard.slides:
            if brief.chapter_id is not None:
                if brief.chapter_id not in known_chapters:
                    raise PPTGenerationError(
                        "designing_story", f"页面 {brief.id} 引用了未知章节 {brief.chapter_id}"
                    )
                if brief.chapter_id != active_chapter:
                    if brief.chapter_id in completed_chapters:
                        raise PPTGenerationError("designing_story", "同一章节的页面必须连续")
                    if active_chapter is not None:
                        completed_chapters.add(active_chapter)
                    active_chapter = brief.chapter_id
            unknown_nodes = set(brief.logic_node_ids) - known_nodes
            if unknown_nodes:
                raise PPTGenerationError(
                    "designing_story", f"页面 {brief.id} 引用了未知逻辑节点 {sorted(unknown_nodes)}"
                )
            if brief.kind.value not in {"cover", "roadmap", "summary"}:
                covered_nodes.update(brief.logic_node_ids)
        missing_nodes = known_nodes - covered_nodes
        if missing_nodes:
            raise PPTGenerationError(
                "designing_story", f"故事板未覆盖逻辑节点 {sorted(missing_nodes)}"
            )

    @staticmethod
    async def _progress(callback: ProgressCallback | None, message: str, percent: int) -> None:
        if callback is not None:
            await callback(message, percent)
