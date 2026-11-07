"""认证安全、JWT 中间件及 AuthService 核心测试。"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("SPARK_MAX_API_PASSWORD", "test-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.auth import security
from app.auth.schemas import UserClaims, UserLogin, UserRegister, UserUpdate
from app.auth.security import (
    AuthError,
    create_token,
    decode_token,
    get_current_user,
    get_current_user_entity,
    hash_password,
    verify_password,
)
from app.auth.service import AuthService
from app.infra.models import User
from app.middleware.jwt import JWTMiddleware


def test_password_hashing():
    """密码加盐哈希及校验功能测试。"""
    pwd = "super-secure-password"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_create_and_decode_token(monkeypatch):
    """验证 JWT Token 签发包含常用信息并能准确解码为 UserClaims。"""
    monkeypatch.setattr(security, "JWT_EXPIRE", 2)
    monkeypatch.setattr(security, "JWT_SECRET", "unit-test-secret-long-enough-for-hs256")

    user = User(
        id=88,
        username="carol",
        email="carol@example.com",
        password="hashed",
        onboarding_completed=True,
    )
    token = create_token(user)
    assert isinstance(token, str)

    raw_payload = jwt.decode(
        token,
        "unit-test-secret-long-enough-for-hs256",
        algorithms=[security.JWT_ALGO],
    )
    assert raw_payload["sub"] == "88"
    assert raw_payload["id"] == 88
    assert raw_payload["username"] == "carol"
    assert raw_payload["email"] == "carol@example.com"
    assert raw_payload["onboarding_completed"] is True
    assert "exp" in raw_payload
    assert "iat" in raw_payload

    # 解码为 UserClaims 模型
    claims = decode_token(token)
    assert isinstance(claims, UserClaims)
    assert claims.id == 88
    assert claims.username == "carol"
    assert claims.email == "carol@example.com"
    assert claims.onboarding_completed is True


def test_decode_token_expired(monkeypatch):
    """过期 Token 应抛出 AuthError。"""
    monkeypatch.setattr(security, "JWT_SECRET", "unit-test-secret-long-enough-for-hs256")
    expired_payload = {
        "sub": "1",
        "id": 1,
        "username": "expired",
        "exp": int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()),
    }
    expired_token = jwt.encode(expired_payload, "unit-test-secret-long-enough-for-hs256", algorithm="HS256")

    with pytest.raises(AuthError, match="Token 已过期"):
        decode_token(expired_token)


def test_decode_token_invalid(monkeypatch):
    """被篡改或非法 Token 应抛出 AuthError。"""
    monkeypatch.setattr(security, "JWT_SECRET", "unit-test-secret-long-enough-for-hs256")
    with pytest.raises(AuthError, match="无效 Token"):
        decode_token("this.is.not.a.valid.jwt")


def test_get_current_user_from_request_state():
    """get_current_user 依赖项直接从 request.state.user 读取。"""
    mock_request = MagicMock(spec=Request)
    mock_claims = UserClaims(id=99, username="state_user")
    mock_request.state.user = mock_claims

    claims = get_current_user(mock_request)
    assert claims.id == 99
    assert claims.username == "state_user"

    # 若未登录抛出 AuthError
    mock_request.state.user = None
    with pytest.raises(AuthError, match="未登录或登录已过期"):
        get_current_user(mock_request)


@pytest.mark.asyncio
async def test_get_current_user_entity():
    """get_current_user_entity 按需从数据库加载完整 ORM 实体。"""
    claims = UserClaims(id=77, username="db_user")
    mock_session = AsyncMock()
    mock_user = User(id=77, username="db_user", password="hashed", school="Tsinghua")
    mock_session.get.return_value = mock_user

    entity = await get_current_user_entity(claims=claims, session=mock_session)
    assert entity.id == 77
    assert entity.school == "Tsinghua"
    mock_session.get.assert_called_once_with(User, 77)

    # 用户在数据库不存在时抛出 404
    mock_session.get.return_value = None
    with pytest.raises(AuthError, match="用户不存在"):
        await get_current_user_entity(claims=claims, session=mock_session)


@pytest.mark.asyncio
async def test_jwt_middleware_extracts_header_and_query(monkeypatch):
    """JWTMiddleware 能够分别从 Authorization Header 与 Query 参数中提取并注入 Claims。"""
    secret = "middleware-test-secret-long-enough"
    monkeypatch.setattr(security, "JWT_SECRET", secret)
    from app.middleware import jwt as jwt_mw
    monkeypatch.setattr(jwt_mw, "JWT_SECRET", secret)

    test_claims = UserClaims(id=101, username="mw_tester")
    valid_token = create_token(test_claims)

    app = FastAPI()
    app.add_middleware(JWTMiddleware)

    @app.get("/test-echo")
    async def echo_user(request: Request):
        user = getattr(request.state, "user", None)
        return {"user": user.model_dump() if user else None}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. 带 Authorization: Bearer Header
        res_header = await client.get("/test-echo", headers={"Authorization": f"Bearer {valid_token}"})
        assert res_header.status_code == 200
        assert res_header.json()["user"]["id"] == 101

        # 2. 带 URL Query ?token=
        res_query = await client.get(f"/test-echo?token={valid_token}")
        assert res_query.status_code == 200
        assert res_query.json()["user"]["id"] == 101

        # 3. 不带 Token
        res_none = await client.get("/test-echo")
        assert res_none.status_code == 200
        assert res_none.json()["user"] is None


@pytest.mark.asyncio
async def test_auth_service_register_and_login_flow():
    """AuthService 注册与登录完整业务逻辑测试。"""
    service = AuthService()

    class FakeSession:
        def __init__(self, existing_user=None):
            self.existing_user = existing_user
            self.added = []
            self.commits = 0

        async def exec(self, *_args, **_kwargs):
            mock_res = MagicMock()
            mock_res.first.return_value = self.existing_user
            return mock_res

        async def scalar(self, *_args, **_kwargs):
            return None

        def add(self, item):
            self.added.append(item)

        async def commit(self):
            self.commits += 1
            if self.added and getattr(self.added[-1], "id", None) is None:
                self.added[-1].id = 1

        async def refresh(self, _item):
            pass

    # 1. 注册成功
    session = FakeSession()
    reg_data = UserRegister(username="newbie", password="password123", email="newbie@example.com")
    read_user = await service.register(session, reg_data)
    assert read_user.username == "newbie"
    assert session.commits == 1

    # 2. 注册冲突（用户名重复）
    existing = User(id=2, username="existing_user", password="hashed")
    session_dup = FakeSession(existing_user=existing)
    with pytest.raises(AuthError) as exc_info:
        await service.register(session_dup, UserRegister(username="existing_user", password="password123"))
    assert exc_info.value.field == "username"
    assert exc_info.value.code == 400

    # 3. 登录成功
    hashed = hash_password("mypassword")
    user_for_login = User(id=10, username="tester", password=hashed, email="t@example.com")
    session_login = FakeSession(existing_user=user_for_login)

    login_result = await service.login(session_login, UserLogin(username="tester", password="mypassword"))
    assert "token" in login_result
    assert login_result["user"].username == "tester"
    assert login_result["user"].id == 10

    # 4. 登录失败：用户不存在
    session_no_user = FakeSession(existing_user=None)
    with pytest.raises(AuthError) as exc_no_user:
        await service.login(session_no_user, UserLogin(username="nobody", password="password"))
    assert exc_no_user.value.field == "username"
    assert exc_no_user.value.code == 401

    # 5. 登录失败：密码错误
    session_wrong_pwd = FakeSession(existing_user=user_for_login)
    with pytest.raises(AuthError) as exc_wrong_pwd:
        await service.login(session_wrong_pwd, UserLogin(username="tester", password="wrongpassword"))
    assert exc_wrong_pwd.value.field == "password"
    assert exc_wrong_pwd.value.code == 401
