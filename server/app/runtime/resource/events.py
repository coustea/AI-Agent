"""
SSE 事件发射器：子智能体通过此工具向前端推送实时状态。
"""

import asyncio
import json
from typing import AsyncGenerator


class AgentEventEmitter:
    """基于 asyncio.Queue 的 SSE 事件发射器。

    后端各节点通过 emit() 推送事件，路由层通过 stream() 消费并转发给前端。
    """

    def __init__(self):
        self._queue: asyncio.Queue[dict | None] = asyncio.Queue()

    async def emit(self, event_type: str, **kwargs) -> None:
        """推送一个事件。"""
        payload = {"type": event_type, **kwargs}
        await self._queue.put(payload)

    async def emit_coordinator(self, status: str, msg: str) -> None:
        await self.emit("coordinator", status=status, msg=msg)

    async def emit_agent_start(self, agent_id: str) -> None:
        await self.emit("agent_start", id=agent_id)

    async def emit_agent_log(self, agent_id: str, log: str) -> None:
        await self.emit("agent_log", id=agent_id, log=log)

    async def emit_agent_done(self, agent_id: str, data: dict | None = None) -> None:
        await self.emit("agent_done", id=agent_id, data=data or {})

    async def emit_agent_error(self, agent_id: str, error: str) -> None:
        await self.emit("agent_error", id=agent_id, error=error)

    async def emit_done(self, message: str = "资源包构建完成") -> None:
        await self.emit("done", message=message)

    async def stream(self) -> AsyncGenerator[str, None]:
        """以 SSE 格式持续输出事件，直到收到 done 信号。"""
        while True:
            event = await self._queue.get()
            if event is None:
                break
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            if event.get("type") == "done":
                break