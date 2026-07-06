"""Typed scene writing with narration-backed visual beats."""

from __future__ import annotations

import json
from pathlib import Path

from app.infra.llm import get_llm
from app.shared.video.schemas import (
    SceneContract,
    SceneDraft,
    VideoMaterialDigest,
    VideoRequest,
    VideoStyleDecision,
)
from app.shared.video.visual_contracts import get_visual_contract

_PROMPT_PATH = Path(__file__).parent / "prompts" / "scene.md"


class SceneWriterAgent:
    def __init__(self, llm=None) -> None:
        self.llm = llm or get_llm()

    async def write(
        self,
        *,
        request: VideoRequest,
        digest: VideoMaterialDigest,
        contract: SceneContract,
        style: VideoStyleDecision,
    ) -> SceneDraft:
        prompt = _PROMPT_PATH.read_text(encoding="utf-8").format(
            request=request.model_dump_json(indent=2),
            digest=digest.model_dump_json(indent=2),
            contract=contract.model_dump_json(indent=2),
            style=style.model_dump_json(indent=2),
            visual_contract=json.dumps(
                {
                    "visual_type": contract.visual_type,
                    "required_keys": get_visual_contract(contract.visual_type),
                    "rule": "visual 仅含知识数据，不含样式、坐标和时间戳。必须严格按 required_keys 的键名和类型生成，数组中的对象必须包含指定的子字段。",
                },
                ensure_ascii=False,
            ),
        )
        draft = await self.llm.ainvoke_json(SceneDraft, prompt)
        return draft.model_copy(
            update={
                "scene_id": contract.scene_id,
                "index": contract.index,
                "visual_type": contract.visual_type,
            }
        )
