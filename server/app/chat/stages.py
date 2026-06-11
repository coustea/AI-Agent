"""三阶段处理器 — 附件分析、搜索、教学图解生成。

每个阶段接收 TurnRequest + 已有 EvidenceSet，产出新的 Evidence，
由 TurnOrchestrator 按顺序调度：

  AttachmentAnalyzer  — 图片 OCR / 文档解析 → attachment evidence
  SearchOrchestrator  — 知识库 + 联网搜索 → knowledge_base / web_search evidence
  TeachingDiagramGenerator — LLM 生成结构化图解 JSON
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage

from app.chat.schemas import Evidence, EvidenceSet, TeachingDiagram, TurnRequest
from app.chat.runtime import _classify_attachments
from app.chat.tools.knowledge import aformat_knowledge_context
from app.chat.tools.search import duckduckgo_search, serp_search, spark_search, tavily_search
from app.chat.utils.files import analyze_documents
from app.chat.utils.vision import VisionService
from app.config import (
    MAX_ANALYZE_FILE_COUNT,
    MAX_ANALYZE_TOTAL_CHARS,
    MAX_DOCX_PARAGRAPHS_TO_READ,
    MAX_FILE_CONTENT_CHARS,
    MAX_IMAGE_ANALYZE_COUNT,
    MAX_PDF_PAGES_TO_READ,
)
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.prompts import prompts

logger = get_logger(__name__)


# ── 附件分析 ────────────────────────────────────────────────────


class AttachmentAnalysisOutput(BaseModel):
    """附件分析结果：evidence 供后续推理使用，records 供持久化。"""
    evidence: list[Evidence] = Field(default_factory=list)
    records: list[dict[str, Any]] = Field(default_factory=list)


class AttachmentAnalyzer:
    """附件分析器：图片走 VisionService OCR，文档走文本解析。

    图片和文档分别分析，各自产出 Evidence。失败不阻断流水线，
    仅 warning 日志，返回已有的部分结果。
    """

    async def analyze(self, request: TurnRequest) -> AttachmentAnalysisOutput:
        if not request.attachments:
            return AttachmentAnalysisOutput()

        image_urls, file_urls = _classify_attachments(request.attachments)
        evidence: list[Evidence] = []
        records: list[dict[str, Any]] = []

        # 图片分析：VisionService 统一处理所有图片，产出一条汇总 evidence
        if image_urls:
            try:
                vision_result = await VisionService().analyze_images(
                    image_urls[:MAX_IMAGE_ANALYZE_COUNT],
                    "请详细分析这些图片中的文字、题目、图表和关键信息，并用中文总结。",
                )
                description = str(vision_result.get("analysis_text") or "").strip()
                if description:
                    for url in image_urls[:MAX_IMAGE_ANALYZE_COUNT]:
                        records.append(
                            {
                                "file_id": request.uploaded_file_ids_by_url.get(url),
                                "file_name": url.split("/")[-1],
                                "file_url": url,
                                "analysis_type": "vision",
                                "summary_text": description,
                                "structured_json": {
                                    "mode": vision_result.get("mode", ""),
                                    "source_count": min(len(image_urls), MAX_IMAGE_ANALYZE_COUNT),
                                },
                            }
                        )
                    evidence.append(
                        Evidence(
                            evidence_type="attachment",
                            summary=f"[图片] {description}",
                            details={
                                "kind": "image",
                                "urls": image_urls[:MAX_IMAGE_ANALYZE_COUNT],
                                "source_count": min(len(image_urls), MAX_IMAGE_ANALYZE_COUNT),
                            },
                        )
                    )
            except Exception as exc:
                logger.warning("[AttachmentAnalyzer] 图片分析失败: %s", exc)

        # 文档分析：提取文本后交由 analyze_documents 生成摘要
        if file_urls:
            try:
                analysis = await analyze_documents(
                    current_user_id=request.user_id,
                    file_urls=file_urls[:MAX_ANALYZE_FILE_COUNT],
                    question="请分析这些文档",
                    max_total_chars=MAX_ANALYZE_TOTAL_CHARS,
                    max_file_content_chars=MAX_FILE_CONTENT_CHARS,
                    max_pdf_pages=MAX_PDF_PAGES_TO_READ,
                    max_docx_paragraphs=MAX_DOCX_PARAGRAPHS_TO_READ,
                )
                summary = str(analysis.get("analysis_text") or "").strip()
                documents = analysis.get("documents", []) if isinstance(analysis.get("documents"), list) else []
                if summary:
                    for url in file_urls[:MAX_ANALYZE_FILE_COUNT]:
                        first_match = next((doc for doc in documents if str(doc.get("url") or "") == url), {})
                        records.append(
                            {
                                "file_id": request.uploaded_file_ids_by_url.get(url),
                                "file_name": first_match.get("name") or url.split("/")[-1],
                                "file_url": url,
                                "analysis_type": "document",
                                "summary_text": summary,
                                "structured_json": {"documents": documents},
                            }
                        )
                    evidence.append(
                        Evidence(
                            evidence_type="attachment",
                            summary=f"[文档] {summary}",
                            details={
                                "kind": "document",
                                "urls": file_urls[:MAX_ANALYZE_FILE_COUNT],
                                "documents": documents,
                            },
                        )
                    )
            except Exception as exc:
                logger.warning("[AttachmentAnalyzer] 文档分析失败: %s", exc)

        return AttachmentAnalysisOutput(evidence=evidence, records=records)


# ── 搜索 ────────────────────────────────────────────────────────


class SearchOutput(BaseModel):
    """搜索结果：知识库 + 联网搜索的 evidence 汇总。"""
    evidence: list[Evidence] = Field(default_factory=list)
    tool_name: str | None = None
    query: str = ""
    sources: list[dict[str, Any]] = Field(default_factory=list)
    raw_result: str = ""


class WebSearchTool:
    """联网搜索工具：按优先级依次尝试 tavily → duckduckgo → serp → spark。

    返回第一个有效结果。有效 = 非空且不含"不可用"/"失败"/"未找到"等标记。
    全部失败时返回空字符串。
    """

    async def search(self, query: str) -> tuple[str, str | None]:
        candidates = [
            ("tavily_search", tavily_search),
            ("duckduckgo_search", duckduckgo_search),
            ("serp_search", serp_search),
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


class SearchOrchestrator:
    """搜索编排器：先查知识库（Chroma 向量检索），再联网搜索。

    两者独立，结果都作为 evidence 返回。知识库返回原文片段 + 来源，
    联网搜索返回摘要文本。
    """

    def __init__(self, *, web_search: Any | None = None) -> None:
        self.web_search = web_search or WebSearchTool()

    async def search(self, request: TurnRequest, evidence_set: EvidenceSet) -> SearchOutput:
        query = str(request.message or "").strip()
        if not query:
            return SearchOutput(query="")

        evidence: list[Evidence] = []
        # 知识库向量检索
        kb_context, kb_rows = await aformat_knowledge_context(query)
        if kb_context.strip():
            evidence.append(
                Evidence(
                    evidence_type="knowledge_base",
                    summary=kb_context,
                    details={"query": query, "sources": kb_rows},
                )
            )

        # 联网搜索（降级链）
        web_result, tool_name = await self.web_search.search(query)
        if web_result.strip():
            evidence.append(
                Evidence(
                    evidence_type="web_search",
                    summary=web_result,
                    details={"query": query, "tool_name": tool_name},
                )
            )

        return SearchOutput(
            evidence=evidence,
            tool_name=tool_name,
            query=query,
            sources=kb_rows,
            raw_result=web_result,
        )


# ── 教学图解 ────────────────────────────────────────────────────


class TeachingDiagramGenerator:
    """教学图解生成器：基于学生问题和回答，让 LLM 生成结构化图解 JSON。

    使用 TeachingDiagram Schema 约束输出格式（6 种图型），
    LLM 通过 ainvoke_json 直接输出 Pydantic 验证后的结构化数据。
    """

    def __init__(self, llm=None) -> None:
        self.llm = llm or get_llm()

    async def generate(
        self,
        request: TurnRequest,
        answer: str,
        evidence_set: EvidenceSet,
    ) -> dict:
        # 从证据中提取附件上下文辅助图解生成
        attachment_context = "\n".join(
            item.summary for item in evidence_set.items if item.evidence_type == "attachment"
        ).strip()
        context_text = attachment_context or "无额外上下文。"
        prompt = (
            f"学生问题：\n{request.message}\n\n"
            f"最终回答：\n{answer}\n\n"
            f"上下文：\n{context_text}\n\n"
            "请生成一张能辅助学生理解答案的教学图解 JSON。"
        )
        # ainvoke_json 使用 TeachingDiagram Schema 做结构化输出约束
        diagram = await self.llm.ainvoke_json(
            TeachingDiagram,
            [
                SystemMessage(content=prompts.get("chat").get("teaching_diagram")),
                HumanMessage(content=prompt),
            ],
            temperature=0.1,
        )
        return diagram.model_dump(mode="json")
