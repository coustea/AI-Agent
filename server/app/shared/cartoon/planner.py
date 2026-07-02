"""Scene planner — designs the narrative arc and scene timeline."""

from __future__ import annotations

from app.infra.llm import get_llm
from app.infra.prompts import prompts
from app.shared.cartoon.schemas import VideoBrief, CartoonVideoRequest


class VideoPlanner:
    def __init__(self, llm=None):
        self.llm = llm or get_llm()

    async def plan(self, request: CartoonVideoRequest) -> VideoBrief:
        prompt = prompts.get("cartoon").render(
            "brief",
            request=request.model_dump_json(indent=2),
        )
        return await self.llm.ainvoke_json(VideoBrief, prompt)
