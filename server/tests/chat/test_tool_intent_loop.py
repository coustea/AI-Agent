from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_turn_orchestrator_executes_single_tool_intent_then_reasons_again() -> None:
    from app.chat.orchestrator import TurnOrchestrator
    from app.chat.schemas import ToolIntent, TurnRequest

    calls: list[str] = []

    class FakeAgent:
        def __init__(self) -> None:
            self.count = 0

        async def reason(self, request, evidence_set, constraints):
            self.count += 1
            if self.count == 1:
                calls.append("intent")
                return ToolIntent(tool_name="learner_profile", payload={"dimension": "goal"})
            calls.append("final")
            return {"kind": "final_answer", "answer": "根据画像给出回答"}

    class FakeTools:
        async def execute(self, intent, request):
            calls.append(f"execute:{intent.tool_name}")
            return {"tool_name": "get_learner_profile", "status": "success", "evidence": []}

    orchestrator = TurnOrchestrator(agent=FakeAgent(), tools=FakeTools())

    result = await orchestrator.run(
        TurnRequest(user_id=7, session_id="session-1", message="我该怎么学", attachments=[])
    )

    assert calls == ["intent", "execute:learner_profile", "final"]
    assert result.final_answer == "根据画像给出回答"
    assert result.tool_records[0].tool_name == "get_learner_profile"
