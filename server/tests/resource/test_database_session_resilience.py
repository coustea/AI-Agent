from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest
from sqlalchemy.exc import OperationalError

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("SPARK_MAX_API_PASSWORD", "test-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


@pytest.mark.asyncio
async def test_get_session_swallows_operational_error_on_close(monkeypatch):
    from app.infra import database

    class FakeSession:
        def __init__(self, *_args, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            raise OperationalError("ROLLBACK", {}, Exception("server lost"))

    monkeypatch.setattr(database, "AsyncSession", FakeSession)

    agen = database.get_session()
    session = await agen.__anext__()

    assert isinstance(session, FakeSession)

    await agen.aclose()


def test_engine_url_is_postgresql_first() -> None:
    from app.infra import database

    url = database.engine.url.render_as_string(hide_password=False)
    assert url.startswith("postgresql+asyncpg://")
    assert database.engine.url.drivername == "postgresql+asyncpg"


@pytest.mark.asyncio
async def test_get_current_user_uses_short_lived_session(monkeypatch):
    from app.auth import security

    calls: list[str] = []

    async def fake_resolve(token: str, session):
        calls.append("get")
        return object()

    monkeypatch.setattr(security, "_resolve_current_user_from_token", fake_resolve)

    credentials = type("Creds", (), {"credentials": "token"})()

    user = await security.get_current_user(credentials, session="fake-session")

    assert user is not None
    assert calls == ["get"]


@pytest.mark.asyncio
async def test_init_db_does_not_run_standalone_source_migration(monkeypatch):
    """init_db 不再执行 generated_resources.source 列的旧迁移修复。"""
    from app.infra import database

    statements: list[str] = []

    class FakeScalarResult:
        def __init__(self, value):
            self._value = value

        def scalar(self):
            return self._value

    class FakeConn:
        def __init__(self):
            self.scalar_calls = 0

        async def execute(self, stmt):
            sql = str(stmt)
            statements.append(sql)
            return FakeScalarResult(1)

    class FakeBegin:
        async def __aenter__(self):
            return FakeConn()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeUrl:
        @staticmethod
        def render_as_string(*_args, **_kwargs):
            return "postgresql+asyncpg://test"

    class FakeEngine:
        url = FakeUrl()

        def begin(self):
            return FakeBegin()

    async def fake_test_connection():
        return True

    monkeypatch.setattr(database, "_test_connection", fake_test_connection)
    monkeypatch.setattr(database, "engine", FakeEngine())

    async def fake_import_schools(_session):
        return 0

    async def fake_import_quiz_bank(_session):
        return 0

    class FakeSession:
        def __init__(self, *_args, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(database, "AsyncSession", FakeSession)

    import app.auth.school_import as school_import_module
    import app.quiz.import_quiz as quiz_import_module

    monkeypatch.setattr(school_import_module, "import_schools", fake_import_schools)
    monkeypatch.setattr(quiz_import_module, "import_quiz_bank", fake_import_quiz_bank)

    await database.init_db()

    assert not any("information_schema.columns" in sql for sql in statements)
    assert not any("ADD COLUMN source" in sql for sql in statements)
