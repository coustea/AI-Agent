"""使用隔离数据库验证聊天登记、历史恢复、权限和 HTTP/SSE 契约。"""
from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from functools import partial
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.chat import context, memory, service
from app.chat.schemas import AgentInput
from app.infra.llm import AIMessage
from app.infra.models import ChatMessage, ChatRun, ChatSession, User

Scope = Callable[[], AbstractAsyncContextManager[AsyncSession]]


@pytest_asyncio.fixture
async def db_scope(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[Scope]:
    """仅创建聊天表并替换数据库入口，不访问开发数据库。"""
    engine = create_async_engine("sqlite+aiosqlite://")
    tables = [model.__table__ for model in (User, ChatSession, ChatRun, ChatMessage)]
    async with engine.begin() as conn:
        await conn.run_sync(partial(SQLModel.metadata.create_all, tables=tables))

    @asynccontextmanager
    async def scope() -> AsyncIterator[AsyncSession]:
        """为一次服务调用创建自动提交的隔离会话。"""
        async with AsyncSession(engine, expire_on_commit=False) as db:
            try:
                yield db
                await db.commit()
            except BaseException:
                await db.rollback()
                raise

    for module in (service, memory, context):
        monkeypatch.setattr(module, "session_scope", scope)
    try:
        yield scope
    finally:
        service._active_runs.clear()
        await engine.dispose()


@pytest.mark.asyncio
async def test_history_limits_turns_and_recovers_snapshots(db_scope: Scope) -> None:
    """历史只返回窗口内轮次，已结束或失败的运行都从快照恢复。"""
    for number in range(4):
        inp = AgentInput(user_id=1, username="alice", session_id="s1", question=f"问题 {number}")
        stream = await service.prepare_chat_run(inp)
        stream.state.content = f"回答 {number}"
        stream.state = stream.result_state("completed" if number < 3 else "failed")
        await service.save_run_result(inp, stream.state, [AIMessage(f"回答 {number}")])
        service._active_runs.pop(inp.run_id)
    history = await service.get_history(user_id=1, session_id="s1", limit=4)
    assert [item.role for item in history] == ["user", "assistant", "user", "assistant"]
    assert [item.content[0]["text"] for item in history] == ["问题 2", "回答 2", "问题 3", "回答 3"]
    assert history[-1].run["status"] == "failed"
    assert await service.get_history(user_id=2, session_id="s1") == []
    async with db_scope() as db:
        session = await db.get(ChatSession, "s1")
        session.is_archived = True
        db.add(session)
    assert await service.get_history(user_id=1, session_id="s1") == []


@pytest.mark.asyncio
async def test_registration_rejects_duplicate_and_foreign_sessions(db_scope: Scope) -> None:
    """会话检查与运行登记应拒绝重复运行、越权和部分写入。"""
    await service.prepare_chat_run(AgentInput(user_id=1, username="alice", session_id="s1", question="第一轮"))
    with pytest.raises(service.RunAlreadyActive):
        await service.prepare_chat_run(AgentInput(user_id=1, username="alice", session_id="s1", question="重复"))
    with pytest.raises(PermissionError):
        await service.prepare_chat_run(AgentInput(user_id=2, username="bob", session_id="s1", question="越权"))
    async with db_scope() as db:
        assert len((await db.exec(select(ChatMessage))).all()) == 1
        assert len((await db.exec(select(ChatRun))).all()) == 1


@pytest.mark.asyncio
async def test_compression_watermark_only_covers_supplied_turns(db_scope: Scope, monkeypatch: pytest.MonkeyPatch) -> None:
    """长对话分批压缩时，摘要水位不能越过未送入模型的轮次。"""
    async with db_scope() as db:
        db.add(ChatSession(id="s1", user_id=1))
        for number in range(8):
            db.add(
                ChatMessage(
                    session_id="s1",
                    role="user" if number % 2 == 0 else "assistant",
                    content=[{"type": "text", "text": f"消息{number}:" + "文" * 4500}],
                )
            )
    captured: list[Any] = []

    async def summarize(messages: list[Any]) -> str:
        """捕获真实压缩输入并返回可保存的摘要。"""
        captured.extend(messages)
        return "摘要"

    monkeypatch.setattr(memory, "LLM", MagicMock(return_value=MagicMock(text=summarize)))
    monkeypatch.setattr(memory, "COMPRESS_KEEP_RECENT_MESSAGES", 2)
    monkeypatch.setattr(memory, "COMPRESS_MIN_MESSAGES", 2)
    summary_md = await memory.compress_session(1, "s1")
    async with db_scope() as db:
        session = await db.get(ChatSession, "s1")
        assert summary_md is not None
        assert session.last_summarized_message_id == 2
        assert "消息1:" in captured[0].content
        assert "消息2:" not in captured[0].content
    history, summary = await context.load_conversation(1, "s1")
    assert summary == "摘要"
    assert "消息2:" in history[0].content


@pytest.mark.asyncio
async def test_long_term_memory_consumes_backlog_without_skipping(
    db_scope: Scope,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """长期记忆按时间顺序分批读取，并保留未处理消息的触发计数。"""
    async with db_scope() as db:
        db.add(User(id=1, username="test", password="pwd"))
        db.add(ChatSession(id="s1", user_id=1, ltm_message_count=62))
        for number in range(62):
            db.add(
                ChatMessage(
                    session_id="s1",
                    role="user",
                    content=[{"type": "text", "text": f"消息{number}:" + "文" * 800}],
                )
            )
    update = AsyncMock(return_value=memory.MemoryUpdateOutput())
    monkeypatch.setattr(memory, "LLM", MagicMock(return_value=MagicMock(json=update)))
    await memory.update_long_term_memory(1, "s1", "我喜欢图解", "好的")
    dialogue = update.call_args.args[1]
    assert "消息0:" in dialogue and "消息59:" in dialogue
    assert "消息60:" not in dialogue
    assert "文" * 800 in dialogue
    async with db_scope() as db:
        session = await db.get(ChatSession, "s1")
        assert session.last_ltm_message_id == 60
        assert session.ltm_message_count == 2
    await memory.update_long_term_memory(1, "s1", "我喜欢图解", "好的")
    assert "消息60:" in update.call_args.args[1]
    async with db_scope() as db:
        session = await db.get(ChatSession, "s1")
        assert session.last_ltm_message_id == 62
        assert session.ltm_message_count == 0


@pytest.mark.asyncio
async def test_http_run_sse_and_history(db_scope: Scope, monkeypatch: pytest.MonkeyPatch) -> None:
    """通过实际路由验证创建、终态 SSE、历史和取消权限契约。"""
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient
    from app.auth.schemas import UserClaims
    from app.auth.security import create_token
    from app.chat.api import router
    from app.infra.llm import Message, TextDelta, TurnDone

    async def user() -> UserClaims:
        """为 HTTP 测试提供固定身份。"""
        return UserClaims(id=1, username="alice")

    async def stream(messages: list[Message], **kwargs: Any) -> AsyncIterator[Any]:
        """替代外部模型，保留完整运行和持久化流程。"""
        yield TextDelta("实际路由回答")
        yield TurnDone(text="实际路由回答")

    monkeypatch.setattr(service, "build_turn_messages", AsyncMock(return_value=[]))
    monkeypatch.setattr(service, "build_tutor_tools", MagicMock(return_value=[]))
    monkeypatch.setattr(service, "LLM", MagicMock(return_value=MagicMock(stream=stream)))
    monkeypatch.setattr(service, "generate_session_title", AsyncMock())
    monkeypatch.setattr(service, "compress_session", AsyncMock())
    monkeypatch.setattr(service, "update_long_term_memory", AsyncMock())
    monkeypatch.setattr(service, "record_dialogue_event", AsyncMock())
    from app.middleware.jwt import JWTMiddleware
    app = FastAPI()
    app.add_middleware(JWTMiddleware)
    app.include_router(router, prefix="/api/v1/ai")
    auth_headers = {"Authorization": f"Bearer {create_token(UserClaims(id=1, username='alice'))}"}
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers=auth_headers,
    ) as client:
        empty = await client.post("/api/v1/ai/chat/messages", json={"question": "  "})
        assert empty.status_code == 400
        invalid = await client.post("/api/v1/ai/chat/messages", json={"attachments": "[]"})
        assert invalid.status_code == 422
        response = await client.post("/api/v1/ai/chat/messages", json={"question": "问题", "session_id": "s1"})
        assert response.status_code == 202
        run_id = response.json()["data"]["run_id"]
        events = await client.get(f"/api/v1/ai/chat/runs/{run_id}/events")
        assert events.text.count("event: run.state") == 1
        assert '"status":"completed"' in events.text
        assert '"content":"实际路由回答"' in events.text
        history = await service.get_history(user_id=1, session_id="s1")
        assert history[-1].content[0]["text"] == "实际路由回答"


@pytest.mark.asyncio
async def test_failed_persistence_does_not_block_next_turn(db_scope: Scope) -> None:
    """数据库恢复后补写进程内失败终态，允许同一会话继续提问。"""
    first = AgentInput(user_id=1, username="alice", session_id="s1", question="问题")
    hooks = await service.prepare_chat_run(first)
    hooks.state.content = "未成功保存的回答"
    hooks.state = hooks.result_state("failed", "保存回答失败")
    second = AgentInput(user_id=1, username="alice", session_id="s1", question="继续")
    await service.prepare_chat_run(second)
    assert service.get_active_run(first.run_id) is None
    async with db_scope() as db:
        row = await db.get(ChatRun, first.run_id)
        assert row.status == "failed"
        assert row.content == "未成功保存的回答"
        assert row.error == "保存回答失败"
        assert row.finished_at is not None
        assert (await db.get(ChatRun, second.run_id)).status == "queued"


@pytest.mark.asyncio
async def test_rolling_summary_preserves_recent_tool_tokens(
    db_scope: Scope, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """滚动摘要复用前文，近期工具消息仍计入未压缩水位。"""
    async with db_scope() as db:
        db.add(ChatSession(
            id="s1",
            user_id=1,
            summary_token_count=500,
            summary_markdown="先前学习 TCP",
            last_summarized_message_id=2,
        ))
        for number in range(3, 9):
            db.add(ChatMessage(
                id=number, session_id="s1", role="user" if number % 2 else "assistant",
                content=[{"type": "text", "text": f"消息{number}"}],
            ))
        db.add(ChatMessage(id=9, session_id="s1", role="tool", tool_call_id="call-1",
                           content=[{"type": "text", "text": "工具结果" * 100}]))
    summarize = AsyncMock(return_value="```markdown\n新的滚动摘要\n```")
    monkeypatch.setattr(memory, "LLM", MagicMock(return_value=MagicMock(text=summarize)))
    monkeypatch.setattr(memory, "COMPRESS_KEEP_RECENT_MESSAGES", 2)
    monkeypatch.setattr(memory, "COMPRESS_MIN_TOKENS", 100)
    summary_md = await memory.compress_session(1, "s1")
    assert summary_md == "新的滚动摘要"
    assert "先前学习 TCP" in summarize.call_args.args[0][0].content
    async with db_scope() as db:
        session = await db.get(ChatSession, "s1")
        assert session.last_summarized_message_id == 6
        assert session.summary_markdown == "新的滚动摘要"
        expected = sum(memory.estimate_token_count(text) for text in ("消息7", "消息8", "工具结果" * 100))
        assert session.summary_token_count == expected


@pytest.mark.asyncio
async def test_memory_failure_and_cooldown_preserve_watermark(
    db_scope: Scope, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """冷却期与模型失败不推进水位；稳定偏好绕过冷却并正常写入。"""
    async with db_scope() as db:
        db.add(User(id=1, username="test", password="pwd", long_term_memory="原记忆"))
        db.add(ChatSession(id="s1", user_id=1, ltm_message_count=100))
        db.add(ChatMessage(session_id="s1", role="user",
                           content=[{"type": "text", "text": "我喜欢图解"}]))
    update = AsyncMock(side_effect=RuntimeError("模型暂不可用"))
    monkeypatch.setattr(memory, "LLM", MagicMock(return_value=MagicMock(json=update)))
    await memory.update_long_term_memory(1, "s1", "你好", "你好")
    update.assert_not_called()
    with pytest.raises(RuntimeError):
        await memory.update_long_term_memory(1, "s1", "我喜欢图解", "好的")
    async with db_scope() as db:
        assert (await db.get(ChatSession, "s1")).last_ltm_message_id is None
    update.side_effect = None
    update.return_value = memory.MemoryUpdateOutput(need_update=True, memory_markdown="偏好图解", confidence=1)
    await memory.update_long_term_memory(1, "s1", "我喜欢图解", "好的")
    async with db_scope() as db:
        assert (await db.get(ChatSession, "s1")).last_ltm_message_id == 1
        user = await db.get(User, 1)
        assert user.long_term_memory == "偏好图解"
