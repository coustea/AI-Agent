"""Agent base class and registry for resource generation agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.resource.schemas import WorkerState, WorkerResult
    from app.resource.events import AgentEventEmitter


AGENT_REGISTRY: dict[str, type[BaseResourceAgent]] = {}


def register_agent(cls: type[BaseResourceAgent]) -> type[BaseResourceAgent]:
    """Decorator to register an agent class in the global registry."""
    AGENT_REGISTRY[cls.agent_id] = cls
    return cls


class BaseResourceAgent(ABC):
    """Base class for all resource generation agents.

    Each agent can run independently with just learning_need + profile,
    or with blueprint + instruction from PlanningAgent in multi-agent mode.
    """

    agent_id: str
    agent_name: str

    def __init__(self, emitter: AgentEventEmitter | None = None) -> None:
        self.emitter = emitter

    async def run(self, state: WorkerState) -> WorkerResult:
        """Unified entry point for both single-agent and multi-agent modes."""
        from app.resource.agents.common import build_worker_base_context

        if self.emitter:
            await self.emitter.emit_agent(
                self.agent_id,
                status="running",
                message=f"{self.agent_name}正在生成资源",
                progress=10,
            )

        parts = build_worker_base_context(state)
        input_text = "\n\n".join(parts)
        try:
            result = await self._execute(input_text, state)
        except Exception as exc:
            if self.emitter:
                await self.emitter.emit_agent(
                    self.agent_id,
                    status="failed",
                    message=f"{self.agent_name}执行异常: {exc}",
                    progress=0,
                )
            raise

        if self.emitter:
            await self.emitter.emit_agent(
                self.agent_id,
                status="finished" if result.success else "failed",
                message=result.summary if result.success else (result.error or f"{self.agent_name}生成失败"),
                progress=100 if result.success else 0,
            )
        return result

    @abstractmethod
    async def _execute(self, input_text: str, state: WorkerState) -> WorkerResult:
        """Execute the agent's core logic and return WorkerResult."""
        ...
