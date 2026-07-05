from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest


@pytest.mark.asyncio
async def test_knowledge_base_has_async_context_formatter(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.chat.tools import knowledge

    def sync_format(query: str, *, course_name: str | None = None, top_k: int | None = None) -> tuple[str, list[dict[str, Any]]]:
        return f"context:{query}:{top_k}", [{"rank": 1, "metadata": {}, "distance": 0.1}]

    monkeypatch.setattr(knowledge, "format_knowledge_context", sync_format)

    context, rows = await knowledge.aformat_knowledge_context("缓存", top_k=2)

    assert context == "context:缓存:2"
    assert rows[0]["rank"] == 1


@pytest.mark.asyncio
async def test_spawn_background_tracks_task_until_done() -> None:
    from app.chat.service import ChatUseCases

    use_cases = ChatUseCases()
    gate = asyncio.Event()

    async def waits() -> None:
        await gate.wait()

    use_cases._spawn_background(waits(), label="tracked")

    assert len(use_cases._background_tasks) == 1
    gate.set()
    await asyncio.gather(*list(use_cases._background_tasks))
    assert use_cases._background_tasks == set()
