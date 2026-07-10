"""Source-neutral teaching material extraction for video production."""

from __future__ import annotations

import json
import time
from pathlib import Path

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.shared.video.schemas import VideoMaterialDigest, VideoRequest

logger = get_logger(__name__)

_PROMPT_PATH = Path(__file__).parent / "prompts" / "material.md"


# 素材 Agent：从教学内容中抽取与来源无关的教学素材
class VideoMaterialAgent:
    def __init__(self, llm=None) -> None:
        self.llm = llm or get_llm()

    # 提取：格式化素材提示词模板并调用 LLM 生成素材摘要
    async def extract(self, request: VideoRequest) -> VideoMaterialDigest:
        # 读取并格式化素材提取提示词模板
        prompt = _PROMPT_PATH.read_text(encoding="utf-8").format(
            topic=request.topic,
            audience=request.audience,
            learning_goal=request.learning_goal,
            materials=json.dumps(
                [material.model_dump(mode="json") for material in request.materials],
                ensure_ascii=False,
                indent=2,
            ),
        )
        logger.info("Video 素材 LLM 调用: topic=%s input_len=%d", request.topic[:50], len(prompt))
        started = time.perf_counter()
        # 调用 LLM 生成结构化教学素材摘要
        digest = await self.llm.ainvoke_json(VideoMaterialDigest, prompt)
        elapsed = int((time.perf_counter() - started) * 1000)
        logger.info(
            "Video 素材 LLM 完成: core_concepts=%d facts=%d elapsed_ms=%d",
            len(digest.core_concepts), len(digest.facts), elapsed,
        )
        return digest
