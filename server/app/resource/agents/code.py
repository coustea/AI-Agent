"""代码智能体 — 基于教学蓝图生成教学示例代码（Markdown 格式）。"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.agents.common import build_path_context, build_resource_context
from app.infra.prompts import prompts
from app.resource.schemas import AgentResult, ResourceInput

if TYPE_CHECKING:
    from app.path.schemas import PathResourceRequest

logger = get_logger(__name__)


@register_agent
class CodeAgent(BaseResourceAgent):
    """基于教学蓝图生成代码示例和讲解。"""

    agent_id = "code"
    agent_name = "代码实操"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)
        self.llm = get_llm()

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        return await self._generate_code(
            input_text="\n\n".join(build_resource_context(input_data)),
            title_prefix=input_data.learning_need[:32],
            config=input_data.agent_config,
        )

    async def generate_for_path(self, request: "PathResourceRequest") -> AgentResult:
        """路径规划统一接口 — 接收 PathResourceRequest，返回 AgentResult。"""
        if request.tutorial is None:
            return AgentResult(
                success=False,
                title="代码示例生成失败",
                file_type="markdown",
                error="缺少教程内容",
            )
        # 将难度映射为代码输出风格
        output_style_map = {"beginner": "tutorial", "intermediate": "reference", "advanced": "challenge"}
        config = {"output_style": output_style_map.get(request.difficulty, "tutorial")}
        result = await self._generate_code(
            input_text="\n\n".join(build_path_context(request)),
            title_prefix=request.node_title,
            config=config,
        )
        result.metadata["node_id"] = request.node_id
        return result

    async def _generate_code(
        self,
        *,
        input_text: str,
        title_prefix: str,
        config: dict,
    ) -> AgentResult:
        """内部方法 — 调用 LLM 生成教学代码示例。"""
        language = config.get("programming_language") or "python"
        output_style = config.get("output_style") or "tutorial"
        focus = config.get("focus") or "syntax"
        include_tests = config.get("include_tests", False)

        logger.info(
            "Agent[%s] 开始生成: learning_need=%s language=%s style=%s",
            self.agent_id, title_prefix, language, output_style,
        )
        started = time.perf_counter()

        input_text += "\n\n请生成教学代码示例，包含代码注释和说明，输出为 Markdown 格式（代码块内为代码）。"
        # 按输出风格注入不同生成指引
        if output_style == "tutorial":
            input_text += "\n请提供完整可运行的代码，包含逐步注释和运行说明。"
        elif output_style == "reference":
            input_text += "\n请提供精简的参考实现，聚焦核心逻辑和接口说明，省略冗余注释。"
        elif output_style == "challenge":
            input_text += "\n请提供框架代码和提示引导，关键实现部分留空让学习者填入。"

        if include_tests:
            input_text += "\n请在代码末尾附带测试用例（使用 assert 或单元测试框架）。"

        await self.emitter.send(self.agent_id, "running", "正在构建代码示例提示词...", 45)
        prompt = prompts.get("resource").get("code")
        await self.emitter.send(self.agent_id, "running", "正在编写教学示例代码...", 60)
        full_prompt = f"{prompt}\n\n{input_text}"
        logger.info("Agent[%s] LLM 调用: input_len=%d", self.agent_id, len(full_prompt))
        llm_started = time.perf_counter()
        content = await self.run_with_heartbeat(
            self.llm.ainvoke_text(full_prompt),
            messages=[
                "正在生成教学示例代码...",
                "正在补充代码注释与运行说明...",
            ],
            interval_seconds=12.0,
            progress=70,
        )
        llm_elapsed = int((time.perf_counter() - llm_started) * 1000)
        logger.info(
            "Agent[%s] LLM 完成: output_len=%d elapsed_ms=%d",
            self.agent_id, len(content), llm_elapsed,
        )

        total_elapsed = int((time.perf_counter() - started) * 1000)
        logger.info(
            "Agent[%s] 生成完成: language=%s elapsed_ms=%d → %s",
            self.agent_id, language, total_elapsed, content[:200].replace("\n", " "),
        )

        return AgentResult(
            success=True,
            content=content,
            file_type="markdown",
            title=f"{title_prefix} - 代码示例",
            summary="生成教学代码示例",
            metrics={"language": language, "output_style": output_style, "focus": focus},
            metadata={"agent_id": "code", "language": language, "output_style": output_style, "focus": focus, "include_tests": include_tests},
        )
