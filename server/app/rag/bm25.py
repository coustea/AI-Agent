"""BM25 关键词检索模块。

基于 jieba 中文分词 + rank_bm25 实现，与向量检索互补。
索引随 ChromaDB 一起构建，持久化到 KB_DIR/bm25_index.pkl。

Called by: app/rag/retriever.py (_bm25_query), app/rag/store.py (build + save).
No external API surface change — BM25 is internal to the RAG module.
Per user: "BM25Index.build() 只保存 metadata，没有保存 chunk正文" — 修复正文丢失。
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

import jieba
from rank_bm25 import BM25Okapi

from app.infra.logging import get_logger

logger = get_logger(__name__)

# 中文停用词：助词 / 连词 / 疑问词 / 人称 / 语气词 / 动词修饰
# 按教育场景精简，覆盖高频虚词
_CHINESE_STOPWORDS: set[str] = set(
    "的 了 和 是 在 我 有 就 不 也 都 还 这 那 一 个 与 及 等 上 下 中 为 以 于 从 把 被 让 使 又 而 但 或"
    "什么 怎么 如何 哪些 哪个 哪里 谁 多少 几 你 他 她 它 我们 他们 她们 它们"
    "请问 请 想 要 需要 能 可以 应该 会 啊 呢 吧 嘛 吗 哦 呀 哈"
    "之 其 此 该 即 各 每 些 种 类 时 后 前 里 外 内 间 已经 正在 一些 一下".split()
)

# BM25 索引持久化文件名
_BM25_INDEX_FILENAME = "bm25_index.pkl"


# jieba 精确分词 + 停用词过滤
def _tokenize(text: str) -> list[str]:
    """jieba 精确分词 + 停用词过滤。"""
    if not text:
        return []
    return [
        t
        for t in jieba.lcut(text)
        if t.strip() and t not in _CHINESE_STOPWORDS and not t.isspace()
    ]


# 内存 BM25 索引类，支持持久化到磁盘
class BM25Index:
    """内存 BM25 索引，支持持久化。"""

    # 初始化索引对象与对齐的文档信息列表
    def __init__(self) -> None:
        self._bm25: BM25Okapi | None = None
        # 与 BM25 索引对齐的文档信息列表（含 text 字段）
        self._docs: list[dict[str, Any]] = []

    # 索引是否已成功构建并可用
    @property
    def is_ready(self) -> bool:
        return self._bm25 is not None and len(self._docs) > 0

    # 构建 BM25 索引（同时保存 chunk 正文，避免检索结果只有路径）
    def build(self, texts: list[str], metadatas: list[dict[str, Any]]) -> None:
        """构建 BM25 索引。

        Args:
            texts: 文档文本列表，与 ChromaDB 中的 chunk 顺序一致。
            metadatas: 对应的元数据列表。
        """
        # 空文本直接跳过构建
        if not texts:
            logger.warning("[bm25] empty texts, skip build")
            return

        # 文本与元数据数量不一致时告警
        if len(texts) != len(metadatas):
            logger.warning(
                "[bm25] texts/metadatas length mismatch: texts=%d, metadatas=%d",
                len(texts),
                len(metadatas),
            )

        # 对所有文本执行分词
        tokenized_corpus = [_tokenize(t) for t in texts]
        # 分词后全部为空则跳过
        if not any(tokenized_corpus):
            logger.warning("[bm25] all tokenized documents are empty, skip build")
            return

        # 用分词语料初始化 BM25 模型
        self._bm25 = BM25Okapi(tokenized_corpus)

        # 关键修复：保存 chunk 正文，避免检索结果只有 source 路径
        self._docs = []
        for idx, (text, meta) in enumerate(zip(texts, metadatas, strict=False)):
            item = dict(meta)
            item["text"] = text
            item["bm25_doc_index"] = idx
            self._docs.append(item)

        avg_tokens = sum(len(t) for t in tokenized_corpus) / max(1, len(tokenized_corpus))
        logger.info("[bm25] index built: %d docs, avg tokens=%.1f", len(self._docs), avg_tokens)

    # 执行 BM25 检索并按最大分数归一化相关性
    def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """BM25 检索。

        Returns:
            列表，每项包含 chunk_id, text, bm25_score, score, metadata。
        """
        if not self._bm25 or not self._docs:
            return []

        tokenized_query = _tokenize(query)
        if not tokenized_query:
            return []

        # 计算查询与各文档的 BM25 分数
        scores = self._bm25.get_scores(tokenized_query)
        if len(scores) == 0:
            return []

        # 取分数最高的 top_k 文档下标
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[
            : max(1, top_k)
        ]

        # 取最大分数用于归一化，最大分为 0 则无有效结果
        max_score = max(float(scores[i]) for i in top_indices) if top_indices else 0.0
        if max_score <= 0:
            return []

        results: list[dict[str, Any]] = []
        for idx in top_indices:
            score = float(scores[idx])
            if score <= 0:
                continue

            meta = dict(self._docs[idx])
            meta["bm25_score"] = score
            meta["score"] = score / max_score
            results.append(meta)

        return results

    # 将 BM25 模型与文档 pickle 持久化到磁盘
    def save(self, kb_dir: Path) -> None:
        """持久化 BM25 索引到磁盘。"""
        if self._bm25 is None:
            return
        path = kb_dir / _BM25_INDEX_FILENAME
        data = {
            "bm25": self._bm25,
            "docs": self._docs,
        }
        path.write_bytes(pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL))
        logger.info("[bm25] index saved: %s (%d docs)", path, len(self._docs))

    # 从磁盘加载已持久化的 BM25 索引
    @classmethod
    def load(cls, kb_dir: Path) -> BM25Index:
        """从磁盘加载 BM25 索引。"""
        path = kb_dir / _BM25_INDEX_FILENAME
        if not path.exists():
            logger.warning("[bm25] index file not found: %s", path)
            return cls()

        # 反序列化索引文件
        try:
            data = pickle.loads(path.read_bytes())
            idx = cls()
            idx._bm25 = data["bm25"]
            idx._docs = data["docs"]
            logger.info("[bm25] index loaded: %d docs", len(idx._docs))
            return idx
        # 加载失败则降级返回空索引
        except Exception as exc:
            logger.warning("[bm25] load failed: %s", exc)
            return cls()


# 模块级懒加载单例
_bm25_index: BM25Index | None = None
_bm25_loaded = False


# 获取 BM25 索引单例（懒加载，不可用则尝试重新加载）
def get_bm25_index(kb_dir: Path) -> BM25Index:
    """获取 BM25 索引单例（懒加载）。

    如果已加载的索引不可用（is_ready=False），会尝试重新加载。
    这确保了启动时自动构建索引后，首次检索能获取到新索引。
    """
    global _bm25_index, _bm25_loaded
    if not _bm25_loaded:
        _bm25_index = BM25Index.load(kb_dir)
        _bm25_loaded = True
    elif _bm25_index is not None and not _bm25_index.is_ready:
        # 索引已加载但不可用（可能启动时 pkl 还不存在），
        # 尝试重新加载（构建完成后 pkl 文件可能已就绪）
        _bm25_index = BM25Index.load(kb_dir)
    return _bm25_index


# 重置单例状态，下次访问时强制重新加载索引
def reset_bm25_index() -> None:
    """重置 BM25 索引单例，下次访问时重新加载。

    在索引构建完成后调用，确保后续检索能获取到新索引。
    """
    global _bm25_index, _bm25_loaded
    _bm25_index = None
    _bm25_loaded = False
