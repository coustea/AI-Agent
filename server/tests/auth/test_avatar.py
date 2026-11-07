"""头像上传与获取接口测试。"""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("SPARK_MAX_API_PASSWORD", "test-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from httpx import ASGITransport, AsyncClient

from app.auth.schemas import UserClaims, UserRead
from app.auth.security import get_current_user
from app.config import user_avatar_dir
from app.infra.database import get_session
from app.main import create_app


@pytest.fixture
def mock_user():
    return UserClaims(
        id=42,
        username="testuser",
        email="test@example.com",
    )


@pytest.fixture
def app_with_auth(mock_user):
    """创建 app 并 override 认证依赖。"""
    app = create_app()

    async def _override_user():
        return mock_user

    async def _override_session():
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_session.rollback = AsyncMock()
        yield mock_session

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_session] = _override_session
    yield app
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_session, None)


def _make_png_bytes() -> bytes:
    """生成最小的合法 PNG 文件字节（1x1 透明像素）。"""
    return (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\nIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n\xb4"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def _make_jpg_bytes() -> bytes:
    """生成最小的合法 JPEG 文件字节。"""
    return (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xdb\x00C\x00\x03\x02\x02\x03\x02\x02\x03\x03\x03\x03\x04\x03"
        b"\x03\x04\x05\x08\x05\x05\x04\x04\x05\n\x07\x07\x06\x08\x0c\n\x0c"
        b"\x0c\x0b\n\x0b\x0b\r\x0e\x12\x10\r\x0e\x11\x0e\x0b\x0b\x10\x16"
        b"\x10\x11\x13\x14\x15\x15\x15\x0c\x0f\x17\x18\x16\x14\x18\x12\x14"
        b"\x15\x14\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
        b"\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\n\xff\xda\x00\x08\x01\x01\x00\x00?\x00T\x9f"
        b"\xff\xd9"
    )


@pytest.mark.asyncio
async def test_upload_avatar_success(app_with_auth, mock_user):
    """POST /me/avatar — 正常上传 PNG 头像。"""
    with patch("app.auth.api.auth_service.update_profile", new_callable=AsyncMock) as mock_update:
        mock_update.return_value = UserRead(
            id=mock_user.id,
            username=mock_user.username,
            avatar="/static/testuser/avatar/avatar.png",
        )

        transport = ASGITransport(app=app_with_auth)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            png_bytes = _make_png_bytes()
            response = await client.post(
                "/api/v1/users/me/avatar",
                files={"file": ("avatar.png", io.BytesIO(png_bytes), "image/png")},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert "avatar" in data["data"]
    assert data["data"]["avatar"].startswith("/static/")
    assert data["data"]["avatar"].endswith(".png")


@pytest.mark.asyncio
async def test_upload_avatar_jpg(app_with_auth, mock_user):
    """POST /me/avatar — 上传 JPG 头像。"""
    with patch("app.auth.api.auth_service.update_profile", new_callable=AsyncMock) as mock_update:
        mock_update.return_value = UserRead(
            id=mock_user.id,
            username=mock_user.username,
            avatar="/static/testuser/avatar/avatar.jpg",
        )

        transport = ASGITransport(app=app_with_auth)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            jpg_bytes = _make_jpg_bytes()
            response = await client.post(
                "/api/v1/users/me/avatar",
                files={"file": ("photo.jpg", io.BytesIO(jpg_bytes), "image/jpeg")},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200


@pytest.mark.asyncio
async def test_upload_avatar_unsupported_format(app_with_auth):
    """POST /me/avatar — 不支持的文件格式应返回 400。"""
    transport = ASGITransport(app=app_with_auth)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        svg_content = b"<svg><circle r='10'/></svg>"
        response = await client.post(
            "/api/v1/users/me/avatar",
            files={"file": ("avatar.svg", io.BytesIO(svg_content), "image/svg+xml")},
        )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_avatar_too_large(app_with_auth):
    """POST /me/avatar — 超过 2MB 的文件应返回 400。"""
    transport = ASGITransport(app=app_with_auth)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        big_content = b"x" * (2 * 1024 * 1024 + 100)
        response = await client.post(
            "/api/v1/users/me/avatar",
            files={"file": ("big.png", io.BytesIO(big_content), "image/png")},
        )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_avatar_no_auth():
    """POST /me/avatar — 未认证应返回 401。"""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        png_bytes = _make_png_bytes()
        response = await client.post(
            "/api/v1/users/me/avatar",
            files={"file": ("avatar.png", io.BytesIO(png_bytes), "image/png")},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_avatar_writes_file(app_with_auth, mock_user, tmp_path):
    """POST /me/avatar — 验证文件实际写入磁盘。"""
    with (
        patch("app.config.WORKPLACE_DIR", tmp_path),
        patch("app.auth.api.auth_service.update_profile", new_callable=AsyncMock) as mock_update,
    ):
        mock_update.return_value = UserRead(
            id=mock_user.id,
            username=mock_user.username,
            avatar="/static/testuser/avatar/avatar.png",
        )

        transport = ASGITransport(app=app_with_auth)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            png_bytes = _make_png_bytes()
            response = await client.post(
                "/api/v1/users/me/avatar",
                files={"file": ("avatar.png", io.BytesIO(png_bytes), "image/png")},
            )

    assert response.status_code == 200
    avatar_dir = user_avatar_dir("testuser")
    written_file = avatar_dir / "avatar.png"
    assert written_file.exists()
    assert written_file.read_bytes() == png_bytes


@pytest.mark.asyncio
async def test_upload_avatar_overwrites_previous(app_with_auth, mock_user, tmp_path):
    """POST /me/avatar — 同一用户再次上传应覆盖旧头像。"""
    with (
        patch("app.config.WORKPLACE_DIR", tmp_path),
        patch("app.auth.api.auth_service.update_profile", new_callable=AsyncMock) as mock_update,
    ):
        mock_update.return_value = UserRead(
            id=mock_user.id,
            username=mock_user.username,
            avatar="/static/testuser/avatar/avatar.png",
        )

        transport = ASGITransport(app=app_with_auth)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            png1 = _make_png_bytes()
            await client.post(
                "/api/v1/users/me/avatar",
                files={"file": ("avatar.png", io.BytesIO(png1), "image/png")},
            )
            png2 = _make_png_bytes() + b"\x00"
            response = await client.post(
                "/api/v1/users/me/avatar",
                files={"file": ("avatar2.png", io.BytesIO(png2), "image/png")},
            )

    assert response.status_code == 200
    avatar_dir = tmp_path / "testuser" / "avatar"
    written_file = avatar_dir / "avatar.png"
    assert written_file.exists()
    assert written_file.read_bytes() == png2
