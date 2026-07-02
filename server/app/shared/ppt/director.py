from __future__ import annotations

import json

from app.infra.llm import get_llm
from app.infra.prompts import prompts
from app.shared.ppt.assets import load_frontend_slides_assets
from app.shared.ppt.schemas import (
    DeckBrief,
    ResourcePPTRequest,
    PathPPTRequest,
    StyleDecision,
)


class StyleDirector:
    def __init__(self, llm=None):
        self.llm = llm or get_llm()

    async def direct(
        self,
        *,
        brief: DeckBrief,
        request: ResourcePPTRequest | PathPPTRequest,
        prompt_prefix: str,
    ) -> StyleDecision:
        assets = load_frontend_slides_assets()
        prompt = prompts.get("ppt").render(
            f"{prompt_prefix}_style",
            brief=brief.model_dump_json(indent=2),
            request=request.model_dump_json(indent=2),
            safe_presets=json.dumps(
                assets.safe_presets, ensure_ascii=False, indent=2
            ),
            bold_templates=json.dumps(
                assets.bold_templates, ensure_ascii=False, indent=2
            ),
        )
        return await self.llm.ainvoke_json(StyleDecision, prompt)
