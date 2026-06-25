"""Chat 模块独立事件流测试。

测试 ChatEvents 的核心行为：
- 精确消息回放
- 频道隔离（user_id, session_id, run_id）
- 终态事件拒绝后续消息
- SSE 编码
- 队列溢出处理
- 终态清理
"""

from __future__ import annotations

import asyncio
import time
from uuid import uuid4

import pytest

from app.chat.emitter import (
    ChatEvent,
    ChatEventClosedError,
    ChatEventNotOpenError,
    ChatEvents,
    _chat_channels,
    _chat_lock,
    encode_chat_sse,
)


def unique_run_id() -> str:
    """生成唯一的 run_id 以避免测试间状态共享。"""
    return f"run-{uuid4().hex[:8]}"


@pytest.fixture(autouse=True)
def clean_chat_channels():
    """每个测试前后清空全局频道注册表。"""
    # 同步清理 - 在测试前
    _chat_channels.clear()
    yield
    # 同步清理 - 在测试后
    _chat_channels.clear()


@pytest.mark.asyncio
async def test_chat_send_replays_exact_backend_message():
    """后端发送的消息必须原样回放，前端不补充任何文案。"""
    run_id = unique_run_id()
    events = ChatEvents(user_id=7, session_id="session-1", run_id=run_id)
    await events.open()
    await events.send(
        event="tool.running",
        message="正在检索课程知识库",
        data={"tool_name": "search_knowledge_base", "query": "Vue 生命周期"},
    )
    queue, replay = await events.subscribe(after_sequence=0)
    assert queue.empty()
    assert [(item.sequence, item.event, item.message) for item in replay] == [
        (1, "tool.running", "正在检索课程知识库"),
    ]
    assert replay[0].data["query"] == "Vue 生命周期"


@pytest.mark.asyncio
async def test_chat_channels_are_isolated_by_user_session_and_run():
    """不同 run 的频道必须完全隔离，消息不能串流。"""
    run_id_1 = unique_run_id()
    run_id_2 = unique_run_id()
    first = ChatEvents(user_id=7, session_id="session-1", run_id=run_id_1)
    second = ChatEvents(user_id=7, session_id="session-1", run_id=run_id_2)
    await first.open()
    await second.open()
    second_queue, _ = await second.subscribe()
    await first.send(event="thinking", message="分析问题", data={})
    assert second_queue.empty()
    # 第一个频道应该能收到消息
    first_queue, first_replay = await first.subscribe(after_sequence=0)
    assert len(first_replay) == 1
    assert first_replay[0].event == "thinking"


@pytest.mark.asyncio
async def test_chat_terminal_event_rejects_late_messages():
    """终态事件后，后续消息必须被拒绝。"""
    run_id = unique_run_id()
    events = ChatEvents(user_id=7, session_id="session-1", run_id=run_id)
    await events.open()
    await events.send(event="run.completed", message="回答完成", data={})
    with pytest.raises(ChatEventClosedError):
        await events.send(event="thinking", message="不应发送", data={})


@pytest.mark.asyncio
async def test_chat_send_before_open_raises_error():
    """在 open() 之前调用 send() 必须抛出明确的异常。"""
    run_id = unique_run_id()
    events = ChatEvents(user_id=7, session_id="session-1", run_id=run_id)
    with pytest.raises(ChatEventNotOpenError):
        await events.send(event="thinking", message="测试消息", data={})


@pytest.mark.asyncio
async def test_chat_sequence_strictly_monotonic():
    """sequence 必须从 1 开始严格单调递增。"""
    run_id = unique_run_id()
    events = ChatEvents(user_id=7, session_id="session-1", run_id=run_id)
    await events.open()
    event1 = await events.send(event="thinking", message="思考中", data={})
    event2 = await events.send(event="tool.running", message="执行工具", data={})
    event3 = await events.send(event="tool.completed", message="工具完成", data={})
    assert event1.sequence == 1
    assert event2.sequence == 2
    assert event3.sequence == 3


@pytest.mark.asyncio
async def test_chat_replay_after_sequence():
    """after_sequence 参数必须正确过滤回放事件。"""
    run_id = unique_run_id()
    events = ChatEvents(user_id=7, session_id="session-1", run_id=run_id)
    await events.open()
    await events.send(event="thinking", message="思考", data={})
    await events.send(event="tool.running", message="执行", data={})
    await events.send(event="tool.completed", message="完成", data={})

    # 从 sequence=1 之后开始回放，应该收到 2 和 3
    _, replay = await events.subscribe(after_sequence=1)
    assert len(replay) == 2
    assert [e.sequence for e in replay] == [2, 3]


@pytest.mark.asyncio
async def test_chat_subscriber_queue_overflow():
    """订阅者队列满时必须丢弃最旧的消息。"""
    run_id = unique_run_id()
    events = ChatEvents(user_id=7, session_id="session-1", run_id=run_id, queue_size=3)
    await events.open()
    queue, _ = await events.subscribe()

    # 发送 5 条消息，队列大小为 3
    for i in range(5):
        await events.send(event="thinking", message=f"消息 {i}", data={})

    # 队列应该只保留最新的 3 条
    assert queue.qsize() == 3
    # 最旧的消息应该是 sequence=3（丢弃了 1 和 2）
    first_in_queue = await queue.get()
    assert first_in_queue.sequence == 3


@pytest.mark.asyncio
async def test_chat_replay_buffer_overflow():
    """回放缓冲区满时必须丢弃最旧的事件。"""
    run_id = unique_run_id()
    events = ChatEvents(
        user_id=7, session_id="session-1", run_id=run_id, replay_size=5
    )
    await events.open()

    # 发送 7 条消息，回放缓冲区大小为 5
    for i in range(7):
        await events.send(event="thinking", message=f"消息 {i}", data={})

    # 新订阅者应该只能回放最新的 5 条
    _, replay = await events.subscribe(after_sequence=0)
    assert len(replay) == 5
    assert [e.sequence for e in replay] == [3, 4, 5, 6, 7]


@pytest.mark.asyncio
async def test_chat_sse_encoding():
    """SSE 编码必须符合规范：event 为 chat.event。"""
    run_id = unique_run_id()
    event = ChatEvent(
        sequence=1,
        run_id=run_id,
        session_id="session-1",
        event="tool.running",
        message="执行中",
        data={"tool": "search"},
        timestamp=1234567890.0,
    )
    sse = encode_chat_sse(event)
    assert "event: chat.event" in sse
    assert "id: 1" in sse
    assert '"event":"tool.running"' in sse
    assert '"message":"执行中"' in sse


@pytest.mark.asyncio
async def test_chat_unsubscribe_removes_queue():
    """取消订阅后队列不再接收新消息。"""
    run_id = unique_run_id()
    events = ChatEvents(user_id=7, session_id="session-1", run_id=run_id)
    await events.open()
    queue, _ = await events.subscribe()

    await events.send(event="thinking", message="第一条", data={})
    assert queue.qsize() == 1

    await events.unsubscribe(queue)
    await events.send(event="thinking", message="第二条", data={})

    # 取消订阅后队列不再增长
    assert queue.qsize() == 1


@pytest.mark.asyncio
async def test_chat_terminal_events_are_run_completed_and_failed():
    """只有 run.completed 和 run.failed 是终态事件。"""
    run_id = unique_run_id()
    events = ChatEvents(user_id=7, session_id="session-1", run_id=run_id)
    await events.open()

    # 这些不是终态
    await events.send(event="thinking", message="思考", data={})
    await events.send(event="tool.running", message="执行", data={})
    await events.send(event="tool.failed", message="失败", data={})
    await events.send(event="content.delta", message="", data={"delta": "text"})

    # 这是终态
    await events.send(event="run.completed", message="完成", data={})

    with pytest.raises(ChatEventClosedError):
        await events.send(event="thinking", message="不应发送", data={})


@pytest.mark.asyncio
async def test_chat_events_isolated_by_session():
    """不同 session 的频道必须隔离。"""
    run_id = unique_run_id()
    first = ChatEvents(user_id=7, session_id="session-1", run_id=run_id)
    second = ChatEvents(user_id=7, session_id="session-2", run_id=run_id)
    await first.open()
    await second.open()

    await first.send(event="thinking", message="会话1", data={})
    second_queue, _ = await second.subscribe()
    assert second_queue.empty()


@pytest.mark.asyncio
async def test_chat_events_isolated_by_user():
    """不同用户的频道必须隔离。"""
    run_id = unique_run_id()
    first = ChatEvents(user_id=7, session_id="session-1", run_id=run_id)
    second = ChatEvents(user_id=8, session_id="session-1", run_id=run_id)
    await first.open()
    await second.open()

    await first.send(event="thinking", message="用户7", data={})
    second_queue, _ = await second.subscribe()
    assert second_queue.empty()


@pytest.mark.asyncio
async def test_chat_multiple_subscribers():
    """一个频道可以有多个订阅者，都收到相同的消息。"""
    run_id = unique_run_id()
    events = ChatEvents(user_id=7, session_id="session-1", run_id=run_id)
    await events.open()
    queue1, _ = await events.subscribe()
    queue2, _ = await events.subscribe()

    await events.send(event="thinking", message="测试", data={})

    assert queue1.qsize() == 1
    assert queue2.qsize() == 1

    msg1 = await queue1.get()
    msg2 = await queue2.get()
    assert msg1.sequence == msg2.sequence
    assert msg1.message == msg2.message


@pytest.mark.asyncio
async def test_chat_event_fields():
    """ChatEvent 必须包含所有必需字段。"""
    run_id = unique_run_id()
    before = time.time()
    events = ChatEvents(user_id=7, session_id="session-1", run_id=run_id)
    await events.open()
    event = await events.send(
        event="tool.running",
        message="执行工具",
        data={"tool_name": "search"},
    )
    after = time.time()

    assert event.sequence == 1
    assert event.run_id == run_id
    assert event.session_id == "session-1"
    assert event.event == "tool.running"
    assert event.message == "执行工具"
    assert event.data == {"tool_name": "search"}
    assert before <= event.timestamp <= after
