"""内容智能体 — 基于教学蓝图生成专业课程讲解文档。"""

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
class ContentAgent(BaseResourceAgent):
    """基于教学蓝图生成课程讲解文档（Markdown 格式）。"""

    agent_id = "content"
    agent_name = "课程讲解"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)
        self.llm = get_llm()

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        config = {
            **input_data.agent_config,
            "_teaching_plan": input_data.teaching_plan,
        }
        result = await self._generate_content(
            input_text="\n\n".join(build_resource_context(input_data)),
            title_prefix=input_data.learning_need[:32],
            config=config,
        )
        await self.emitter.send(self.agent_id, "completed" if result.success else "failed", result.summary if result.success else (result.error or f"{self.agent_name}生成失败"), 100 if result.success else 0)
        return result

    async def generate_node(self, input_data: NodeInput) -> AgentResult:
        result = await self._generate_content(
            input_text="\n\n".join(build_node_context(input_data)),
            title_prefix=input_data.node_title,
            config=input_data.agent_config,
        )
        result.metadata["path_id"] = input_data.path_id
        result.metadata["node_id"] = input_data.node_id
        await self.emitter.send(self.agent_id, "completed" if result.success else "failed", result.summary if result.success else (result.error or f"{self.agent_name}生成失败"), 100 if result.success else 0)
        return result

    async def _generate_content(
        self,
        *,
        input_text: str,
        title_prefix: str,
        config: dict,
    ) -> AgentResult:
        """内部方法 — 调用 LLM 生成课程内容 Markdown。

        agent_config 已由 build_resource_context / build_node_context 统一注入，
        此处仅提取运行时需要的参数（如 search 关键词）。
        """
        input_text += "\n\n请生成专业课程讲解文档，只输出 Markdown 内容。"

        # 执行搜索以获取最新/更全面的参考信息以生成更高质量的文档
        await self.emitter.send(self.agent_id, "running", "正在搜索相关课程讲解素材...", 30)
        search_query = f"{title_prefix} 教程 概念"
        search_text = await self.search(search_query)

        if "搜索失败" not in search_text and "未找到" not in search_text:
            input_text = f"## 搜索到的参考背景信息\n{search_text}\n\n" + input_text

        await self.emitter.send(self.agent_id, "running", "正在构建课程讲解提示词...", 45)
        prompt = prompts.get("resource").get("content")
        await self.emitter.send(self.agent_id, "running", "正在精解讲义内容...", 60)
        response = await self.llm.ainvoke(f"{prompt}\n\n{input_text}")
        content = response.content if hasattr(response, "content") else str(response)

        return AgentResult(
            success=True,
            content=content,
            file_type="markdown",
            title=f"{title_prefix} - 课程内容",
            summary="生成专业课程讲解文档",
            metrics={"char_count": len(content)},
            metadata={"agent_id": "content"},
        )
