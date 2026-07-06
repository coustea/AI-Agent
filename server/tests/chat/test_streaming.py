from __future__ import annotations

import pytest

from app.chat.streaming import ResponseStreamer


class TestResponseStreamer:
    @pytest.mark.asyncio
    async def test_empty_answer(self):
        rs = ResponseStreamer(chunk_size=10)
        chunks = [e async for e in rs.stream_answer("")]
        assert chunks == []

    @pytest.mark.asyncio
    async def test_blank_answer_skipped(self):
        rs = ResponseStreamer(chunk_size=10)
        chunks = [e async for e in rs.stream_answer("   ", skip_blank=True)]
        assert chunks == []

    @pytest.mark.asyncio
    async def test_blank_answer_not_skipped(self):
        rs = ResponseStreamer(chunk_size=10)
        chunks = [e async for e in rs.stream_answer("   ", skip_blank=False)]
        assert len(chunks) == 1
        assert chunks[0]["data"] == "   "

    @pytest.mark.asyncio
    async def test_single_chunk(self):
        rs = ResponseStreamer(chunk_size=100)
        chunks = [e async for e in rs.stream_answer("hello")]
        assert len(chunks) == 1
        assert chunks[0] == {"event": "token", "data": "hello"}

    @pytest.mark.asyncio
    async def test_multiple_chunks(self):
        rs = ResponseStreamer(chunk_size=3)
        chunks = [e async for e in rs.stream_answer("abcdef")]
        assert len(chunks) == 2
        assert chunks[0]["data"] == "abc"
        assert chunks[1]["data"] == "def"

    @pytest.mark.asyncio
    async def test_chunk_size_one(self):
        rs = ResponseStreamer(chunk_size=1)
        chunks = [e async for e in rs.stream_answer("ab")]
        assert len(chunks) == 2

    @pytest.mark.asyncio
    async def test_chunk_size_clamped_to_min_one(self):
        rs = ResponseStreamer(chunk_size=0)
        assert rs.chunk_size == 1
