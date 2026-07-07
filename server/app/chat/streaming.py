"""SSE token 事件流辅助工具，用于聊天响应的流式分发。"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator


class ResponseStreamer:
    """将最终回答文本拆分为节奏化的 token 事件，通过 SSE 投递。"""

    def __init__(self, chunk_size: int = 48, chunk_delay: float = 0.012) -> None:
        self.chunk_size = max(1, chunk_size)
        self.chunk_delay = max(0.0, chunk_delay)

    async def stream_answer(self, answer: str, *, skip_blank: bool = True) -> AsyncIterator[dict[str, str]]:
        if not answer or (skip_blank and not answer.strip()):
            return

        for start in range(0, len(answer), self.chunk_size):
            chunk = answer[start : start + self.chunk_size]
            if not chunk:
                continue

            yield {"event": "token", "data": chunk}
            if self.chunk_delay and start + self.chunk_size < len(answer):
                await asyncio.sleep(self.chunk_delay)
