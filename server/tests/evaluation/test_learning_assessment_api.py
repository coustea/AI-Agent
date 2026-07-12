from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from app.main import app
from app.auth.security import get_current_user
from app.infra.models import User, LearningAssessmentReport
from app.evaluation.service import ConcurrencyError

# Setup test client
client = TestClient(app)
mock_user = User(id=1, username="test_api_user", email="test_api@example.com")

@pytest.fixture
def authenticated_client():
    async def mock_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = mock_get_current_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)


def test_post_generate_report_endpoint(authenticated_client):
    mock_report = LearningAssessmentReport(
        id=42,
        user_id=1,
        range_days=7,
        window_start=datetime.now(timezone.utc),
        window_end=datetime.now(timezone.utc),
        status="ready",
        facts_snapshot={"activity": {"total_minutes": 25}},
        report_markdown="## 学习概览\n"
    )

    with patch("app.evaluation.api.evaluation_service") as mock_service:
        mock_service.generate_report = AsyncMock(return_value=mock_report)

        response = authenticated_client.post(
            "/api/v1/ai/evaluation/reports",
            json={"range_days": 7}
        )

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["code"] == 200
        assert json_data["data"]["id"] == 42
        assert json_data["data"]["status"] == "ready"
        assert json_data["data"]["facts_snapshot"]["activity"]["total_minutes"] == 25


def test_post_generate_report_concurrency_conflict(authenticated_client):
    with patch("app.evaluation.api.evaluation_service") as mock_service:
        mock_service.generate_report = AsyncMock(side_effect=ConcurrencyError("in progress"))

        response = authenticated_client.post(
            "/api/v1/ai/evaluation/reports",
            json={"range_days": 7}
        )

        assert response.status_code == 409
        json_data = response.json()
        assert json_data["code"] == 409
        assert json_data["message"] == "assessment_generation_in_progress"


def test_get_latest_report_endpoint(authenticated_client):
    mock_report = LearningAssessmentReport(
        id=43,
        user_id=1,
        range_days=14,
        window_start=datetime.now(timezone.utc),
        window_end=datetime.now(timezone.utc),
        status="ready",
        facts_snapshot={},
        report_markdown="## 学习概览\n"
    )

    # Use mock db session query result
    # We will test the actual router mapping
    pass


def test_old_endpoints_are_deleted(authenticated_client):
    # GET /api/v1/ai/evaluation/summary -> should be 444 or 404 (not registered)
    res_summary = authenticated_client.get("/api/v1/ai/evaluation/summary")
    assert res_summary.status_code == 404

    res_stats = authenticated_client.get("/api/v1/ai/evaluation/time-stats")
    assert res_stats.status_code == 404

    res_dashboard = authenticated_client.get("/api/v1/ai/dashboard/study-stats")
    assert res_dashboard.status_code == 404
