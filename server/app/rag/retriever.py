"""单路向量检索模块。

唯一公共接口：retrieve() 和 check_index_health()。
ChatAgent 不感知 Chroma、embedding、distance 等细节。
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

import chromadb
from pydantic import BaseModel

from app.config import (
    KB_DIR,
    KB_ENABLED,
    KB_EMBED_MODEL,
    KB_TOP_K,
)
from app.infra.logging import get_logger
from app.rag.bm25 import get_bm25_index  # hybrid search: BM25 keyword retrieval
from app.rag.embeddings import embed_query
from app.rag.models import CHROMA_COLLECTION, RetrievedChunk, RetrievalResult

logger = get_logger(__name__)

# 并发检索限制
_semaphore = asyncio.Semaphore(4)

# Manifest 文件名
_MANIFEST_FILENAME = "manifest.json"

# 混合检索内部参数（实现细节，不暴露为运行时配置）
_FETCH_K = 12          # 向量检索拉取数量，融合后截断到 top_k
_RRF_K = 60            # RRF 融合常数（Cormack et al. 2009 推荐 60）


class IndexHealth(BaseModel):
    """索引健康状态。"""

    ready: bool
    reason: str
    document_count: int = 0
    chunk_count: int = 0


def _load_manifest(kb_dir: Path) -> dict[str, Any] | None:
    manifest_path = kb_dir / _MANIFEST_FILENAME
    if not manifest_path.exists():
        return None
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _validate_manifest(manifest: dict[str, Any] | None, kb_dir: Path) -> IndexHealth:
    """校验 Manifest 和实际索引一致性。"""
    if manifest is None:
        return IndexHealth(ready=False, reason="manifest_missing")

    schema_version = str(manifest.get("schema_version", ""))
    if schema_version != "1":
        return IndexHealth(ready=False, reason=f"schema_version_mismatch:{schema_version}")

    collection_name = str(manifest.get("collection", ""))
    if collection_name != CHROMA_COLLECTION:
        return IndexHealth(ready=False, reason=f"collection_mismatch:{collection_name}")

    embed_model = str(manifest.get("embedding_model", ""))
    if embed_model and embed_model != KB_EMBED_MODEL:
        return IndexHealth(ready=False, reason=f"embedding_model_mismatch:{embed_model}")

    chunk_count = int(manifest.get("chunk_count", 0))
    if chunk_count <= 0:
        return IndexHealth(ready=False, reason="chunk_count_zero")

    # 校验 Chroma 实际数量
    try:
        client = chromadb.PersistentClient(path=str(kb_dir))
        collection = client.get_collection(name=CHROMA_COLLECTION)
        actual_count = collection.count()
        if actual_count != chunk_count:
            return IndexHealth(
                ready=False,
                reason=f"count_mismatch:manifest={chunk_count},actual={actual_count}",
            )
    except Exception as exc:
        return IndexHealth(ready=False, reason=f"chroma_error:{exc}")

    return IndexHealth(ready=True, reason="ok", document_count=0, chunk_count=chunk_count)


def check_index_health() -> IndexHealth:
    """检查知识库索引健康状态（非阻塞，不请求嵌入服务）。

    供 FastAPI lifespan 调用，异常不影响启动。
    """
    if not KB_ENABLED:
        return IndexHealth(ready=False, reason="disabled_by_config")

    kb_dir = Path(KB_DIR)
    if not kb_dir.exists():
        return IndexHealth(ready=False, reason="kb_dir_missing")

    try:
        manifest = _load_manifest(kb_dir)
        return _validate_manifest(manifest, kb_dir)
    except Exception as exc:
        logger.warning("[retriever] index health check failed: %s", exc)
        return IndexHealth(ready=False, reason=f"unexpected_error:{exc}")


def _build_query_text(query: str, course_name: str | None) -> str:
    """构建实际查询文本。

    课程名称直接加入查询，利用 bge-m3 的语义理解能力
    将检索聚焦到相关教材，无需 LLM 路由或 metadata 过滤。
    """
    parts: list[str] = []
    if course_name and course_name.strip():
        parts.append(course_name.strip())
    parts.append(query.strip())
    return " ".join(parts)


def _chroma_query(
    query_embedding: list[float],
    fetch_k: int,
    where_filter: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """同步 Chroma 向量检索（在线程池中调用）。"""
    client = chromadb.PersistentClient(path=str(KB_DIR))
    collection = client.get_collection(name=CHROMA_COLLECTION)
    query_kwargs: dict[str, Any] = dict(
        query_embeddings=[query_embedding],
        n_results=fetch_k,
        include=["documents", "metadatas", "distances"],
    )
    if where_filter:
        query_kwargs["where"] = where_filter
    results = collection.query(**query_kwargs)
    return results


def _parse_chroma_results(
    results: dict[str, Any],
) -> list[RetrievedChunk]:
    """解析 Chroma 查询结果为 RetrievedChunk 列表。"""
    chunks: list[RetrievedChunk] = []
    seen_ids: set[str] = set()

    if not results:
        return chunks

    documents = (results.get("documents") or [[]])[0]
    metadatas = (results.get("metadatas") or [[]])[0]
    distances = (results.get("distances") or [[]])[0]

    for doc, meta, dist in zip(documents, metadatas, distances, strict=False):
        text = str(doc or "").strip()
        if not text:
            continue

        chunk_id = str(meta.get("chunk_id", "")) if meta else ""
        source = str(meta.get("source", "")) if meta else ""
        title = str(meta.get("title", "")) if meta else ""
        section = str(meta.get("section", "")) if meta else ""
        course = str(meta.get("course", "")) if meta else ""
        parent_id = str(meta.get("parent_id", "")) if meta else ""
        heading_path = str(meta.get("heading_path", "")) if meta else ""

        # chunk_id 去重
        if chunk_id and chunk_id in seen_ids:
            continue
        if chunk_id:
            seen_ids.add(chunk_id)

        chunks.append(
            RetrievedChunk(
                chunk_id=chunk_id,
                content=text,
                source=source,
                title=title,
                section=section,
                course=course,
                distance=float(dist) if dist is not None else None,
                parent_id=parent_id,
                heading_path=heading_path,
            )
        )

    return chunks


def _bm25_query(query: str, top_k: int) -> list[RetrievedChunk]:
    """BM25 关键词检索（内存操作，无 IO 阻塞）。"""
    kb_dir = Path(KB_DIR)
    index = get_bm25_index(kb_dir)
    if not index.is_ready:
        return []

    results = index.search(query, top_k=top_k * 2)
    chunks: list[RetrievedChunk] = []
    seen: set[str] = set()

    for r in results:
        chunk_id = str(r.get("chunk_id", ""))
        if chunk_id and chunk_id in seen:
            continue
        if chunk_id:
            seen.add(chunk_id)

        chunks.append(
            RetrievedChunk(
                chunk_id=chunk_id,
                content=str(r.get("text", r.get("source", ""))),
                source=str(r.get("source", "")),
                title=str(r.get("title", "")),
                section=str(r.get("section", "")),
                course=str(r.get("course", "")),
                distance=None,
                parent_id=str(r.get("parent_id", "")),
                heading_path=str(r.get("heading_path", "")),
            )
        )

    return chunks


def _rrf_fusion(
    vector_chunks: list[RetrievedChunk],
    bm25_chunks: list[RetrievedChunk],
    top_k: int,
    k: int = 60,
) -> list[RetrievedChunk]:
    """Reciprocal Rank Fusion: score(d) = Σ 1/(k + rank_i)

    Args:
        vector_chunks: 向量检索结果（按相似度降序）
        bm25_chunks: BM25 检索结果（按分数降序）
        top_k: 返回数量
        k: RRF 平滑常数（默认 60, Cormack et al. 2009）
    """
    doc_scores: dict[str, float] = {}
    doc_objects: dict[str, RetrievedChunk] = {}

    for rank, chunk in enumerate(vector_chunks, start=1):
        key = chunk.chunk_id or f"v_{hash(chunk.content[:200])}"
        doc_scores[key] = doc_scores.get(key, 0) + 1.0 / (k + rank)
        if key not in doc_objects:
            doc_objects[key] = chunk

    for rank, chunk in enumerate(bm25_chunks, start=1):
        key = chunk.chunk_id or f"b_{hash(chunk.content[:200])}"
        doc_scores[key] = doc_scores.get(key, 0) + 1.0 / (k + rank)
        if key not in doc_objects:
            doc_objects[key] = chunk

    sorted_keys = sorted(doc_scores.keys(), key=lambda d: doc_scores[d], reverse=True)

    return [doc_objects[k] for k in sorted_keys[:top_k]]


async def retrieve(
    query: str,
    *,
    course_name: str | None = None,
    top_k: int | None = None,
) -> RetrievalResult:
    """执行混合检索（向量 + BM25，RRF 融合）。

    同时执行向量检索和 BM25 关键词检索，使用 RRF 融合两路结果；
    BM25 无结果时退化为纯向量检索。

    Args:
        query: 用户查询文本。
        course_name: 可选课程名称，用于 ChromaDB where 过滤 + 查询增强。
        top_k: 返回结果数，默认从配置读取，限制 1~8。

    Returns:
        结构化检索结果，status 为 ok/empty/unavailable。
    """
    normalized_query = (query or "").strip()
    if not normalized_query:
        return RetrievalResult(status="empty", query="")

    if not KB_ENABLED:
        return RetrievalResult(status="unavailable", query=normalized_query, message="KB disabled")

    # 校验 top_k 范围
    effective_k = max(1, min(8, top_k or KB_TOP_K))
    fetch_k = max(effective_k, _FETCH_K)

    start = time.monotonic()

    async with _semaphore:
        # 校验索引
        health = check_index_health()
        if not health.ready:
            return RetrievalResult(
                status="unavailable",
                query=normalized_query,
                message=f"index not ready: {health.reason}",
            )

        # 构建查询文本
        query_text = _build_query_text(normalized_query, course_name)

        # 构建 ChromaDB where 过滤
        where_filter: dict[str, Any] | None = None
        if course_name and course_name.strip():
            where_filter = {"course": {"$eq": course_name.strip()}}

        # 请求 embedding
        embedding = embed_query(query_text)
        if embedding is None:
            return RetrievalResult(
                status="unavailable",
                query=normalized_query,
                message="embedding unavailable",
            )

        # Chroma 向量检索
        try:
            results = await asyncio.to_thread(_chroma_query, embedding, fetch_k, where_filter)
        except Exception as exc:
            logger.warning("[retriever] chroma query failed: %s", exc)
            return RetrievalResult(
                status="unavailable",
                query=normalized_query,
                message=f"chroma error: {exc}",
            )

    # 解析向量检索结果
    vector_chunks = _parse_chroma_results(results)

    # 混合检索：向量 + BM25，RRF 融合（BM25 无结果时退化为纯向量）
    bm25_chunks = _bm25_query(normalized_query, effective_k)
    if bm25_chunks:
        chunks = _rrf_fusion(vector_chunks, bm25_chunks, effective_k, k=_RRF_K)
    else:
        chunks = vector_chunks[:effective_k]

    if not chunks:
        elapsed = int((time.monotonic() - start) * 1000)
        return RetrievalResult(
            status="empty",
            query=normalized_query,
            elapsed_ms=elapsed,
        )

    elapsed = int((time.monotonic() - start) * 1000)
    return RetrievalResult(
        status="ok",
        query=normalized_query,
        chunks=chunks,
        elapsed_ms=elapsed,
    )
