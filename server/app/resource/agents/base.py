"""资源生成 Agent 基类与注册表。

所有资源生成 Agent 继承 BaseResourceAgent，通过 @register_agent 装饰器
自动注册到全局 AGENT_REGISTRY 字典中，供路径模块和资源服务按 agent_id 查找调用。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.infra.logging import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from app.resource.schemas import WorkerState, WorkerResult
    from app.resource.events import AgentEventEmitter


# 全局 Agent 注册表：agent_id → Agent 类
AGENT_REGISTRY: dict[str, type[BaseResourceAgent]] = {}


def register_agent(cls: type[BaseResourceAgent]) -> type[BaseResourceAgent]:
    """装饰器：将 Agent 类注册到全局注册表，按 agent_id 索引。"""
    AGENT_REGISTRY[cls.agent_id] = cls
    return cls


class BaseResourceAgent:
    """资源生成 Agent 基类。

    每个 Agent 可独立运行（仅需 learning_need + profile），
    也可在多智能体模式下接收 PlanningAgent 的 blueprint + instruction。
    """

    agent_id: str
    agent_name: str

    def __init__(self, emitter: AgentEventEmitter | None = None) -> None:
        # 事件发射器 — 用于向 SSE 客户端推送进度事件
        self.emitter = emitter

    async def run(self, state: WorkerState) -> WorkerResult:
        """统一入口 — 构建上下文、调用 _execute、推送进度事件。"""
        from app.resource.agents.common import build_worker_base_context

        # 推送开始事件
        if self.emitter:
            await self.emitter.emit_agent(
                self.agent_id,
                status="running",
                message=f"{self.agent_name}正在生成资源",
                progress=10,
            )

        # 构建基础上下文（学习需求 + 画像 + 蓝图 + 指令）
        parts = build_worker_base_context(state)
        input_text = "\n\n".join(parts)
        logger.info("Agent[%s] _execute 开始: input_len=%d learning_need='%.60s'", self.agent_id, len(input_text), state.learning_need)
        try:
            result = await self._execute(input_text, state)
        except Exception as exc:
            # 异常时推送失败事件
            if self.emitter:
                await self.emitter.emit_agent(
                    self.agent_id,
                    status="failed",
                    message=f"{self.agent_name}执行异常: {exc}",
                    progress=0,
                )
            raise

        # 推送完成/失败事件
        if self.emitter:
            await self.emitter.emit_agent(
                self.agent_id,
                status="finished" if result.success else "failed",
                message=result.summary if result.success else (result.error or f"{self.agent_name}生成失败"),
                progress=100 if result.success else 0,
            )
        return result

    async def _execute(self, input_text: str, state: WorkerState) -> WorkerResult:
        """子类必须实现的核心生成逻辑，返回 WorkerResult。"""
        raise NotImplementedError(f"{self.__class__.__name__} must implement _execute or override run")
