"""Create one structured storyboard for the complete teaching video."""

from __future__ import annotations

import time
from typing import Any

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.prompts import prompts
from app.shared.cartoon.schemas import CartoonVideoRequest, VideoBrief

logger = get_logger(__name__)


class VideoPlanner:
    """Use one model call to produce narration and semantic visual instructions."""

    def __init__(self, llm: Any = None) -> None:
        self.llm = llm or get_llm()

    async def plan(self, request: CartoonVideoRequest) -> VideoBrief:
        prompt = prompts.get("cartoon").render(
            "brief",
            request=request.model_dump_json(indent=2),
        )
        logger.info("Cartoon 分镜 LLM 调用: input_len=%d", len(prompt))
        started = time.perf_counter()
        brief = await self.llm.ainvoke_json(VideoBrief, prompt)
        elapsed = int((time.perf_counter() - started) * 1000)
        logger.info(
            "Cartoon 分镜 LLM 完成: scenes=%d subject=%s elapsed_ms=%d",
            len(brief.scenes), brief.subject, elapsed,
        )
        return brief
