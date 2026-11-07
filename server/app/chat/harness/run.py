"""ChatRun — 装配循环、钩子与事件流，对外只暴露 run()/cancel()。

这里是唯一知道「一轮对话由哪些部分组成」的地方：
创建运行行 → 打开事件流 → 注册钩子 → 构建上下文 → 驱动循环 → 收尾。
"""

from __future__ import annotations

from typing import Any

from app.chat.harness.events import ChatRunEvents, RunState, load_run_state
from app.chat.harness.handlers import ChatRunHandlers, RunContext
from app.chat.harness.hooks import HookBus
from app.chat.harness.loop import AgentLoop, RunCancelled
from app.chat.tools import build_tutor_tools
from app.infra.database import session_scope
from app.infra.llm import LLM
from app.infra.logging import get_logger
from app.infra.models import ChatRun as ChatRunRow
from app.shared.tools import ToolRegistry

logger = get_logger(__name__)

# 进程内活跃运行表，供取消接口在循环检查点打断
_active_runs: dict[str, "ChatRun"] = {}


class ChatRun:
    """一次对话运行的装配与生命周期管理。"""

    def __init__(self, ctx: RunContext) -> None:
        """绑定运行上下文并初始化事件发布器。"""
        self.ctx = ctx
        self.events = ChatRunEvents(ctx.run_id)
        self.handlers = ChatRunHandlers(ctx, self.events)
        self._loop: AgentLoop | None = None

    @classmethod
    async def reserve(
        cls,
        *,
        run_id: str,
        user_id: int,
        session_id: str,
        user_message_id: int,
    ) -> None:
        """登记运行行，保证前端拿到 run_id 后能立即订阅事件。"""
        async with session_scope() as db:
            db.add(
                ChatRunRow(
                    id=run_id,
                    session_id=session_id,
                    user_id=user_id,
                    user_message_id=user_message_id,
                    status="queued",
                )
            )
            await db.commit()

    @classmethod
    def build(
        cls,
        *,
        run_id: str,
        user_id: int,
        username: str,
        session_id: str,
        user_message_id: int,
        question: str,
        attachments: list[str] | None = None,
        diagram_mode: str = "auto",
        video_mode: bool = False,
        session_summary: str = "",
        history: list[Any] | None = None,
    ) -> "ChatRun":
        """按已登记的 run_id 装配运行对象（不写库）。"""
        return cls(
            RunContext(
                run_id=run_id,
                user_id=user_id,
                username=username,
                session_id=session_id,
                user_message_id=user_message_id,
                question=question,
                attachments=list(attachments or []),
                diagram_mode=diagram_mode,
                video_mode=video_mode,
                session_summary=session_summary,
                history=list(history or []),
            )
        )

    async def run(self) -> RunState:
        """执行一次运行，返回最终快照；任何异常都收敛为终态事件。"""
        bus = HookBus()
        self.handlers.bind(bus)
        _active_runs[self.ctx.run_id] = self
        try:
            messages = await self.handlers.prepare()
            tools = build_tutor_tools(
                user_id=self.ctx.user_id,
                username=self.ctx.username,
                session_id=self.ctx.session_id,
            )
            registry = ToolRegistry(tools=tools) if tools else None
            loop = AgentLoop(
                llm=LLM(provider="text", temperature=0.7, max_tokens=8192),
                messages=messages,
                registry=registry,
                hooks=bus,
            )
            self._loop = loop
            await bus.trigger("run_started")
            answer = await loop.run()
            await bus.trigger("run_finished", answer)
            return await self.state()
        except RunCancelled:
            await self._fail("run.cancelled", "运行已取消")
            return await self.state()
        except Exception as exc:
            logger.exception("[ChatRun] 运行失败: run_id=%s", self.ctx.run_id)
            await self._fail("run.failed", str(exc))
            return await self.state()
        finally:
            _active_runs.pop(self.ctx.run_id, None)

    async def _fail(self, event: str, message: str) -> None:
        """发布终态失败事件并标记运行结束。"""
        try:
            await self.events.emit(event, {"error": message})  # type: ignore[arg-type]
        except Exception:
            logger.exception("[ChatRun] 发布失败事件异常: run_id=%s", self.ctx.run_id)

    @classmethod
    def request_cancel(cls, run_id: str) -> bool:
        """请求取消运行；返回是否有活跃实例被通知。"""
        active = _active_runs.get(run_id)
        if active is None:
            return False
        active.events.request_cancel()
        if active._loop is not None:
            active._loop.cancelled = True
        return True

    async def state(self) -> RunState:
        """读取当前运行快照。"""
        state = await load_run_state(self.ctx.run_id)
        return state or RunState(run_id=self.ctx.run_id)


__all__ = ["ChatRun"]
