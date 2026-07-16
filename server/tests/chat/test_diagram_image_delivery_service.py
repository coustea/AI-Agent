from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.chat.schemas import TutorRuntimeEvent


def _diagram() -> dict:
    return {
        "graph_type": "framework",
        "title": "TCP 连接建立",
        "teaching_goal": "理解三次握手",
        "visual_content": {"center": "三次握手", "modules": []},
        "teaching_content": {"summary": "建立可靠连接"},
    }


class _FakeUseCases:
    def __init__(self) -> None:
        self._memory_service = _FakeMemoryService()

    def default_session_id(self, user_id: int) -> str:
        return "default"

    def _spawn_background(self, coro, *, label: str = "") -> None:
        coro.close()


class _FakeMemoryService:
    def __init__(self) -> None:
        self.saved_messages: list[dict] = []

    async def upsert_activity(self, **kwargs) -> None:
        return None

    async def count_messages(self, **kwargs) -> int:
        return 2

    async def get_session_summary_context(self, **kwargs) -> str:
        return ""

    async def save_message(self, **kwargs):
        self.saved_messages.append(kwargs)
        return SimpleNamespace(id=99)


async def _events_for_final_payload(monkeypatch: pytest.MonkeyPatch, delivery) -> tuple[list[dict], _FakeMemoryService]:
    import app.chat.service as service

    class FakeTutorAgent:
        async def chat(self, agent_input):
            yield TutorRuntimeEvent(type="final", payload={"final_answer": "答案", "diagram_result": _diagram()})

    async def empty_history(*args, **kwargs):
        return []

    memory_service = _FakeMemoryService()
    use_cases = _FakeUseCases()
    use_cases._memory_service = memory_service
    monkeypatch.setattr(service, "get_chat_usecases", lambda: use_cases)
    monkeypatch.setattr(service, "get_chat_memory_service", lambda: memory_service)
    monkeypatch.setattr(service, "build_messages", empty_history)
    monkeypatch.setattr(service, "TutorAgent", FakeTutorAgent)

    monkeypatch.setattr(service, "ensure_teaching_diagram_png_payload", delivery)
    return [
        event async for event in service.chat(
            user_message_id=10,
            user_id=7,
            username="alice",
            session_id="s1",
            user_input="解释 TCP",
            diagram_mode="required",
        )
    ], memory_service


@pytest.mark.asyncio
async def test_chat_emits_png_payload_for_final_diagram(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.chat.diagram_image_renderer import ensure_teaching_diagram_png_payload

    image = {"kind": "image", "title": "TCP 连接建立", "image_url": "/diagram.png"}

    async def png_renderer(diagram: dict, *, username: str, session_id: str) -> dict:
        return image

    async def delivery(diagram: dict, *, username: str, session_id: str) -> dict:
        return await ensure_teaching_diagram_png_payload(
            diagram, username=username, session_id=session_id, renderer=png_renderer,
        )

    events, memory_service = await _events_for_final_payload(monkeypatch, delivery)

    assert next(event for event in events if event["event"] == "diagram")["data"] == image
    assert memory_service.saved_messages[0]["usage_metadata"]["diagram"] == image


@pytest.mark.asyncio
async def test_png_delivery_retries_exactly_once_before_succeeding() -> None:
    from app.chat.diagram_image_renderer import ensure_teaching_diagram_png_payload

    calls = 0

    async def flaky_renderer(diagram: dict, *, username: str, session_id: str) -> dict:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise TimeoutError("first screenshot timed out")
        return {"kind": "image", "title": diagram["title"], "image_url": "/diagram.png"}

    delivered = await ensure_teaching_diagram_png_payload(
        _diagram(),
        username="alice",
        session_id="s1",
        renderer=flaky_renderer,
    )

    assert calls == 2
    assert delivered["kind"] == "image"


@pytest.mark.asyncio
async def test_chat_done_payload_identifies_the_persisted_assistant_message(monkeypatch: pytest.MonkeyPatch) -> None:
    async def delivery(diagram: dict, *, username: str, session_id: str) -> dict:
        return {"kind": "image", "title": diagram["title"], "image_url": "/diagram.png"}

    events, _ = await _events_for_final_payload(monkeypatch, delivery)

    done = next(event for event in events if event["event"] == "done")
    assert done["data"]["saved_message_id"] == 99


@pytest.mark.asyncio
async def test_runtime_sse_completion_includes_persisted_assistant_message_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.chat.service as service

    emitted: list[dict] = []

    class FakeEvents:
        def __init__(self, **kwargs) -> None:
            pass

        async def open(self) -> None:
            return None

        async def send(self, *, event: str, message: str, data: dict | None = None) -> None:
            emitted.append({"event": event, "message": message, "data": data or {}})

    class FakeMemoryService:
        async def upsert_activity(self, **kwargs) -> None:
            return None

    async def completed_chat(**kwargs):
        yield {"event": "done", "data": {"session_id": "s1", "saved_message_id": 99}}

    class FakeSessionScope:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, *args) -> None:
            return None

    async def record_dialogue(**kwargs) -> None:
        return None

    monkeypatch.setattr(service, "ChatEvents", FakeEvents)
    monkeypatch.setattr(service, "get_chat_memory_service", FakeMemoryService)
    monkeypatch.setattr(service, "chat", completed_chat)
    monkeypatch.setattr(service, "session_scope", FakeSessionScope)
    monkeypatch.setattr(service, "record_dialogue_event", record_dialogue)

    await service.run_chat_agent(
        user_message_id=10,
        user_id=7,
        username="alice",
        session_id="s1",
        user_input="解释 TCP",
        attachments=[],
        enable_web_search=False,
        diagram_mode="required",
    )

    completion = next(event for event in emitted if event["event"] == "message.completed")
    assert completion["data"]["saved_message_id"] == 99


@pytest.mark.asyncio
async def test_runtime_sse_maps_delivered_diagram_to_diagram_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.chat.service as service

    emitted: list[dict] = []
    image = {"kind": "image", "title": "TCP", "image_url": "/diagram.png"}

    class FakeEvents:
        def __init__(self, **kwargs) -> None:
            pass

        async def open(self) -> None:
            return None

        async def send(self, *, event: str, message: str, data: dict | None = None) -> None:
            emitted.append({"event": event, "message": message, "data": data or {}})

    class FakeMemoryService:
        async def upsert_activity(self, **kwargs) -> None:
            return None

    async def completed_chat(**kwargs):
        yield {"event": "diagram", "data": image}
        yield {"event": "done", "data": {"session_id": "s1", "saved_message_id": 99}}

    class FakeSessionScope:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, *args) -> None:
            return None

    async def record_dialogue(**kwargs) -> None:
        return None

    monkeypatch.setattr(service, "ChatEvents", FakeEvents)
    monkeypatch.setattr(service, "get_chat_memory_service", FakeMemoryService)
    monkeypatch.setattr(service, "chat", completed_chat)
    monkeypatch.setattr(service, "session_scope", FakeSessionScope)
    monkeypatch.setattr(service, "record_dialogue_event", record_dialogue)

    await service.run_chat_agent(
        user_message_id=10,
        user_id=7,
        username="alice",
        session_id="s1",
        user_input="解释 TCP",
        attachments=[],
        enable_web_search=False,
        diagram_mode="required",
    )

    ready = next(event for event in emitted if event["event"] == "diagram.ready")
    assert ready["data"] == image


@pytest.mark.asyncio
async def test_chat_emits_structured_fallback_when_png_rendering_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.chat.diagram_image_renderer import ensure_teaching_diagram_png_payload

    diagram = _diagram()
    fallback = {
        "kind": "fallback",
        "diagram": diagram,
        "render_error": "图片生成暂时失败",
        "retryable": True,
    }

    calls = 0

    async def failing_renderer(diagram: dict, *, username: str, session_id: str) -> dict:
        nonlocal calls
        calls += 1
        raise TimeoutError("screenshot timeout")

    async def delivery(diagram: dict, *, username: str, session_id: str) -> dict:
        return await ensure_teaching_diagram_png_payload(
            diagram, username=username, session_id=session_id, renderer=failing_renderer,
        )

    events, memory_service = await _events_for_final_payload(monkeypatch, delivery)

    assert calls == 2
    assert next(event for event in events if event["event"] == "diagram")["data"] == fallback
    assert memory_service.saved_messages[0]["usage_metadata"]["diagram"] == fallback
