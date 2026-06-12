from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_turn_orchestrator_runs_attachment_then_search_then_answer_then_diagram() -> None:
    from app.chat.orchestrator import TurnOrchestrator
    from app.chat.schemas import TurnRequest

    calls: list[str] = []

    class FakeAttachments:
        async def analyze(self, request):
            calls.append("attachments")
            return []

    class FakeSearch:
        async def search(self, request, evidence_set):
            calls.append("search")
            return []

    class FakeAgent:
        async def reason(self, request, evidence_set, constraints):
            calls.append("answer")
            return {"kind": "final_answer", "answer": "讲解完成"}

    class FakeDiagram:
        async def generate(self, request, answer, evidence_set):
            calls.append("diagram")
            return {"graph_type": "summary", "title": "图解"}

    orchestrator = TurnOrchestrator(
        attachments=FakeAttachments(),
        search=FakeSearch(),
        agent=FakeAgent(),
        diagram=FakeDiagram(),
        eager_search_enabled=True,
    )

    await orchestrator.run(
        TurnRequest(
            user_id=7,
            session_id="session-1",
            message="解释这张图",
            attachments=["/tmp/a.png"],
            attachment_analysis_enabled=True,
            search_enabled=True,
            diagram_enabled=True,
        )
    )

    assert calls == ["attachments", "search", "answer", "diagram"]


@pytest.mark.asyncio
async def test_turn_orchestrator_does_not_eager_search_when_tool_agent_can_search() -> None:
    from app.chat.orchestrator import TurnOrchestrator
    from app.chat.schemas import TurnRequest

    calls: list[str] = []

    class FakeSearch:
        async def search(self, request, evidence_set):
            calls.append("search")
            return []

    class FakeAgent:
        async def reason(self, request, evidence_set, constraints, tools=None):
            calls.append("answer")
            assert tools is not None
            return {"kind": "final_answer", "answer": "讲解完成"}

    orchestrator = TurnOrchestrator(search=FakeSearch(), agent=FakeAgent(), eager_search_enabled=False)

    result = await orchestrator.run(
        TurnRequest(user_id=7, session_id="session-1", message="解释 TCP", search_enabled=True)
    )

    assert calls == ["answer"]
    assert result.final_answer == "讲解完成"


@pytest.mark.asyncio
async def test_turn_orchestrator_does_not_mask_agent_type_errors() -> None:
    from app.chat.orchestrator import TurnOrchestrator
    from app.chat.schemas import TurnRequest

    class FakeAgent:
        async def reason(self, request, evidence_set, constraints, tools=None):
            raise TypeError("internal agent failure")

    orchestrator = TurnOrchestrator(agent=FakeAgent())

    with pytest.raises(TypeError, match="internal agent failure"):
        await orchestrator.run(TurnRequest(user_id=7, session_id="session-1", message="解释 TCP"))


@pytest.mark.asyncio
async def test_turn_orchestrator_omits_tools_kwarg_for_legacy_executor() -> None:
    from app.chat.orchestrator import TurnOrchestrator
    from app.chat.schemas import TurnRequest

    class LegacyExecutor:
        async def execute(self, intent, request=None):
            raise AssertionError("should not execute tools for final answer")

    class FakeAgent:
        async def reason(self, request, evidence_set, constraints):
            return {"kind": "final_answer", "answer": "讲解完成"}

    orchestrator = TurnOrchestrator(agent=FakeAgent(), tools=LegacyExecutor())

    result = await orchestrator.run(TurnRequest(user_id=7, session_id="session-1", message="解释 TCP"))

    assert result.final_answer == "讲解完成"
