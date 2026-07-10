"""混合检索模块（向量 + BM25，RRF 融合）。

唯一公共接口：retrieve() 和 check_index_health()。
ChatAgent 不感知 Chroma、embedding、distance 等细节。

优化点（per user 要求）：
  1. BM25 先执行，embedding 不可用时 BM25 兜底
  2. course_name 软过滤，不足时放宽为全库检索
  3. 扩大召回后融合截断
  4. BM25 结果不再用 source 冒充正文

Called by: app/rag/tools.py (retrieve), app/rag/indexing/build.py (check_index_health),
           app/main.py lifespan (check_index_health).
Per user: "retrieve() 里 embedding 失败就直接返回 unavailable，没有使用 BM25 兜底"
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
from app.rag.bm25 import get_bm25_index
from app.rag.embeddings import embed_query
from app.rag.models import CHROMA_COLLECTION, RetrievedChunk, RetrievalResult

logger = get_logger(__name__)

# 并发检索限制
_semaphore = asyncio.Semaphore(4)

# Manifest 文件名
_MANIFEST_FILENAME = "manifest.json"

# 混合检索内部参数
_VECTOR_FETCH_K = 40       # 向量召回数量，先多召回
_BM25_FETCH_K = 40         # BM25 召回数量
_RRF_CANDIDATE_K = 20      # RRF 融合后保留候选
_RRF_K = 60                # RRF 平滑常数
_FINAL_TOP_K_LIMIT = 8     # 对外最多返回 8 条


# 索引健康状态模型
class IndexHealth(BaseModel):
    """索引健康状态。"""

    ready: bool
    reason: str
    document_count: int = 0
    chunk_count: int = 0


# ============ 辅助函数 ============


# 安全将值转为 int，失败返回 None
def _safe_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except Exception:
        return None


# 将向量距离转换为 0~1 相似度分数（距离越小越相似）
def _distance_to_score(distance: float | None) -> float | None:
    """把向量距离转成 0~1 左右的相似度分数。

    Chroma distance 越小越相似，这里只作为展示/排序辅助，不作为唯一依据。
    """
    if distance is None:
        return None
    try:
        d = max(0.0, float(distance))
        return 1.0 / (1.0 + d)
    except Exception:
        return None


# 按 chunk_id 去重，保留首次出现的结果
def _dedupe_chunks(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """按 chunk_id 去重，保留先出现的结果。"""
    seen: set[str] = set()
    deduped: list[RetrievedChunk] = []

    for chunk in chunks:
        key = chunk.chunk_id or f"{chunk.source}:{chunk.chunk_index}:{hash(chunk.content[:120])}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(chunk)

    return deduped


# 计算自 start 起的耗时（毫秒）
def _elapsed_ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)


# ============ 索引健康检查 ============


# 读取索引 manifest，失败返回 None
def _load_manifest(kb_dir: Path) -> dict[str, Any] | None:
    manifest_path = kb_dir / _MANIFEST_FILENAME
    if not manifest_path.exists():
        return None
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return None


# 校验 manifest 与实际 Chroma 索引的一致性
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


# 非阻塞检查索引健康状态（不请求嵌入服务）
def check_index_health(kb_dir: Path | None = None) -> IndexHealth:
    """检查知识库索引健康状态（非阻塞，不请求嵌入服务）。

    供 FastAPI lifespan 与 build.py --check-only 调用，异常不影响启动。
    传入 kb_dir 时检查指定目录，否则回退到配置中的 KB_DIR。
    """
    # 配置未启用或目录缺失直接返回不健康
    if not KB_ENABLED:
        return IndexHealth(ready=False, reason="disabled_by_config")

    target_dir = Path(kb_dir) if kb_dir else Path(KB_DIR)
    if not target_dir.exists():
        return IndexHealth(ready=False, reason="kb_dir_missing")

    try:
        manifest = _load_manifest(target_dir)
        return _validate_manifest(manifest, target_dir)
    except Exception as exc:
        # 健康检查异常不影响服务启动
        logger.warning("[retriever] index health check failed: %s", exc)
        return IndexHealth(ready=False, reason=f"unexpected_error:{exc}")


# ============ 查询构建 ============


# 拼接课程名与查询文本，引导向量检索聚焦相关教材
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


# ============ 向量检索 ============


# 同步执行 Chroma 向量检索（在线程池中调用）
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
    # 传入课程过滤条件
    if where_filter:
        query_kwargs["where"] = where_filter
    results = collection.query(**query_kwargs)
    return results


# 将 Chroma 原始查询结果解析为 RetrievedChunk 列表
def _parse_chroma_results(results: dict[str, Any]) -> list[RetrievedChunk]:
    """解析 Chroma 查询结果为 RetrievedChunk 列表。"""
    chunks: list[RetrievedChunk] = []
    seen_ids: set[str] = set()

    # 无结果直接返回空
    if not results:
        return chunks

    documents = (results.get("documents") or [[]])[0]
    metadatas = (results.get("metadatas") or [[]])[0]
    distances = (results.get("distances") or [[]])[0]

    for doc, meta, dist in zip(documents, metadatas, distances, strict=False):
        text = str(doc or "").strip()
        if not text:
            continue

        meta = meta or {}

        chunk_id = str(meta.get("chunk_id", ""))
        # 同一结果集内按 chunk_id 去重
        if chunk_id and chunk_id in seen_ids:
            continue
        if chunk_id:
            seen_ids.add(chunk_id)

        distance = float(dist) if dist is not None else None

        chunks.append(
            RetrievedChunk(
                chunk_id=chunk_id,
                content=text,
                source=str(meta.get("source", "")),
                title=str(meta.get("title", "")),
                section=str(meta.get("section", "")),
                course=str(meta.get("course", "")),
                distance=distance,
                score=_distance_to_score(distance),
                retrieval_type="vector",
                parent_id=str(meta.get("parent_id", "")),
                heading_path=str(meta.get("heading_path", "")),
                page=_safe_int(meta.get("page")),
                chunk_index=_safe_int(meta.get("chunk_index")),
            )
        )

    return chunks


# 向量检索：优先课程过滤，结果不足时自动放宽到全库
async def _vector_search_soft_course(
    embedding: list[float],
    course_name: str | None,
    fetch_k: int,
    min_results: int,
) -> list[RetrievedChunk]:
    """向量检索：优先课程过滤，不足时自动放宽。

    避免 course metadata 推断不准导致直接查空。
    """
    where_filter: dict[str, Any] | None = None
    if course_name and course_name.strip():
        where_filter = {"course": {"$eq": course_name.strip()}}

    chunks: list[RetrievedChunk] = []

    # 先尝试课程过滤检索
    if where_filter:
        try:
            filtered_results = await asyncio.to_thread(
                _chroma_query,
                embedding,
                fetch_k,
                where_filter,
            )
            chunks.extend(_parse_chroma_results(filtered_results))
        except Exception as exc:
            logger.warning("[retriever] chroma filtered query failed: %s", exc)

        # 课程过滤结果已足够则直接返回
        if len(chunks) >= min_results:
            return _dedupe_chunks(chunks)

    # 课程过滤不足或失败，放宽到全库检索
    try:
        broad_results = await asyncio.to_thread(
            _chroma_query,
            embedding,
            fetch_k,
            None,
        )
        chunks.extend(_parse_chroma_results(broad_results))
    except Exception as exc:
        logger.warning("[retriever] chroma broad query failed: %s", exc)

    return _dedupe_chunks(chunks)


# ============ BM25 检索 ============


# BM25 关键词检索（内存操作，无 IO 阻塞）
def _bm25_query(query: str, top_k: int) -> list[RetrievedChunk]:
    """BM25 关键词检索（内存操作，无 IO 阻塞）。"""
    kb_dir = Path(KB_DIR)
    index = get_bm25_index(kb_dir)
    if not index.is_ready:
        return []

    results = index.search(query, top_k=top_k)
    chunks: list[RetrievedChunk] = []
    seen: set[str] = set()

    for r in results:
        chunk_id = str(r.get("chunk_id", ""))
        if chunk_id and chunk_id in seen:
            continue
        if chunk_id:
            seen.add(chunk_id)

        text = str(r.get("text", "")).strip()
        if not text:
            # 旧索引可能缺正文，跳过避免把 source 当正文返回
            continue

        score = r.get("score", r.get("bm25_score"))

        chunks.append(
            RetrievedChunk(
                chunk_id=chunk_id,
                content=text,
                source=str(r.get("source", "")),
                title=str(r.get("title", "")),
                section=str(r.get("section", "")),
                course=str(r.get("course", "")),
                distance=None,
                score=float(score) if score is not None else None,
                retrieval_type="bm25",
                parent_id=str(r.get("parent_id", "")),
                heading_path=str(r.get("heading_path", "")),
                page=_safe_int(r.get("page")),
                chunk_index=_safe_int(r.get("chunk_index")),
            )
        )

    return chunks


# ============ RRF 融合 ============


# RRF 倒数排名融合：score = Σ 1/(k + rank)
def _rrf_fusion(
    vector_chunks: list[RetrievedChunk],
    bm25_chunks: list[RetrievedChunk],
    top_k: int,
    k: int = 60,
) -> list[RetrievedChunk]:
    """Reciprocal Rank Fusion: score(d) = Σ 1/(k + rank_i)。"""
    doc_scores: dict[str, float] = {}
    doc_objects: dict[str, RetrievedChunk] = {}
    doc_sources: dict[str, set[str]] = {}

    def add_chunks(chunks: list[RetrievedChunk], retrieval_type: str) -> None:
        for rank, chunk in enumerate(chunks, start=1):
            key = chunk.chunk_id or f"{chunk.source}:{chunk.chunk_index}:{hash(chunk.content[:120])}"

            doc_scores[key] = doc_scores.get(key, 0.0) + 1.0 / (k + rank)
            doc_sources.setdefault(key, set()).add(retrieval_type)

            if key not in doc_objects:
                doc_objects[key] = chunk

    # 分别把向量与 BM25 结果加入融合打分
    add_chunks(vector_chunks, "vector")
    add_chunks(bm25_chunks, "bm25")

    # 按融合分数降序排列
    sorted_keys = sorted(doc_scores.keys(), key=lambda d: doc_scores[d], reverse=True)

    fused: list[RetrievedChunk] = []
    for key in sorted_keys[:top_k]:
        chunk = doc_objects[key]
        chunk.score = doc_scores[key]

        # 根据命中来源标注检索类型
        source_types = doc_sources.get(key, set())
        if "vector" in source_types and "bm25" in source_types:
            chunk.retrieval_type = "hybrid"
        elif "bm25" in source_types:
            chunk.retrieval_type = "bm25"
        else:
            chunk.retrieval_type = "vector"

        fused.append(chunk)

    return fused


# ============ 公共接口 ============


# 混合检索公共接口：BM25 兜底 + 向量检索 + RRF 融合
async def retrieve(
    query: str,
    *,
    course_name: str | None = None,
    top_k: int | None = None,
) -> RetrievalResult:
    """执行混合检索（向量 + BM25，RRF 融合）。

    优化点：
    1. BM25 先执行，embedding 不可用时可兜底。
    2. course_name 使用软过滤，避免 metadata 不准导致查空。
    3. 扩大召回，再融合截断。
    """
    # 空查询直接返回 empty
    normalized_query = (query or "").strip()
    if not normalized_query:
        return RetrievalResult(status="empty", query="")

    # 知识库未启用返回 unavailable
    if not KB_ENABLED:
        return RetrievalResult(
            status="unavailable",
            query=normalized_query,
            message="KB disabled",
        )

    # 计算最终返回条数并构造查询文本
    effective_k = max(1, min(_FINAL_TOP_K_LIMIT, top_k or KB_TOP_K))
    query_text = _build_query_text(normalized_query, course_name)
    start = time.monotonic()

    async with _semaphore:
        health = check_index_health()

        # 先做 BM25：即使向量服务失败也能兜底
        bm25_chunks = _bm25_query(query_text, _BM25_FETCH_K)

        # 索引未就绪时尝试用 BM25 兜底
        if not health.ready:
            if bm25_chunks:
                return RetrievalResult(
                    status="ok",
                    query=normalized_query,
                    chunks=bm25_chunks[:effective_k],
                    elapsed_ms=_elapsed_ms(start),
                    message=f"vector index not ready, bm25 fallback: {health.reason}",
                )

            return RetrievalResult(
                status="unavailable",
                query=normalized_query,
                elapsed_ms=_elapsed_ms(start),
                message=f"index not ready: {health.reason}",
            )

        # 向量检索需嵌入查询；嵌入失败则用 BM25 兜底
        embedding = embed_query(query_text)
        if embedding is None:
            if bm25_chunks:
                return RetrievalResult(
                    status="ok",
                    query=normalized_query,
                    chunks=bm25_chunks[:effective_k],
                    elapsed_ms=_elapsed_ms(start),
                    message="embedding unavailable, bm25 fallback",
                )

            return RetrievalResult(
                status="unavailable",
                query=normalized_query,
                elapsed_ms=_elapsed_ms(start),
                message="embedding unavailable",
            )

        vector_chunks = await _vector_search_soft_course(
            embedding=embedding,
            course_name=course_name,
            fetch_k=_VECTOR_FETCH_K,
            min_results=effective_k,
        )

    # 双路均有结果则做 RRF 融合，否则取单边
    if vector_chunks and bm25_chunks:
        chunks = _rrf_fusion(
            vector_chunks=vector_chunks,
            bm25_chunks=bm25_chunks,
            top_k=_RRF_CANDIDATE_K,
            k=_RRF_K,
        )
    elif vector_chunks:
        chunks = vector_chunks
    else:
        chunks = bm25_chunks

    # 去重并按最终条数截断
    chunks = _dedupe_chunks(chunks)[:effective_k]

    # 无任何结果返回 empty
    if not chunks:
        return RetrievalResult(
            status="empty",
            query=normalized_query,
            elapsed_ms=_elapsed_ms(start),
        )

    # 返回检索成功结果
    return RetrievalResult(
        status="ok",
        query=normalized_query,
        chunks=chunks,
        elapsed_ms=_elapsed_ms(start),
    )
