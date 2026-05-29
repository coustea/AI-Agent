"""
内容智能体 — 生成专业课程讲解文档。
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
class ContentAgent(BaseResourceAgent):
    """基于教学蓝图生成课程讲解文档。"""

    agent_id = "content"
    agent_name = "内容生成"

    def __init__(self, emitter: AgentEventEmitter | None = None):
        super().__init__(emitter=emitter)
        self.llm = get_llm()

    async def _execute(self, input_text: str, state: WorkerState) -> WorkerResult:
        await self.emitter.emit_agent("content", status="running", message="正在准备课程讲解", progress=0)
        await self.emitter.emit_agent_action(
            "content", "prepare", detail="正在梳理核心概念",
            current_step=1, total_steps=4, step_label="梳理概念", progress=15,
        )

        prompt = registry.get("resource/content")
        full_input = f"{prompt}\n\n{input_text}"

        await self.emitter.emit_agent_action(
            "content", "generate", detail="正在编写知识讲解",
            current_step=2, total_steps=4, step_label="编写讲解", progress=35,
        )

        response = await self.llm.ainvoke(
            full_input,
            temperature=0.3,
        )

        await self.emitter.emit_agent_action(
            "content", "refine", detail="正在补充易错点解析",
            current_step=3, total_steps=4, step_label="补充解析", progress=70,
        )

        content = response.content if hasattr(response, "content") else str(response)
        content = self._clean_content(content)

        await self.emitter.emit_agent_action(
            "content", "done", detail="讲解文档生成完成",
            current_step=4, total_steps=4, step_label="生成完成", progress=100,
        )
        await self.emitter.emit_agent("content", status="success", message="课程讲解生成完成", progress=100)
        return WorkerResult(
            success=True,
            content=content,
            file_type="markdown",
            title=f"{state.learning_need[:32]} - 课程内容",
            summary="生成专业课程讲解文档",
            summary_data={"char_count": len(content)},
            metadata={"agent_id": "content"},
        )

    def _build_input_override(self, state: WorkerState) -> str:
        """Content-specific input building with config."""
        parts = build_worker_base_context(state)

        config = state.agent_config
        if config:
            cfg_lines = ["## 内容配置"]
            cfg_lines.append(f"- 结构: {config.get('structure', 'progressive')}")
            cfg_lines.append(f"- 深度: {config.get('depth_level', 'standard')}")
            cfg_lines.append(f"- 关注模式: {config.get('focus_mode', 'key_concepts')}")
            cfg_lines.append(
                "- 包含示例和代码说明" if config.get("include_examples", True) else "- 不包含示例"
            )
            cfg_lines.append(
                "- 包含常见误区和易错点" if config.get("include_common_mistakes", True) else "- 不包含常见误区"
            )
            parts.append("\n".join(cfg_lines))

        parts.append("请生成专业课程讲解文档，只输出 Markdown 内容。")
        return "\n\n".join(parts)

    async def run(self, state: WorkerState) -> WorkerResult:
        """Override run() to use content-specific input building."""
        input_text = self._build_input_override(state)
        return await self._execute(input_text, state)

    def _clean_content(self, content: str) -> str:
        """清理内容中的常见问题。"""
        lines = content.split("\n")
        cleaned = []
        for line in lines:
            stripped = line.strip()
            if stripped in ("```", "```markdown", "```text"):
                continue
            cleaned.append(line)
        return "\n".join(cleaned)