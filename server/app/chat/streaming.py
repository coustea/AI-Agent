"""SSE token event streaming helpers for chat responses.

流式输出层：将 LLM 回答文本分块推送给前端。
"""

from __future__ import annotations

from collections.abc import AsyncIterator


class ResponseStreamer:
    """基础 SSE 流 — 将完整回答文本按固定大小分块输出。"""

    def __init__(self, chunk_size: int = 1024) -> None:
        # 每个 SSE event 的最大字符数，确保不超出网络缓冲区
        self.chunk_size = max(1, chunk_size)  # 至少 1 字符，防止零切片

    async def stream_answer(self, answer: str, *, skip_blank: bool = True) -> AsyncIterator[dict[str, str]]:
        """将回答文本分块 yield 为 SSE 事件。"""
        # 空回答或纯空白回答直接跳过（skip_blank=True 时）
        if not answer or (skip_blank and not answer.strip()):
            return

        # 按 chunk_size 步长切片，逐块 yield
        for start in range(0, len(answer), self.chunk_size):
            chunk = answer[start : start + self.chunk_size]
            if chunk:
                # SSE 事件格式：event: token 表示文本块，前端据此拼接完整回答
                yield {"event": "token", "data": chunk}
