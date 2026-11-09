"""聊天循环、内存流事件、工具结果与取消行为测试。"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
import json
from pathlib import Path
import subprocess
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel

from app.chat import agent, service
from app.chat.agent import AgentResult
from app.chat.hooks import RunHooks
from app.chat.schemas import AgentInput
from app.infra.llm import AIMessage, HumanMessage, Message, TextDelta, ToolCall, ToolMessage, TurnDone
from app.shared.tools import Tool, ToolRegistry


class QueryArgs(BaseModel):
    """测试工具输入。"""

    query: str


@pytest.fixture
def stream() -> RunHooks:
    """创建纯内存运行流实例。"""
    return RunHooks("run-test")


def install_model(monkeypatch: pytest.MonkeyPatch, rounds: list[list[Any]]) -> tuple[list[list[Message]], Any]:
    """安装确定性的流式模型并捕获每次输入消息。"""
    inputs: list[list[Message]] = []

    async def _stream(messages: list[Message], **kwargs: Any) -> AsyncIterator[Any]:
        """按预设顺序返回文本和工具调用。"""
        inputs.append(list(messages))
        for item in rounds.pop(0):
            yield item

    model = MagicMock(stream=_stream)
    monkeypatch.setattr(service, "LLM", MagicMock(return_value=model))
    monkeypatch.setattr(service, "build_turn_messages", AsyncMock(return_value=[]))
    return inputs, model


async def run(stream: RunHooks, model: Any, tools: list[Tool] | None = None) -> AgentResult:
    """以固定用户上下文调用真实循环。"""
    return await agent.run_tutor_agent(
        messages=[],
        llm=model,
        registry=ToolRegistry(tools=tools or []),
        hooks=stream,
    )


@pytest.mark.asyncio
async def test_tool_ids_sequential_execution_and_final_text(
    monkeypatch: pytest.MonkeyPatch,
    stream: RunHooks,
) -> None:
    """验证缺失调用 ID 只生成一次，依赖工具顺序执行且回答不混入中间文本。"""
    inputs, model = install_model(
        monkeypatch,
        [
            [
                TextDelta("先查询"),
                TurnDone(
                    text="先查询",
                    tool_calls=(
                        ToolCall(id="", name="query_tool", args={"query": "first"}),
                        ToolCall(id="", name="query_tool", args={"query": "second"}),
                    ),
                ),
            ],
            [TextDelta("最终回答"), TurnDone(text="最终回答")],
        ],
    )
    executed: list[str] = []

    async def search(query: str) -> dict[str, Any]:
        """通过主动让出执行权检查工具是否按调用顺序完成。"""
        if query == "second":
            assert executed == ["first"]
        await asyncio.sleep(0)
        executed.append(query)
        return {"text": query, "sources": [{"source": "mock", "title": query}]}

    tools = [Tool("query_tool", "查询", QueryArgs, search)]
    queue = stream.subscribe()
    result = await run(stream, model, tools)
    assert result.answer == "最终回答"
    stream.state = stream.result_state("completed")
    stream.publish()

    assert stream.state.content == "最终回答"
    assert executed == ["first", "second"]
    request = next(m for m in inputs[1] if m.role == "assistant")
    replies = [m for m in inputs[1] if m.role == "tool"]
    assert len({c.id for c in request.tool_calls}) == 2
    assert [c.id for c in request.tool_calls] == [m.tool_call_id for m in replies]

    # 验证返回的 new_messages 包含完整配对的 assistant 与 tool 消息
    ai_msgs = [m for m in result.new_messages if m.role == "assistant"]
    tool_msgs = [m for m in result.new_messages if m.role == "tool"]
    assert [c.id for c in ai_msgs[0].tool_calls] == [m.tool_call_id for m in tool_msgs]
    assert all(step.status == "completed" for step in stream.state.steps)
    assert len(stream.state.sources) == 2

    assert queue.qsize() == 1
    snapshot = stream.snapshot().model_dump()
    root = Path(__file__).resolve().parents[3]
    script = """
const fs = require('node:fs')
const ts = require('typescript')
const assert = require('node:assert/strict')
function load(file, imports) {
  const source = fs.readFileSync(file, 'utf8')
  const output = ts.transpileModule(source, {compilerOptions: {module: ts.ModuleKind.CommonJS}})
  const exports = {}
  new Function('exports', 'require', output.outputText)(exports, name => imports[name])
  return exports
}
const types = load('src/features/chat/types/chatRun.ts', {})
const connections = []
class EventSource {
  static CLOSED = 2
  constructor(url) { this.url = url; this.readyState = 1; connections.push(this) }
  addEventListener(name, handler) { assert.equal(name, 'run.state'); this.receive = handler }
  close() { this.readyState = 2 }
}
global.EventSource = EventSource
const api = { cancelChatRun: async () => {}, createChatMessage: async () => {} }
const { useChatRun } = load('src/features/chat/composables/useChatRun.ts', {
  vue: require('vue'),
  '@/features/chat/api/chat': api,
  '@/shared/auth/token': { getAuthToken: () => 'test-token' },
  '@/features/chat/types/chatRun': types,
})
const snapshot = JSON.parse(fs.readFileSync(0, 'utf8'))
const chat = useChatRun()
const rendered = []
chat.connect(types.emptyRun(snapshot.run_id), state => rendered.push(state))
const first = connections[0]
first.onerror()
assert.equal(chat.connection.value, 'reconnecting')
// Reconnect replaces the displayed snapshot without event replay.
first.receive({data: JSON.stringify(snapshot)})
assert.equal(chat.connection.value, 'closed')
assert.equal(first.readyState, EventSource.CLOSED)
assert.deepEqual(rendered.at(-1).content, snapshot.content)
chat.connect(types.emptyRun('other-run'), state => rendered.push(state))
first.receive({data: JSON.stringify(snapshot)})
assert.equal(rendered.at(-1).run_id, 'other-run')
const second = connections[1]
second.readyState = EventSource.CLOSED
second.onerror()
assert.equal(chat.connection.value, 'closed')
chat.close()
process.stdout.write(JSON.stringify(rendered[1]))
"""
    proc = subprocess.run(
        ["rtk", "proxy", "node", "-e", script],
        cwd=root,
        input=json.dumps(snapshot),
        text=True,
        capture_output=True,
        check=True,
    )
    rendered = json.loads(proc.stdout)
    assert rendered["content"] == snapshot["content"]
    assert rendered["status"] == snapshot["status"]
    assert rendered["steps"] == snapshot["steps"]


@pytest.mark.asyncio
async def test_failed_command_is_visible(stream: RunHooks) -> None:
    """非零命令退出码应显示失败步骤。"""
    call = ToolCall(id="bash-1", name="bash", args={"command": "false"})
    stream.on_tool_start(call)
    stream.on_tool_end(call, {"exit_code": 1, "stderr": "failed"}, "failed")
    assert stream.state.steps[0].status == "failed"
    assert stream.state.steps[0].error == "failed"


@pytest.mark.asyncio
async def test_repeated_subagents_keep_separate_progress(stream: RunHooks) -> None:
    """同名子智能体的不同调用分别保存进度和产物。"""
    for number in (1, 2):
        call = ToolCall(id=str(number), name="generate_ppt_deck", args={})
        stream.on_tool_start(call)
        await stream.on_subagent_progress(call.name, f"生成第 {number} 份")
        stream.on_tool_end(call, {"pptx_url": f"/static/{number}.pptx"}, "完成")
    assert [s.sub_steps[0].title for s in stream.state.steps] == ["生成第 1 份", "生成第 2 份"]
    assert len(stream.state.artifacts) == 2


@pytest.mark.asyncio
async def test_slow_subscriber_receives_final_snapshot(stream: RunHooks) -> None:
    """订阅队列溢出后仍能恢复完整文本和终态。"""
    queue = stream.subscribe()
    for _ in range(512):
        stream.on_text("a")
    stream.state = stream.result_state("completed")
    stream.publish()
    assert queue.qsize() == 1
    snapshot = stream.snapshot()
    assert snapshot.status == "completed"
    assert snapshot.content == "a" * 512


@pytest.mark.asyncio
async def test_cancel_interrupts_waiting_tool(
    monkeypatch: pytest.MonkeyPatch,
    stream: RunHooks,
) -> None:
    """取消运行应立即中断挂起工具并清理运行注册。"""
    entered = asyncio.Event()
    cleaned = asyncio.Event()
    install_model(
        monkeypatch,
        [[TurnDone(text="", tool_calls=(ToolCall(id="c", name="slow", args={"query": "q"}),))]],
    )

    async def slow(query: str) -> str:
        """模拟可取消的长任务。"""
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            cleaned.set()
        return ""

    monkeypatch.setattr(
        service,
        "build_tutor_tools",
        MagicMock(return_value=[Tool("slow", "等待", QueryArgs, slow)]),
    )
    monkeypatch.setattr(service, "save_run_result", AsyncMock())
    monkeypatch.setattr(service, "get_run_state", AsyncMock(return_value=stream.state))
    service._active_runs[stream.state.run_id] = stream
    inp = AgentInput(
        run_id=stream.state.run_id,
        user_id=1,
        username="alice",
        session_id="session-test",
        user_message_id=1,
        question="测试",
        is_first_turn=False,
    )
    task = asyncio.create_task(service.execute_chat_run(inp))
    try:
        await asyncio.wait_for(entered.wait(), timeout=2)
        assert await service.cancel_run(1, stream.state.run_id) == "cancelling"
        assert await service.cancel_run(1, stream.state.run_id) == "cancelling"
        await asyncio.wait_for(task, timeout=2)
        assert cleaned.is_set()
        assert stream.state.status == "cancelled"
        assert service.get_active_run(stream.state.run_id) is None
    finally:
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        service._active_runs.pop(stream.state.run_id, None)


@pytest.mark.asyncio
async def test_empty_answer_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    stream: RunHooks,
) -> None:
    """模型空响应不能被标记为成功回答。"""
    _, model = install_model(monkeypatch, [[TurnDone(text="")]])
    with pytest.raises(RuntimeError, match="未生成回答"):
        await run(stream, model)


@pytest.mark.asyncio
async def test_agent_does_not_mutate_input_messages(
    monkeypatch: pytest.MonkeyPatch,
    stream: RunHooks,
) -> None:
    """循环内部追加工具消息不能污染调用方提供的上下文。"""
    _, model = install_model(
        monkeypatch,
        [
            [TurnDone(text="", tool_calls=(ToolCall(id="c", name="lookup", args={"query": "q"}),))],
            [TurnDone(text="完成")],
        ],
    )

    async def lookup(query: str) -> str:
        """返回一次查询结果。"""
        return query

    messages = [HumanMessage("原始问题")]
    result = await agent.run_tutor_agent(
        messages=messages,
        llm=model,
        registry=ToolRegistry(tools=[Tool("lookup", "查询", QueryArgs, lookup)]),
        hooks=stream,
    )
    assert result.answer == "完成"
    assert [message.content for message in messages] == ["原始问题"]


@pytest.mark.asyncio
async def test_checkpoint_failure_finishes_with_error(
    monkeypatch: pytest.MonkeyPatch,
    stream: RunHooks,
) -> None:
    """终态保存失败也应结束事件流，并明确报告失败。"""
    _, model = install_model(monkeypatch, [[TurnDone(text="正常回答")]])
    monkeypatch.setattr(service, "build_tutor_tools", MagicMock(return_value=[]))
    monkeypatch.setattr(
        service,
        "save_run_result",
        AsyncMock(side_effect=RuntimeError("数据库不可用")),
    )
    service._active_runs[stream.state.run_id] = stream
    queue = stream.subscribe()
    inp = AgentInput(
        run_id=stream.state.run_id,
        user_id=1,
        username="alice",
        session_id="session-test",
        user_message_id=1,
        question="测试",
        is_first_turn=False,
    )
    await service.execute_chat_run(inp)
    assert queue.qsize() == 1
    assert stream.state.status == "failed"
    assert "数据库不可用" in stream.state.error
    assert service.get_active_run(stream.state.run_id).snapshot().status == "failed"
    service._active_runs.pop(stream.state.run_id)


def test_incomplete_tool_history_keeps_only_paired_results() -> None:
    """中途取消留下的未完成工具调用不能污染下一轮模型上下文。"""
    from app.chat.context import sanitize_tool_message_chain

    messages = [
        AIMessage(
            "准备",
            tool_calls=[
                ToolCall(id="one", name="read", args={}),
                ToolCall(id="two", name="read", args={}),
            ],
        ),
        ToolMessage("已完成", tool_call_id="one"),
        HumanMessage("下一轮"),
        ToolMessage("迟到的结果", tool_call_id="two"),
    ]
    cleaned = sanitize_tool_message_chain(messages)
    assert [message.role for message in cleaned] == ["assistant", "tool", "user"]
    assert [call.id for call in cleaned[0].tool_calls] == ["one"]


def test_model_step_remains_running_while_streaming(stream: RunHooks) -> None:
    """首段文本不代表模型调用完成，完成状态必须等待响应结束。"""
    stream.on_model_start(1)
    before = stream.snapshot()
    stream.on_text("部分输出")
    assert stream.state.phase == "streaming"
    assert stream.state.steps[0].status == "running"
    assert before.content == "" and before.phase == "waiting_model"
    stream.on_model_end(AIMessage("完整输出"))
    assert stream.state.steps[0].status == "completed"
    assert stream.state.content == "完整输出"


@pytest.mark.asyncio
async def test_sse_reconnect_and_disconnect(
    monkeypatch: pytest.MonkeyPatch,
    stream: RunHooks,
) -> None:
    """真实 SSE 生成器合并更新、恢复快照，并在断开和终态时释放订阅。"""
    from app.auth.schemas import UserClaims
    from app.chat import api

    monkeypatch.setattr(api, "get_run_state", AsyncMock(return_value=stream.state))
    monkeypatch.setattr(api, "get_active_run", MagicMock(return_value=stream))
    monkeypatch.setattr(api, "get_current_user", lambda: UserClaims(id=1, username="alice"))
    response = await api.stream_chat_run_events(stream.state.run_id)
    events = response.body_iterator
    first = await anext(events)
    assert '"status":"queued"' in first
    stream.on_model_start(1)
    for _ in range(100):
        stream.on_text("a")
    update = await anext(events)
    assert '"content":"' + "a" * 100 + '"' in update
    assert len(stream._subscribers) == 1
    await events.aclose()
    assert not stream._subscribers

    response = await api.stream_chat_run_events(stream.state.run_id)
    events = response.body_iterator
    assert '"content":"' + "a" * 100 + '"' in await anext(events)
    stream.state = stream.result_state("cancelled")
    stream.publish()
    assert '"status":"cancelled"' in await anext(events)
    with pytest.raises(StopAsyncIteration):
        await anext(events)
    assert not stream._subscribers


@pytest.mark.asyncio
async def test_terminal_state_waits_for_save(
    monkeypatch: pytest.MonkeyPatch,
    stream: RunHooks,
) -> None:
    """保存期间仍为 running，重复取消不得打断提交，提交完成后才发布终态。"""
    install_model(monkeypatch, [[TurnDone(text="已生成")]])
    monkeypatch.setattr(service, "build_tutor_tools", MagicMock(return_value=[]))
    monkeypatch.setattr(service, "compress_session", AsyncMock())
    monkeypatch.setattr(service, "update_long_term_memory", AsyncMock())
    monkeypatch.setattr(service, "record_dialogue_event", AsyncMock())
    monkeypatch.setattr(service, "get_run_state", AsyncMock(return_value=stream.state))
    saving = asyncio.Event()
    release = asyncio.Event()

    async def save(*args: Any) -> None:
        """在提交前暂停，以验证可见状态。"""
        saving.set()
        await release.wait()

    monkeypatch.setattr(service, "save_run_result", save)
    service._active_runs[stream.state.run_id] = stream
    inp = AgentInput(user_id=1, username="alice", run_id=stream.state.run_id)
    task = asyncio.create_task(service.execute_chat_run(inp))
    try:
        await asyncio.wait_for(saving.wait(), timeout=2)
        assert stream.snapshot().status == "running"
        assert stream.snapshot().phase == "saving"
        assert await service.cancel_run(1, inp.run_id) == "saving"
        assert not task.cancelling()
        release.set()
        await asyncio.wait_for(task, timeout=2)
        assert stream.state.status == "completed"
        assert service.get_active_run(inp.run_id) is None
    finally:
        release.set()
        await task
        service._active_runs.pop(inp.run_id, None)


@pytest.mark.asyncio
async def test_cancel_before_execution(
    monkeypatch: pytest.MonkeyPatch,
    stream: RunHooks,
) -> None:
    """任务启动前收到取消时仍保存终态，且不会准备上下文或调用模型。"""
    prepare = AsyncMock()
    save = AsyncMock()
    monkeypatch.setattr(service, "build_turn_messages", prepare)
    monkeypatch.setattr(service, "save_run_result", save)
    monkeypatch.setattr(service, "get_run_state", AsyncMock(return_value=stream.state))
    service._active_runs[stream.state.run_id] = stream
    inp = AgentInput(user_id=1, username="alice", run_id=stream.state.run_id)
    assert await service.cancel_run(1, inp.run_id) == "cancelling"
    assert stream.state.status == "running"
    await service.execute_chat_run(inp)
    prepare.assert_not_awaited()
    save.assert_awaited_once()
    assert stream.state.status == "cancelled"
    assert service.get_active_run(inp.run_id) is None
