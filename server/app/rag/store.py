"""向量数据库存储 — ChromaDB 向量索引 + BM25 关键词索引。

公共接口：
  build_store()       构建向量库（ChromaDB）
  build_bm25()        构建 BM25 索引并持久化
  verify_store()      验证向量库完整性

Called by: app/rag/indexing/build.py.
User instruction: "还有存到向量数据库中的文件，需要设计好rag系统...每个模块要划分开，不要耦合"
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any

import chromadb
from langchain_core.documents import Document

from app.infra.logging import get_logger
from app.rag.embeddings import embed_documents
from app.rag.bm25 import BM25Index
from app.rag.models import CHROMA_COLLECTION

logger = get_logger(__name__)

SCHEMA_VERSION = "1"


# 基于来源与内容生成稳定的 chunk 哈希 ID
def _stable_chunk_id(doc: Document) -> str:
    """生成稳定的 chunk 哈希 ID。"""
    source = doc.metadata.get("source", "")
    section = doc.metadata.get("section", "")
    heading_path = doc.metadata.get("heading_path", "")
    content = doc.page_content
    raw = f"{source}|{section}|{heading_path}|{content}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


# 确保每个 chunk 具备稳定唯一 ID（Chroma 与 BM25 共用，保证对齐）
def _ensure_chunk_ids(chunks: list[Document]) -> None:
    """确保每个 chunk 都有稳定且唯一的 chunk_id。

    build_store 与 build_bm25 共用此函数，保证 Chroma 与 BM25 使用完全一致的 chunk_id，
    使得 RRF 融合、去重、前端来源追踪能正确对应同一段内容。已有 chunk_id 会被复用（幂等）。
    """
    seen_ids: set[str] = set()
    dup_count = 0

    for chunk in chunks:
        chunk_id = str(chunk.metadata.get("chunk_id", "")).strip()
        # 缺失则重新生成稳定 ID
        if not chunk_id:
            chunk_id = _stable_chunk_id(chunk)

        # 冲突时追加后缀保证唯一
        if chunk_id in seen_ids:
            dup_count += 1
            chunk_id = f"{chunk_id}_{dup_count}"

        seen_ids.add(chunk_id)
        chunk.metadata["chunk_id"] = chunk_id
        chunk.metadata["schema_version"] = SCHEMA_VERSION

    if dup_count:
        logger.warning("[store] %d duplicate chunk IDs resolved by suffix", dup_count)


# 构建 ChromaDB 向量库，返回 (文档数, chunk 数)
def build_store(
    chunks: list[Document],
    output_dir: Path,
    collection: str = CHROMA_COLLECTION,
    batch_size: int = 32,
) -> tuple[int, int]:
    """构建向量库（ChromaDB），返回 (doc_count, chunk_count)。

    使用 ChromaDB PersistentClient 直接写入，批量嵌入文档文本。

    Args:
        chunks: 切分后的 Document 列表（metadata 已填充）。
        output_dir: 索引输出目录。
        collection: ChromaDB collection 名称。
        batch_size: 嵌入批量大小。

    Returns:
        (doc_count, chunk_count) 元组。
    """
    if not chunks:
        raise ValueError("No chunks to index")

    # 统计唯一来源文档数
    unique_sources: set[str] = set()
    for chunk in chunks:
        unique_sources.add(chunk.metadata.get("source", ""))
    doc_count = len(unique_sources)

    # 统一分配 chunk_id（与 BM25 对齐，便于融合与去重）
    _ensure_chunk_ids(chunks)

    all_ids: list[str] = []
    all_texts: list[str] = []
    all_metas: list[dict[str, Any]] = []

    for chunk in chunks:
        chunk_id = str(chunk.metadata["chunk_id"])
        meta = dict(chunk.metadata)

        all_ids.append(chunk_id)
        all_texts.append(chunk.page_content)
        all_metas.append(meta)

    total_chunks = len(all_ids)
    if total_chunks == 0:
        raise ValueError("No chunks produced after deduplication")

    # 创建 Chroma 集合，显式声明 cosine 距离（与 manifest 一致）
    client = chromadb.PersistentClient(path=str(output_dir))
    col = client.create_collection(
        name=collection,
        metadata={"hnsw:space": "cosine"},
    )

    # 分批嵌入文本并写入向量库
    for start in range(0, total_chunks, batch_size):
        end = min(start + batch_size, total_chunks)
        batch_texts = all_texts[start:end]
        batch_ids = all_ids[start:end]
        batch_metas = all_metas[start:end]

        # 嵌入失败则中断构建
        embeddings = embed_documents(batch_texts)
        if embeddings is None:
            raise RuntimeError(
                f"Embedding failed at batch starting index {start}. "
                "Cannot build index without embeddings."
            )

        col.add(ids=batch_ids, documents=batch_texts, embeddings=embeddings, metadatas=batch_metas)
        # 批次间短暂停顿，缓解嵌入服务压力
        if end < total_chunks:
            time.sleep(0.1)

    logger.info("[store] ChromaDB index built: %d docs, %d chunks", doc_count, total_chunks)
    return doc_count, total_chunks


# 构建 BM25 索引并持久化（失败不致命）
def build_bm25(chunks: list[Document], output_dir: Path) -> None:
    """构建 BM25 索引并持久化。

    Args:
        chunks: 切分后的 Document 列表。
        output_dir: 索引输出目录。
    """
    # 复用同一 chunk_id 分配逻辑，保证 BM25 与 Chroma 对齐
    _ensure_chunk_ids(chunks)

    texts = [chunk.page_content for chunk in chunks]
    metadatas = [dict(chunk.metadata) for chunk in chunks]

    try:
        bm25 = BM25Index()
        bm25.build(texts, metadatas)
        bm25.save(output_dir)
        logger.info("[store] BM25 index built and saved")
    except Exception as exc:
        # BM25 构建失败不影响向量库可用性
        logger.warning("[store] BM25 index build failed (non-fatal): %s", exc)


# 重新打开索引并校验 chunk 数量完整性
def verify_store(
    output_dir: Path,
    collection: str = CHROMA_COLLECTION,
    expected_count: int | None = None,
) -> None:
    """验证向量库完整性。

    重新打开索引并检查 collection 数量。

    Args:
        output_dir: 索引目录。
        collection: collection 名称。
        expected_count: 期望的 chunk 数量，为 None 则跳过数量校验。

    Raises:
        RuntimeError: 验证失败。
    """
    try:
        client = chromadb.PersistentClient(path=str(output_dir))
        col = client.get_collection(name=collection)
        actual = col.count()

        # 实际数量与期望不符则校验失败
        if expected_count is not None and actual != expected_count:
            raise RuntimeError(
                f"Verification failed: expected {expected_count} chunks, found {actual}"
            )

        logger.info("[store] verification passed: %d chunks", actual)
    except RuntimeError:
        # 已明确的校验错误直接上抛
        raise
    except Exception as exc:
        # 其它异常包装为 RuntimeError 上抛
        raise RuntimeError(f"Store verification failed: {exc}") from exc
