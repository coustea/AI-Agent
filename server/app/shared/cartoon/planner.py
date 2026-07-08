"""Create one structured storyboard for the complete teaching video.

使用简化 schema (SimpleVideoBrief) 让 LLM 输出，然后通过确定性桥接层
(bridge_simple_to_brief) 映射为完整 VideoBrief。
枚举组合从 22,984 降到 108，大幅降低 LLM 枚举选择错误率。
"""

from __future__ import annotations

import time
from typing import Any

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.prompts import prompts
from app.shared.cartoon.schemas import (
    CartoonVideoRequest,
    SimpleVideoBrief,
    VideoBrief,
    bridge_simple_to_brief,
)

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
        logger.info("Cartoon 分镜 LLM 调用 (simplified schema): input_len=%d", len(prompt))
        started = time.perf_counter()

        # LLM 输出简化 schema，枚举组合仅 108 种
        simple_brief = await self.llm.ainvoke_json(SimpleVideoBrief, prompt)

        # 确定性桥接：简化 → 完整，零 LLM 参与
        brief = bridge_simple_to_brief(simple_brief)

        elapsed = int((time.perf_counter() - started) * 1000)
        logger.info(
            "Cartoon 分镜 LLM 完成: scenes=%d subject=%s elapsed_ms=%d",
            len(brief.scenes), brief.subject, elapsed,
        )
        return brief
