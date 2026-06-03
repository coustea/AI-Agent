"""代码智能体 — 生成教学示例代码。"""

from __future__ import annotations

from app.infra.llm import get_llm
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.agents.common import build_worker_base_context
from app.resource.schemas import WorkerResult, WorkerState


@register_agent
class CodeAgent(BaseResourceAgent):
    """基于教学蓝图生成代码示例和讲解。"""

    agent_id = "code"
    agent_name = "代码生成"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)
        self.llm = get_llm()

    async def _execute(self, state: WorkerState) -> WorkerResult:
        from app.prompts import registry

        parts = build_worker_base_context(state)
        config = state.agent_config
        if config:
            cfg = ["## 代码配置"]
            cfg.append(f"- 代码语言: {config.get('language', 'Python')}")
            cfg.append(f"- 复杂度: {config.get('complexity', 'basic')}")
            cfg.append(f"- 代码风格: {config.get('style', 'educational')}")
            cfg.append("- 包含详细注释" if config.get("include_comments", True) else "- 不包含注释")
            parts.append("\n".join(cfg))
        parts.append("请生成教学代码示例，包含代码注释和说明，输出为 Markdown 格式（代码块内为代码）。")

        prompt = registry.get("resource/code")
        full_input = f"{prompt}\n\n{'\n\n'.join(parts)}"
        response = await self.llm.ainvoke(full_input, temperature=0.3)
        content = response.content if hasattr(response, "content") else str(response)

        return WorkerResult(
            success=True,
            content=content,
            file_type="markdown",
            title=f"{state.learning_need[:32]} - 代码示例",
            summary="生成教学代码示例",
            summary_data={"language": config.get("language", "Python") if config else "Python"},
            metadata={"agent_id": "code"},
        )
