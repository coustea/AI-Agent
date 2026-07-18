"""资源生成 Agent 基类与注册表。

所有资源生成 Agent 继承 BaseResourceAgent，通过 @register_agent 装饰器
自动注册到全局 AGENT_REGISTRY 字典中，供资源工作流按 agent_id 查找调用。
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Awaitable, Sequence, TypeVar

from app.infra.logging import get_logger

logger = get_logger(__name__)

# 类型检查阶段才引入的别名，避免运行时循环依赖
if TYPE_CHECKING:
    from app.resource.event import ResourceEvents
    from app.resource.schemas import AgentResult, ResourceInput


_T = TypeVar("_T")

# 全局 Agent 注册表：按 agent_id 索引所有已注册的 Agent 类
AGENT_REGISTRY: dict[str, type[BaseResourceAgent]] = {}


def register_agent(cls: type[BaseResourceAgent]) -> type[BaseResourceAgent]:
    """装饰器：将 Agent 类注册到全局注册表，按 agent_id 索引。"""
    # 以 agent_id 为键写入注册表，供路径/资源服务按 id 查找
    AGENT_REGISTRY[cls.agent_id] = cls
    logger.info("[AgentRegistry] 注册Agent: agent_id=%s cls=%s", cls.agent_id, cls.__name__)
    return cls


class BaseResourceAgent:
    """独立资源生成 Agent 的基类。"""

    agent_id: str
    agent_name: str
    def __init__(
        self,
        emitter: ResourceEvents | None = None,
    ) -> None:
        self.emitter = emitter
        if emitter is None:
            class NoopEvents:
                def __getattr__(self, name):
                    async def noop(*args, **kwargs):
                        pass
                    return noop

            self.emitter = NoopEvents()

    async def _heartbeat_loop(
        self,
        *,
        messages: Sequence[str],
        stop_event: asyncio.Event,
        interval_seconds: float,
        progress: int | None,
        send_first: bool = True,
    ) -> None:
        """长时间任务心跳：只发送 running，不发送 completed / failed。"""
        # 没有心跳文案则直接退出，不做任何操作
        if not messages:
            return

        index = 0

        # 可选先发送首条心跳，避免 LLM 调用前长时间无反馈
        if send_first:
            try:
                await self.emitter.send(
                    self.agent_id,
                    "running",
                    messages[0],
                    progress,
                    data={
                        "phase": "heartbeat",
                        "heartbeat": True,
                    },
                )
            except Exception:
                logger.debug(
                    "Agent[%s] 首条心跳发送被忽略（频道可能已关闭）",
                    self.agent_id,
                )
            index = 1

        # 周期性发送心跳，直到任务结束或被取消
        while not stop_event.is_set():
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
                break
            except asyncio.TimeoutError:
                # 超时未结束则取出下一条循环文案继续心跳
                message = messages[index % len(messages)]
                index += 1

                try:
                    await self.emitter.send(
                        self.agent_id,
                        "running",
                        message,
                        progress,
                        data={
                            "phase": "heartbeat",
                            "heartbeat": True,
                        },
                    )
                except Exception:
                    logger.debug(
                        "Agent[%s] 心跳发送被忽略（频道可能已关闭）",
                        self.agent_id,
                    )

    async def run_with_heartbeat(
        self,
        awaitable: Awaitable[_T],
        *,
        messages: Sequence[str],
        interval_seconds: float = 12.0,
        progress: int | None = None,
        send_first: bool = True,
    ) -> _T:
        """包装长耗时 awaitable，期间定时向前端发送 running 心跳。"""
        # 用事件通知心跳任务何时停止
        stop_event = asyncio.Event()
        heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(
                messages=messages,
                stop_event=stop_event,
                interval_seconds=interval_seconds,
                progress=progress,
                send_first=send_first,
            )
        )

        try:
            # 执行实际任务，心跳在后台并发运行
            return await awaitable
        finally:
            # 任务结束，停止并取消心跳任务
            stop_event.set()
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

    # -- 子类必须实现的入口 ----------------------------------------------------

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        """多智能体资源生成入口。子类必须实现。"""
        raise NotImplementedError(f"{self.__class__.__name__}.generate_resource is required")
