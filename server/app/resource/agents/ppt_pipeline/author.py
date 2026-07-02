from __future__ import annotations

import re

from app.infra.llm import get_llm
from app.infra.prompts import prompts
from app.resource.agents.ppt_pipeline.assets import load_frontend_slides_assets
from app.resource.agents.ppt_pipeline.schemas import (
    DeckBrief,
    SourcePack,
    StyleDecision,
)


_HTML_FENCE = re.compile(
    r"\A\s*```(?:html)?\s*(?P<html>.*?)\s*```\s*\Z",
    flags=re.DOTALL | re.IGNORECASE,
)


def html_output_token_budget(slide_count: int) -> int:
    return min(24_576, max(8_192, 2_048 + slide_count * 2_048))


def strip_outer_html_fence(content: str) -> str:
    match = _HTML_FENCE.fullmatch(content)
    return (match.group("html") if match else content).strip()


class HTMLAuthor:
    def __init__(self, llm=None):
        self.llm = llm or get_llm()

    async def author(
        self,
        *,
        source_pack: SourcePack,
        brief: DeckBrief,
        style: StyleDecision,
    ) -> str:
        assets = load_frontend_slides_assets()
        prompt = prompts.get("resource").render(
            "ppt_html",
            source_pack=source_pack.model_dump_json(indent=2),
            brief=brief.model_dump_json(indent=2),
            style=style.selected.model_dump_json(indent=2),
            viewport_css=assets.viewport_css,
            html_contract=assets.html_contract,
            animation_guide=assets.animation_guide,
        )
        response = await self.llm.ainvoke(
            prompt,
            max_tokens=html_output_token_budget(brief.target_slide_count),
        )
        content = response if isinstance(response, str) else response.content
        return strip_outer_html_fence(str(content or ""))
