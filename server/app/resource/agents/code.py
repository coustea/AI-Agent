"""代码智能体 — 基于教学蓝图生成教学示例代码（Markdown 格式）。"""

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
class CodeAgent(BaseResourceAgent):
    """基于教学蓝图生成代码示例和讲解。"""

    agent_id = "code"
    agent_name = "代码生成"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)
        self.llm = get_llm()

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        config = {
            **input_data.agent_config,
            "_teaching_plan": input_data.teaching_plan,
        }
        result = await self._generate_code(
            input_text="\n\n".join(build_resource_context(input_data)),
            title_prefix=input_data.learning_need[:32],
            config=config,
        )
        lang = result.metrics.get("language") or "python"
        case_type = result.metrics.get("case_type") or "basic_demo"
        difficulty = result.metrics.get("difficulty") or "beginner"
        code_outline_ids = assigned_outline_ids(input_data.teaching_plan, "code")
        handoff = build_basic_handoff(
            source_agent="code",
            title=result.title,
            summary=result.summary,
            teaching_plan=input_data.teaching_plan,
            covered_outline_ids=code_outline_ids,
            code_refs=[lang, case_type],
        )
        result.downstream_context = handoff
        await self.emit_finish(result)
        return result

    async def generate_node(self, input_data: NodeInput) -> AgentResult:
        config = {
            "difficulty": input_data.difficulty or "beginner",
            **input_data.agent_config,
        }
        result = await self._generate_code(
            input_text="\n\n".join(build_node_context(input_data)),
            title_prefix=input_data.node_title,
            config=config,
        )
        result.metadata["path_id"] = input_data.path_id
        result.metadata["node_id"] = input_data.node_id
        await self.emit_finish(result)
        return result

    async def _generate_code(
        self,
        *,
        input_text: str,
        title_prefix: str,
        config: dict,
    ) -> AgentResult:
        """内部方法 — 调用 LLM 生成教学代码示例。"""
        language = config.get("programming_language") or config.get("language") or "python"
        case_type = config.get("case_type") or "basic_demo"
        difficulty = config.get("difficulty") or config.get("complexity") or "beginner"
        if config:
            cfg = ["## 代码配置"]
            cfg.append(f"- programming_language: {language}")
            cfg.append(f"- case_type: {case_type}")
            cfg.append(f"- difficulty: {difficulty}")
            cfg.append("- 包含详细注释" if config.get("include_comments", True) else "- 不包含注释")
            input_text += f"\n\n{chr(10).join(cfg)}"
        input_text += "\n\n请生成教学代码示例，包含代码注释和说明，输出为 Markdown 格式（代码块内为代码）。"

        await self.emit_start("正在构建代码示例提示词", progress=25)
        prompt = prompts.get("resource").get("code")
        response = await self.llm.ainvoke(f"{prompt}\n\n{input_text}", temperature=INFERENCE_TEMPERATURE)
        content = response.content if hasattr(response, "content") else str(response)

        return AgentResult(
            success=True,
            content=content,
            file_type="markdown",
            title=f"{title_prefix} - 代码示例",
            summary="生成教学代码示例",
            metrics={"language": language, "case_type": case_type, "difficulty": difficulty},
            metadata={"agent_id": "code", "language": language, "case_type": case_type, "difficulty": difficulty},
        )
