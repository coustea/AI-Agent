"""Create a mechanism-oriented storyboard for computer undergraduate theory videos.

Primary path:
    TheoryAnimationBrief → bridge_theory_to_brief → VideoBrief
Fallback path:
    SimpleVideoBrief → bridge_simple_to_brief → VideoBrief

The theory schema is intentionally richer than the old simplified schema: it lets
LLM describe objects, relations and operation steps, while the backend remains
responsible for deterministic visual mapping and HyperFrames compilation.
"""

from __future__ import annotations

import time
from typing import Any

from pydantic import ValidationError

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.prompts import prompts
from app.shared.cartoon.schemas import (
    CartoonVideoRequest,
    SimpleVideoBrief,
    TheoryAnimationBrief,
    VideoBrief,
    bridge_simple_to_brief,
    bridge_theory_to_brief,
)

logger = get_logger(__name__)


class VideoPlanner:
    """Plan a complete theory mechanism animation with one primary LLM call.

    The planner asks for TheoryAnimationBrief first because undergraduate
    computer theory knowledge needs operation steps: state changes, table
    transforms, address mappings, scheduling timelines and structure builds.
    A SimpleVideoBrief fallback is kept to avoid total failure when the model or
    prompt still returns the older compact schema.
    """

    def __init__(self, llm: Any = None) -> None:
        self.llm = llm or get_llm()

    async def plan(self, request: CartoonVideoRequest) -> VideoBrief:
        prompt = prompts.get("cartoon").render(
            "brief",
            request=request.model_dump_json(indent=2),
        )
        logger.info("Cartoon 理论机制分镜 LLM 调用: input_len=%d", len(prompt))
        started = time.perf_counter()

        try:
            theory_brief = await self.llm.ainvoke_json(TheoryAnimationBrief, prompt)
            brief = bridge_theory_to_brief(theory_brief)
            mode = f"theory:{theory_brief.animation_type}"
        except (ValidationError, ValueError, TypeError) as theory_exc:
            logger.warning(
                "TheoryAnimationBrief 生成/校验失败，回退 SimpleVideoBrief: %s",
                theory_exc,
            )
            simple_brief = await self.llm.ainvoke_json(SimpleVideoBrief, prompt)
            brief = bridge_simple_to_brief(simple_brief)
            mode = "simple-fallback"

        elapsed = int((time.perf_counter() - started) * 1000)
        logger.info(
            "Cartoon 分镜 LLM 完成: mode=%s scenes=%d subject=%s elapsed_ms=%d",
            mode,
            len(brief.scenes),
            brief.subject,
            elapsed,
        )
        return brief