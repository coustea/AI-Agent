from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.auth.security import get_current_user
from app.infra.models import User
from app.path.schemas import LearningPathOverviewResponse, LearningPathNodeDTO

# Setup test client
client = TestClient(app)

# Create a mock user
mock_user = User(id=1, username="test_user", email="test@example.com")

@pytest.fixture
def authenticated_client(monkeypatch):
    # Override authentication dependency to return mock user
    async def mock_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = mock_get_current_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)


def test_get_active_path_endpoint(authenticated_client):
    mock_response = LearningPathOverviewResponse(
        id=12,
        module="mentor",
        title="SQL Path",
        goal="Learn SQL Joins",
        topic=None,
        overall_progress=0,
        current_node_key=None,
        status="active",
        stages=[],
        nodes=[
            LearningPathNodeDTO(
                id=101,
                node_id="sql-basics",
                stage_id="stage-1",
                title="SQL Basics",
                status="available",
                priority=10,
                attempt_count=0,
                prerequisites=[]
            )
        ],
        created_at="2026-05-29T11:44:08",
        updated_at="2026-05-29T11:44:08",
    )

    with patch("app.path.api.PathService") as MockService:
        mock_service_instance = MockService.return_value
        mock_service_instance.get_active_path_overview = AsyncMock(return_value=mock_response)

        response = authenticated_client.get("/api/v1/ai/path-plan/active")

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["code"] == 200
        assert json_data["message"] == "success"
        assert json_data["data"]["title"] == "SQL Path"
        assert json_data["data"]["nodes"][0]["node_id"] == "sql-basics"


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


def test_get_path_resource_detail_endpoint(authenticated_client):
    from app.infra.models import PathNodeResource
    from app.infra.database import get_session
    from sqlmodel.ext.asyncio.session import AsyncSession

    mock_resource = PathNodeResource(
        id=88,
        path_id=1,
        node_id=1,
        user_id=1,
        resource_type="content",
        title="路径节点资源",
        content_format="markdown",
        content_text="test",
    )

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.get = AsyncMock(return_value=mock_resource)

    async def override_get_session():
        yield mock_session

    app.dependency_overrides[get_session] = override_get_session
    response = authenticated_client.get("/api/v1/ai/path-plan/resources/88")
    app.dependency_overrides.pop(get_session, None)

    assert response.status_code == 200


def test_list_path_resources_endpoint(authenticated_client):
    from app.infra.database import get_session
    from sqlmodel.ext.asyncio.session import AsyncSession

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.exec = AsyncMock()

    class _EmptyResult:
        def all(self):
            return []

    mock_session.exec.return_value = _EmptyResult()

    async def override_get_session():
        yield mock_session

    app.dependency_overrides[get_session] = override_get_session
    response = authenticated_client.get("/api/v1/ai/path-plan/resources?limit=12&offset=24")
    app.dependency_overrides.pop(get_session, None)

    assert response.status_code == 200
    json_data = response.json()
    assert json_data["code"] == 200
    assert json_data["data"]["items"] == []
    assert json_data["data"]["total"] == 0


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

    with patch("app.path.api.PathService") as MockService, patch(
        "app.path.api.bg_apply_profile_update_from_learning_event", new_callable=AsyncMock
    ) as mock_profile_update:
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
        assert json_data["data"]["path_id"] == 12
        assert json_data["data"]["node_id"] == "sql-join"
        mock_profile_update.assert_awaited_once()
        assert mock_profile_update.await_args.args[0] == 1
        assert mock_profile_update.await_args.args[1]["event_type"] == "quiz_submitted"
        assert mock_profile_update.await_args.args[1]["topic"] == "SQL Join"


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
