"""纯 Agent 循环 — 只有「请求模型 → 派发工具 → 追加消息」。

循环体内不做任何持久化、不构造事件、不收集产物；这些都在 ``handlers.py``
注册的钩子里完成，因此循环本身可以脱离数据库与 SSE 单独测试。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from app.chat.harness.hooks import HookBus
from app.infra.llm import (
    AIMessage,
    LLM,
    Message,
    TextDelta,
    ToolCall,
    ToolMessage,
    TurnDone,
)
from app.infra.logging import get_logger
from app.shared.tools import ToolRegistry

logger = get_logger(__name__)


class RunCancelled(Exception):
    """协作式取消：循环在检查点抛出，由运行层收敛为 run.cancelled。"""


@dataclass(slots=True)
class ToolResult:
    """单个工具调用的执行结果。"""

    call_id: str
    name: str
    args: dict[str, Any]
    text: str
    status: str
    raw: Any = None


class AgentLoop:
    """驱动一次 ReAct 循环的最小内核。"""

    def __init__(
        self,
        *,
        llm: LLM,
        messages: list[Message],
        registry: ToolRegistry | None,
        hooks: HookBus,
        max_steps: int = 8,
        max_tool_rounds: int = 6,
        timeout_s: float = 300.0,
    ) -> None:
        """装配循环所需的模型、消息、工具与钩子。"""
        self.llm = llm
        self.messages = messages
        self.registry = registry
        self.hooks = hooks
        self.max_steps = max_steps
        self.max_tool_rounds = max_tool_rounds
        self.timeout_s = timeout_s
        self._tool_schemas = registry.openai_schemas() if registry else None
        self.tool_rounds = 0
        self.cancelled = False

    async def run(self) -> str:
        """执行循环并返回最终回答文本。"""
        try:
            async with asyncio.timeout(self.timeout_s):
                return await self._iterate()
        except TimeoutError:
            raise RuntimeError(f"运行超时 (>{self.timeout_s}s)") from None

    async def _iterate(self) -> str:
        """逐轮推理，直到模型不再请求工具。"""
        for step in range(1, self.max_steps + 1):
            self._raise_if_cancelled()
            await self.hooks.trigger("step_started", step)
            done = await self._stream_turn(step)
            if not done.tool_calls:
                await self.hooks.trigger("turn_finished", done.text)
                return done.text
            await self._run_tools(done)
        raise RuntimeError(f"超过最大推理步数 ({self.max_steps})")

    async def _stream_turn(self, step: int) -> TurnDone:
        """流式请求一次模型输出，增量文本直接交给钩子。"""
        force_final = self.tool_rounds >= self.max_tool_rounds
        done: TurnDone | None = None
        async for item in self.llm.stream(
            self.messages,
            tools=None if force_final else self._tool_schemas,
            tool_choice="none" if force_final else None,
        ):
            if self.cancelled:
                raise RunCancelled("用户取消运行")
            if isinstance(item, TextDelta):
                await self.hooks.trigger("text_delta", item.text)
            elif isinstance(item, TurnDone):
                done = item
        if done is None:
            raise RuntimeError("模型流式输出异常中断（未收到 TurnDone）")
        return done

    async def _run_tools(self, done: TurnDone) -> None:
        """执行本轮全部工具调用，并把结果按调用顺序追加回消息链。"""
        calls = [
            (call.id or f"call-{uuid4().hex}", call)
            for call in (done.tool_calls or ())
        ]
        normalized = [
            (call_id, ToolCall(id=call_id, name=call.name, args=dict(call.args or {}), raw_arguments=call.raw_arguments))
            for call_id, call in calls
        ]
        self.messages.append(
            AIMessage(done.text, tool_calls=[call for _, call in normalized])
        )
        await self.hooks.trigger("tools_started", normalized)
        results = await asyncio.gather(
            *(self._execute(call_id, call) for call_id, call in normalized)
        )
        for result in results:
            await self.hooks.trigger("tool_finished", result)
            self.messages.append(
                ToolMessage(result.text or f"[{result.name} 无输出]", tool_call_id=result.call_id)
            )
        self.tool_rounds += 1

    async def _execute(self, call_id: str, call: ToolCall) -> ToolResult:
        """执行单个工具调用；异常收敛为失败结果而不抛出。"""
        self._raise_if_cancelled()
        if self.registry is None:
            return ToolResult(call_id, call.name, dict(call.args or {}), f"工具不可用: {call.name}", "failed")
        try:
            raw = await self.registry.execute(call.name, dict(call.args or {}))
            return ToolResult(call_id, call.name, dict(call.args or {}), _as_text(raw), "ok", raw)
        except Exception as exc:
            logger.warning("[AgentLoop] 工具 %s 执行失败: %s", call.name, exc)
            return ToolResult(
                call_id, call.name, dict(call.args or {}), f"工具执行失败: {exc}", "failed"
            )

    def _raise_if_cancelled(self) -> None:
        """在循环检查点响应取消请求。"""
        if self.cancelled:
            raise RunCancelled("用户取消运行")


def _as_text(raw: Any) -> str:
    """把工具返回值压成纯文本，供消息链与前端共用。"""
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        for key in ("text", "message", "content"):
            value = raw.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return str(raw)


__all__ = ["AgentLoop", "RunCancelled", "ToolResult"]
