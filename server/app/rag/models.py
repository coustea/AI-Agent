"""RAG 检索结果数据模型。

定义检索返回的结构化模型，隔离 ChatAgent 对底层检索实现的感知。
"""

from typing import Literal

from pydantic import BaseModel, Field

RetrievalStatus = Literal["ok", "empty", "unavailable"]
RetrievalType = Literal["vector", "bm25", "hybrid", ""]

# ChromaDB collection 名（build 与 retriever 共享的索引契约，属实现细节，不暴露为运行时配置）
CHROMA_COLLECTION = "langchain"


class RetrievedChunk(BaseModel):
    """单条检索结果。"""

    chunk_id: str
    content: str
    source: str
    title: str
    section: str = ""
    course: str = ""

    # 向量检索距离，越小越相似
    distance: float | None = None

    # 统一相关性分数：BM25 / RRF / rerank 都可以写这里
    score: float | None = None

    # 结果来源：vector / bm25 / hybrid
    retrieval_type: RetrievalType = ""

    # 源文档关联信息
    parent_id: str = ""
    heading_path: str = ""
    page: int | None = None

    # 当前文档内的 chunk 序号，用于相邻 chunk 扩展
    chunk_index: int | None = None


class RetrievalResult(BaseModel):
    """检索结果容器。

    status 语义：
      ok          — 索引正常，至少返回一条 chunk
      empty       — 索引正常，但没有匹配结果
      unavailable — 索引不存在 / 损坏 / 嵌入服务不可用
    """

    status: RetrievalStatus
    query: str
    chunks: list[RetrievedChunk] = Field(default_factory=list)
    elapsed_ms: int = 0
    message: str = ""
