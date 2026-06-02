"""
代码智能体 — 生成编程示例 / 练习代码，支持代码块提取和语言检测。
"""

from __future__ import annotations

import re
import time

from app.infra.llm import get_llm
from app.infra.logging import get_module_logger
from app.prompts import registry
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.events import AgentEventEmitter
from app.resource.schemas import WorkerResult, WorkerState

logger = get_module_logger("resource", sub="code")


@register_agent
class CodeAgent(BaseResourceAgent):
    """基于教学蓝图生成编程示例和练习代码。"""

    agent_id = "code"
    agent_name = "代码生成"

    def __init__(self, emitter: AgentEventEmitter | None = None):
        super().__init__(emitter=emitter)
        self.llm = get_llm()

    async def _execute(self, input_text: str, state: WorkerState) -> WorkerResult:
        start = time.perf_counter()
        logger.info("Agent[code] 启动: learning_need=%s", state.learning_need[:50])

        await self.emitter.emit_agent("code", status="running", message="正在准备代码示例", progress=0)
        await self.emitter.emit_agent_action(
            "code", "analyze", detail="正在分析代码结构需求",
            current_step=1, total_steps=3, step_label="分析需求", progress=15,
        )

        prompt = registry.get("resource/code")

        await self.emitter.emit_agent_action(
            "code", "generate", detail="正在编写代码",
            current_step=2, total_steps=3, step_label="编写代码", progress=40,
        )

        response = await self.llm.ainvoke(
            f"{prompt}\n\n{input_text}",
            temperature=0.3,
        )

        elapsed = time.perf_counter() - start
        logger.debug("Agent[code] LLM 调用完成: %.2fs", elapsed)

        content = response.content if hasattr(response, "content") else str(response)

        code_blocks = re.findall(r"```(\w+)?\s*\n(.*?)```", content, re.DOTALL)
        languages: list[str] = []
        for lang, _ in code_blocks:
            if lang:
                languages.append(lang.lower())

        primary_lang = languages[0] if languages else state.agent_config.get("language", "python")

        await self.emitter.emit_agent_action(
            "code", "done", detail=f"已生成 {len(code_blocks)} 个代码示例",
            current_step=3, total_steps=3, step_label="生成完成", progress=100,
        )
        await self.emitter.emit_agent("code", status="success", message="代码示例生成完成", progress=100)

        elapsed = time.perf_counter() - start
        logger.info("Agent[code] 完成: %.2fs", elapsed)

        return WorkerResult(
            success=True,
            content=content,
            file_type="markdown",
            title=f"{state.learning_need[:32]} - 代码示例",
            summary=f"生成 {len(code_blocks)} 个代码示例",
            summary_data={"code_count": len(code_blocks), "language": primary_lang},
            metadata={
                "engine": "code_md",
                "language": primary_lang,
                "code_count": len(code_blocks),
                "agent_id": "code",
            },
        )

    def agent_input_parts(self, state: WorkerState) -> list[str]:
        parts = []
        config = state.agent_config
        if config:
            cfg_lines = ["## 代码配置"]
            cfg_lines.append(f"- 编程语言: {config.get('language', 'python')}")
            cfg_lines.append(f"- 项目类型: {config.get('project_type', 'script')}")
            cfg_lines.append(f"- 难度: {config.get('difficulty', 'beginner')}")
            cfg_lines.append(
                "- 包含运行说明和注释" if config.get("include_comments", True) else "- 不包含注释"
            )
            cfg_lines.append(
                "- 包含错误处理" if config.get("include_error_handling", False) else "- 不包含错误处理"
            )
            parts.append("\n".join(cfg_lines))
        parts.append("请生成代码示例和练习，输出 Markdown 格式。")
        return parts