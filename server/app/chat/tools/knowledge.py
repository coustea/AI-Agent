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
from typing import Any, Awaitable, Callable

from langchain_ollama import OllamaEmbeddings
from pydantic import BaseModel, Field

try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma

from app.rag.knowledge_rewrite import (
    compute_retrieval_confidence,
    filter_rewrite_variants,
    get_effectiveness_cache,
    rewrite_query_with_llm,
    should_trigger_rewrite,
)
from app.config import (
    KB_COLLECTION,
    KB_DIR,
    KB_EMBED_MODEL,
    KB_ENABLED,
    KB_OLLAMA_BASE_URL,
    KB_REWRITE_CONFIDENCE_THRESHOLD,
    KB_RRF_K,
    KB_SNIPPET_MAX,
    KB_SNIPPET_MIN,
    KB_TOP_K,
    KB_QUERY_EMBEDDING_CACHE_SIZE,
    KB_SPARSE_CORPUS_LIMIT,
)
from app.chat.tools.knowledge_router import route_query_sources as _hybrid_route, QueryRouteResult as _RouterQueryRouteResult
from app.infra.logging import get_logger

logger = get_logger(__name__)

# Cache for query embeddings to avoid repeated model calls.
# Key: normalized query string, Value: embedding vector.
# 中文分词正则：匹配连续 2 个及以上的中文字符
_CHINESE_TERM_RE = re.compile(r"[\u4e00-\u9fff]{2,}")
# 英文/数字分词正则：匹配连续 2 个及以上的字母、数字、+、#、.、-
_ASCII_TERM_RE = re.compile(r"[A-Za-z0-9+#.-]{2,}")
# 查询改写规则：对特定领域术语进行同义词扩展，提升召回率
# 格式：(匹配模式, 扩展词列表)
_QUERY_REWRITE_RULES: tuple[tuple[re.Pattern[str], tuple[str, ...]], ...] = (
    # 网络相关
    (re.compile(r"tcp\s*三次握手", re.IGNORECASE), ("TCP", "三次握手", "连接建立", "传输控制协议")),
    (re.compile(r"udp", re.IGNORECASE), ("UDP", "用户数据报协议", "无连接", "传输层")),
    # 408 计算机网络 - 应用层（DNS/HTTP）
    (re.compile(r"dns|域名解析", re.IGNORECASE), ("DNS", "域名解析", "递归查询", "迭代查询", "CNAME", "IP地址")),
    (re.compile(r"http|请求方法", re.IGNORECASE), ("HTTP", "GET", "POST", "PUT", "DELETE", "请求方法")),
    # 408 操作系统 - 内存管理
    (re.compile(r"虚拟内存", re.IGNORECASE), ("虚拟内存", "页表", "缺页中断", "地址变换", "交换")),
    (re.compile(r"页面置换", re.IGNORECASE), ("页面置换", "FIFO", "LRU", "OPT", "Belady", "缺页率")),
    # 408 计算机组成原理 - 存储系统（Cache映射）
    (re.compile(r"cache.*映射|映射方式", re.IGNORECASE), ("Cache", "直接映射", "全相联", "组相联", "局部性")),
    # Java面向对象核心概念
    (re.compile(r"封装"), ("封装", "private", "getter", "setter", "访问权限", "隐藏")),
    (re.compile(r"继承"), ("继承", "extends", "子类", "父类", "super", "重写")),
    (re.compile(r"多态"), ("多态", "重写", "override", "接口", "抽象方法")),
    (re.compile(r"抽象类"), ("抽象类", "abstract", "接口", "不能实例化")),
    (re.compile(r"接口"), ("接口", "interface", "implements", "抽象方法", "多态")),
    # Java多线程
    (re.compile(r"多线程"), ("多线程", "Thread", "Runnable", "并发", "同步", "synchronized")),
    (re.compile(r"synchronized", re.IGNORECASE), ("synchronized", "同步", "锁", "线程安全")),
    # Java集合
    (re.compile(r"HashMap", re.IGNORECASE), ("HashMap", "哈希表", "put", "get", "Entry", "键值对")),
    (re.compile(r"ArrayList", re.IGNORECASE), ("ArrayList", "动态数组", "List", "增删")),
    # 其他
    (re.compile(r"逻辑回归"), ("逻辑回归", "机器学习", "分类", "logistic regression")),
    (re.compile(r"指针"), ("指针", "C语言", "变量", "地址")),
    # Redis
    (re.compile(r"缓存穿透"), ("缓存穿透", "Redis", "空值", "布隆过滤器")),
    (re.compile(r"缓存雪崩"), ("缓存雪崩", "Redis", "失效", "过期时间")),
)

_NOISE_TERMS: tuple[str, ...] = ("z-library.sk", "1lib.sk", "z-lib.sk")
_LOW_VALUE_TEXT_MARKERS: tuple[str, ...] = ("前言", "目录", "致谢", "未知")


def route_query_sources(query: str, course_name: str | None = None) -> _RouterQueryRouteResult:
    """Route query to relevant source textbooks using hybrid routing."""
    return _hybrid_route(query, course_name=course_name)


def _normalize_source_text(value: Any) -> str:
    text = str(value or "").strip().casefold()
    if not text:
        return ""
    return "".join(ch for ch in text if ch.isalnum())


def _normalize_book_title(source: str) -> str:
    title = source
    for term in _NOISE_TERMS:
        title = title.replace(term, "")
    title = re.sub(r"\(\s*,?\s*\)", "", title)
    title = re.sub(r"\s{2,}", " ", title)
    return title.strip(" ()")


def _normalize_source_identity_text(value: Any) -> str:
    """Normalize source identity text for canonical comparison.

    Applies book title normalization (strips noise terms) then converts
    to casefolded alphanumeric-only form for fuzzy identity matching.
    """
    text = _normalize_book_title(str(value or ""))
    text = text.casefold().strip()
    if not text:
        return ""
    return "".join(ch for ch in text if ch.isalnum())


def extract_source_identities(metadata: dict[str, Any]) -> tuple[str, ...]:
    identities: list[str] = []
    seen: set[str] = set()
    for key in ("book_name", "source_stem", "book_title", "source", "file_name"):
        normalized = _normalize_source_identity_text(metadata.get(key))
        if normalized and normalized not in seen:
            identities.append(normalized)
            seen.add(normalized)
    return tuple(identities)


def extract_canonical_source_identity(metadata: dict[str, Any]) -> str:
    """Extract a canonical source identity from metadata.

    Tries metadata keys in priority order: book_name, source_stem, book_title, file_name, source.
    Returns casefolded alphanumeric-only string for fuzzy matching.
    """
    identities = extract_source_identities(metadata)
    return identities[0] if identities else ""


def build_sparse_search_text(text: str, metadata: dict[str, Any]) -> str:
    title = _normalize_book_title(
        str(
            metadata.get("book_name")
            or metadata.get("source_stem")
            or metadata.get("source")
            or metadata.get("file_name")
            or ""
        )
    )
    heading = str(metadata.get("heading_path") or metadata.get("h1") or metadata.get("h2") or "").strip()
    return "\n".join(part for part in (str(text or "").strip(), heading, title) if part).lower()


def _matches_source_filter(metadata: dict[str, Any], source_filter: tuple[str, ...] | None) -> bool:
    """Check if metadata matches any of the source filter values.

    Uses multi-identity matching with fallback for fuzzy matching across
    different metadata field naming conventions.
    """
    if not source_filter:
        return True

    candidate_identities = extract_source_identities(metadata)
    if not candidate_identities:
        return False

    expected_identities = tuple(
        normalized
        for item in source_filter
        for normalized in (_normalize_source_identity_text(item),)
        if normalized
    )
    for candidate in candidate_identities:
        for expected in expected_identities:
            if candidate == expected or expected in candidate or candidate in expected:
                return True
    return False


class BM25Index:
    """内存级 BM25 索引，基于 Chroma 已有的文档块构建。

    BM25 是经典的稀疏检索算法，通过词频(TF)和逆文档频率(IDF)计算相关性分数。
    相比向量检索（dense），BM25 对精确关键词匹配更敏感。
    """

    def __init__(self, documents: list[dict[str, Any]], tokenized_documents: list[list[str]]) -> None:
        self.documents = documents  # 原始文档列表（含 metadata 和 text）
        self.tokenized_documents = tokenized_documents  # 分词后的 token 列表
        self.doc_count = len(documents)  # 文档总数
        self.doc_lengths = [len(tokens) for tokens in tokenized_documents]  # 每篇文档的 token 数
        # 计算平均文档长度，用于 BM25 公式中的长度归一化
        self.avg_doc_length = (
            sum(self.doc_lengths) / self.doc_count if self.doc_count else 0.0
        )
        # term_doc_freqs: 每个词出现在多少篇文档中（用于计算 IDF）
        self.term_doc_freqs: dict[str, int] = {}
        # doc_term_freqs: 每篇文档中每个词的出现次数（用于计算 TF）
        self.doc_term_freqs: list[dict[str, int]] = []

        for tokens in tokenized_documents:
            # 统计单篇文档的词频
            term_freqs: dict[str, int] = {}
            for token in tokens:
                term_freqs[token] = term_freqs.get(token, 0) + 1
            self.doc_term_freqs.append(term_freqs)
            # 更新全局文档频率（该词出现在多少篇文档中）
            for token in term_freqs:
                self.term_doc_freqs[token] = self.term_doc_freqs.get(token, 0) + 1


def rewrite_query(query: str) -> str:
    """对短查询或歧义查询进行同义词扩展。

    使用预定义的领域规则，将专业术语扩展为多个相关词汇，
    提升稀疏检索的召回率（如 "tcp三次握手" → "tcp 三次握手 连接建立 传输控制协议"）。
    """
    normalized_query = (query or "").strip()
    if not normalized_query:
        return ""

    expanded_terms: list[str] = [normalized_query]
    lowered = normalized_query.lower()
    # 遍历改写规则，匹配则追加扩展词（去重）
    for pattern, terms in _QUERY_REWRITE_RULES:
        if pattern.search(lowered):
            for term in terms:
                if term not in expanded_terms:
                    expanded_terms.append(term)
    return " ".join(expanded_terms)


def _extract_query_terms(query: str) -> list[str]:
    """从查询文本中提取所有分词结果。

    提取策略：
    1. 先提取英文/数字 token（正则匹配）
    2. 再提取中文 token（连续 2+ 中文字符）
    3. 最后追加领域规则扩展词
    4. 使用 dict.fromkeys 去重（保序）
    """
    normalized_query = (query or "").strip()
    if not normalized_query:
        return []

    terms: list[str] = []
    # 提取英文、数字、技术符号（如 C++、Node.js）组成的 token
    for match in _ASCII_TERM_RE.findall(normalized_query):
        token = match.strip()
        if token:
            terms.append(token)
    # 提取连续中文字符组成的 token（如 "机器学习"、"三次握手"）
    for match in _CHINESE_TERM_RE.findall(normalized_query):
        token = match.strip()
        if token:
            terms.append(token)

    # 追加领域规则扩展词，提升召回率
    for pattern, related_terms in _QUERY_REWRITE_RULES:
        if pattern.search(normalized_query.lower()):
            for term in related_terms:
                if term not in terms:
                    terms.append(term)

    # 使用 dict.fromkeys 去重，保持原始顺序
    return list(dict.fromkeys(terms))


def _tokenize_for_bm25(text: str) -> list[str]:
    """BM25 分词器：优先使用中英文分词规则，fallback 到空格分词。"""
    tokens = _extract_query_terms(text)
    if tokens:
        # 全部转小写，确保 BM25 匹配时不区分大小写
        return [token.lower() for token in tokens]

    # 如果提取不到 token（如纯标点），使用空格分词兜底
    normalized = (text or "").strip().lower()
    if not normalized:
        return []
    return normalized.split()


@lru_cache(maxsize=1)
def _get_embeddings() -> OllamaEmbeddings | None:
    """获取 Ollama embeddings 实例（全局缓存，只创建一次）。

    使用本地 Ollama 服务生成文本向量，避免外部 API 调用。
    """
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
    """获取 Chroma 向量数据库实例（全局缓存）。

    Chroma 是本地向量数据库，数据持久化到磁盘目录。
    """
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
        # 连接到本地 Chroma 持久化目录，使用指定的 collection 和 embedding 模型
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
    """从 Chroma collection 加载文档语料，用于构建内存级 BM25 索引。

    加载内容包含文档文本和元数据（source、file_name、h1、h2），
    拼接为 search_text 用于稀疏检索时的全文匹配。
    """
    vectorstore = _get_vectorstore()
    if vectorstore is None:
        return []

    try:
        # 直接访问 Chroma 内部 collection 对象，批量获取文档和元数据
        collection = getattr(vectorstore, "_collection", None)
        if collection is None:
            return []
        # 限制加载数量，防止超大知识库撑爆内存
        raw = collection.get(include=["documents", "metadatas"], limit=KB_SPARSE_CORPUS_LIMIT)
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
        if _is_low_value_sparse_chunk(meta, text):
            continue
        # 拼接全文搜索字段：正文 + 来源 + 文件名 + 章节标题，全部小写化
        corpus.append(
            {
                "metadata": meta,
                "text": text,
                "search_text": build_sparse_search_text(text, meta),
            }
        )
    return corpus


def build_bm25_index(corpus: list[dict[str, Any]]) -> BM25Index:
    """从语料构建 BM25 索引。

    每篇文档的分词文本使用预计算的 search_text，确保来源信息也能被 BM25 匹配到。
    """
    tokenized_documents = [
        _tokenize_for_bm25(row.get("search_text", ""))
        for row in corpus
    ]
    return BM25Index(corpus, tokenized_documents)


@lru_cache(maxsize=1)
def _get_bm25_index() -> BM25Index:
    return build_bm25_index(_get_sparse_corpus())


@lru_cache(maxsize=KB_QUERY_EMBEDDING_CACHE_SIZE)
def _get_cached_embedding(query: str) -> tuple[float, ...] | None:
    """获取查询的向量表示（带 LRU 缓存）。

    使用 tuple 而非 list 作为返回值，因为 list 不可哈希，无法用于 LRU 缓存。
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
    """从元数据中提取文档去重键：(来源文件, chunk索引)。

    同一文件的同一 chunk 视为相同文档，用于 dense/sparse 结果合并时去重。
    """
    return (
        str(metadata.get("source") or metadata.get("file_name") or ""),
        str(metadata.get("chunk_index") or metadata.get("id") or ""),
    )


def _normalize_ranked_rows(
    rows: list[tuple[Any, float]],
    *,
    retrieval_mode: str,
) -> list[dict[str, Any]]:
    """将 Chroma 返回的 (Document, score) 元组列表标准化为统一格式。

    统一格式包含 rank、distance、metadata、text、retrieval_mode 字段，
    便于后续合并和格式化处理。
    """
    items: list[dict[str, Any]] = []
    for idx, (doc, score) in enumerate(rows, 1):
        items.append(
            {
                "rank": idx,
                "distance": float(score),  # Chroma 返回的是 L2 距离，越小越相似
                "metadata": dict(doc.metadata or {}),
                "text": str(doc.page_content or "").strip(),
                "retrieval_mode": retrieval_mode,  # 标记来源："dense" 或 "sparse"
            }
        )
    return items


def rank_with_bm25(
    query: str,
    index: BM25Index,
    *,
    top_k: int | None = None,
    source_filter: tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    """使用 BM25 算法对语料进行稀疏检索排名。

    BM25 公式：score = IDF * (TF * (k1 + 1)) / (TF + k1 * (1 - b + b * dl/avgdl))
    k1=1.5, b=0.75 是经典参数，分别控制词频饱和度和文档长度归一化强度。
    """
    # 对查询进行分词（含同义词扩展）
    query_terms = _tokenize_for_bm25(rewrite_query(query))
    if not query_terms or index.doc_count == 0:
        return []

    k1 = 1.5  # 词频饱和参数：越大，高频词的权重增长越慢
    b = 0.75  # 文档长度归一化参数：0 表示不归一化，1 表示完全归一化
    scored_rows: list[tuple[float, dict[str, Any]]] = []
    for row, term_freqs, doc_length in zip(index.documents, index.doc_term_freqs, index.doc_lengths, strict=False):
        metadata = dict(row.get("metadata") or {})
        if not _matches_source_filter(metadata, source_filter):
            continue
        score = 0.0
        for term in query_terms:
            tf = term_freqs.get(term, 0)
            if tf <= 0:
                continue
            # IDF: 逆文档频率，衡量词的区分能力
            doc_freq = index.term_doc_freqs.get(term, 0)
            idf = math.log(1 + ((index.doc_count - doc_freq + 0.5) / (doc_freq + 0.5)))
            # BM25 分母：包含词频和文档长度归一化
            denominator = tf + k1 * (1 - b + b * (doc_length / (index.avg_doc_length or 1.0)))
            score += idf * ((tf * (k1 + 1)) / denominator)

        if score > 0:
            scored_rows.append((score, row))

    # 按分数降序排列，取 top_k 结果
    scored_rows.sort(key=lambda item: item[0], reverse=True)
    items: list[dict[str, Any]] = []
    for idx, (score, row) in enumerate(scored_rows[: (top_k or KB_TOP_K)], 1):
        items.append(
            {
                "rank": idx,
                "distance": float(-score),  # 取负号，因为 dense 用距离（越小越好），sparse 用分数（越大越好）
                "metadata": dict(row.get("metadata") or {}),
                "text": str(row.get("text") or "").strip(),
                "retrieval_mode": "sparse",
            }
        )
    return items


def retrieve_dense_knowledge(
    query: str,
    *,
    top_k: int | None = None,
    source_filter: tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    """Dense 路径检索：使用向量相似度搜索本地知识库。

    流程：query → rewrite → embed → 相似度搜索 → 排名结果
    """
    vectorstore = _get_vectorstore()
    normalized_query = (query or "").strip()
    if vectorstore is None or not normalized_query:
        return []

    # 先对查询进行同义词扩展，提升召回率
    rewritten_query = rewrite_query(normalized_query)

    try:
        # 使用 LRU 缓存的 embedding，避免重复调用 Ollama 模型
        cached_embedding = _get_cached_embedding(rewritten_query)
        if cached_embedding is None:
            return []
        # 使用预计算的向量直接进行相似度搜索（跳过 embedding 步骤）
        rows = vectorstore.similarity_search_by_vector_with_relevance_scores(
            list(cached_embedding),
            k=max(top_k or KB_TOP_K, KB_TOP_K),
            filter={"source": {"$in": list(source_filter)}} if source_filter else None,
        )
        if source_filter:
            fallback_rows = vectorstore.similarity_search_by_vector_with_relevance_scores(
                list(cached_embedding),
                k=max(top_k or KB_TOP_K, KB_TOP_K),
                filter=None,
            )
            merged_rows: dict[tuple[str, str], tuple[Any, float, dict[str, Any]]] = {}
            for doc, score in rows:
                metadata = dict(doc.metadata or {})
                metadata.setdefault("matched_by", "vector_filter")
                key = _metadata_key(metadata)
                merged_rows[key] = (doc, score, metadata)
            for doc, score in fallback_rows:
                metadata = dict(doc.metadata or {})
                if not _matches_source_filter(metadata, source_filter):
                    continue
                metadata["matched_by"] = "metadata_fallback"
                key = _metadata_key(metadata)
                if key not in merged_rows:
                    merged_rows[key] = (doc, score, metadata)
            rows = sorted(merged_rows.values(), key=lambda item: float(item[1]))[: (top_k or KB_TOP_K)]
    except Exception:
        logger.exception("[knowledge] dense query failed")
        return []

    # Build result preserving matched_by from stored metadata
    items: list[dict[str, Any]] = []
    for idx, item in enumerate(rows, 1):
        doc = item[0]
        score = item[1]
        stored_metadata = item[2] if len(item) > 2 else dict(doc.metadata or {})
        items.append(
            {
                "rank": idx,
                "distance": float(score),
                "metadata": stored_metadata,
                "text": str(doc.page_content or "").strip(),
                "retrieval_mode": "dense",
            }
        )
    return items


def retrieve_sparse_knowledge(
    query: str,
    *,
    top_k: int | None = None,
    source_filter: tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    """Sparse 路径检索：使用内存 BM25 索引进行关键词匹配。

    BM25 对精确关键词匹配效果好，适合查询中包含专有名词的场景。
    """
    normalized_query = (query or "").strip()
    if not normalized_query:
        return []
    return rank_with_bm25(
        normalized_query,
        _get_bm25_index(),
        top_k=max(top_k or KB_TOP_K, KB_TOP_K),
        source_filter=source_filter,
    )


def _rrf_score(rank: int, constant: int | None = None) -> float:
    """计算 Reciprocal Rank Fusion 分数。

    RRF 分数 = 1 / (constant + rank)
    constant 默认从配置加载，与业界常见设置一致。
    """
    return 1.0 / ((constant or KB_RRF_K) + rank)


def _low_value_chunk_penalty(metadata: dict[str, Any], text: str) -> float:
    """Return an additive penalty for cover/preface-like chunks."""
    normalized_text = str(text or "").strip()
    if not normalized_text:
        return 0.0

    heading = str(metadata.get("heading_path") or "").strip()
    preview = normalized_text[:200]
    penalty = 0.0

    if not heading:
        penalty += 0.02

    if any(marker in preview for marker in _LOW_VALUE_TEXT_MARKERS):
        penalty += 0.02

    lines = [line.strip() for line in normalized_text.splitlines() if line.strip()]
    if lines:
        first_line = lines[0]
        if len(lines) <= 3 and len(first_line) >= 6 and first_line in normalized_text[1:160]:
            penalty += 0.02

    return penalty


def _is_low_value_sparse_chunk(metadata: dict[str, Any], text: str) -> bool:
    """Return True when a chunk should be excluded from sparse indexing only."""
    normalized_text = str(text or "").strip()
    if not normalized_text:
        return True

    heading = str(metadata.get("heading_path") or "").strip()
    preview = normalized_text[:200]

    if heading:
        return False

    if any(marker in preview for marker in _LOW_VALUE_TEXT_MARKERS):
        return True

    lines = [line.strip() for line in normalized_text.splitlines() if line.strip()]
    if len(lines) <= 3 and lines and len(lines[0]) >= 6:
        return True

    return False


def merge_ranked_results(
    query: str,
    *,
    dense_rows: list[dict[str, Any]],
    sparse_rows: list[dict[str, Any]],
    top_k: int | None = None,
    source_filter: tuple[str, ...] | None = None,
    original_boost: float = 1.0,
) -> list[dict[str, Any]]:
    """合并 dense 和 sparse 两路检索结果，使用 Reciprocal Rank Fusion (RRF) 算法。

    RRF 是一种简单有效的融合策略：
    - 对每个列表中的每个结果，计算 RRF 分数 = 1/(60 + rank)
    - 同一文档在多个列表中出现时，分数相加
    - 按合并分数降序排列，相同分数时按原始 rank 排序
    - 如果提供了 source_filter，匹配源的文档会优先排序

    该方法不需要调参，对排序融合有良好效果。
    """
    merged_scores: dict[tuple[str, str], dict[str, Any]] = {}

    # 处理 dense 和 sparse 两路结果
    for rows in (dense_rows, sparse_rows):
        for item in rows:
            metadata = dict(item.get("metadata") or {})
            key = _metadata_key(metadata)
            score = _rrf_score(int(item.get("rank") or 0))
            if item.get("_is_original"):
                score *= original_boost
            score -= _low_value_chunk_penalty(metadata, str(item.get("text") or ""))
            existing = merged_scores.get(key)
            if existing is None:
                # 首次出现，直接插入
                merged_scores[key] = {"item": {**item, "metadata": metadata}, "score": score}
            else:
                # 已存在，累加分数
                existing["score"] += score
                # 如果当前结果的 rank 更优，则更新 item
                if item.get("rank", 9999) < existing["item"].get("rank", 9999):
                    existing["item"] = {**item, "metadata": metadata}

    # 按分数降序排列，优先匹配源文档，相同分数时按 rank 升序排列（保序）
    ordered = sorted(
        merged_scores.values(),
        key=lambda x: (
            0 if _matches_source_filter(x["item"].get("metadata") or {}, source_filter) else 1,
            -x["score"],
            x["item"].get("rank", 9999),
        ),
    )
    result: list[dict[str, Any]] = []
    for idx, candidate in enumerate(ordered[: (top_k or KB_TOP_K)], 1):
        item = dict(candidate["item"])
        item["rank"] = idx
        result.append(item)
    return result


def retrieve_knowledge(
    query: str,
    *,
    course_name: str | None = None,
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    """Hybrid retrieval with retrieval-aware query rewrite."""
    normalized_query = (query or "").strip()
    if not normalized_query:
        return []

    effective_top_k = top_k or KB_TOP_K
    route = route_query_sources(normalized_query, course_name=course_name)

    # Initial retrieval with original query
    candidate_k = max(effective_top_k * 2, KB_TOP_K)
    dense_rows = retrieve_dense_knowledge(
        route.query,
        top_k=candidate_k,
        source_filter=route.source_filter,
    )
    sparse_rows = retrieve_sparse_knowledge(
        route.query,
        top_k=candidate_k,
        source_filter=route.source_filter,
    )

    # Check retrieval confidence
    all_initial = dense_rows + sparse_rows
    confidence = compute_retrieval_confidence(all_initial)

    if confidence >= KB_REWRITE_CONFIDENCE_THRESHOLD or not should_trigger_rewrite(normalized_query):
        if not dense_rows and not sparse_rows:
            return []
        return merge_ranked_results(
            route.query,
            dense_rows=dense_rows,
            sparse_rows=sparse_rows,
            top_k=effective_top_k,
            source_filter=route.source_filter,
        )

    # Low confidence — check effectiveness cache
    eff_cache = get_effectiveness_cache()
    if not eff_cache.is_effective(normalized_query):
        if not dense_rows and not sparse_rows:
            return []
        return merge_ranked_results(
            route.query,
            dense_rows=dense_rows,
            sparse_rows=sparse_rows,
            top_k=effective_top_k,
            source_filter=route.source_filter,
        )

    # LLM rewrite
    variants = rewrite_query_with_llm(normalized_query)
    filtered_variants = filter_rewrite_variants(normalized_query, variants)

    if not filtered_variants:
        if not dense_rows and not sparse_rows:
            return []
        return merge_ranked_results(
            route.query,
            dense_rows=dense_rows,
            sparse_rows=sparse_rows,
            top_k=effective_top_k,
            source_filter=route.source_filter,
        )

    # Parallel retrieval for rewrite variants
    rewrite_dense: list[dict[str, Any]] = []
    rewrite_sparse: list[dict[str, Any]] = []
    for variant in filtered_variants:
        v_dense = retrieve_dense_knowledge(variant, top_k=effective_top_k, source_filter=route.source_filter)
        v_sparse = retrieve_sparse_knowledge(variant, top_k=effective_top_k, source_filter=route.source_filter)
        rewrite_dense.extend(v_dense)
        rewrite_sparse.extend(v_sparse)

    all_dense = dense_rows + rewrite_dense
    all_sparse = sparse_rows + rewrite_sparse

    if not all_dense and not all_sparse:
        return []

    # Mark original query results for boost
    for row in dense_rows:
        row["_is_original"] = True
    for row in sparse_rows:
        row["_is_original"] = True

    result = merge_ranked_results(
        route.query,
        dense_rows=all_dense,
        sparse_rows=all_sparse,
        top_k=effective_top_k,
        source_filter=route.source_filter,
        original_boost=1.5,
    )

    # Record effectiveness
    initial_result = merge_ranked_results(
        route.query,
        dense_rows=dense_rows,
        sparse_rows=sparse_rows,
        top_k=effective_top_k,
        source_filter=route.source_filter,
    )
    if initial_result and result:
        initial_best = abs(initial_result[0].get("distance", 0))
        rewritten_best = abs(result[0].get("distance", 0))
        if initial_best > 0:
            gain = (rewritten_best - initial_best) / initial_best
            eff_cache.record(normalized_query, gain=gain)

    return result


def _semantic_truncate(text: str, *, min_len: int = 500, max_len: int = 900) -> str:
    """Truncate text at semantic boundaries (sentence endings)."""
    if len(text) <= min_len:
        return text
    search_start = min_len
    search_end = min(max_len, len(text))
    for i in range(search_start, search_end):
        if text[i] in "。！？\n":
            return text[:i + 1].rstrip()
    if len(text) > max_len:
        return text[:max_len].rstrip() + "..."
    return text


def format_knowledge_context(
    query: str,
    *,
    course_name: str | None = None,
    top_k: int | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """将检索结果格式化为可读的上下文文本，供 LLM 消费。

    返回格式：
    [1] 来源: 书名 | 位置: 章节 | 距离: 0.xxxx
    文档内容摘要...

    同时返回原始结果列表，供调用方进一步处理。
    """
    rows = retrieve_knowledge(query, course_name=course_name, top_k=top_k)
    if not rows:
        return "", []

    parts: list[str] = []
    for item in rows:
        metadata = item.get("metadata") or {}
        # 按优先级获取来源标题：书名 > source > 文件名
        title = metadata.get("book_title") or metadata.get("source") or metadata.get("file_name") or "未知来源"
        # 获取章节位置信息
        heading = metadata.get("heading_path") or metadata.get("section") or metadata.get("chapter") or ""
        distance = item.get("distance")
        score_text = f"{distance:.4f}" if isinstance(distance, (int, float)) else "NA"
        # 清理文本中的换行符，截断过长内容
        snippet = _semantic_truncate(
            str(item.get("text") or "").replace("\r", " ").replace("\n", " ").strip(),
            min_len=KB_SNIPPET_MIN,
            max_len=KB_SNIPPET_MAX,
        )
        # 拼接头部信息：排名、来源、位置、距离分数
        header = f"[{item.get('rank', '?')}] 来源: {title}"
        if heading:
            header += f" | 位置: {heading}"
        header += f" | 距离: {score_text}"
        parts.append(f"{header}\n{snippet}")

    return "\n\n".join(parts), rows


async def aformat_knowledge_context(
    query: str,
    *,
    course_name: str | None = None,
    top_k: int | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """异步包装器：将同步的 format_knowledge_context 放到线程池执行。

    检索操作（向量搜索、BM25 排序）涉及 CPU 密集计算，
    放到线程池避免阻塞 asyncio 事件循环。
    """
    return await asyncio.to_thread(format_knowledge_context, query, course_name=course_name, top_k=top_k)


class SearchKnowledgeBaseArgs(BaseModel):
    query: str = Field(description="Search query for local course knowledge.")
    course_name: str | None = Field(default=None, description="Course name used as a retrieval hint.")
    top_k: int = Field(default=4, ge=1, le=8, description="Maximum number of snippets to return.")


async def search_knowledge_base(
    query: str,
    course_name: str | None = None,
    top_k: int = 4,
) -> str:
    """搜索本地课程知识库。

    适用于查询学术概念、定义、理论等教材内容。
    内部执行混合检索（dense + sparse），返回格式化的上下文片段。
    """
    context, rows = await aformat_knowledge_context(query, course_name=course_name, top_k=top_k)
    if not rows:
        return "本地知识库没有检索到相关内容，或知识库尚未正确加载。"
    return context


# 知识库搜索工具的输入参数模型（用于 LLM tool call 参数校验）
from app.chat.tools.user_context import _compact


def make_search_knowledge_base() -> Callable[..., Awaitable[str]]:
    """工厂函数：创建知识库搜索工具的闭包。

    与 profile/memory 不同，知识库搜索不依赖用户身份，无需捕获 request。
    course_name 作为检索前缀拼接到查询前，提升课程相关内容的召回率。
    """
    async def _impl(
        query: str,
        course_name: str | None = None,
        top_k: int = 4,
    ) -> str:
        # 将课程名拼接到查询前，帮助检索模型聚焦到特定课程内容
        try:
            context, _rows = await aformat_knowledge_context(
                query,
                course_name=course_name,
                top_k=top_k,
            )
            return _compact(context or "本地知识库没有检索到相关内容，或知识库尚未正确加载。")
        except Exception as exc:
            logger.warning("[search_knowledge_base] failed: %s", exc)
            return "本地知识库暂时不可用。"

    return _impl
