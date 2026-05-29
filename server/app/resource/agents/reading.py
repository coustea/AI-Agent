"""
阅读智能体 — 生成学习阅读材料（教程/文档/案例）。
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
class ReadingAgent(BaseResourceAgent):
    """基于教学蓝图生成阅读材料。"""

    agent_id = "reading"
    agent_name = "阅读生成"

    def __init__(self, emitter: AgentEventEmitter | None = None):
        super().__init__(emitter=emitter)
        self.llm = get_llm()

    async def _execute(self, input_text: str, state: WorkerState) -> WorkerResult:
        await self.emitter.emit_agent("reading", status="running", message="正在准备阅读材料", progress=0)
        await self.emitter.emit_agent_action(
            "reading", "analyze", detail="正在梳理阅读要点",
            current_step=1, total_steps=3, step_label="梳理要点", progress=15,
        )

        prompt = registry.get("resource/reading")

        await self.emitter.emit_agent_action(
            "reading", "generate", detail="正在撰写阅读材料",
            current_step=2, total_steps=3, step_label="撰写材料", progress=45,
        )

        response = await self.llm.ainvoke(
            f"{prompt}\n\n{input_text}",
            temperature=0.3,
        )
        content = response.content if hasattr(response, "content") else str(response)

        await self.emitter.emit_agent_action(
            "reading", "done", detail="阅读材料生成完成",
            current_step=3, total_steps=3, step_label="生成完成", progress=100,
        )
        await self.emitter.emit_agent("reading", status="success", message="阅读材料生成完成", progress=100)
        return WorkerResult(
            success=True,
            content=content,
            file_type="markdown",
            title=f"{state.learning_need[:32]} - 阅读材料",
            summary="生成学习阅读材料",
            summary_data={
                "reading_type": state.agent_config.get("reading_type", "tutorial"),
                "char_count": len(content),
            },
            metadata={
                "engine": "reading_md",
                "reading_type": state.agent_config.get("reading_type", "tutorial"),
                "agent_id": "reading",
            },
        )

    def _build_input_override(self, state: WorkerState) -> str:
        parts = build_worker_base_context(state)
        config = state.agent_config
        if config:
            cfg_lines = ["## 阅读配置"]
            cfg_lines.append(f"- 阅读类型: {config.get('reading_type', 'tutorial')}")
            cfg_lines.append(f"- 深度: {config.get('depth', 'standard')}")
            cfg_lines.append(
                "- 包含实操示例" if config.get("include_examples", True) else "- 不包含实操示例"
            )
            parts.append("\n".join(cfg_lines))
        parts.append("请生成学习阅读材料，输出 Markdown 格式。")
        return "\n\n".join(parts)

    async def run(self, state: WorkerState) -> WorkerResult:
        input_text = self._build_input_override(state)
        return await self._execute(input_text, state)