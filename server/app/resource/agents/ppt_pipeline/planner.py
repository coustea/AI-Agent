from __future__ import annotations

from app.infra.llm import get_llm
from app.infra.prompts import prompts
from app.resource.agents.ppt_pipeline.schemas import DeckBrief, SourcePack


class BriefPlanner:
    def __init__(self, llm=None):
        self.llm = llm or get_llm()

    async def plan(self, source_pack: SourcePack) -> DeckBrief:
        prompt = prompts.get("resource").render(
            "ppt_brief",
            source_pack=source_pack.model_dump_json(indent=2),
        )
        return await self.llm.ainvoke_json(DeckBrief, prompt)
