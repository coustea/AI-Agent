"""向量数据库存储 — ChromaDB 向量索引 + BM25 关键词索引。

公共接口：
  build_store()       构建向量库（ChromaDB）
  build_bm25()        构建 BM25 索引并持久化
  verify_store()      验证向量库完整性

Called by: app/rag/build.py.
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any

import chromadb
from langchain_core.documents import Document

from app.infra.logging import get_logger
from app.rag.bm25 import BM25Index
from app.rag.embeddings import embed_documents
from app.rag.models import CHROMA_COLLECTION, SCHEMA_VERSION

logger = get_logger(__name__)

# 向量构建进度日志策略
_PROGRESS_BATCH_INTERVAL = 25
_PROGRESS_SECONDS_INTERVAL = 10.0

# 批次间短暂停顿，缓解本地 embedding 服务压力。
_BATCH_SLEEP_SECONDS = 0.1


# ============ 工具函数 ============


def _format_duration(seconds: float) -> str:
    """格式化耗时 / ETA。"""
    seconds = max(0, int(seconds))

    if seconds < 60:
        return f"{seconds}s"

    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m{sec:02d}s"

    hours, minutes = divmod(minutes, 60)
    return f"{hours}h{minutes:02d}m{sec:02d}s"


def _stable_chunk_id(doc: Document) -> str:
    """基于来源与内容生成稳定的 chunk 哈希 ID。"""
    source = doc.metadata.get("source", "")
    section = doc.metadata.get("section", "")
    heading_path = doc.metadata.get("heading_path", "")
    content = doc.page_content
    raw = f"{source}|{section}|{heading_path}|{content}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _ensure_chunk_ids(chunks: list[Document]) -> None:
    """确保每个 chunk 都有稳定且唯一的 chunk_id。

    build_store 与 build_bm25 共用此函数，保证 Chroma 与 BM25 使用完全一致的 chunk_id。
    """
    seen_ids: set[str] = set()
    dup_count = 0

    for chunk in chunks:
        chunk_id = str(chunk.metadata.get("chunk_id", "")).strip()

        if not chunk_id:
            chunk_id = _stable_chunk_id(chunk)

        if chunk_id in seen_ids:
            dup_count += 1
            chunk_id = f"{chunk_id}_{dup_count}"

        seen_ids.add(chunk_id)
        chunk.metadata["chunk_id"] = chunk_id
        chunk.metadata["schema_version"] = SCHEMA_VERSION

    if dup_count:
        logger.warning("[store] %d duplicate chunk IDs resolved by suffix", dup_count)


def _should_log_progress(
    *,
    batch_no: int,
    total_batches: int,
    last_log_time: float,
) -> bool:
    """判断当前批次是否需要输出进度日志。"""
    if batch_no == 1:
        return True

    if batch_no == total_batches:
        return True

    if batch_no % _PROGRESS_BATCH_INTERVAL == 0:
        return True

    return time.monotonic() - last_log_time >= _PROGRESS_SECONDS_INTERVAL


def _log_vector_progress(
    *,
    batch_no: int,
    total_batches: int,
    processed: int,
    total_chunks: int,
    start_time: float,
) -> None:
    """输出向量构建进度日志。"""
    elapsed = time.monotonic() - start_time
    rate = processed / elapsed if elapsed > 0 else 0.0
    remaining = max(0, total_chunks - processed)
    eta = remaining / rate if rate > 0 else 0.0
    percent = processed / total_chunks * 100 if total_chunks else 100.0

    logger.info(
        "[store] vector progress: batch=%d/%d chunks=%d/%d %.2f%% speed=%.1f chunks/s elapsed=%s eta=%s",
        batch_no,
        total_batches,
        processed,
        total_chunks,
        percent,
        rate,
        _format_duration(elapsed),
        _format_duration(eta),
    )


# ============ ChromaDB 向量库构建 ============


def build_store(
    chunks: list[Document],
    output_dir: Path,
    collection: str = CHROMA_COLLECTION,
    batch_size: int = 32,
) -> tuple[int, int]:
    """构建向量库（ChromaDB），返回 (doc_count, chunk_count)。

    使用 ChromaDB PersistentClient 直接写入，批量调用 embedding 模型生成向量。
    构建过程中会输出批次进度，避免大知识库构建时看起来像卡住。
    """
    if not chunks:
        raise ValueError("No chunks to index")

    if batch_size <= 0:
        raise ValueError("batch_size must be greater than 0")

    # 统计唯一来源文档数
    unique_sources: set[str] = set()
    for chunk in chunks:
        unique_sources.add(str(chunk.metadata.get("source", "")))
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

    total_batches = (total_chunks + batch_size - 1) // batch_size

    logger.info(
        "[store] ChromaDB build started: docs=%d chunks=%d batch_size=%d batches=%d output=%s collection=%s",
        doc_count,
        total_chunks,
        batch_size,
        total_batches,
        output_dir,
        collection,
    )

    # 创建 Chroma 集合，显式声明 cosine 距离（与 manifest 一致）
    client = chromadb.PersistentClient(path=str(output_dir))
    col = client.create_collection(
        name=collection,
        metadata={"hnsw:space": "cosine"},
    )

    started_at = time.monotonic()
    last_log_time = 0.0

    # 分批嵌入文本并写入向量库
    for batch_no, start in enumerate(range(0, total_chunks, batch_size), start=1):
        end = min(start + batch_size, total_chunks)

        batch_texts = all_texts[start:end]
        batch_ids = all_ids[start:end]
        batch_metas = all_metas[start:end]

        if _should_log_progress(
            batch_no=batch_no,
            total_batches=total_batches,
            last_log_time=last_log_time,
        ):
            logger.info(
                "[store] embedding batch started: batch=%d/%d range=%d-%d size=%d",
                batch_no,
                total_batches,
                start + 1,
                end,
                len(batch_texts),
            )

        # 嵌入失败则中断构建
        embeddings = embed_documents(batch_texts)
        if embeddings is None:
            raise RuntimeError(
                f"Embedding failed at batch {batch_no}/{total_batches}, "
                f"starting index {start}. Cannot build index without embeddings."
            )

        if len(embeddings) != len(batch_texts):
            raise RuntimeError(
                f"Embedding count mismatch at batch {batch_no}/{total_batches}: "
                f"expected {len(batch_texts)}, got {len(embeddings)}"
            )

        col.add(
            ids=batch_ids,
            documents=batch_texts,
            embeddings=embeddings,
            metadatas=batch_metas,
        )

        processed = end

        if _should_log_progress(
            batch_no=batch_no,
            total_batches=total_batches,
            last_log_time=last_log_time,
        ):
            _log_vector_progress(
                batch_no=batch_no,
                total_batches=total_batches,
                processed=processed,
                total_chunks=total_chunks,
                start_time=started_at,
            )
            last_log_time = time.monotonic()

        # 批次间短暂停顿，缓解 embedding 服务压力
        if end < total_chunks and _BATCH_SLEEP_SECONDS > 0:
            time.sleep(_BATCH_SLEEP_SECONDS)

    elapsed = time.monotonic() - started_at
    logger.info(
        "[store] ChromaDB index built: docs=%d chunks=%d batches=%d elapsed=%s avg_speed=%.1f chunks/s",
        doc_count,
        total_chunks,
        total_batches,
        _format_duration(elapsed),
        total_chunks / elapsed if elapsed > 0 else 0.0,
    )

    return doc_count, total_chunks


# ============ BM25 关键词索引构建 ============


def build_bm25(chunks: list[Document], output_dir: Path) -> None:
    """构建 BM25 索引并持久化。

    BM25 构建失败不影响向量库可用性，但会影响关键词检索和 embedding 失败时的兜底检索。
    """
    if not chunks:
        logger.warning("[store] BM25 skipped: empty chunks")
        return

    started_at = time.monotonic()
    logger.info("[store] BM25 build started: chunks=%d output=%s", len(chunks), output_dir)

    # 复用同一 chunk_id 分配逻辑，保证 BM25 与 Chroma 对齐
    _ensure_chunk_ids(chunks)

    texts = [chunk.page_content for chunk in chunks]
    metadatas = [dict(chunk.metadata) for chunk in chunks]

    try:
        bm25 = BM25Index()
        bm25.build(texts, metadatas)
        bm25.save(output_dir)

        elapsed = time.monotonic() - started_at
        logger.info(
            "[store] BM25 index built and saved: chunks=%d elapsed=%s",
            len(chunks),
            _format_duration(elapsed),
        )
    except Exception as exc:
        logger.warning("[store] BM25 index build failed (non-fatal): %s", exc)


# ============ 向量库完整性校验 ============


def verify_store(
    output_dir: Path,
    collection: str = CHROMA_COLLECTION,
    expected_count: int | None = None,
) -> None:
    """验证向量库完整性。

    重新打开索引并检查 collection 数量。
    """
    try:
        logger.info(
            "[store] verification started: output=%s collection=%s expected_count=%s",
            output_dir,
            collection,
            expected_count,
        )

        client = chromadb.PersistentClient(path=str(output_dir))
        col = client.get_collection(name=collection)
        actual = col.count()

        if expected_count is not None and actual != expected_count:
            raise RuntimeError(
                f"Verification failed: expected {expected_count} chunks, found {actual}"
            )

        logger.info("[store] verification passed: %d chunks", actual)

    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Store verification failed: {exc}") from exc