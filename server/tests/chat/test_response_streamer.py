from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("SPARK_MAX_API_PASSWORD", "test-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.chat.streaming import ResponseStreamer


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
