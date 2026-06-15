"""内容智能体 — 基于教学蓝图生成专业课程讲解文档。"""

from __future__ import annotations

from app.config import INFERENCE_TEMPERATURE
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.infra.prompts import prompts
from app.resource.schemas import WorkerResult, WorkerState

logger = get_logger(__name__)


@register_agent
class ContentAgent(BaseResourceAgent):
    """基于教学蓝图生成课程讲解文档（Markdown 格式）。"""

    agent_id = "content"
    agent_name = "内容生成"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)
        self.llm = get_llm()

    async def _execute(self, input_text: str, state: WorkerState) -> WorkerResult:
        """核心生成逻辑：拼接配置 → 调用 LLM → 清洗 Markdown 格式。"""
        config = state.agent_config
        # 将用户配置（结构、深度、关注模式等）拼接到 prompt 中
        if config:
            cfg = ["## 内容配置"]
            cfg.append(f"- 结构: {config.get('structure', 'progressive')}")
            cfg.append(f"- 深度: {config.get('depth_level', 'standard')}")
            cfg.append(f"- 关注模式: {config.get('focus_mode', 'key_concepts')}")
            cfg.append("- 包含示例和代码说明" if config.get("include_examples", True) else "- 不包含示例")
            cfg.append("- 包含常见误区和易错点" if config.get("include_common_mistakes", True) else "- 不包含常见误区")
            input_text += f"\n\n{chr(10).join(cfg)}"
        input_text += "\n\n请生成专业课程讲解文档，只输出 Markdown 内容。"

        if self.emitter:
            await self.emitter.emit_agent(
                self.agent_id, status="running",
                message="正在构建课程讲解提示词",
                progress=25,
            )

        logger.info("Agent[content] 步骤: 调用 LLM 生成课程内容, input_len=%d", len(input_text))
        prompt = prompts.get("resource").get("content")
        response = await self.llm.ainvoke(f"{prompt}\n\n{input_text}", temperature=INFERENCE_TEMPERATURE)

        if self.emitter:
            await self.emitter.emit_agent(
                self.agent_id, status="running",
                message="大模型已返回，正在清洗格式",
                progress=85,
            )

        content = response.content if hasattr(response, "content") else str(response)
        # 清理 LLM 输出中多余的 markdown fence 标记
        content = _clean_markdown_fences(content)
        logger.info("Agent[content] 步骤: 内容清洗完成, output_len=%d", len(content))

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
    """移除 LLM 输出中的 markdown fence 包裹标记。"""
    lines = content.split("\n")
    return "\n".join(line for line in lines if line.strip() not in ("```", "```markdown", "```text"))
