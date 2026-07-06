"""代码智能体 — 基于教学蓝图生成教学示例代码（Markdown 格式）。"""

from __future__ import annotations

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.agents.common import (
    build_node_context,
    build_resource_context,
)
from app.infra.prompts import prompts
from app.resource.schemas import AgentResult, NodeInput, ResourceInput

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
        result = await self._generate_code(
            input_text="\n\n".join(build_resource_context(input_data)),
            title_prefix=input_data.learning_need[:32],
            config=input_data.agent_config,
        )
        await self.emitter.send(self.agent_id, "completed" if result.success else "failed", result.summary if result.success else (result.error or f"{self.agent_name}生成失败"), 100 if result.success else 0)
        return result

    async def generate_node(self, input_data: NodeInput) -> AgentResult:
        # Path node context: merge difficulty → output_style mapping
        node_difficulty = input_data.difficulty or "beginner"
        output_style_map = {"beginner": "tutorial", "intermediate": "reference", "advanced": "challenge"}
        config = {
            "output_style": output_style_map.get(node_difficulty, "tutorial"),
            **input_data.agent_config,
        }
        result = await self._generate_code(
            input_text="\n\n".join(build_node_context(input_data)),
            title_prefix=input_data.node_title,
            config=config,
        )
        result.metadata["path_id"] = input_data.path_id
        result.metadata["node_id"] = input_data.node_id
        await self.emitter.send(self.agent_id, "completed" if result.success else "failed", result.summary if result.success else (result.error or f"{self.agent_name}生成失败"), 100 if result.success else 0)
        return result

    async def _generate_code(
        self,
        *,
        input_text: str,
        title_prefix: str,
        config: dict,
    ) -> AgentResult:
        """内部方法 — 调用 LLM 生成教学代码示例。

        agent_config 已由 build_resource_context / build_node_context 统一注入，
        此处仅提取运行时需要的参数（如 search 关键词、metrics 统计）。
        """
        language = config.get("programming_language") or "python"
        output_style = config.get("output_style") or "tutorial"
        focus = config.get("focus") or "syntax"
        include_tests = config.get("include_tests", False)

        input_text += "\n\n请生成教学代码示例，包含代码注释和说明，输出为 Markdown 格式（代码块内为代码）。"
        if output_style == "tutorial":
            input_text += "\n请提供完整可运行的代码，包含逐步注释和运行说明。"
        elif output_style == "reference":
            input_text += "\n请提供精简的参考实现，聚焦核心逻辑和接口说明，省略冗余注释。"
        elif output_style == "challenge":
            input_text += "\n请提供框架代码和提示引导，关键实现部分留空让学习者填入。"

        if include_tests:
            input_text += "\n请在代码末尾附带测试用例（使用 assert 或单元测试框架）。"

        # 执行搜索以获取该知识点的最佳实践或真实代码示例
        await self.emitter.send(self.agent_id, "running", "正在搜索相关代码最佳实践...", 30)
        search_query = f"{language} {title_prefix} 示例代码 best practice"
        search_report = await self.search(search_query)
        search_text = self.format_search_result(search_report)
        if search_text:
            input_text = f"## 搜索到的参考代码示例背景\n{search_text}\n\n" + input_text

        await self.emitter.send(self.agent_id, "running", "正在构建代码示例提示词...", 45)
        prompt = prompts.get("resource").get("code")
        await self.emitter.send(self.agent_id, "running", "正在编写教学示例代码...", 60)
        response = await self.llm.ainvoke(f"{prompt}\n\n{input_text}")
        content = response.content if hasattr(response, "content") else str(response)

        return AgentResult(
            success=True,
            content=content,
            file_type="markdown",
            title=f"{title_prefix} - 代码示例",
            summary="生成教学代码示例",
            metrics={"language": language, "output_style": output_style, "focus": focus},
            metadata={"agent_id": "code", "language": language, "output_style": output_style, "focus": focus, "include_tests": include_tests},
        )
