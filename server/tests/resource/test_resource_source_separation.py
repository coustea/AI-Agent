from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.auth.security import get_current_user
from app.infra.models import User
from app.main import app


client = TestClient(app)
mock_user = User(id=1, username="test_user", email="test@example.com")


def _override_auth() -> None:
    """覆盖当前请求认证依赖为测试用户。"""
    async def mock_get_current_user() -> User:
        return mock_user

    app.dependency_overrides[get_current_user] = mock_get_current_user


def _clear_auth_override() -> None:
    """清理请求认证依赖覆盖。"""
    app.dependency_overrides.pop(get_current_user, None)


def test_list_resources_uses_standalone_sources_only() -> None:
    """验证列表接口调用独立资源服务函数并返回分页结果。"""
    _override_auth()
    try:
        with patch("app.resource.api.list_resources", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = {"items": [], "total": 0, "type_summary": {}}

            response = client.get("/api/v1/ai/resources")

            assert response.status_code == 200
            mock_list.assert_awaited_once_with(1, limit=20, offset=0)
    finally:
        _clear_auth_override()


def test_get_resource_detail_rejects_path_node_resource_from_standalone_endpoint() -> None:
    """验证详情接口对不存在或无权限的资源返回 404。"""
    _override_auth()
    try:
        with patch("app.resource.api.get_resource_bundle", new_callable=AsyncMock) as mock_bundle:
            mock_bundle.return_value = None

            response = client.get("/api/v1/ai/resources/101")

            assert response.status_code == 404
            mock_bundle.assert_awaited_once_with(1, 101)
    finally:
        _clear_auth_override()


def test_get_resource_status_rejects_path_node_resource_from_standalone_endpoint() -> None:
    """验证状态接口对不存在或无权限的资源返回 404。"""
    _override_auth()
    try:
        with patch("app.resource.api.get_resource_status", new_callable=AsyncMock) as mock_status:
            mock_status.return_value = None

            response = client.get("/api/v1/ai/resources/101/status")

            assert response.status_code == 404
            mock_status.assert_awaited_once_with(1, 101)
    finally:
        _clear_auth_override()
