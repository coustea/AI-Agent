from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.auth.schemas import UserClaims
from app.auth.security import create_token
from app.main import app

# Setup test client
client = TestClient(app)


@pytest.fixture
def authenticated_client():
    """返回注入了真实 JWT 的客户端，走完整鉴权链路。"""
    client.headers["Authorization"] = f"Bearer {create_token(UserClaims(id=1, username='test_user'))}"
    yield client
    client.headers.pop("Authorization", None)






def test_get_path_learning_evaluation_endpoint(authenticated_client):
    mock_response = MagicMock()
    mock_response.model_dump.return_value = {
        "path_id": 12,
        "overall_progress": 50,
        "current_node_key": "sql-join",
        "needs_optimization": True,
        "optimization_tips": ["检测到测验得分偏低"],
    }

    with patch("app.path.api.PathService") as MockService:
        mock_service_instance = MockService.return_value
        mock_service_instance.get_learning_evaluation = AsyncMock(return_value=mock_response)

        response = authenticated_client.get("/api/v1/ai/path-plan/12/evaluation")

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["code"] == 200
        assert json_data["data"]["path_id"] == 12
        assert json_data["data"]["needs_optimization"] is True










def test_record_path_learning_event_endpoint(authenticated_client):
    from datetime import datetime
    from app.infra.models import LearningEvent

    mock_event = LearningEvent(
        id=99,
        user_id=1,
        path_id=12,
        path_node_id=34,
        node_id="sql-join",
        event_type="quiz_submitted",
        topic="SQL Join",
        score=59,
        created_at=datetime.now(),
    )

    with patch("app.path.api.PathService") as MockService:
        mock_service_instance = MockService.return_value
        mock_service_instance.record_learning_event = AsyncMock(
            return_value=(mock_event, {"event_type": "quiz_submitted", "topic": "SQL Join"})
        )

        response = authenticated_client.post(
            "/api/v1/ai/path-plan/12/events",
            json={
                "event_type": "quiz_submitted",
                "path_node_id": 34,
                "node_id": "sql-join",
                "topic": "SQL Join",
                "score": 59,
            },
        )

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["code"] == 200
        assert json_data["data"]["entity_id"] == "12"
        assert json_data["data"]["event_metadata"]["node_id"] == "sql-join"
        mock_service_instance.record_learning_event.assert_awaited_once()


def test_generation_task_endpoints_removed(authenticated_client):
    active_response = authenticated_client.get("/api/v1/ai/path-plan/tasks/active")
    status_response = authenticated_client.get("/api/v1/ai/path-plan/tasks/12/status")
    generate_response = authenticated_client.post(
        "/api/v1/ai/path-plan/generate",
        json={"goal": "learn sql", "topic": "sql"},
    )

    assert active_response.status_code == 404
    assert status_response.status_code == 404
    assert generate_response.status_code == 405


def test_generate_cartoon_endpoint(authenticated_client):
    mock_task = MagicMock()
    mock_task.resource.id = 1
    mock_task.model_dump.return_value = {
        "resource": {
            "id": 1,
            "resource_type": "cartoon",
            "version_no": 1,
            "title": "Cartoon",
            "content_format": "mp4",
            "content_text": "cartoon-video-url",
            "created_at": "2026-07-06T11:00:00",
        },
        "run_id": "test-run-123",
    }

    with patch("app.path.api.PathService") as MockService, patch(
        "app.path.api.PathEvents"
    ) as MockEvents, patch(
        "app.path.api.run_resource_generation_bg", new_callable=AsyncMock
    ):
        mock_events_instance = AsyncMock()
        MockEvents.return_value = mock_events_instance
        mock_service_instance = MockService.return_value
        mock_service_instance.create_node_resource_task = AsyncMock(return_value=mock_task)

        response = authenticated_client.post("/api/v1/ai/path-plan/nodes/101/resources/cartoon")

        assert response.status_code == 202
        json_data = response.json()
        assert json_data["code"] == 200
        assert json_data["data"]["resource"]["resource_type"] == "cartoon"
        mock_service_instance.create_node_resource_task.assert_awaited_once()




