"""Typed scene writing with narration-backed visual beats."""

from __future__ import annotations

import json
import time
from pathlib import Path

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.shared.video.schemas import (
    SceneContract,
    SceneDraft,
    VideoMaterialDigest,
    VideoRequest,
    VideoStyleDecision,
    scene_draft_for,
)
from app.shared.video.visual_contracts import get_visual_contract

logger = get_logger(__name__)

_PROMPT_PATH = Path(__file__).parent / "prompts" / "scene.md"


# 场景编写 Agent：基于契约生成带旁白与视觉节拍的场景脚本
class SceneWriterAgent:
    def __init__(self, llm=None) -> None:
        self.llm = llm or get_llm()

    # 编写：按视觉类型选择强类型 schema 并调用 LLM 生成场景草稿
    async def write(
        self,
        *,
        request: VideoRequest,
        digest: VideoMaterialDigest,
        contract: SceneContract,
        style: VideoStyleDecision,
    ) -> SceneDraft:
        # 根据 visual_type 获取强类型 schema，确保 LLM 输出结构正确
        typed_schema = scene_draft_for(contract.visual_type)

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
        logger.info(
            "Video 场景编写 LLM 调用: index=%d role=%s visual_type=%s",
            contract.index, contract.role, contract.visual_type,
        )
        started = time.perf_counter()
        # 调用 LLM 生成强类型场景草稿
        draft = await self.llm.ainvoke_json(typed_schema, prompt)
        elapsed = int((time.perf_counter() - started) * 1000)
        logger.info(
            "Video 场景编写 LLM 完成: index=%d narration_len=%d visual_beats=%d elapsed_ms=%d",
            contract.index, len(draft.narration), len(draft.visual_beats), elapsed,
        )
        # 统一转为 SceneDraft（visual 已是强类型实例，model_dump 后可赋给 dict 字段）
        visual_data = draft.visual.model_dump() if hasattr(draft.visual, "model_dump") else draft.visual
        # 组装并返回标准 SceneDraft
        return SceneDraft(
            scene_id=contract.scene_id,
            index=contract.index,
            title=draft.title,
            narration=draft.narration,
            visual_type=contract.visual_type,
            visual=visual_data,
            visual_beats=draft.visual_beats,
        )
