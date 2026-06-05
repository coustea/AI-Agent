"""阅读智能体 — 生成拓展阅读材料。"""

from __future__ import annotations

from app.infra.llm import get_llm
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.schemas import WorkerResult, WorkerState


@register_agent
class ReadingAgent(BaseResourceAgent):
    """基于教学蓝图生成拓展阅读材料。"""

    agent_id = "reading"
    agent_name = "阅读生成"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)
        self.llm = get_llm()

    async def _execute(self, input_text: str, state: WorkerState) -> WorkerResult:
        from app.prompts import registry

        config = state.agent_config
        if config:
            cfg = ["## 阅读配置"]
            cfg.append(f"- 阅读类型: {config.get('reading_type', 'extended')}")
            cfg.append(f"- 来源风格: {config.get('source_style', 'academic')}")
            cfg.append(f"- 篇幅: {config.get('length', 'medium')}")
            input_text += f"\n\n{chr(10).join(cfg)}"
        input_text += "\n\n请生成拓展阅读材料，输出为 Markdown 格式。"

        prompt = registry.get("resource/reading")
        response = await self.llm.ainvoke(f"{prompt}\n\n{input_text}", temperature=0.3)
        content = response.content if hasattr(response, "content") else str(response)

        return WorkerResult(
            success=True,
            content=content,
            file_type="markdown",
            title=f"{state.learning_need[:32]} - 拓展阅读",
            summary="生成拓展阅读材料",
            summary_data={"reading_type": config.get("reading_type", "extended") if config else "extended"},
            metadata={"agent_id": "reading"},
        )
