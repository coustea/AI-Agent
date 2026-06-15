"""工具处理器 — 联网搜索 + 教学图解生成。

保留：
  WebSearchTool          — 联网搜索降级链（tavily → duckduckgo → serp → spark）
  TeachingDiagramGenerator — LLM 生成结构化图解 JSON

已删除（职责归入 TutorAgent 节点）：
  AttachmentAnalyzer  → TutorAgent.analysis_files 节点
  SearchOrchestrator  → agent 通过 web_search / search_knowledge_base 工具自行调用
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.chat.schemas import Evidence, EvidenceSet, TeachingDiagram, TutorTurnContext
from app.chat.tools.search import duckduckgo_search, spark_search, tavily_search
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.prompts import prompts

logger = get_logger(__name__)


# ── 联网搜索 ────────────────────────────────────────────────────


class WebSearchTool:
    """联网搜索工具：按优先级依次尝试 tavily → duckduckgo → serp → spark。

    返回第一个有效结果。有效 = 非空且不含"不可用"/"失败"/"未找到"等标记。
    全部失败时返回空字符串。
    """

    async def search(self, query: str) -> tuple[str, str | None]:
        """执行搜索，返回 (结果文本, 使用的工具名)"""
        candidates = [
            ("tavily_search", tavily_search),
            ("duckduckgo_search", duckduckgo_search),
            ("spark_search", spark_search),
        ]
        for tool_name, tool in candidates:
            try:
                result = str(await tool.ainvoke({"query": query}) if hasattr(tool, "ainvoke") else await tool(query)).strip()
            except Exception as exc:
                logger.warning("[WebSearchTool] %s 失败: %s", tool_name, exc)
                continue
            if result and "不可用" not in result and "失败" not in result and "未找到" not in result:
                return result, tool_name
        return "", None


# ── 教学图解 ────────────────────────────────────────────────────


class TeachingDiagramGenerator:
    """教学图解生成器：基于学生问题和回答，让 LLM 生成结构化图解 JSON。"""

    def __init__(self, llm=None) -> None:
        self.llm = llm or get_llm()

    async def generate(
        self,
        request: TutorTurnContext,
        answer: str,
        evidence_set: EvidenceSet,
    ) -> dict:
        attachment_context = "\n".join(
            item.summary for item in evidence_set.items if item.evidence_type == "attachment"
        ).strip()
        context_text = attachment_context or "无额外上下文。"
        prompt = (
            f"学生问题：\n{request.user_input}\n\n"
            f"最终回答：\n{answer}\n\n"
            f"上下文：\n{context_text}\n\n"
            "请生成一张能辅助学生理解答案的教学图解 JSON。"
        )
        diagram = await self.llm.ainvoke_json(
            TeachingDiagram,
            [
                SystemMessage(content=prompts.get("chat").get("teaching_diagram")),
                HumanMessage(content=prompt),
            ],
            temperature=0.1,
        )
        return diagram.model_dump(mode="json")
