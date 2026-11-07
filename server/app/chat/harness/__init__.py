"""Chat Agent Harness — 循环 + 钩子 + 事件流。

对外只暴露 ``ChatRun``：创建运行、驱动循环、读写运行快照。
"""

from app.chat.harness.events import (
    ChatActivity,
    ChatRunEvents,
    RunArtifact,
    RunEvent,
    RunState,
    encode_chat_sse,
    has_active_run,
    load_run_state,
    mark_interrupted_runs,
)
from app.chat.harness.run import ChatRun

__all__ = [
    "ChatActivity",
    "ChatRun",
    "ChatRunEvents",
    "RunArtifact",
    "RunEvent",
    "RunState",
    "encode_chat_sse",
    "has_active_run",
    "load_run_state",
    "mark_interrupted_runs",
]
