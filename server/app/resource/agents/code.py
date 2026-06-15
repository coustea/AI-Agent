"""代码智能体 — 基于教学蓝图生成教学示例代码（Markdown 格式）。"""

from __future__ import annotations

from app.config import INFERENCE_TEMPERATURE
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.infra.prompts import prompts
from app.resource.schemas import WorkerResult, WorkerState

logger = get_logger(__name__)


@register_agent
class CodeAgent(BaseResourceAgent):
    """基于教学蓝图生成代码示例和讲解。"""

    agent_id = "code"
    agent_name = "代码生成"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)
        self.llm = get_llm()

    async def _execute(self, input_text: str, state: WorkerState) -> WorkerResult:
        """核心生成逻辑：提取代码配置 → 调用 LLM → 返回 Markdown 代码块。"""
        config = state.agent_config
        # 从配置中提取编程语言、案例类型、难度等参数
        language = config.get("programming_language") or config.get("language") or "python"
        case_type = config.get("case_type") or "basic_demo"
        difficulty = config.get("difficulty") or config.get("complexity") or "beginner"
        # 将代码配置拼接到 prompt 中
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

        logger.info("Agent[code] 步骤: 调用 LLM 生成代码示例, language=%s case_type=%s difficulty=%s", language, case_type, difficulty)
        prompt = prompts.get("resource").get("code")
        response = await self.llm.ainvoke(f"{prompt}\n\n{input_text}", temperature=INFERENCE_TEMPERATURE)

        if self.emitter:
            await self.emitter.emit_agent(
                self.agent_id, status="running",
                message="代码已生成，正在提取元信息",
                progress=85,
            )

        content = response.content if hasattr(response, "content") else str(response)
        logger.info("Agent[code] 步骤: 代码提取完成, output_len=%d", len(content))

        return WorkerResult(
            success=True,
            content=content,
            file_type="markdown",
            title=f"{state.learning_need[:32]} - 代码示例",
            summary="生成教学代码示例",
            summary_data={"language": language, "case_type": case_type, "difficulty": difficulty},
            metadata={"agent_id": "code", "language": language, "case_type": case_type, "difficulty": difficulty},
        )
