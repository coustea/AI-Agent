"""SSE token event streaming helpers for chat responses."""

from __future__ import annotations

from collections.abc import AsyncIterator


class ResponseStreamer:
    def __init__(self, chunk_size: int = 1024) -> None:
        self.chunk_size = max(1, chunk_size)

    async def stream_answer(self, answer: str) -> AsyncIterator[dict[str, str]]:
        if not answer or not answer.strip():
            return

        for start in range(0, len(answer), self.chunk_size):
            chunk = answer[start : start + self.chunk_size]
            if chunk:
                yield {"event": "token", "data": chunk}
