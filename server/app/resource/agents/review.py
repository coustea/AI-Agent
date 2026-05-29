"""
审核智能体 — 校验各 Worker Agent 的生成结果，输出评审意见和修改建议。
"""

from __future__ import annotations

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.prompts import registry
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.agents.common import build_worker_base_context
from app.resource.events import AgentEventEmitter
from app.resource.schemas import WorkerResult, WorkerState

logger = get_logger(__name__)


@register_agent
class ReviewAgent(BaseResourceAgent):
    """审核各 Agent 生成结果，确保质量。"""

    agent_id = "review"
    agent_name = "审核"

    def __init__(self, emitter: AgentEventEmitter | None = None):
        super().__init__(emitter=emitter)
        self.llm = get_llm()

    async def _execute(self, input_text: str, state: WorkerState) -> WorkerResult:
        await self.emitter.emit_agent("review", status="running", message="正在审核生成结果", progress=0)
        await self.emitter.emit_agent_action(
            "review", "inspect", detail="正在检查内容质量",
            current_step=1, total_steps=3, step_label="检查质量", progress=20,
        )

        prompt = registry.get("resource/review")

        await self.emitter.emit_agent_action(
            "review", "evaluate", detail="正在评估与大纲一致性",
            current_step=2, total_steps=3, step_label="评估一致性", progress=60,
        )

        response = await self.llm.ainvoke(
            f"{prompt}\n\n{input_text}",
            temperature=0.2,
        )
        content = response.content if hasattr(response, "content") else str(response)

        await self.emitter.emit_agent_action(
            "review", "done", detail="审核完成",
            current_step=3, total_steps=3, step_label="审核完成", progress=100,
        )
        await self.emitter.emit_agent("review", status="success", message="审核完成", progress=100)
        return WorkerResult(
            success=True,
            content=content,
            file_type="markdown",
            title="审核意见",
            summary="审核各 Agent 生成结果",
            metadata={"agent_id": "review"},
        )

    def _build_input_override(self, state: WorkerState) -> str:
        parts = build_worker_base_context(state)

        worker_results = state.agent_config.get("worker_results", [])
        if worker_results:
            parts.append("## 待审核内容")
            for wr in worker_results:
                agent_name = wr.get("agent_name", wr.get("agent_id", "unknown"))
                parts.append(f"### {agent_name}")
                parts.append(wr.get("content", "")[:2000])
                parts.append("")

        parts.append("请审核以上内容，指出问题和修改建议。")
        return "\n\n".join(parts)

    async def run(self, state: WorkerState) -> WorkerResult:
        input_text = self._build_input_override(state)
        return await self._execute(input_text, state)