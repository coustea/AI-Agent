"""Strict LLM boundary for assigning renderer-neutral visuals to content slides."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.infra.llm import get_llm
from app.infra.prompts import prompts
from app.shared.ppt.contract import (
    CourseDomain,
    SlideKind,
    visual_family_values,
)
from app.shared.ppt.models import PPTStoryboard
from app.shared.ppt.profiles import course_profile
from app.shared.ppt.visual_ir import VisualModel


_VISUAL_PLAN_MAX_TOKENS = 4_800
_META_KINDS = {SlideKind.COVER, SlideKind.ROADMAP, SlideKind.SUMMARY}


class VisualPlanModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class VisualPlanSlide(VisualPlanModel):
    slide_id: str = Field(pattern=r"^s[0-9]{2}$")
    visual: VisualModel


class VisualPlanDraft(VisualPlanModel):
    slides: list[VisualPlanSlide] = Field(min_length=1, max_length=15)

    @model_validator(mode="after")
    def validate_unique_slide_ids(self) -> "VisualPlanDraft":
        slide_ids = [slide.slide_id for slide in self.slides]
        if len(slide_ids) != len(set(slide_ids)):
            raise ValueError("visual plan slide ids must be unique")
        return self


class VisualPlanner:
    """Plan exactly one Visual IR payload for every non-meta storyboard slide."""

    def __init__(self, *, llm: Any | None = None) -> None:
        self._llm = llm or get_llm()

    async def plan(
        self,
        storyboard: PPTStoryboard,
        domain: CourseDomain,
    ) -> dict[str, VisualModel]:
        from app.shared.ppt.generator import PPTGenerationError

        content_slides = [
            slide for slide in storyboard.slides if slide.kind not in _META_KINDS
        ]
        expected_ids = [slide.id for slide in content_slides]
        profile = course_profile(domain)
        profile_payload = {
            "course_domain": domain.value,
            "name": profile.name_zh,
            "planning_guidance": profile.planning_guidance,
            "preferred_families": [
                family.value for family in profile.preferred_families
            ],
            "representative_models": list(profile.representative_models),
        }
        storyboard_payload = [
            {
                "slide_id": slide.id,
                "kind": slide.kind.value,
                "title": slide.title,
                "teaching_goal": slide.teaching_goal,
                "content_focus": slide.content_focus,
                "question": slide.question,
                "claim": slide.claim,
                "bridge": slide.bridge,
                "logic_relation": (
                    slide.logic_relation.value if slide.logic_relation else None
                ),
            }
            for slide in content_slides
        ]

        try:
            prompt = prompts.get("ppt").render(
                "visual_plan",
                storyboard=json.dumps(
                    storyboard_payload,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                course_profile=json.dumps(
                    profile_payload,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                visual_families=visual_family_values(),
            )
            draft = await self._llm.ainvoke_json(
                VisualPlanDraft,
                prompt,
                temperature=0.08,
                max_tokens=_VISUAL_PLAN_MAX_TOKENS,
            )
        except PPTGenerationError:
            raise
        except Exception as exc:
            raise PPTGenerationError("visual_planning", str(exc)) from exc

        actual_ids = [slide.slide_id for slide in draft.slides]
        expected = set(expected_ids)
        actual = set(actual_ids)
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        duplicates = sorted(
            slide_id for slide_id in actual if actual_ids.count(slide_id) > 1
        )
        if missing or unexpected or duplicates or len(actual_ids) != len(expected_ids):
            raise PPTGenerationError(
                "visual_planning",
                "视觉计划与内容页不一致: "
                f"missing={missing} unexpected={unexpected} duplicate={duplicates}",
            )
        return {slide.slide_id: slide.visual for slide in draft.slides}

