from __future__ import annotations

import pytest

from app.chat.streaming import ResponseStreamer, SafetyBufferedResponseStreamer


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


class TestSafetyBufferedResponseStreamer:
    @pytest.mark.asyncio
    async def test_push_and_flush(self):
        inner = ResponseStreamer(chunk_size=1024)
        results = []

        async def safe_check(text):
            class R:
                has_violation = False
                sanitized_text = text
            return R()

        sbs = SafetyBufferedResponseStreamer(
            response_streamer=inner,
            safety_check=safe_check,
            guard_chars=2,
        )
        async for event in sbs.push("hello "):
            results.append(event)
        async for event in sbs.push("world"):
            results.append(event)
        async for event in sbs.flush():
            results.append(event)

        all_text = "".join(e["data"] for e in results)
        assert "hello " in all_text or "helloworld" in all_text

    @pytest.mark.asyncio
    async def test_flush_empty(self):
        inner = ResponseStreamer(chunk_size=1024)

        async def safe_check(text):
            class R:
                has_violation = False
                sanitized_text = text
            return R()

        sbs = SafetyBufferedResponseStreamer(
            response_streamer=inner,
            safety_check=safe_check,
            guard_chars=2,
        )
        chunks = [e async for e in sbs.flush()]
        assert chunks == []

    @pytest.mark.asyncio
    async def test_guard_chars_zero(self):
        inner = ResponseStreamer(chunk_size=1024)
        results = []

        async def safe_check(text):
            class R:
                has_violation = False
                sanitized_text = text
            return R()

        sbs = SafetyBufferedResponseStreamer(
            response_streamer=inner,
            safety_check=safe_check,
            guard_chars=0,
        )
        async for event in sbs.push("abc"):
            results.append(event)
        all_text = "".join(e["data"] for e in results)
        assert "abc" in all_text

    @pytest.mark.asyncio
    async def test_violation_sanitized(self):
        inner = ResponseStreamer(chunk_size=1024)
        results = []

        async def safe_check(text):
            class R:
                has_violation = True
                sanitized_text = text.replace("bad", "***")
            return R()

        sbs = SafetyBufferedResponseStreamer(
            response_streamer=inner,
            safety_check=safe_check,
            guard_chars=0,
        )
        async for event in sbs.push("this is bad text"):
            results.append(event)
        async for event in sbs.flush():
            results.append(event)
        all_text = "".join(e["data"] for e in results)
        assert "bad" not in all_text
        assert "***" in all_text
