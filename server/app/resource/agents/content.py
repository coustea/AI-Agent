"""内容智能体 — 基于教学蓝图生成专业课程讲解文档。"""

from __future__ import annotations

import time

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.agents.common import (
    build_node_context,
    build_resource_context,
)
from app.infra.prompts import prompts
from app.resource.schemas import AgentResult, NodeInput, ResourceInput
from app.rag.tools import build_knowledge_tool

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
        return await self._generate_content(
            input_text="\n\n".join(build_resource_context(input_data)),
            title_prefix=input_data.learning_need[:32],
            config=input_data.agent_config,
        )

    async def generate_node(self, input_data: NodeInput) -> AgentResult:
        result = await self._generate_content(
            input_text="\n\n".join(build_node_context(input_data)),
            title_prefix=input_data.node_title,
            config=input_data.agent_config,
        )
        result.metadata["path_id"] = input_data.path_id
        result.metadata["node_id"] = input_data.node_id
        return result

    async def _generate_content(
        self,
        *,
        input_text: str,
        title_prefix: str,
        config: dict,
    ) -> AgentResult:
        """内部方法 — 调用 LLM 生成课程内容 Markdown。"""
        logger.info("Agent[%s] 开始生成: learning_need=%s", self.agent_id, title_prefix)
        input_text += "\n\n请生成专业课程讲解文档，只输出 Markdown 内容。"
        started = time.perf_counter()

        # 收集参考资料：本地知识库检索（教材）+ 联网搜索，两者独立进行
        context_parts: list[str] = []

        # 1. 本地知识库检索 —— 直接调用 RAG 工具，独立于联网搜索
        await self.emitter.send(self.agent_id, "running", "正在检索本地教材资料...", 25)
        try:
            kb_result = await build_knowledge_tool().handler(query=title_prefix)
            kb_text = (
                kb_result.get("text")
                if isinstance(kb_result, dict) and kb_result.get("status") == "ok"
                else None
            )
        except Exception as exc:
            logger.warning("Agent[%s] 知识库检索失败: %s", self.agent_id, exc)
            kb_text = None
        if kb_text:
            context_parts.append(f"## 本地教材资料\n{kb_text}")
            logger.info("Agent[%s] 知识库命中", self.agent_id)

        # 2. 联网搜索 —— 获取最新/更全面的参考信息
        await self.emitter.send(self.agent_id, "running", "正在搜索相关课程讲解素材...", 35)
        search_query = f"{title_prefix} 教程 概念"
        search_report = await self.search(search_query)
        search_text = self.format_search_result(search_report)
        search_elapsed = int((time.perf_counter() - started) * 1000)
        logger.info(
            "Agent[%s] 搜索完成: query=%s → sources=%d elapsed_ms=%d",
            self.agent_id, search_query, len(search_report.sources), search_elapsed,
        )
        if search_text:
            context_parts.append(f"## 联网参考资料\n{search_text}")

        if context_parts:
            input_text = "\n\n".join(context_parts) + "\n\n" + input_text

        await self.emitter.send(self.agent_id, "running", "正在构建课程讲解提示词...", 45)
        prompt = prompts.get("resource").get("content")
        await self.emitter.send(self.agent_id, "running", "正在精解讲义内容...", 60)
        full_prompt = f"{prompt}\n\n{input_text}"
        logger.info("Agent[%s] LLM 调用: input_len=%d", self.agent_id, len(full_prompt))
        llm_started = time.perf_counter()
        response = await self.run_with_heartbeat(
            self.llm.ainvoke(full_prompt),
            messages=[
                "正在生成讲解文档主体内容...",
                "正在补充关键概念与学习提示...",
            ],
            interval_seconds=12.0,
            progress=70,
        )
        content = response.content if hasattr(response, "content") else str(response)
        llm_elapsed = int((time.perf_counter() - llm_started) * 1000)
        logger.info(
            "Agent[%s] LLM 完成: output_len=%d elapsed_ms=%d",
            self.agent_id, len(content), llm_elapsed,
        )

        total_elapsed = int((time.perf_counter() - started) * 1000)
        logger.info(
            "Agent[%s] 生成完成: char_count=%d elapsed_ms=%d → %s",
            self.agent_id, len(content), total_elapsed, content[:200].replace("\n", " "),
        )
        return AgentResult(
            success=True,
            content=content,
            file_type="markdown",
            title=f"{title_prefix} - 课程内容",
            summary="生成专业课程讲解文档",
            metrics={"char_count": len(content)},
            metadata={"agent_id": "content"},
        )
