"""Shared service for uploaded document analysis."""

from __future__ import annotations

from pathlib import Path

from app.infra.logging import get_logger

from .attachments import read_uploaded_file_content, resolve_uploaded_path

logger = get_logger(__name__)


class DocumentAnalysisService:
    """Analyze uploaded documents without going through tool execution."""

    async def analyze(
        self,
        current_user_id: int,
        file_urls: list[str],
        question: str,
    ) -> dict:
        documents: list[dict[str, str]] = []
        snippets: list[str] = []

        for file_url in file_urls:
            resolved = resolve_uploaded_path(file_url)
            if resolved is None:
                logger.warning("[DocumentAnalysis] failed to resolve %s", file_url)
                continue

            owner_id, absolute_path = resolved
            if owner_id != current_user_id:
                logger.warning("[DocumentAnalysis] forbidden file access user=%s owner=%s", current_user_id, owner_id)
                continue

            content = read_uploaded_file_content(absolute_path)
            documents.append(
                {
                    "url": file_url,
                    "name": Path(absolute_path).name,
                    "absolute_path": absolute_path,
                    "content": content,
                }
            )
            snippets.append(f"文件《{Path(absolute_path).name}》内容如下：\n{content}")

        if not documents:
            return {
                "success": False,
                "documents": [],
                "analysis_text": "未能读取可分析的文档内容。",
                "error": "未找到可访问的文档。",
            }

        analysis_text = (
            f"用户问题：{question or '请分析这些文档'}\n\n"
            "以下是已提取的文档内容，请基于它们回答用户问题，并在回答中尽量提炼知识点：\n\n"
            + "\n\n".join(snippets)
        )
        return {
            "success": True,
            "documents": documents,
            "analysis_text": analysis_text,
            "error": None,
        }


document_analysis_service = DocumentAnalysisService()
