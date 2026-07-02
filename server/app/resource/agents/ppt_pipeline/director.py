from __future__ import annotations

import json

from app.infra.llm import get_llm
from app.infra.prompts import prompts
from app.resource.agents.ppt_pipeline.assets import load_frontend_slides_assets
from app.resource.agents.ppt_pipeline.schemas import (
    DeckBrief,
    SourcePack,
    StyleDecision,
)


class StyleDirector:
    def __init__(self, llm=None):
        self.llm = llm or get_llm()

    async def direct(
        self,
        *,
        brief: DeckBrief,
        source_pack: SourcePack,
    ) -> StyleDecision:
        assets = load_frontend_slides_assets()
        prompt = prompts.get("resource").render(
            "ppt_style",
            brief=brief.model_dump_json(indent=2),
            source_pack=source_pack.model_dump_json(indent=2),
            safe_presets=json.dumps(
                assets.safe_presets, ensure_ascii=False, indent=2
            ),
            bold_templates=json.dumps(
                assets.bold_templates, ensure_ascii=False, indent=2
            ),
        )
        return await self.llm.ainvoke_json(StyleDecision, prompt)
