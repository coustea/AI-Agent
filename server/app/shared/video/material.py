"""Source-neutral teaching material extraction for video production."""

from __future__ import annotations

import json
from pathlib import Path

from app.infra.llm import get_llm
from app.shared.video.schemas import VideoMaterialDigest, VideoRequest

_PROMPT_PATH = Path(__file__).parent / "prompts" / "material.md"


class VideoMaterialAgent:
    def __init__(self, llm=None) -> None:
        self.llm = llm or get_llm()

    async def extract(self, request: VideoRequest) -> VideoMaterialDigest:
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
        return await self.llm.ainvoke_json(VideoMaterialDigest, prompt)
