from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
import sys
from pathlib import Path

import jwt
import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("SPARK_MAX_API_PASSWORD", "test-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.auth import security
from app.auth import api as auth_api
from app.auth.schemas import UserLogin, UserRead, UserRegister
from app.auth import service as auth_service
from app.auth.service import AuthUseCases, UserAccountStore
from app.infra.models import ActiveToken, User


class _Result:
    def __init__(self, value):
        self._value = value

    def first(self):
        return self._value


class _FakeSession:
    def __init__(self, result=None):
        self.result = result
        self.added = []
        self.deleted = []
        self.commits = 0
        self.rolled_back = 0
        self.refreshed = []
        self.get_calls = []

    async def exec(self, *_args, **_kwargs):
        return _Result(self.result)

    def add(self, item):
        self.added.append(item)

    async def commit(self):
        self.commits += 1
        if self.added:
            latest = self.added[-1]
            if getattr(latest, "id", None) is None:
                latest.id = len(self.added)

    async def rollback(self):
        self.rolled_back += 1

    async def delete(self, item):
        self.deleted.append(item)

    async def refresh(self, item):
        self.refreshed.append(item)

    async def get(self, model, identifier):
        self.get_calls.append((model, identifier))
        if isinstance(self.result, model) and getattr(self.result, "id", None) == identifier:
            return self.result
        return None


@pytest.mark.asyncio
async def test_create_token_persists_active_token_and_uses_jwt_claims(monkeypatch):
    monkeypatch.setattr(security, "JWT_EXPIRE", 2)
    monkeypatch.setattr(security, "JWT_SECRET", "unit-test-secret-with-sufficient-length")

    session = _FakeSession()

    token = await security.create_token(7, session)

    payload = jwt.decode(token, "unit-test-secret-with-sufficient-length", algorithms=[security.JWT_ALGO])
    assert payload["sub"] == "7"
    assert len(session.added) == 1
    stored = session.added[0]
    assert isinstance(stored, ActiveToken)
    assert stored.user_id == 7
    assert stored.token == token
    assert stored.expires_at.tzinfo is not None
    assert session.commits == 1


@pytest.mark.asyncio
async def test_create_token_generates_distinct_tokens_with_same_expiry_second(monkeypatch):
    frozen_now = datetime(2026, 6, 7, 8, 30, 0, tzinfo=timezone.utc)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return frozen_now.replace(tzinfo=None)
            return frozen_now.astimezone(tz)

    monkeypatch.setattr(security, "JWT_EXPIRE", 2)
    monkeypatch.setattr(security, "JWT_SECRET", "unit-test-secret-with-sufficient-length")
    monkeypatch.setattr(security, "datetime", FrozenDateTime)

    session = _FakeSession()

    token_a = await security.create_token(7, session)
    token_b = await security.create_token(7, session)

    assert token_a != token_b
    assert session.commits == 2


@pytest.mark.asyncio
async def test_is_token_valid_rejects_expired_timezone_aware_token(monkeypatch):
    expired_utc = datetime.now(timezone.utc) - timedelta(minutes=1)
    token = ActiveToken(
        user_id=7,
        token="token",
        expires_at=expired_utc.astimezone(timezone(timedelta(hours=8))),
    )
    session = _FakeSession(token)

    valid = await security.is_token_valid("token", session)

    assert valid is False
    assert session.deleted == [token]
    assert session.commits == 1


@pytest.mark.asyncio
async def test_is_token_valid_rejects_expired_naive_token_and_cleans_it_up(monkeypatch):
    expired_naive = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
    token = ActiveToken(
        user_id=7,
        token="token",
        expires_at=expired_naive,
    )
    session = _FakeSession(token)

    valid = await security.is_token_valid("token", session)

    assert valid is False
    assert session.deleted == [token]
    assert session.commits == 1


@pytest.mark.asyncio
async def test_revoke_token_removes_active_token(monkeypatch):
    token = ActiveToken(
        user_id=7,
        token="token",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    session = _FakeSession(token)

    await security.revoke_token("token", session)

    assert session.deleted == [token]
    assert session.commits == 1


@pytest.mark.asyncio
async def test_debug_mode_does_not_bypass_missing_jwt(monkeypatch):
    monkeypatch.setattr(security, "DEBUG", True, raising=False)

    with pytest.raises(security.AuthError, match="缺少 Token"):
        await security.get_current_user(None)


@pytest.mark.asyncio
async def test_flexible_auth_validates_query_jwt_in_debug_mode(monkeypatch):
    calls: list[str] = []

    async def fake_resolve_current_user(token: str, session) -> User:
        calls.append(token)
        return User(id=7, username="alice", password="hashed")

    monkeypatch.setattr(security, "DEBUG", True, raising=False)
    monkeypatch.setattr(security, "_resolve_current_user_from_token", fake_resolve_current_user)

    user = await security.get_current_user_flexible(None, token="signed-token")

    assert user.id == 7
    assert calls == ["signed-token"]


def test_protected_bearer_dependencies_require_credentials_in_debug_mode(monkeypatch):
    monkeypatch.setattr(security, "DEBUG", True, raising=False)

    assert security.bearer_scheme.auto_error is True
    assert auth_api.bearer_scheme.auto_error is True


@pytest.mark.asyncio
async def test_user_account_store_register_and_login_round_trip(monkeypatch):
    # UserRead.created_at is str, but User.created_at is datetime;
    # patch _read_user to convert properly.
    def _patched_read_user(user):
        return UserRead(
            id=user.id,
            username=user.username,
            email=user.email,
            avatar=user.avatar,
            created_at=user.created_at.isoformat() if user.created_at else None,
            is_first_login=user.is_first_login,
        )

    monkeypatch.setattr(auth_service, "_read_user", _patched_read_user)

    store = UserAccountStore()
    session = _FakeSession()

    register_data = UserRegister(username="alice", password="password123", email="alice@example.com")
    monkeypatch.setattr(auth_service, "hash_password", lambda _password: "hashed-password")
    registered = await store.register(session, register_data)

    assert registered is not None
    assert session.added and isinstance(session.added[0], User)
    assert session.added[0].password == "hashed-password"
    assert registered["user"].username == "alice"
    assert session.commits == 1

    user = User(
        id=99,
        username="alice",
        password="hashed-password",
        email="alice@example.com",
    )
    session.result = user
    login_data = UserLogin(username="alice", password="password123")
    monkeypatch.setattr(auth_service, "verify_password", lambda plain, hashed: plain == "password123" and hashed == "hashed-password")

    async def fake_create_token(user_id, _session):
        return f"token-for-{user_id}"

    monkeypatch.setattr(auth_service, "create_token", fake_create_token)

    authenticated = await store.authenticate(session, login_data.username, login_data.password)

    assert authenticated is not None
    assert authenticated["token"] == "token-for-99"
    assert authenticated["user"].id == 99
    assert session.refreshed[-1] == user


@pytest.mark.asyncio
async def test_auth_usecases_logout_forwards_token_to_revoke(monkeypatch):
    calls: list[tuple[object, str]] = []

    async def fake_revoke_token(token: str, session):
        calls.append((session, token))

    monkeypatch.setattr(auth_service, "revoke_token", fake_revoke_token)

    usecases = AuthUseCases(UserAccountStore())
    session = _FakeSession()

    await usecases.logout(session, "logout-token")

    assert calls == [(session, "logout-token")]
