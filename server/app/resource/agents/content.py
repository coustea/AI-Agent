"""内容智能体 — 基于教学蓝图生成专业课程讲解文档。"""

from __future__ import annotations

from app.config import INFERENCE_TEMPERATURE
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.agents.common import (
    build_basic_handoff,
    build_node_context,
    build_resource_context,
    assigned_outline_ids,
)
from app.infra.prompts import prompts
from app.resource.schemas import AgentResult, NodeInput, ResourceInput

logger = get_logger(__name__)


@register_agent
class ContentAgent(BaseResourceAgent):
    """基于教学蓝图生成课程讲解文档（Markdown 格式）。"""

    agent_id = "content"
    agent_name = "内容生成"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)
        self.llm = get_llm()

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        parts = build_resource_context(input_data)
        input_text = "\n\n".join(parts)
        config = {
            **input_data.agent_config,
            "_teaching_plan": input_data.teaching_plan,
        }
        result = await self._generate_content(
            input_text=input_text,
            title_prefix=input_data.learning_need[:32],
            config=config,
        )
        outline_ids = assigned_outline_ids(input_data.teaching_plan, "content")
        first_outline = input_data.teaching_plan.outline[0] if input_data.teaching_plan and input_data.teaching_plan.outline else None
        handoff = build_basic_handoff(
            source_agent="content",
            title=result.title,
            summary=result.summary,
            teaching_plan=input_data.teaching_plan,
            covered_outline_ids=outline_ids,
            examples=first_outline.suggested_examples if first_outline else [],
            visual_ideas=first_outline.suggested_visuals if first_outline else [],
        )
        result.downstream_context = handoff
        await self.emit_finish(result)
        return result

    async def generate_node(self, input_data: NodeInput) -> AgentResult:
        parts = build_node_context(input_data)
        input_text = "\n\n".join(parts)
        result = await self._generate_content(
            input_text=input_text,
            title_prefix=input_data.node_title,
            config=input_data.agent_config,
        )
        result.metadata["path_id"] = input_data.path_id
        result.metadata["node_id"] = input_data.node_id
        await self.emit_finish(result)
        return result

    async def _generate_content(
        self,
        *,
        input_text: str,
        title_prefix: str,
        config: dict,
    ) -> AgentResult:
        if config:
            cfg = ["## 内容配置"]
            cfg.append(f"- 结构: {config.get('structure', 'progressive')}")
            cfg.append(f"- 深度: {config.get('depth_level', 'standard')}")
            cfg.append(f"- 关注模式: {config.get('focus_mode', 'key_concepts')}")
            cfg.append("- 包含示例和代码说明" if config.get("include_examples", True) else "- 不包含示例")
            cfg.append("- 包含常见误区和易错点" if config.get("include_common_mistakes", True) else "- 不包含常见误区")
            input_text += f"\n\n{chr(10).join(cfg)}"
        input_text += "\n\n请生成专业课程讲解文档，只输出 Markdown 内容。"

        await self.emit_start("正在构建课程讲解提示词", progress=25)
        prompt = prompts.get("resource").get("content")
        response = await self.llm.ainvoke(f"{prompt}\n\n{input_text}", temperature=INFERENCE_TEMPERATURE)
        content = response.content if hasattr(response, "content") else str(response)
        content = _clean_markdown_fences(content)

        return AgentResult(
            success=True,
            content=content,
            file_type="markdown",
            title=f"{title_prefix} - 课程内容",
            summary="生成专业课程讲解文档",
            metrics={"char_count": len(content)},
            metadata={"agent_id": "content"},
        )


def _clean_markdown_fences(content: str) -> str:
    """移除 LLM 输出中的 markdown fence 包裹标记。"""
    lines = content.split("\n")
    return "\n".join(line for line in lines if line.strip() not in ("```", "```markdown", "```text"))
