"""Cross-Encoder重排序模块

使用BAAI/bge-reranker-base对检索结果进行精细重排序。
Cross-Encoder比双塔模型更精确，但计算成本更高，适合对少量候选结果重排序。
"""

from __future__ import annotations

from typing import Any

from app.infra.logging import get_logger
from app.rag.config.source_registry import extract_canonical_source_identity, normalize_book_title

logger = get_logger(__name__)

# Lazy-loaded CrossEncoder instance
_cross_encoder: Any = None


def _build_rerank_document_payload(candidate: dict[str, Any]) -> str:
    metadata = dict(candidate.get("metadata") or {})
    title = normalize_book_title(
        str(
            metadata.get("book_title")
            or metadata.get("book_name")
            or metadata.get("source")
            or metadata.get("file_name")
            or ""
        )
    )
    heading = str(metadata.get("heading_path") or metadata.get("section") or metadata.get("chapter") or "").strip()
    course = str(metadata.get("course") or "").strip()
    chunk_type = str(metadata.get("chunk_type") or candidate.get("chunk_type") or "").strip()
    body = str(candidate.get("text", "")).strip()
    parts = [part for part in (title, course, heading, chunk_type, body) if part]
    return "\n".join(parts)


def get_cross_encoder() -> Any:
    """获取CrossEncoder实例（延迟加载）。

    首次调用时加载模型，后续调用返回缓存的实例。
    模型加载失败时返回None，不抛出异常。
    """
    global _cross_encoder

    if _cross_encoder is not None:
        return _cross_encoder

    try:
        from sentence_transformers import CrossEncoder

        from app.config import KB_RERANK_MODEL

        logger.info("[reranker] Loading CrossEncoder model: %s", KB_RERANK_MODEL)
        _cross_encoder = CrossEncoder(KB_RERANK_MODEL)
        logger.info("[reranker] CrossEncoder model loaded successfully")
        return _cross_encoder

    except ImportError:
        logger.warning("[reranker] sentence-transformers not installed, reranking disabled")
        _cross_encoder = None
        return None

    except Exception as e:
        logger.warning("[reranker] Failed to load CrossEncoder: %s", e)
        _cross_encoder = None
        return None


def rerank_candidates(
    query: str,
    candidates: list[dict[str, Any]],
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    """使用Cross-Encoder对候选结果重排序。

    Args:
        query: 用户查询文本
        candidates: 检索候选结果列表，每个元素应包含"text"字段
        top_k: 返回前k个结果，None时从配置读取

    Returns:
        重排序后的结果列表（按相关性降序），每个结果额外包含：
        - rerank_score: Cross-Encoder相关性分数
        - retrieval_mode: 添加"+rerank"后缀标记
    """
    if not candidates:
        return []

    if not query or not query.strip():
        return candidates[:top_k] if top_k else candidates

    # 从配置读取top_k
    if top_k is None:
        from app.config import KB_RERANK_TOP_K
        top_k = KB_RERANK_TOP_K

    encoder = get_cross_encoder()

    if encoder is None:
        # 无法重排序，返回原始结果
        return candidates[:top_k]

    # 构建query-document pairs
    pairs = [(query, _build_rerank_document_payload(candidate)) for candidate in candidates]

    try:
        # 计算相关性分数
        scores = encoder.predict(pairs)

        # 确保scores是可迭代的
        if not hasattr(scores, "__iter__"):
            scores = [float(scores)]
        else:
            scores = [float(s) for s in scores]

        # 按分数降序排序
        scored_candidates = list(zip(candidates, scores))
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        # 返回top_k结果，附带rerank_score
        reranked: list[dict[str, Any]] = []
        seen_sources: set[str] = set()
        deferred_duplicates: list[tuple[dict[str, Any], float]] = []
        for candidate, score in scored_candidates:
            reranked_item = dict(candidate)
            reranked_item["rerank_score"] = float(score)
            original_mode = candidate.get("retrieval_mode", "")
            reranked_item["retrieval_mode"] = f"{original_mode}+rerank" if original_mode else "rerank"
            canonical_source = extract_canonical_source_identity(dict(candidate.get("metadata") or {}))
            if canonical_source and canonical_source in seen_sources:
                deferred_duplicates.append((reranked_item, score))
                continue
            if canonical_source:
                seen_sources.add(canonical_source)
            reranked.append(reranked_item)
            if len(reranked) >= top_k:
                break

        if len(reranked) < top_k:
            for reranked_item, _score in deferred_duplicates:
                reranked.append(reranked_item)
                if len(reranked) >= top_k:
                    break

        return reranked

    except Exception as e:
        logger.warning("[reranker] Reranking failed: %s", e)
        return candidates[:top_k]


def is_rerank_enabled() -> bool:
    """检查是否启用重排序。

    从配置读取开关，同时检查模型是否可用。
    """
    from app.config import KB_RERANK_ENABLED

    if not KB_RERANK_ENABLED:
        return False

    # 检查模型是否可用（不实际加载）
    try:
        from sentence_transformers import CrossEncoder  # noqa: F401
        return True
    except ImportError:
        return False
