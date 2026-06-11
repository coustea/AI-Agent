"""本地 Chroma 知识库检索 — 混合 dense + sparse 双路召回。

检索策略：
  1. Dense 路径：Chroma 向量相似度搜索(Ollama embeddings)，缓存 query embedding 避免重复计算
  2. Sparse 路径：内存 BM25 索引(从 Chroma collection 加载)，支持中文分词
  3. 合并：merge_ranked_results 按 (来源+chunk_index) 去重，综合 dense rank、sparse rank、
     词汇命中数加权排序，返回 top_k 结果

query rewrite：对短查询用领域规则扩展同义词(如"tcp三次握手"→[TCP,三次握手,连接建立])
"""

from __future__ import annotations

import asyncio
import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from langchain_core.tools import tool
from langchain_ollama import OllamaEmbeddings

try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma

from app.config import (
    KB_COLLECTION,
    KB_DIR,
    KB_EMBED_MODEL,
    KB_ENABLED,
    KB_OLLAMA_BASE_URL,
    KB_TOP_K,
)
from app.infra.logging import get_logger

logger = get_logger(__name__)

# Cache for query embeddings to avoid repeated model calls.
# Key: normalized query string, Value: embedding vector.
_QUERY_EMBEDDING_CACHE_SIZE = 500
_SPARSE_CORPUS_LIMIT = 12000
_CHINESE_TERM_RE = re.compile(r"[\u4e00-\u9fff]{2,}")
_ASCII_TERM_RE = re.compile(r"[A-Za-z0-9+#.-]{2,}")
_QUERY_REWRITE_RULES: tuple[tuple[re.Pattern[str], tuple[str, ...]], ...] = (
    (re.compile(r"tcp\s*三次握手", re.IGNORECASE), ("TCP", "三次握手", "连接建立", "传输控制协议")),
    (re.compile(r"逻辑回归"), ("逻辑回归", "机器学习", "分类", "logistic regression")),
    (re.compile(r"指针"), ("指针", "C语言", "变量", "地址")),
)


class BM25Index:
    """Minimal in-memory BM25 index over existing Chroma chunks."""

    def __init__(self, documents: list[dict[str, Any]], tokenized_documents: list[list[str]]) -> None:
        self.documents = documents
        self.tokenized_documents = tokenized_documents
        self.doc_count = len(documents)
        self.doc_lengths = [len(tokens) for tokens in tokenized_documents]
        self.avg_doc_length = (
            sum(self.doc_lengths) / self.doc_count if self.doc_count else 0.0
        )
        self.term_doc_freqs: dict[str, int] = {}
        self.doc_term_freqs: list[dict[str, int]] = []

        for tokens in tokenized_documents:
            term_freqs: dict[str, int] = {}
            for token in tokens:
                term_freqs[token] = term_freqs.get(token, 0) + 1
            self.doc_term_freqs.append(term_freqs)
            for token in term_freqs:
                self.term_doc_freqs[token] = self.term_doc_freqs.get(token, 0) + 1


def rewrite_query(query: str) -> str:
    """Expand short or ambiguous queries with lightweight domain hints."""
    normalized_query = (query or "").strip()
    if not normalized_query:
        return ""

    expanded_terms: list[str] = [normalized_query]
    lowered = normalized_query.lower()
    for pattern, terms in _QUERY_REWRITE_RULES:
        if pattern.search(lowered):
            for term in terms:
                if term not in expanded_terms:
                    expanded_terms.append(term)
    return " ".join(expanded_terms)


def _extract_query_terms(query: str) -> list[str]:
    normalized_query = (query or "").strip()
    if not normalized_query:
        return []

    terms: list[str] = []
    for match in _ASCII_TERM_RE.findall(normalized_query):
        token = match.strip()
        if token:
            terms.append(token)
    for match in _CHINESE_TERM_RE.findall(normalized_query):
        token = match.strip()
        if token:
            terms.append(token)

    for pattern, related_terms in _QUERY_REWRITE_RULES:
        if pattern.search(normalized_query.lower()):
            for term in related_terms:
                if term not in terms:
                    terms.append(term)

    return list(dict.fromkeys(terms))


def _tokenize_for_bm25(text: str) -> list[str]:
    tokens = _extract_query_terms(text)
    if tokens:
        return [token.lower() for token in tokens]

    normalized = (text or "").strip().lower()
    if not normalized:
        return []
    return normalized.split()


@lru_cache(maxsize=1)
def _get_embeddings() -> OllamaEmbeddings | None:
    """Get Ollama embeddings instance (cached)."""
    if not KB_ENABLED:
        return None
    try:
        return OllamaEmbeddings(
            model=KB_EMBED_MODEL,
            base_url=KB_OLLAMA_BASE_URL,
        )
    except Exception:
        logger.exception("[knowledge] failed to create embeddings")
        return None


@lru_cache(maxsize=1)
def _get_vectorstore() -> Chroma | None:
    if not KB_ENABLED:
        logger.info("[knowledge] local KB disabled by config")
        return None

    db_dir = Path(KB_DIR)
    if not db_dir.exists():
        logger.warning("[knowledge] KB dir does not exist: %s", db_dir)
        return None

    try:
        embeddings = _get_embeddings()
        if embeddings is None:
            return None
        return Chroma(
            collection_name=KB_COLLECTION,
            embedding_function=embeddings,
            persist_directory=str(db_dir),
        )
    except Exception:
        logger.exception("[knowledge] failed to open KB vectorstore")
        return None


@lru_cache(maxsize=1)
def _get_sparse_corpus() -> list[dict[str, Any]]:
    """Load a bounded in-memory corpus for lightweight lexical retrieval."""
    vectorstore = _get_vectorstore()
    if vectorstore is None:
        return []

    try:
        collection = getattr(vectorstore, "_collection", None)
        if collection is None:
            return []
        raw = collection.get(include=["documents", "metadatas"], limit=_SPARSE_CORPUS_LIMIT)
    except Exception:
        logger.exception("[knowledge] failed to load sparse corpus")
        return []

    documents = raw.get("documents") or []
    metadatas = raw.get("metadatas") or []
    corpus: list[dict[str, Any]] = []
    for document, metadata in zip(documents, metadatas, strict=False):
        text = str(document or "").strip()
        if not text:
            continue
        meta = dict(metadata or {})
        corpus.append(
            {
                "metadata": meta,
                "text": text,
                "search_text": f"{text}\n{meta.get('source', '')}\n{meta.get('file_name', '')}\n{meta.get('h1', '')}\n{meta.get('h2', '')}".lower(),
            }
        )
    return corpus


def build_bm25_index(corpus: list[dict[str, Any]]) -> BM25Index:
    tokenized_documents = [
        _tokenize_for_bm25(
            f"{row.get('text', '')}\n{(row.get('metadata') or {}).get('source', '')}\n{(row.get('metadata') or {}).get('file_name', '')}"
        )
        for row in corpus
    ]
    return BM25Index(corpus, tokenized_documents)


@lru_cache(maxsize=1)
def _get_bm25_index() -> BM25Index:
    return build_bm25_index(_get_sparse_corpus())


@lru_cache(maxsize=_QUERY_EMBEDDING_CACHE_SIZE)
def _get_cached_embedding(query: str) -> tuple[float, ...] | None:
    """Get embedding for query with LRU cache.

    Returns tuple for hashability (list is not hashable).
    """
    embeddings = _get_embeddings()
    if embeddings is None:
        return None
    try:
        embedding = embeddings.embed_query(query)
        return tuple(embedding) if embedding else None
    except Exception:
        logger.exception("[knowledge] failed to embed query")
        return None


def _metadata_key(metadata: dict[str, Any]) -> tuple[str, str]:
    return (
        str(metadata.get("source") or metadata.get("file_name") or ""),
        str(metadata.get("chunk_index") or metadata.get("id") or ""),
    )


def _normalize_ranked_rows(
    rows: list[tuple[Any, float]],
    *,
    retrieval_mode: str,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for idx, (doc, score) in enumerate(rows, 1):
        items.append(
            {
                "rank": idx,
                "distance": float(score),
                "metadata": dict(doc.metadata or {}),
                "text": str(doc.page_content or "").strip(),
                "retrieval_mode": retrieval_mode,
            }
        )
    return items


def rank_with_bm25(query: str, index: BM25Index, *, top_k: int | None = None) -> list[dict[str, Any]]:
    query_terms = _tokenize_for_bm25(rewrite_query(query))
    if not query_terms or index.doc_count == 0:
        return []

    k1 = 1.5
    b = 0.75
    scored_rows: list[tuple[float, dict[str, Any]]] = []
    for row, term_freqs, doc_length in zip(index.documents, index.doc_term_freqs, index.doc_lengths, strict=False):
        score = 0.0
        for term in query_terms:
            tf = term_freqs.get(term, 0)
            if tf <= 0:
                continue
            doc_freq = index.term_doc_freqs.get(term, 0)
            idf = math.log(1 + ((index.doc_count - doc_freq + 0.5) / (doc_freq + 0.5)))
            denominator = tf + k1 * (1 - b + b * (doc_length / (index.avg_doc_length or 1.0)))
            score += idf * ((tf * (k1 + 1)) / denominator)

        if score > 0:
            scored_rows.append((score, row))

    scored_rows.sort(key=lambda item: item[0], reverse=True)
    items: list[dict[str, Any]] = []
    for idx, (score, row) in enumerate(scored_rows[: (top_k or KB_TOP_K)], 1):
        items.append(
            {
                "rank": idx,
                "distance": float(-score),
                "metadata": dict(row.get("metadata") or {}),
                "text": str(row.get("text") or "").strip(),
                "retrieval_mode": "sparse",
            }
        )
    return items


def retrieve_dense_knowledge(query: str, *, top_k: int | None = None) -> list[dict[str, Any]]:
    vectorstore = _get_vectorstore()
    normalized_query = (query or "").strip()
    if vectorstore is None or not normalized_query:
        return []

    rewritten_query = rewrite_query(normalized_query)

    try:
        cached_embedding = _get_cached_embedding(rewritten_query)
        if cached_embedding is None:
            return []
        rows = vectorstore.similarity_search_by_vector_with_relevance_scores(
            list(cached_embedding),
            k=max(top_k or KB_TOP_K, KB_TOP_K),
        )
    except Exception:
        logger.exception("[knowledge] dense query failed")
        return []

    return _normalize_ranked_rows(rows, retrieval_mode="dense")


def retrieve_sparse_knowledge(query: str, *, top_k: int | None = None) -> list[dict[str, Any]]:
    normalized_query = (query or "").strip()
    if not normalized_query:
        return []
    return rank_with_bm25(normalized_query, _get_bm25_index(), top_k=max(top_k or KB_TOP_K, KB_TOP_K))


def merge_ranked_results(
    query: str,
    *,
    dense_rows: list[dict[str, Any]],
    sparse_rows: list[dict[str, Any]],
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    query_terms = [term.lower() for term in _extract_query_terms(rewrite_query(query))]
    merged_scores: dict[tuple[str, str], dict[str, Any]] = {}

    for idx, item in enumerate(dense_rows, 1):
        metadata = dict(item.get("metadata") or {})
        key = _metadata_key(metadata)
        lexical_hits = sum(1 for term in query_terms if term and term in str(item.get("text") or "").lower())
        merged_scores[key] = {
            "item": {
                **item,
                "metadata": metadata,
                "rank": idx,
            },
            "score": 100 - idx * 3 + lexical_hits * 5,
        }

    for idx, item in enumerate(sparse_rows, 1):
        metadata = dict(item.get("metadata") or {})
        key = _metadata_key(metadata)
        lexical_hits = sum(1 for term in query_terms if term and term in str(item.get("text") or "").lower())
        candidate_score = 200 - idx * 4 + lexical_hits * 8
        existing = merged_scores.get(key)
        if existing is None or candidate_score > existing["score"]:
            merged_scores[key] = {
                "item": {
                    **item,
                    "metadata": metadata,
                    "rank": idx,
                },
                "score": candidate_score,
            }

    ordered = sorted(merged_scores.values(), key=lambda item: item["score"], reverse=True)
    result: list[dict[str, Any]] = []
    for idx, candidate in enumerate(ordered[: (top_k or KB_TOP_K)], 1):
        item = dict(candidate["item"])
        item["rank"] = idx
        result.append(item)
    return result


def retrieve_knowledge(query: str, *, top_k: int | None = None) -> list[dict[str, Any]]:
    normalized_query = (query or "").strip()
    if not normalized_query:
        return []

    dense_rows = retrieve_dense_knowledge(normalized_query, top_k=max((top_k or KB_TOP_K) * 2, KB_TOP_K))
    sparse_rows = retrieve_sparse_knowledge(normalized_query, top_k=max((top_k or KB_TOP_K) * 2, KB_TOP_K))
    if not dense_rows and not sparse_rows:
        return []
    return merge_ranked_results(
        normalized_query,
        dense_rows=dense_rows,
        sparse_rows=sparse_rows,
        top_k=top_k or KB_TOP_K,
    )


def format_knowledge_context(query: str, *, top_k: int | None = None) -> tuple[str, list[dict[str, Any]]]:
    rows = retrieve_knowledge(query, top_k=top_k)
    if not rows:
        return "", []

    parts: list[str] = []
    for item in rows:
        metadata = item.get("metadata") or {}
        title = metadata.get("book_title") or metadata.get("source") or metadata.get("file_name") or "未知来源"
        heading = metadata.get("heading_path") or metadata.get("section") or metadata.get("chapter") or ""
        distance = item.get("distance")
        score_text = f"{distance:.4f}" if isinstance(distance, (int, float)) else "NA"
        snippet = str(item.get("text") or "").replace("\r", " ").replace("\n", " ").strip()
        if len(snippet) > 700:
            snippet = snippet[:700].rstrip() + "..."
        header = f"[{item.get('rank', '?')}] 来源: {title}"
        if heading:
            header += f" | 位置: {heading}"
        header += f" | 距离: {score_text}"
        parts.append(f"{header}\n{snippet}")

    return "\n\n".join(parts), rows


async def aformat_knowledge_context(query: str, *, top_k: int | None = None) -> tuple[str, list[dict[str, Any]]]:
    """Async wrapper for formatted local knowledge context."""
    return await asyncio.to_thread(format_knowledge_context, query, top_k=top_k)


@tool("search_knowledge_base")
async def search_knowledge_base(query: str) -> str:
    """搜索本地课程知识库，返回教材相关内容片段。适用于查询学术概念、定义、理论等教材内容。"""
    context, rows = await aformat_knowledge_context(query)
    if not rows:
        return "本地知识库没有检索到相关内容，或知识库尚未正确加载。"
    return context
