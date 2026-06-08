"""代码智能体 — 生成教学示例代码。"""

from __future__ import annotations

from app.infra.llm import get_llm
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.prompt_manager import resource_prompts
from app.resource.schemas import WorkerResult, WorkerState


@register_agent
class CodeAgent(BaseResourceAgent):
    """基于教学蓝图生成代码示例和讲解。"""

    agent_id = "code"
    agent_name = "代码生成"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)
        self.llm = get_llm()

    async def _execute(self, input_text: str, state: WorkerState) -> WorkerResult:
        config = state.agent_config
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

        if self.emitter:
            await self.emitter.emit_agent(
                self.agent_id, status="running",
                message="正在构建代码示例提示词",
                progress=25,
            )

        prompt = resource_prompts.get("code")
        response = await self.llm.ainvoke(f"{prompt}\n\n{input_text}", temperature=0.3)

        if self.emitter:
            await self.emitter.emit_agent(
                self.agent_id, status="running",
                message="代码已生成，正在提取元信息",
                progress=85,
            )

        content = response.content if hasattr(response, "content") else str(response)

        return WorkerResult(
            success=True,
            content=content,
            file_type="markdown",
            title=f"{state.learning_need[:32]} - 代码示例",
            summary="生成教学代码示例",
            summary_data={"language": language, "case_type": case_type, "difficulty": difficulty},
            metadata={"agent_id": "code", "language": language, "case_type": case_type, "difficulty": difficulty},
        )
