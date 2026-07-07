"""Teaching direction and constrained visual-style selection."""

from __future__ import annotations

import time
from pathlib import Path

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.shared.video.schemas import (
    VideoMaterialDigest,
    VideoOutline,
    VideoRequest,
    VideoStyleDecision,
    VideoStyleId,
)

logger = get_logger(__name__)

_PROMPT_PATH = Path(__file__).parent / "prompts" / "director.md"

_PRECISION_TERMS = {
    "算法",
    "代码",
    "编程",
    "数据结构",
    "数组",
    "链表",
    "栈",
    "队列",
    "树",
    "排序",
    "查找",
    "复杂度",
    "指针",
}
_SYSTEM_TERMS = {
    "操作系统",
    "进程",
    "线程",
    "调度",
    "内存",
    "cpu",
    "处理器",
    "网络",
    "协议",
    "tcp",
    "体系结构",
    "存储",
    "缓存",
    "中断",
}


def select_style(
    topic: str,
    concepts: list[str],
    *,
    style_hint: VideoStyleId | None = None,
) -> VideoStyleDecision:
    """Choose one visual system from the teaching subject, with explicit override."""
    if style_hint is not None:
        return VideoStyleDecision(
            id=style_hint,
            rationale="调用方提供了明确的视觉风格偏好",
        )

    corpus = f"{topic} {' '.join(concepts)}".lower()
    precision_score = sum(term in corpus for term in _PRECISION_TERMS)
    systems_score = sum(term in corpus for term in _SYSTEM_TERMS)

    if precision_score > systems_score:
        return VideoStyleDecision(
            id="precision_light",
            rationale="主题以算法、代码或数据操作为核心，适合精确明亮的演算视图",
        )
    if systems_score > 0:
        return VideoStyleDecision(
            id="systems_dark",
            rationale="主题强调系统组件、状态或数据流，适合深色系统图谱",
        )
    return VideoStyleDecision(
        id="editorial_classroom",
        rationale="主题以概念理解、辨析和总结为主，适合编辑式课堂表达",
    )


class VideoDirectorAgent:
    def __init__(self, llm=None) -> None:
        self.llm = llm or get_llm()

    async def plan(
        self,
        request: VideoRequest,
        digest: VideoMaterialDigest,
    ) -> VideoOutline:
        style = select_style(
            request.topic,
            digest.core_concepts + digest.visual_opportunities,
            style_hint=request.style_hint,
        )
        prompt = _PROMPT_PATH.read_text(encoding="utf-8").format(
            request=request.model_dump_json(indent=2),
            digest=digest.model_dump_json(indent=2),
            style=style.model_dump_json(indent=2),
            scene_count=request.scene_count,
            narrative_focus=request.narrative_focus or "concept",
        )
        logger.info("Video 导演 LLM 调用: scene_count=%d style=%s", request.scene_count, style.id)
        started = time.perf_counter()
        outline = await self.llm.ainvoke_json(VideoOutline, prompt)
        elapsed = int((time.perf_counter() - started) * 1000)
        logger.info(
            "Video 导演 LLM 完成: scenes=%d narrative=%s elapsed_ms=%d",
            len(outline.scenes), outline.narrative, elapsed,
        )
        return outline.model_copy(update={"style": style})
