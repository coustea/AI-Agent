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
    slide_kind_values,
    visual_component_guidance,
    visual_kind_values,
)
from app.shared.ppt.html import PPTHTMLPublisher, PPTHTMLRenderer, PPTPublication
from app.shared.ppt.models import (
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
_STORYBOARD_MAX_TOKENS = 2_800
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
    """一次故事板设计 + 三段并行视觉编排 + 确定性 HTML/SVG 渲染。"""

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

            stage = "designing_story"
            await self._progress(progress, "教学总监正在设计整套叙事与视觉方向…", 24)
            storyboard = await self._generate_storyboard(context)

            stage = "composing_sections"
            await self._progress(progress, "三个视觉编排智能体正在并行完成页面…", 46)
            deck = await self._compose_deck(context, storyboard, progress)

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

    async def _generate_storyboard(self, context: PPTGenerationContext) -> PPTStoryboard:
        prompt = prompts.get("ppt").render(
            "storyboard",
            context=json.dumps(context.model_dump(mode="json"), ensure_ascii=False, indent=2),
            preferences=self._render_preferences(context.preferences),
            slide_kinds=slide_kind_values(),
            visual_kinds=visual_kind_values(),
            layouts=layout_kind_values(),
            layout_guidance=layout_guidance(),
            visual_component_guidance=visual_component_guidance(),
        )
        return await self._llm.ainvoke_json(
            PPTStoryboard, prompt, temperature=0.18, max_tokens=_STORYBOARD_MAX_TOKENS
        )

    async def _compose_deck(
        self,
        context: PPTGenerationContext,
        storyboard: PPTStoryboard,
        progress: ProgressCallback | None,
    ) -> PPTDeck:
        chunks = self._split_briefs(storyboard.slides)

        async def compose(index: int, briefs: list[SlideBrief]) -> PPTSection:
            await self._progress(progress, f"第 {index + 1}/{len(chunks)} 组页面正在视觉编排…", 52 + index * 8)
            prompt = prompts.get("ppt").render(
                "section_compose",
                context=json.dumps(context.model_dump(mode="json"), ensure_ascii=False, indent=2),
                visual_direction=storyboard.visual_direction,
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
        return PPTDeck(
            title=storyboard.title,
            language=storyboard.language,
            visual_direction=storyboard.visual_direction,
            slides=ordered_slides,
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
