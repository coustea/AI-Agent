from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.chat.agent import TutorAgent, TutorAgentState
from app.chat.emitter import ChatEventName, SSE_EVENT_MAP, runtime_status
from app.chat.schemas import TutorRuntimeEvent


# ── Verify new event types exist in ChatEventName ──


class TestChatEventNames:
    def test_content_replace_is_valid(self):
        event: ChatEventName = "content.replace"
        assert event == "content.replace"

    def test_attachment_running_is_valid(self):
        event: ChatEventName = "attachment.running"
        assert event == "attachment.running"

    def test_attachment_completed_is_valid(self):
        event: ChatEventName = "attachment.completed"
        assert event == "attachment.completed"

    def test_attachment_failed_is_valid(self):
        event: ChatEventName = "attachment.failed"
        assert event == "attachment.failed"


# ── Verify SSE_EVENT_MAP includes event types ──


class TestSseEventMap:
    def test_agent_status_mapped(self):
        assert "agent_status" in SSE_EVENT_MAP
        assert SSE_EVENT_MAP["agent_status"] == "agent_status"

    def test_content_replace_mapped(self):
        assert "content_replace" in SSE_EVENT_MAP
        assert SSE_EVENT_MAP["content_replace"] == "content_replace"

    def test_diagram_mapped(self):
        assert "diagram" in SSE_EVENT_MAP
        assert SSE_EVENT_MAP["diagram"] == "diagram"


# ── Verify runtime_status ──


class TestRuntimeStatus:
    def test_done_to_completed(self):
        assert runtime_status("done") == "completed"

    def test_error_to_failed(self):
        assert runtime_status("error") == "failed"

    def test_running_stays(self):
        assert runtime_status("running") == "running"

    def test_none_defaults_to_running(self):
        assert runtime_status(None) == "running"


class TestEmitEvent:
    @pytest.mark.asyncio
    async def test_emit_appends_to_events(self):
        agent = TutorAgent.__new__(TutorAgent)
        agent.memory_service = MagicMock()

        state: TutorAgentState = {
            "event_queue": asyncio.Queue(),
            "user_id": 1,
            "session_id": "s1",
        }
        event = TutorRuntimeEvent(
            type="agent_status",
            payload={"tool_name": "search", "status": "running"},
        )
        result = await agent._emit_event(state, event)
        assert len(result) == 1
        assert result[0].type == "agent_status"

    @pytest.mark.asyncio
    async def test_emit_put_to_queue(self):
        agent = TutorAgent.__new__(TutorAgent)
        agent.memory_service = MagicMock()

        queue = asyncio.Queue()
        state: TutorAgentState = {
            "event_queue": queue,
            "user_id": 1,
            "session_id": "s1",
        }
        event = TutorRuntimeEvent(
            type="agent_status",
            payload={"status": "running"},
        )
        await agent._emit_event(state, event)
        assert not queue.empty()
        queued = queue.get_nowait()
        assert queued.type == "agent_status"

    @pytest.mark.asyncio
    async def test_emit_no_queue_still_returns_event(self):
        agent = TutorAgent.__new__(TutorAgent)
        agent.memory_service = MagicMock()

        state: TutorAgentState = {
            "user_id": 1,
            "session_id": "s1",
        }
        event = TutorRuntimeEvent(
            type="agent_status",
            payload={"status": "running"},
        )
        result = await agent._emit_event(state, event)
        assert len(result) == 1
        assert result[0].type == "agent_status"
