"""SSE token 事件流辅助工具，用于聊天响应的流式分发。"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from app.infra.logging import get_logger

logger = get_logger(__name__)


# ResponseStreamer：将最终回答文本按固定大小切片，以带节奏延迟的方式流式输出 token
class ResponseStreamer:
    """将最终回答文本拆分为节奏化的 token 事件，通过 SSE 投递。"""

    # 初始化分片大小与分片间延迟（保证最小为 1 / 0）
    def __init__(self, chunk_size: int = 48, chunk_delay: float = 0.012) -> None:
        self.chunk_size = max(1, chunk_size)
        self.chunk_delay = max(0.0, chunk_delay)

    # 按 chunk_size 切分回答并逐个 yield token，非空快进，末尾不延迟
    async def stream_answer(self, answer: str, *, skip_blank: bool = True) -> AsyncIterator[dict[str, str]]:
        # 空回答直接结束
        if not answer or (skip_blank and not answer.strip()):
            logger.debug("[ChatStreaming] stream_answer 跳过空回答")
            return

        logger.info("[ChatStreaming] stream_answer 开始: answer_len=%d chunk_size=%d", len(answer), self.chunk_size)
        chunk_count = 0
        # 逐片生成 token，片间按 chunk_delay 节流
        for start in range(0, len(answer), self.chunk_size):
            chunk = answer[start : start + self.chunk_size]
            if not chunk:
                continue

            chunk_count += 1
            yield {"event": "token", "data": chunk}
            if self.chunk_delay and start + self.chunk_size < len(answer):
                await asyncio.sleep(self.chunk_delay)

        logger.info("[ChatStreaming] stream_answer 完成: chunks=%d", chunk_count)
