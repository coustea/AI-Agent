from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("SPARK_MAX_API_PASSWORD", "test-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.chat.streaming import ResponseStreamer, SafetyBufferedResponseStreamer


async def collect_events(answer: str, *, chunk_size: int = 4) -> list[dict[str, str]]:
    streamer = ResponseStreamer(chunk_size=chunk_size)
    return [event async for event in streamer.stream_answer(answer)]


@pytest.mark.asyncio
async def test_stream_answer_yields_token_events_in_configured_chunks() -> None:
    assert await collect_events("abcdefghi", chunk_size=4) == [
        {"event": "token", "data": "abcd"},
        {"event": "token", "data": "efgh"},
        {"event": "token", "data": "i"},
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("answer", ["", "   ", "\n\t "])
async def test_stream_answer_skips_blank_or_whitespace_answers(answer: str) -> None:
    assert await collect_events(answer, chunk_size=4) == []


async def collect_buffered_events(chunks: list[str], *, guard_chars: int = 1) -> list[dict[str, str]]:
    async def safety_check(text: str):
        return SimpleNamespace(has_violation="赌博" in text, sanitized_text=text.replace("赌博", "***"))

    streamer = SafetyBufferedResponseStreamer(
        response_streamer=ResponseStreamer(chunk_size=20),
        safety_check=safety_check,
        guard_chars=guard_chars,
    )
    events: list[dict[str, str]] = []
    for chunk in chunks:
        events.extend([event async for event in streamer.push(chunk)])
    events.extend([event async for event in streamer.flush()])
    return events


@pytest.mark.asyncio
async def test_buffered_streamer_preserves_whitespace_chunks_between_text() -> None:
    events = await collect_buffered_events(["Hello", " ", "world"])

    assert "".join(event["data"] for event in events) == "Hello world"


@pytest.mark.asyncio
async def test_buffered_streamer_preserves_leading_whitespace_before_text() -> None:
    events = await collect_buffered_events(["  ", "x"])

    assert "".join(event["data"] for event in events) == "  x"


@pytest.mark.asyncio
async def test_buffered_streamer_sanitizes_terms_split_across_chunks() -> None:
    events = await collect_buffered_events(["赌", "博", "建议"])
    streamed_text = "".join(event["data"] for event in events)

    assert streamed_text == "***建议"
    assert "赌博" not in streamed_text


@pytest.mark.asyncio
async def test_buffered_streamer_skips_fully_blank_answer() -> None:
    assert await collect_buffered_events([" ", "\n\t"]) == []
