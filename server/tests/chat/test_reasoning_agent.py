"""TutorAgent LangGraph graph tests — verify node routing and basic execution."""

from __future__ import annotations

import pytest

from app.chat.agent import TutorAgent, TutorAgentState
from app.chat.agent.routing import route_after_classify, route_after_analysis, route_after_answer
from app.chat.schemas import ClassificationResult, TutorAgentInput


@pytest.mark.asyncio
async def test_route_after_classify_goes_to_answer_when_no_needs() -> None:
    state: TutorAgentState = {
        "classification": ClassificationResult(
            intent="general_qa",
            needs_file_analysis=False,
            needs_knowledge_search=False,
            needs_web_search=False,
            needs_diagram=False,
        ),
        "attachments": [],
    }
    assert route_after_classify(state) == "answer_node"


@pytest.mark.asyncio
async def test_route_after_classify_goes_to_analysis_when_attachments() -> None:
    state: TutorAgentState = {
        "classification": ClassificationResult(needs_file_analysis=True),
        "attachments": ["http://example.com/file.pdf"],
    }
    assert route_after_classify(state) == "analysis_files"


@pytest.mark.asyncio
async def test_route_after_classify_goes_to_search_when_knowledge_needed() -> None:
    state: TutorAgentState = {
        "classification": ClassificationResult(needs_knowledge_search=True),
        "attachments": [],
    }
    assert route_after_classify(state) == "search_node"


@pytest.mark.asyncio
async def test_route_after_classify_goes_to_search_when_web_needed() -> None:
    state: TutorAgentState = {
        "classification": ClassificationResult(needs_web_search=True),
        "attachments": [],
    }
    assert route_after_classify(state) == "search_node"


@pytest.mark.asyncio
async def test_route_after_classify_goes_to_answer_when_no_classification() -> None:
    state: TutorAgentState = {"classification": None}
    assert route_after_classify(state) == "answer_node"


@pytest.mark.asyncio
async def test_route_after_answer_goes_to_diagram_when_needed() -> None:
    state: TutorAgentState = {
        "classification": ClassificationResult(needs_diagram=True),
        "final_answer": "some answer",
    }
    assert route_after_answer(state) == "diagram_node"


@pytest.mark.asyncio
async def test_route_after_answer_goes_to_end_when_no_diagram() -> None:
    from langgraph.graph import END

    state: TutorAgentState = {
        "classification": ClassificationResult(needs_diagram=False),
        "final_answer": "some answer",
    }
    assert route_after_answer(state) == END


@pytest.mark.asyncio
async def test_route_after_analysis_goes_to_search_when_needed() -> None:
    state: TutorAgentState = {
        "classification": ClassificationResult(needs_knowledge_search=True),
    }
    assert route_after_analysis(state) == "search_node"


@pytest.mark.asyncio
async def test_route_after_analysis_goes_to_answer_when_no_search() -> None:
    state: TutorAgentState = {
        "classification": ClassificationResult(needs_knowledge_search=False, needs_web_search=False),
    }
    assert route_after_analysis(state) == "answer_node"


@pytest.mark.asyncio
async def test_tutor_agent_graph_compiles() -> None:
    """Verify the LangGraph graph can be built and compiled."""
    agent = TutorAgent()
    assert agent._graph is not None


@pytest.mark.asyncio
async def test_classification_result_defaults() -> None:
    """Verify ClassificationResult has sensible defaults."""
    cls = ClassificationResult()
    assert cls.intent == "general_qa"
    assert cls.needs_file_analysis is False
    assert cls.needs_knowledge_search is False
    assert cls.needs_diagram is False
    assert cls.safety_risk == "none"


@pytest.mark.asyncio
async def test_tutor_agent_input_defaults() -> None:
    """Verify TutorAgentInput has sensible defaults."""
    input = TutorAgentInput(user_id=1, session_id="s1", question="hello")
    assert input.attachments == []
    assert input.history_messages == []
    assert input.session_summary == ""
    assert input.enable_web_search is False
