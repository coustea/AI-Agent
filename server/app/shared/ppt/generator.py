from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from app.infra.llm import get_llm
from app.infra.prompts import prompts
from app.shared.ppt.contract import (
    layout_guidance,
    layout_kind_values,
    logic_layout_guidance,
    logic_node_role_values,
    logic_relation_values,
    slide_kind_values,
    visual_component_guidance,
    visual_kind_values,
)
from app.shared.ppt.html import PPTHTMLPublisher, PPTHTMLRenderer, PPTPublication
from app.shared.ppt.models import (
    DeckLogicModel,
    PPTArtifact,
    PPTDeck,
    PPTGenerationContext,
    PPTPreferences,
    PPTSection,
    PPTStoryboard,
    PathPPT,
    ResourcePPT,
    SlideBrief,
)


ProgressCallback = Callable[[str, int], Awaitable[None]]
_LOGIC_MODEL_MAX_TOKENS = 3_400
_STORYBOARD_MAX_TOKENS = 3_800
_SECTION_MAX_TOKENS = 3_800
_PRESENTATION_TIMEZONE = ZoneInfo("Asia/Shanghai")
_SECTION_COUNT = 3
_MAX_SOURCE_MATERIALS = 10
_MAX_SOURCE_MATERIAL_CHARS = 2_400
_MAX_SOURCE_CONTEXT_CHARS = 12_000


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
                topic=cls._clip(request.learning_need, 160),
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
            topic=cls._clip(request.node_title, 160),
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
    """逻辑建模 + 故事板映射 + 分段视觉编排 + 确定性渲染。"""

    def __init__(self, *, llm: Any | None = None, renderer: PPTHTMLRenderer | None = None) -> None:
        self._llm = llm or get_llm()
        self._renderer = renderer or PPTHTMLRenderer()

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
            await self._progress(progress, "教学总监正在将逻辑模型映射为故事板…", 34)
            storyboard = await self._generate_storyboard(context, logic_model)
            self._validate_storyboard_logic(storyboard, logic_model)

            stage = "composing_sections"
            await self._progress(progress, "三个视觉编排智能体正在按全局逻辑完成页面…", 48)
            deck = await self._compose_deck(context, logic_model, storyboard, progress)

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
        prompt = prompts.get("ppt").render(
            "logic_model",
            context=json.dumps(context.model_dump(mode="json"), ensure_ascii=False, indent=2),
            preferences=self._render_preferences(context.preferences),
            logic_node_roles=logic_node_role_values(),
            logic_relations=logic_relation_values(),
        )
        return await self._llm.ainvoke_json(
            DeckLogicModel, prompt, temperature=0.12, max_tokens=_LOGIC_MODEL_MAX_TOKENS
        )

    async def _generate_storyboard(
        self,
        context: PPTGenerationContext,
        logic_model: DeckLogicModel,
    ) -> PPTStoryboard:
        prompt = prompts.get("ppt").render(
            "storyboard",
            context=json.dumps(context.model_dump(mode="json"), ensure_ascii=False, indent=2),
            preferences=self._render_preferences(context.preferences),
            logic_model=json.dumps(logic_model.model_dump(mode="json"), ensure_ascii=False, indent=2),
            slide_kinds=slide_kind_values(),
            visual_kinds=visual_kind_values(),
            layouts=layout_kind_values(),
            layout_guidance=layout_guidance(),
            logic_layout_guidance=logic_layout_guidance(),
            visual_component_guidance=visual_component_guidance(),
        )
        return await self._llm.ainvoke_json(
            PPTStoryboard, prompt, temperature=0.18, max_tokens=_STORYBOARD_MAX_TOKENS
        )

    async def _compose_deck(
        self,
        context: PPTGenerationContext,
        logic_model: DeckLogicModel,
        storyboard: PPTStoryboard,
        progress: ProgressCallback | None,
    ) -> PPTDeck:
        chunks = self._split_briefs(storyboard.slides)

        outline = [
            {
                "id": brief.id,
                "chapter_id": brief.chapter_id,
                "logic_node_ids": brief.logic_node_ids,
                "question": brief.question,
                "claim": brief.claim,
                "bridge": brief.bridge,
            }
            for brief in storyboard.slides
        ]
        index_by_id = {brief.id: index for index, brief in enumerate(storyboard.slides)}

        async def compose(index: int, briefs: list[SlideBrief]) -> PPTSection:
            await self._progress(progress, f"第 {index + 1}/{len(chunks)} 组页面正在视觉编排…", 52 + index * 8)
            first_index = index_by_id[briefs[0].id]
            last_index = index_by_id[briefs[-1].id]
            neighbors = {
                "previous": storyboard.slides[first_index - 1].model_dump(mode="json") if first_index else None,
                "next": storyboard.slides[last_index + 1].model_dump(mode="json")
                if last_index + 1 < len(storyboard.slides)
                else None,
            }
            prompt = prompts.get("ppt").render(
                "section_compose",
                context=json.dumps(context.model_dump(mode="json"), ensure_ascii=False, indent=2),
                visual_direction=storyboard.visual_direction,
                logic_model=json.dumps(logic_model.model_dump(mode="json"), ensure_ascii=False, indent=2),
                storyboard_outline=json.dumps(outline, ensure_ascii=False, indent=2),
                neighbor_context=json.dumps(neighbors, ensure_ascii=False, indent=2),
                section=json.dumps([brief.model_dump(mode="json") for brief in briefs], ensure_ascii=False, indent=2),
                preferences=self._render_preferences(context.preferences),
                layout_guidance=layout_guidance(),
                visual_component_guidance=visual_component_guidance(),
            )
            return await self._llm.ainvoke_json(
                PPTSection, prompt, temperature=0.22, max_tokens=_SECTION_MAX_TOKENS
            )

        sections = await asyncio.gather(*(compose(index, chunk) for index, chunk in enumerate(chunks)))
        expected_ids = [brief.id for brief in storyboard.slides]
        actual_ids = [slide.id for section in sections for slide in section.slides]
        duplicate_ids = sorted({slide_id for slide_id in actual_ids if actual_ids.count(slide_id) > 1})
        missing_ids = sorted(set(expected_ids) - set(actual_ids))
        unexpected_ids = sorted(set(actual_ids) - set(expected_ids))
        if duplicate_ids or missing_ids or unexpected_ids:
            raise PPTGenerationError(
                "composing_sections",
                "分段编排结果与故事板不一致: "
                f"missing={missing_ids} unexpected={unexpected_ids} duplicate={duplicate_ids}",
            )
        slides_by_id = {slide.id: slide for section in sections for slide in section.slides}
        ordered_slides = [slides_by_id[brief_id] for brief_id in expected_ids]
        for brief, slide in zip(storyboard.slides, ordered_slides, strict=True):
            self._validate_composed_slide(brief, slide)
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
    def _validate_composed_slide(brief: SlideBrief, slide: Any) -> None:
        expected = {
            "kind": brief.kind,
            "title": brief.title,
            "chapter_id": brief.chapter_id,
            "logic_node_ids": brief.logic_node_ids,
            "question": brief.question,
            "claim": brief.claim,
            "bridge": brief.bridge,
            "logic_relation": brief.logic_relation,
            "layout": brief.layout,
            "visual_kind": brief.visual_kind,
        }
        actual = {
            "kind": slide.kind,
            "title": slide.title,
            "chapter_id": slide.chapter_id,
            "logic_node_ids": slide.logic_node_ids,
            "question": slide.question,
            "claim": slide.claim,
            "bridge": slide.bridge,
            "logic_relation": slide.logic_relation,
            "layout": slide.layout,
            "visual_kind": slide.visual.kind,
        }
        changed = [name for name, value in expected.items() if actual[name] != value]
        if changed:
            raise PPTGenerationError(
                "composing_sections",
                f"页面 {brief.id} 修改了受保护字段: {changed}",
            )

    @staticmethod
    def _split_briefs(briefs: list[SlideBrief]) -> list[list[SlideBrief]]:
        size = max(1, -(-len(briefs) // _SECTION_COUNT))
        return [briefs[start : start + size] for start in range(0, len(briefs), size)]

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
    async def _progress(callback: ProgressCallback | None, message: str, percent: int) -> None:
        if callback is not None:
            await callback(message, percent)
