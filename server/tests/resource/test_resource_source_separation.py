from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.auth.schemas import UserClaims
from app.auth.security import create_token
from app.main import app


client = TestClient(app)
AUTH_HEADERS = {
    "Authorization": f"Bearer {create_token(UserClaims(id=1, username='test_user'))}",
}


def test_list_resources_uses_standalone_sources_only() -> None:
    """验证列表接口调用独立资源服务函数并返回分页结果。"""
    with patch("app.resource.api.list_resources", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = {"items": [], "total": 0}

        response = client.get("/api/v1/ai/resources", headers=AUTH_HEADERS)

        assert response.status_code == 200
        mock_list.assert_awaited_once_with(1, limit=20, offset=0)


def test_get_bundle_rejects_path_node_resource_from_standalone_endpoint() -> None:
    """验证资源包接口对不存在或无权限的资源返回 404。"""
    with patch("app.resource.api.get_resource_bundle", new_callable=AsyncMock) as mock_bundle:
        mock_bundle.return_value = None

        response = client.get("/api/v1/ai/resource/bundles/101", headers=AUTH_HEADERS)

        assert response.status_code == 404
        mock_bundle.assert_awaited_once_with(1, 101)
