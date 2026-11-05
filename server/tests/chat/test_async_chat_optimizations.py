from __future__ import annotations

import asyncio
import pytest


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
