from __future__ import annotations

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from sqlmodel.ext.asyncio.session import AsyncSession

import app.chat.api as chat_api
from app.auth.security import get_current_user_flexible
from app.infra.database import get_session
from app.infra.models import ChatMessage, User
from app.main import app


client = TestClient(app)
current_user = User(id=1, username="alice", email="alice@example.com")
valid_diagram = {"graph_type": "framework", "title": "TCP", "visual_content": {}}


class _Result:
    def __init__(self, message: ChatMessage | None) -> None:
        self.message = message

    def first(self) -> ChatMessage | None:
        return self.message


def _install_dependencies(monkeypatch, message: ChatMessage | None) -> AsyncMock:
    session = AsyncMock(spec=AsyncSession)
    session.exec.return_value = _Result(message)

    async def override_user() -> User:
        return current_user

    async def override_session():
        yield session

    monkeypatch.setitem(app.dependency_overrides, get_current_user_flexible, override_user)
    monkeypatch.setitem(app.dependency_overrides, get_session, override_session)
    return session


def _fallback_message() -> ChatMessage:
    return ChatMessage(
        id=41,
        session_id="s1",
        role="assistant",
        usage_metadata={"diagram": {"kind": "fallback", "diagram": valid_diagram, "retryable": True}},
    )


def test_retry_diagram_image_returns_new_image_for_owned_fallback(monkeypatch) -> None:
    message = _fallback_message()
    session = _install_dependencies(monkeypatch, message)
    image = {"kind": "image", "title": "TCP", "image_url": "/static/tcp.png"}
    monkeypatch.setattr(chat_api, "render_teaching_diagram_png", AsyncMock(return_value=image))

    response = client.post("/api/v1/ai/chat/messages/41/diagram-image/retry")

    assert response.status_code == 200
    assert response.json()["data"]["diagram"] == image
    assert message.usage_metadata["diagram"] == image
    session.add.assert_called_once_with(message)
    session.commit.assert_awaited_once()


def test_retry_diagram_image_hides_message_owned_by_another_user(monkeypatch) -> None:
    _install_dependencies(monkeypatch, None)

    response = client.post("/api/v1/ai/chat/messages/41/diagram-image/retry")

    assert response.status_code == 404


def test_retry_diagram_image_rejects_existing_image(monkeypatch) -> None:
    message = _fallback_message()
    message.usage_metadata = {"diagram": {"kind": "image", "image_url": "/static/tcp.png"}}
    _install_dependencies(monkeypatch, message)

    response = client.post("/api/v1/ai/chat/messages/41/diagram-image/retry")

    assert response.status_code == 409


def test_retry_diagram_image_keeps_fallback_when_renderer_fails(monkeypatch) -> None:
    message = _fallback_message()
    session = _install_dependencies(monkeypatch, message)
    fallback = message.usage_metadata["diagram"].copy()
    monkeypatch.setattr(chat_api, "render_teaching_diagram_png", AsyncMock(side_effect=TimeoutError("timeout")))

    response = client.post("/api/v1/ai/chat/messages/41/diagram-image/retry")

    assert response.status_code == 503
    assert message.usage_metadata["diagram"] == fallback
    session.add.assert_not_called()
    session.commit.assert_not_awaited()
