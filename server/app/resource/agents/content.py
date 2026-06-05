"""内容智能体 — 生成专业课程讲解文档。"""

from __future__ import annotations

from app.infra.llm import get_llm
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.schemas import WorkerResult, WorkerState


@register_agent
class ContentAgent(BaseResourceAgent):
    """基于教学蓝图生成课程讲解文档。"""

    agent_id = "content"
    agent_name = "内容生成"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)
        self.llm = get_llm()

    async def _execute(self, input_text: str, state: WorkerState) -> WorkerResult:
        from app.prompts import registry

        config = state.agent_config
        if config:
            cfg = ["## 内容配置"]
            cfg.append(f"- 结构: {config.get('structure', 'progressive')}")
            cfg.append(f"- 深度: {config.get('depth_level', 'standard')}")
            cfg.append(f"- 关注模式: {config.get('focus_mode', 'key_concepts')}")
            cfg.append("- 包含示例和代码说明" if config.get("include_examples", True) else "- 不包含示例")
            cfg.append("- 包含常见误区和易错点" if config.get("include_common_mistakes", True) else "- 不包含常见误区")
            input_text += f"\n\n{chr(10).join(cfg)}"
        input_text += "\n\n请生成专业课程讲解文档，只输出 Markdown 内容。"

        prompt = registry.get("resource/content")
        response = await self.llm.ainvoke(f"{prompt}\n\n{input_text}", temperature=0.3)
        content = response.content if hasattr(response, "content") else str(response)
        content = _clean_markdown_fences(content)

        return WorkerResult(
            success=True,
            content=content,
            file_type="markdown",
            title=f"{state.learning_need[:32]} - 课程内容",
            summary="生成专业课程讲解文档",
            summary_data={"char_count": len(content)},
            metadata={"agent_id": "content"},
        )


def _clean_markdown_fences(content: str) -> str:
    lines = content.split("\n")
    return "\n".join(line for line in lines if line.strip() not in ("```", "```markdown", "```text"))
