"""Create one structured storyboard for the complete teaching video."""

from __future__ import annotations

from typing import Any

from app.infra.llm import get_llm
from app.infra.prompts import prompts
from app.shared.cartoon.schemas import CartoonVideoRequest, VideoBrief


class VideoPlanner:
    """Use one model call to produce narration and semantic visual instructions."""

    def __init__(self, llm: Any = None) -> None:
        self.llm = llm or get_llm()

    async def plan(self, request: CartoonVideoRequest) -> VideoBrief:
        prompt = prompts.get("cartoon").render(
            "brief",
            request=request.model_dump_json(indent=2),
        )
        return await self.llm.ainvoke_json(VideoBrief, prompt)
