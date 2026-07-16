from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from app.infra.llm import get_llm
from app.infra.prompts import prompts
from app.shared.ppt.contract import (
    LogicNodeRole,
    LogicRelation,
    SlideKind,
    VisualFamily,
    course_domain_values,
    logic_node_role_values,
    select_layout,
    select_provisional_layout,
)
from app.shared.ppt.html import PPTHTMLPublisher, PPTHTMLRenderer, PPTPublication
from app.shared.ppt.models import (
    DeckLogicDraft,
    DeckLogicModel,
    LogicChapter,
    LogicEdge,
    LogicNode,
    PPTArtifact,
    PPTDeck,
    PPTGenerationContext,
    PPTPreferences,
    PPTSlide,
    PPTStoryboard,
    PRESENTATION_TITLE_MAX_LENGTH,
    PathPPT,
    ResourcePPT,
    SlideBrief,
    section_draft_contract,
)
from app.shared.ppt.visual_ir import VisualModel
from app.shared.ppt.visual_planner import VisualPlanner


ProgressCallback = Callable[[str, int], Awaitable[None]]
_LOGIC_MODEL_MAX_TOKENS = 3_600
_SECTION_MAX_TOKENS = 2_400
_PRESENTATION_TIMEZONE = ZoneInfo("Asia/Shanghai")
_SECTION_COUNT = 3
_MAX_SOURCE_MATERIALS = 10
_MAX_SOURCE_MATERIAL_CHARS = 2_400
_MAX_SOURCE_CONTEXT_CHARS = 12_000
_PROMPT_VARIABLE = re.compile(r"(?<!\{)\{(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)\}(?!\})")
_PROMPT_VARIABLES: dict[str, frozenset[str]] = {
    "logic_model": frozenset(
        {"context", "preferences", "logic_node_roles", "course_domains"}
    ),
    "section_compose": frozenset(
        {
            "lesson_context",
            "preferences",
            "neighbor_context",
            "section",
        }
    ),
    "visual_plan": frozenset(
        {"storyboard", "course_profile", "visual_families"}
    ),
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
            materials = [
                json.dumps(
                    request.resource_plan,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
            ]
            materials.extend(
                f"{source.title}: {source.summary}\n" + "\n".join(source.materials[:4])
                for source in request.artifacts[:6]
            )
            return PPTGenerationContext(
                source="resource",
                topic=cls._resource_topic(request),
                learner_profile=cls._profile_text(request.profile),
                learning_goal=cls._clip(request.learning_need, 1_200),
                prerequisites=[],
                source_materials=cls._clean_materials(materials),
                constraints=[f"学习场景：{cls._clip(request.learning_scenario, 80)}"],
                preferences=request.preferences,
            )

        materials = [request.tutorial_summary, request.tutorial_core_content]
        materials.extend(request.tutorial_knowledge_points[:12])
        return PPTGenerationContext(
            source="path",
            topic=cls._clip(request.node_title, PRESENTATION_TITLE_MAX_LENGTH),
            learner_profile=cls._profile_text(request.profile),
            learning_goal=cls._clip(request.path_goal, 1_200),
            prerequisites=[cls._clip(item, 100) for item in request.knowledge_points[:12]],
            source_materials=cls._clean_materials(materials),
            constraints=[
                f"路径：{cls._clip(request.path_title, 120)}",
                f"难度：{cls._clip(request.difficulty, 40)}",
                "薄弱点：" + "、".join(cls._clip(item, 60) for item in request.weak_knowledge_points[:8]),
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
            title = cls._clip(candidate, PRESENTATION_TITLE_MAX_LENGTH)
            if title:
                return title
        raise ValueError("资源教学计划没有可用的课件主题")

    @staticmethod
    def _profile_text(profile: dict[str, Any] | str) -> str:
        value = profile if isinstance(profile, str) else json.dumps(profile, ensure_ascii=False)
        return PPTContextAdapter._clip(value, 1_600)

    @staticmethod
    def _clean_materials(values: list[str]) -> list[str]:
        """Build one bounded source packet reused by every planning call.

        The storyboard and all section composers receive the same context.  A
        per-item limit alone lets a resource request multiply into a very large
        prompt four times, which is both slow and prone to provider timeouts.
        Keep complete, ordered source units until the shared packet budget is
        exhausted instead of silently building a different context per worker.
        """
        materials: list[str] = []
        used = 0
        for value in values:
            text = " ".join(value.split())
            if not text or len(materials) >= _MAX_SOURCE_MATERIALS:
                continue
            remaining = _MAX_SOURCE_CONTEXT_CHARS - used
            if remaining <= 0:
                break
            clipped = text[: min(_MAX_SOURCE_MATERIAL_CHARS, remaining)]
            if not clipped:
                break
            materials.append(clipped)
            used += len(clipped)
        return materials or ["请基于课程主题组织完整、准确的教学讲解。"]

    @staticmethod
    def _clip(value: str, limit: int) -> str:
        return " ".join(value.split())[:limit]


class PPTGenerator:
    """逻辑建模 + 确定性教学编排 + 视觉规划 + 文案编排 + 确定性渲染。"""

    def __init__(
        self,
        *,
        llm: Any | None = None,
        renderer: PPTHTMLRenderer | None = None,
        planner: VisualPlanner | None = None,
    ) -> None:
        self._llm = llm or get_llm()
        self._renderer = renderer or PPTHTMLRenderer()
        self._planner = planner or VisualPlanner(llm=self._llm)

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
            logic_model = await self._generate_logic_model(context)

            stage = "designing_story"
            await self._progress(progress, "正在将知识链编译为教学故事板…", 34)
            storyboard = self._compile_storyboard(context, logic_model)
            self._validate_storyboard_logic(storyboard, logic_model)

            stage = "visual_planning"
            await self._progress(progress, "视觉规划智能体正在为每页选择领域模型…", 40)
            visuals = await self._planner.plan(storyboard, logic_model.course_domain)

            stage = "composing_sections"
            await self._progress(progress, "三个视觉编排智能体正在按全局逻辑完成页面…", 48)
            deck = await self._compose_deck(
                context,
                logic_model,
                storyboard,
                visuals,
                progress,
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

    async def _generate_logic_model(self, context: PPTGenerationContext) -> DeckLogicModel:
        prompt = self._render_prompt(
            "logic_model",
            context=json.dumps(context.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":")),
            preferences=self._render_preferences(context.preferences),
            logic_node_roles=logic_node_role_values(),
            course_domains=course_domain_values(),
        )
        draft = await self._llm.ainvoke_json(
            DeckLogicDraft, prompt, temperature=0.08, max_tokens=_LOGIC_MODEL_MAX_TOKENS
        )
        return self._materialize_logic_model(draft)

    @staticmethod
    def _materialize_logic_model(draft: DeckLogicDraft) -> DeckLogicModel:
        """Assign graph identity once, after the LLM has finished teaching design.

        Chapter/node IDs and cross-reference bookkeeping are backend transport
        details used by the storyboard and renderer. Generating them in the
        LLM response coupled content quality to a fragile formatting convention
        (for example ``ch1`` versus ``c01``).  The draft instead expresses a
        readable ordered lesson; this boundary creates the canonical graph.
        """

        chapters: list[LogicChapter] = []
        nodes: list[LogicNode] = []
        node_order = 1

        for chapter_order, chapter in enumerate(draft.chapters, start=1):
            chapter_id = f"c{chapter_order:02d}"
            chapter_node_ids: list[str] = []
            for node in chapter.nodes:
                node_id = f"l{node_order:02d}"
                chapter_node_ids.append(node_id)
                nodes.append(
                    LogicNode(
                        id=node_id,
                        chapter_id=chapter_id,
                        title=node.title,
                        role=node.role,
                        question=node.question,
                        claim=node.claim,
                        evidence=node.evidence,
                        output=node.output,
                    )
                )
                node_order += 1
            chapters.append(
                LogicChapter(
                    id=chapter_id,
                    title=chapter.title,
                    question=chapter.nodes[0].question,
                    outcome=chapter.nodes[-1].output,
                    node_ids=chapter_node_ids,
                )
            )

        return DeckLogicModel(
            course_domain=draft.course_domain,
            central_question=nodes[0].question,
            thesis=nodes[-1].output,
            chapters=chapters,
            nodes=nodes,
            edges=[
                LogicEdge(
                    source_id=source.id,
                    target_id=target.id,
                    relation=PPTGenerator._relation_for(target),
                    bridge=PPTGenerator._bridge_for(source, target),
                )
                for source, target in zip(nodes, nodes[1:])
            ],
        )

    @staticmethod
    def _relation_for(target: LogicNode) -> LogicRelation:
        return {
            LogicNodeRole.QUESTION: LogicRelation.PREREQUISITE,
            LogicNodeRole.PREMISE: LogicRelation.PREREQUISITE,
            LogicNodeRole.CONCEPT: LogicRelation.DECOMPOSES,
            LogicNodeRole.MECHANISM: LogicRelation.DERIVES,
            LogicNodeRole.METHOD: LogicRelation.APPLIES,
            LogicNodeRole.EVIDENCE: LogicRelation.SUPPORTS,
            LogicNodeRole.CASE: LogicRelation.VERIFIES,
            LogicNodeRole.CONCLUSION: LogicRelation.SUMMARIZES,
        }[target.role]

    @staticmethod
    def _bridge_for(source: LogicNode, target: LogicNode) -> str:
        return f"{source.output}，进一步回答：{target.question}"[:96]

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
            for edge in logic_model.edges:
                if edge.source_id in node_ids:
                    return edge
            raise PPTGenerationError("designing_story", f"知识节点 {node_ids} 缺少教学衔接")

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
            supporting = "；".join(primary.evidence[:1])
            focus = "；".join(part for part in (primary.claim, supporting) if part)
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

    async def _compose_deck(
        self,
        context: PPTGenerationContext,
        logic_model: DeckLogicModel,
        storyboard: PPTStoryboard,
        visuals: dict[str, VisualModel],
        progress: ProgressCallback | None,
    ) -> PPTDeck:
        chunks = self._split_briefs(storyboard.slides)

        index_by_id = {brief.id: index for index, brief in enumerate(storyboard.slides)}

        async def compose(index: int, briefs: list[SlideBrief]) -> list[PPTSlide]:
            await self._progress(progress, f"第 {index + 1}/{len(chunks)} 组页面正在视觉编排…", 52 + index * 8)
            first_index = index_by_id[briefs[0].id]
            last_index = index_by_id[briefs[-1].id]
            neighbors = self._neighbor_context(
                storyboard,
                first_index=first_index,
                last_index=last_index,
            )
            prompt = self._render_prompt(
                "section_compose",
                lesson_context=json.dumps(
                    {
                        "topic": context.topic,
                        "learning_goal": context.learning_goal,
                        "constraints": context.constraints,
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                neighbor_context=json.dumps(neighbors, ensure_ascii=False, separators=(",", ":")),
                section=json.dumps(
                    [self._section_brief_payload(brief) for brief in briefs],
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                preferences=self._render_preferences(context.preferences),
            )
            section_schema = section_draft_contract(briefs)
            draft = await self._llm.ainvoke_json(
                section_schema, prompt, temperature=0.12, max_tokens=_SECTION_MAX_TOKENS
            )
            if len(draft.slides) != len(briefs):
                raise PPTGenerationError(
                    "composing_sections",
                    f"第 {index + 1} 组视觉内容数量错误: expected={len(briefs)} actual={len(draft.slides)}",
                )
            slides: list[PPTSlide] = []
            for brief, content in zip(briefs, draft.slides, strict=True):
                visual = visuals.get(brief.id)
                layout = brief.layout
                if visual is not None:
                    if brief.logic_relation is None:
                        raise PPTGenerationError(
                            "composing_sections",
                            f"内容页 {brief.id} 缺少教学关系",
                        )
                    layout = select_layout(
                        brief.kind,
                        VisualFamily(visual.kind),
                        brief.logic_relation,
                    )
                slides.append(
                    PPTSlide(
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
                        **content.model_dump(mode="python"),
                    )
                )
            return slides

        sections = await asyncio.gather(*(compose(index, chunk) for index, chunk in enumerate(chunks)))
        expected_ids = [brief.id for brief in storyboard.slides]
        actual_ids = [slide.id for section in sections for slide in section]
        duplicate_ids = sorted({slide_id for slide_id in actual_ids if actual_ids.count(slide_id) > 1})
        missing_ids = sorted(set(expected_ids) - set(actual_ids))
        unexpected_ids = sorted(set(actual_ids) - set(expected_ids))
        if duplicate_ids or missing_ids or unexpected_ids:
            raise PPTGenerationError(
                "composing_sections",
                "分段编排结果与故事板不一致: "
                f"missing={missing_ids} unexpected={unexpected_ids} duplicate={duplicate_ids}",
            )
        slides_by_id = {slide.id: slide for section in sections for slide in section}
        ordered_slides = [slides_by_id[brief_id] for brief_id in expected_ids]

        return PPTDeck(
            title=storyboard.title,
            language=storyboard.language,
            visual_direction=storyboard.visual_direction,
            logic_model=logic_model,
            slides=ordered_slides,
        )

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
    def _split_briefs(briefs: list[SlideBrief]) -> list[list[SlideBrief]]:
        size = max(1, -(-len(briefs) // _SECTION_COUNT))
        return [briefs[start : start + size] for start in range(0, len(briefs), size)]

    @staticmethod
    def _section_brief_payload(brief: SlideBrief) -> dict[str, object]:
        """Expose only the semantic facts a section composer can actually use."""

        payload: dict[str, object] = {
            "title": brief.title,
            "teaching_goal": brief.teaching_goal,
            "content_focus": brief.content_focus,
            "question": brief.question,
            "claim": brief.claim,
            "bridge": brief.bridge,
            "output_fields": ["lead", "points", "speaker_notes"],
        }
        return payload

    @staticmethod
    def _neighbor_context(
        storyboard: PPTStoryboard,
        *,
        first_index: int,
        last_index: int,
    ) -> dict[str, dict[str, str] | None]:
        def compact(brief: SlideBrief | None) -> dict[str, str] | None:
            if brief is None:
                return None
            return {"title": brief.title, "claim": brief.claim, "bridge": brief.bridge}

        return {
            "previous": compact(storyboard.slides[first_index - 1] if first_index else None),
            "next": compact(
                storyboard.slides[last_index + 1]
                if last_index + 1 < len(storyboard.slides)
                else None
            ),
        }

    @staticmethod
    def _render_preferences(preferences: PPTPreferences) -> str:
        narrative = {
            "concept": "从概念、边界到机制与应用递进。",
            "case_driven": "从场景或案例切入，抽象出概念与判断方法。",
            "problem_led": "从核心问题出发，逐步建立解决问题的知识结构。",
            "review": "围绕复习、薄弱点和易错判断组织讲解。",
        }[preferences.narrative_style]
        density = {
            "concise": "每页 2～3 个信息单元，留出视觉呼吸。",
            "standard": "每页 3～4 个信息单元，内容与图解均衡。",
            "detailed": "每页最多 5 个信息单元，不能缩小字号或堆砌。",
        }[preferences.density]
        emphasis = "、".join(preferences.emphasis)
        return f"叙事：{narrative}\n密度：{density}\n强调：{emphasis}"

    @staticmethod
    def _render_prompt(name: str, **values: object) -> str:
        """Render a checked prompt rather than silently preserving a typo.

        Presentation prompt files are executable contracts with the compiler.
        The generic registry deliberately supports permissive legacy modules;
        this generator does not.  Its prompt assets must declare exactly
        the values supplied by their producing stage, otherwise generation
        stops before an invalid request reaches the LLM.
        """

        expected = _PROMPT_VARIABLES[name]
        document = prompts.get("ppt").get(name)
        declared = frozenset(match.group("name") for match in _PROMPT_VARIABLE.finditer(document))
        provided = frozenset(values)
        if declared != expected or provided != expected:
            raise PPTGenerationError(
                "loading_prompts",
                f"提示词 {name}.md 变量契约不一致: "
                f"declared={sorted(declared)} expected={sorted(expected)} provided={sorted(provided)}",
            )
        return prompts.get("ppt").render(name, **values)

    @staticmethod
    async def _progress(callback: ProgressCallback | None, message: str, percent: int) -> None:
        if callback is not None:
            await callback(message, percent)
