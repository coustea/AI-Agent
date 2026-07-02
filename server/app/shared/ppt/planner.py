from __future__ import annotations

from app.infra.llm import get_llm
from app.infra.prompts import prompts
from app.shared.ppt.schemas import DeckBrief, ResourcePPTRequest, PathPPTRequest


class BriefPlanner:
    def __init__(self, llm=None):
        self.llm = llm or get_llm()

    async def plan(
        self,
        request: ResourcePPTRequest | PathPPTRequest,
        prompt_prefix: str,
    ) -> DeckBrief:
        prompt = prompts.get("ppt").render(
            f"{prompt_prefix}_brief",
            request=request.model_dump_json(indent=2),
        )
        return await self.llm.ainvoke_json(DeckBrief, prompt)
