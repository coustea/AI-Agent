"""文档分割器 — 基于 LangChain TextSplitters，按文档类型选择切分策略。

公共接口：
  split_documents()   批量切分文档列表

MD: MarkdownHeaderTextSplitter → RecursiveCharacterTextSplitter（中文分隔符）
PDF: RecursiveCharacterTextSplitter（中文分隔符）
代码块保护：分割前替换为占位符，分割后恢复

Called by: app/rag/indexing/build.py
Per user: "splitter.py 用到了 Path，但顶部没有导入…短块合并可能跨 heading 合并"
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from app.infra.logging import get_logger

logger = get_logger(__name__)

# ============ 切分参数 ============

CHUNK_MAX_SIZE = 800
CHUNK_MIN_SIZE = 100
CHUNK_OVERLAP = 100

# 中文分隔符列表（用于 RecursiveCharacterTextSplitter）
_CHINESE_SEPARATORS = [
    "\n\n",
    "\n",
    "。",
    "！",
    "？",
    ".",
    "!",
    "?",
    "，",
    "，",  # 全角逗号
    "、",  # 顿号
    "．",  # 全角句号
    "。",  # 中文句号
    " ",
    "",
]


# 将代码块替换为占位符，避免被切分破坏
def _protect_code_blocks(text: str) -> tuple[str, dict[str, str]]:
    """保护代码块：替换为占位符，分割后恢复。

    Returns:
        (safe_text, placeholder_map)
    """
    placeholder_map: dict[str, str] = {}
    idx = 0
    safe_text = text
    while "```" in safe_text:
        start = safe_text.index("```")
        end_pos = safe_text.find("```", start + 3)
        if end_pos == -1:
            break
        code_block = safe_text[start : end_pos + 3]
        placeholder = f"<<CODE_BLOCK_{idx}>>"
        placeholder_map[placeholder] = code_block
        safe_text = safe_text[:start] + placeholder + safe_text[end_pos + 3 :]
        idx += 1
    return safe_text, placeholder_map


# 将占位符还原为原始代码块
def _restore_code_blocks(text: str, placeholder_map: dict[str, str]) -> str:
    """恢复代码块占位符为原始代码。"""
    for placeholder, code in placeholder_map.items():
        text = text.replace(placeholder, code)
    return text


# ============ Markdown 分割 ============


# Markdown 切分：保护代码 → 标题分割 → 递归切分 → 恢复 → 合并短块
def _split_markdown(doc: Document) -> list[Document]:
    """Markdown 文档分割：标题结构分割 + 递归字符分割。

    流程：
    1. 保护代码块（替换为占位符）
    2. MarkdownHeaderTextSplitter 按 h1/h2/h3 分割
    3. RecursiveCharacterTextSplitter 处理超长块
    4. 恢复代码块
    5. 合并过短块（仅允许同 source 同 heading_path 的合并）
    """
    text = doc.page_content
    if not text or not text.strip():
        return []

    # 1. 保护代码块为占位符
    safe_text, placeholder_map = _protect_code_blocks(text)

    # 2. 按 h1/h2/h3 标题结构分割
    headers_to_split_on = [
        ("#", "h1"),
        ("##", "h2"),
        ("###", "h3"),
    ]
    md_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False,
    )

    try:
        md_chunks = md_splitter.split_text(safe_text)
    except Exception:
        # 标题分割失败时回退按段落切分
        md_chunks = []
        for para in safe_text.split("\n\n"):
            if para.strip():
                md_chunks.append(Document(page_content=para.strip(), metadata={}))

    # 3. 还原代码块并构建 heading_path 章节路径
    chunks_with_heading: list[tuple[str, str]] = []
    for chunk in md_chunks:
        content = chunk.page_content
        content = _restore_code_blocks(content, placeholder_map)

        meta = chunk.metadata
        heading_parts = []
        for key in ("h1", "h2", "h3"):
            if key in meta and meta[key]:
                heading_parts.append(meta[key])
        heading_path = " > ".join(heading_parts)

        content = content.strip()
        if not content:
            continue

        chunks_with_heading.append((content, heading_path))

    # 4. 用递归字符切分器处理超长块（中文分隔符）
    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_MAX_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=_CHINESE_SEPARATORS,
    )

    final_chunks: list[Document] = []
    for content, heading_path in chunks_with_heading:
        if len(content) > CHUNK_MAX_SIZE:
            # 先恢复代码块再分割
            sub_docs = char_splitter.split_text(content)
            for sub_text in sub_docs:
                sub_text = _restore_code_blocks(sub_text, placeholder_map)
                final_chunks.append(
                    Document(
                        page_content=sub_text.strip(),
                        metadata={**doc.metadata, "heading_path": heading_path},
                    )
                )
        else:
            final_chunks.append(
                Document(
                    page_content=content,
                    metadata={**doc.metadata, "heading_path": heading_path},
                )
            )

    # 5. 合并同章节相邻短块
    final_chunks = _merge_short_chunks(final_chunks)

    return final_chunks


# 合并相邻短块（仅同 source 同 heading_path，避免跨章节）
def _merge_short_chunks(chunks: list[Document]) -> list[Document]:
    """合并过短块。

    只允许合并同一 source、同一 heading_path 下的相邻短块，
    避免把不同章节内容混在一个 chunk 中。
    """
    if not chunks:
        return chunks

    merged: list[Document] = []
    buf_doc: Document | None = None

    for chunk in chunks:
        text = chunk.page_content.strip()
        if not text:
            continue

        if buf_doc is None:
            buf_doc = chunk
            continue

        buf_heading = str(buf_doc.metadata.get("heading_path", ""))
        cur_heading = str(chunk.metadata.get("heading_path", ""))
        buf_source = str(buf_doc.metadata.get("source", ""))
        cur_source = str(chunk.metadata.get("source", ""))

        same_context = buf_source == cur_source and buf_heading == cur_heading
        candidate = (buf_doc.page_content.strip() + "\n\n" + text).strip()

        should_merge = (
            same_context
            and (
                len(buf_doc.page_content.strip()) < CHUNK_MIN_SIZE
                or len(text) < CHUNK_MIN_SIZE
            )
            and len(candidate) <= CHUNK_MAX_SIZE
        )

        if should_merge:
            buf_doc = Document(
                page_content=candidate,
                metadata=dict(buf_doc.metadata),
            )
        else:
            merged.append(buf_doc)
            buf_doc = chunk

    if buf_doc is not None and buf_doc.page_content.strip():
        merged.append(buf_doc)

    return merged


# ============ PDF 分割 ============


# PDF 切分：递归字符切分（中文分隔符），heading_path 置空
def _split_pdf(doc: Document) -> list[Document]:
    """PDF 文档分割：递归字符分割（中文分隔符）。"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_MAX_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=_CHINESE_SEPARATORS,
    )
    chunks = splitter.split_documents([doc])
    # 补充 heading_path 为空
    for chunk in chunks:
        chunk.metadata.setdefault("heading_path", "")
    return chunks


# ============ 分割器注册表 ============

# 按扩展名分派的切分器注册表
_SPLITTERS: dict[str, Any] = {
    ".md": _split_markdown,
    ".pdf": _split_pdf,
}


# ============ 公共接口 ============


# 公共接口：按文件类型选择切分器并补充 chunk 元数据
def split_documents(docs: list[Document]) -> list[Document]:
    """批量切分文档列表，按文件类型自动选择分割策略。

    Returns:
        切分后的 Document 列表，每个包含 heading_path、chunk_index、global_chunk_index 等元数据。
    """
    all_chunks: list[Document] = []
    global_chunk_counter = 0
    source_chunk_counters: dict[str, int] = {}

    for doc in docs:
        file_type = doc.metadata.get("file_type", "")
        if not file_type:
            source = doc.metadata.get("source", "")
            file_type = Path(source).suffix.lower() if source else ""

        # 取对应类型切分器，无则回退默认递归切分
        splitter = _SPLITTERS.get(file_type)
        if splitter is None:
            logger.warning(
                "[splitter] no splitter for %s, using RecursiveCharacterTextSplitter",
                file_type,
            )
            chunks = RecursiveCharacterTextSplitter(
                chunk_size=CHUNK_MAX_SIZE,
                chunk_overlap=CHUNK_OVERLAP,
                separators=_CHINESE_SEPARATORS,
            ).split_documents([doc])
            for chunk in chunks:
                chunk.metadata.setdefault("heading_path", "")
        else:
            chunks = splitter(doc)

        for chunk in chunks:
            if not chunk.page_content or not chunk.page_content.strip():
                continue

            source = str(chunk.metadata.get("source", ""))
            local_index = source_chunk_counters.get(source, 0)

            # 写入文档内与全局 chunk 序号
            chunk.metadata["chunk_index"] = local_index
            chunk.metadata["global_chunk_index"] = global_chunk_counter

            # 规范 page 字段为 int（PDF loader 可能缺省）
            if "page" in chunk.metadata:
                try:
                    chunk.metadata["page"] = int(chunk.metadata["page"])
                except Exception:
                    chunk.metadata.pop("page", None)

            source_chunk_counters[source] = local_index + 1
            global_chunk_counter += 1
            all_chunks.append(chunk)

    logger.info("[splitter] total: %d docs → %d chunks", len(docs), len(all_chunks))
    return all_chunks
