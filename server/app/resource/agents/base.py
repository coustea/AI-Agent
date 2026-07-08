"""资源生成 Agent 基类与注册表。

所有资源生成 Agent 继承 BaseResourceAgent，通过 @register_agent 装饰器
自动注册到全局 AGENT_REGISTRY 字典中，供路径模块和资源服务按 agent_id 查找调用。
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any, Awaitable, Sequence, TypeVar

from app.infra.logging import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from app.resource.event import ResourceEvents
    from app.resource.schemas import AgentResult, NodeInput, ResourceInput


_T = TypeVar("_T")

AGENT_REGISTRY: dict[str, type[BaseResourceAgent]] = {}


def register_agent(cls: type[BaseResourceAgent]) -> type[BaseResourceAgent]:
    """装饰器：将 Agent 类注册到全局注册表，按 agent_id 索引。"""
    AGENT_REGISTRY[cls.agent_id] = cls
    return cls


class BaseResourceAgent:
    """资源 Agent 基类。子类必须显式实现 resource 和 node 两个入口。"""

    agent_id: str
    agent_name: str
    research_enabled: bool = True

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
        if not messages:
            return

        index = 0

        # 立即发送第一条心跳，避免 LLM 调用前长时间无消息
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

        while not stop_event.is_set():
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
                break
            except asyncio.TimeoutError:
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
            return await awaitable
        finally:
            stop_event.set()
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

    async def search(self, query: str) -> "ResearchReport":
        """通过共享 research 工具把网页研究委托给 ResearchAgent。

        Returns:
            ResearchReport: 包含 sources 列表的搜索结果报告
        """
        if not self.research_enabled:
            from app.shared.research.schemas import ResearchReport, ResearchError
            return ResearchReport(
                query=query,
                errors=[ResearchError(stage="search", code="disabled", message="联网研究已关闭")],
            )

        from app.shared.research.agent import ResearchAgent
        from app.shared.research.schemas import ResearchTask

        async def handle_research_event(event: dict[str, Any]) -> None:
            status = str(event.get("status") or "running")
            action = str(event.get("action") or "核验网页资料")
            duration = event.get("duration_ms")
            if status == "done":
                message = f"ResearchAgent：{action}已完成"
                tool_status = "completed"
            elif status == "failed":
                message = f"ResearchAgent：{action}未完成"
                tool_status = "failed"
            else:
                message = f"ResearchAgent：正在{action}..."
                tool_status = "running"
            await self.emitter.send(
                getattr(self, "agent_id", "base_resource"),
                "running",
                message,
                data={
                    "phase": "research",
                    "sub_agent": "research",
                    "action": action,
                    "tool_name": event.get("tool_name"),
                    "tool_status": tool_status,
                    "elapsed_ms": duration,
                },
            )

        started_at = time.perf_counter()
        duration = 0
        try:
            logger.info(
                "Agent[%s] 搜索开始: query=%s",
                getattr(self, "agent_id", "base"), query[:80],
            )
            await self.emitter.send(
                getattr(self, "agent_id", "base_resource"),
                "running",
                "正在委托 ResearchAgent 研究资料...",
                data={
                    "phase": "research_delegate",
                    "sub_agent": "research",
                    "tool_name": "research",
                    "tool_status": "running",
                },
            )
            report = await ResearchAgent(
                event_handler=handle_research_event,
            ).run(
                ResearchTask(
                    query=query,
                    objective="为资源生成提供准确、可引用的网页资料",
                    depth="standard",
                    sources={"web"},
                )
            )
            duration = int((time.perf_counter() - started_at) * 1000)
            await self.emitter.send(
                getattr(self, "agent_id", "base_resource"),
                "running",
                f"ResearchAgent 已完成资料研究（耗时 {duration}ms）",
                data={
                    "phase": "research_delegate",
                    "sub_agent": "research",
                    "tool_name": "research",
                    "tool_status": "completed",
                    "elapsed_ms": duration,
                },
            )
            logger.info(
                "Agent[%s] 搜索完成: sources=%d elapsed_ms=%d",
                getattr(self, "agent_id", "base"), len(report.sources), duration,
            )
            return report
        except Exception as exc:
            duration = int((time.perf_counter() - started_at) * 1000)
            logger.error(
                "Agent[%s] 搜索失败: elapsed_ms=%d error=%s",
                getattr(self, "agent_id", "base"), duration, exc, exc_info=True,
            )
            await self.emitter.send(
                getattr(self, "agent_id", "base_resource"),
                "running",
                f"ResearchAgent 研究失败: {exc}",
                data={
                    "phase": "research_delegate",
                    "sub_agent": "research",
                    "tool_name": "research",
                    "tool_status": "failed",
                },
            )
            from app.shared.research.schemas import ResearchReport, ResearchError
            return ResearchReport(
                query=query,
                errors=[ResearchError(stage="search", code="exception", message=str(exc))],
            )

    # -- 搜索结果格式化 -------------------------------------------------------

    def format_search_result(self, report: "ResearchReport", *, max_chars: int = 6000) -> str | None:
        """将 ResearchReport 格式化为供 LLM 提示词使用的文本。

        所有子类统一使用此方法处理搜索结果，避免对 ResearchReport
        做字符串操作（如 ``"搜索失败" not in report``），那会因
        Pydantic 对象不支持 ``in`` 运算而抛出 TypeError。

        Returns:
            格式化后的文本，如果搜索无有效结果则返回 None。
        """
        if not report.has_results:
            return None
        parts: list[str] = []
        for src in report.sources:
            entry = f"- {src.title}"
            if src.url:
                entry += f" ({src.url})"
            if src.summary:
                entry += f": {src.summary}"
            parts.append(entry)
        text = "\n".join(parts)
        return text[:max_chars] if text else None

    # -- 子类必须实现的入口 ----------------------------------------------------

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        """多智能体资源生成入口。子类必须实现。"""
        raise NotImplementedError(f"{self.__class__.__name__}.generate_resource is required")

    async def generate_node(self, input_data: NodeInput) -> AgentResult:
        """路径节点资源生成入口。子类必须实现。"""
        raise NotImplementedError(f"{self.__class__.__name__}.generate_node is required")
