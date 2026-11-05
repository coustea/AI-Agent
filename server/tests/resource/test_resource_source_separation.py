from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.auth.security import get_current_user
from app.infra.models import User
from app.main import app


client = TestClient(app)
mock_user = User(id=1, username="test_user", email="test@example.com")


def _override_auth():
    async def mock_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = mock_get_current_user


def _clear_auth_override():
    app.dependency_overrides.pop(get_current_user, None)


def test_list_resources_uses_standalone_sources_only():
    _override_auth()
    try:
      with patch("app.resource.api.ResourceService") as MockService:
          mock_service = MockService.return_value
          mock_service.list_resources = AsyncMock(return_value=[])
          mock_service.count_resources = AsyncMock(return_value=0)
          mock_service.list_resource_type_summary = AsyncMock(return_value={})

          response = client.get("/api/v1/ai/resources")

          assert response.status_code == 200
          mock_service.list_resources.assert_awaited_once_with(1, 20, 0)
          mock_service.count_resources.assert_awaited_once_with(1)
    finally:
        _clear_auth_override()


def test_get_resource_detail_rejects_path_node_resource_from_standalone_endpoint():
    _override_auth()
    try:
         with patch("app.resource.api.ResourceService") as MockService:
             mock_service = MockService.return_value
             mock_service.get_resource_bundle = AsyncMock(return_value=None)

             response = client.get("/api/v1/ai/resources/101")

             assert response.status_code == 404
             mock_service.get_resource_bundle.assert_awaited_once_with(
                 1,
                 101,
             )
    finally:
         _clear_auth_override()


def test_get_resource_status_rejects_path_node_resource_from_standalone_endpoint():
    _override_auth()
    try:
        with patch("app.resource.api.ResourceService") as MockService:
            mock_service = MockService.return_value
            mock_service.get_generation_status = AsyncMock(return_value=None)

            response = client.get("/api/v1/ai/resources/101/status")

            assert response.status_code == 404
            mock_service.get_generation_status.assert_awaited_once_with(
                user_id=1,
                resource_id=101,
            )
    finally:
        _clear_auth_override()


def test_get_path_resource_detail_uses_path_node_source_only():
    _override_auth()
    try:
        from app.infra.models import PathNodeResource
        from app.infra.database import get_session
        from sqlmodel.ext.asyncio.session import AsyncSession

        mock_resource = PathNodeResource(
            id=88,
            path_id=1,
            node_id=1,
            user_id=1,
            resource_type="content",
            title="路径资源",
            content_format="markdown",
            content_text="test",
        )

        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.get = AsyncMock(return_value=mock_resource)

        async def override_get_session():
            yield mock_session

        app.dependency_overrides[get_session] = override_get_session
        response = client.get("/api/v1/ai/path-plan/resources/88")
        app.dependency_overrides.pop(get_session, None)

        assert response.status_code == 200
        assert response.json()["data"]["id"] == 88
    finally:
        _clear_auth_override()


def test_list_path_resources_uses_path_source_only():
    _override_auth()
    try:
        from app.infra.database import get_session
        from sqlmodel.ext.asyncio.session import AsyncSession

        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.exec = AsyncMock()

        class _EmptyResult:
            def all(self):
                return []

            def first(self):
                return 0

        mock_session.exec.return_value = _EmptyResult()

        async def override_get_session():
            yield mock_session

        app.dependency_overrides[get_session] = override_get_session
        response = client.get("/api/v1/ai/path-plan/resources?limit=12&offset=24")
        app.dependency_overrides.pop(get_session, None)

        assert response.status_code == 200
        assert response.json()["data"]["items"] == []
        assert response.json()["data"]["total"] == 0
    finally:
        _clear_auth_override()
