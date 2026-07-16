"""RAG 检索结果数据模型。

定义检索返回的结构化模型，隔离 ChatAgent 对底层检索实现的感知。
"""

from typing import Literal

from pydantic import BaseModel, Field

RetrievalStatus = Literal["ok", "partial", "empty", "unavailable"]
RetrievalType = Literal["vector", "bm25", "hybrid", ""]

ChannelStatus = Literal["ok", "unavailable", "disabled", "not_ready"]

CourseFilterMode = Literal["none", "filtered", "fallback"]

# ChromaDB collection 名（build 与 retriever 共享的索引契约，属实现细节，不暴露为运行时配置）
CHROMA_COLLECTION = "langchain"

# 索引 Schema 版本（store 与 build 共享）
SCHEMA_VERSION = "1"

# Manifest 文件名（retriever 与 build 共享）
MANIFEST_FILENAME = "manifest.json"


# 单条检索结果的数据模型
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

    # 通道特定的分数字段（用于 provenance）
    dense_distance: float | None = None  # 向量距离
    bm25_score: float | None = None  # BM25 原始分数
    fusion_score: float | None = None  # RRF 融合分数

    # 课程过滤标记
    course_fallback: bool = False  # 是否从全局结果补充

    # 结果来源：vector / bm25 / hybrid
    retrieval_type: RetrievalType = ""

    # 源文档关联信息
    parent_id: str = ""
    heading_path: str = ""
    page: int | None = None

    # 当前文档内的 chunk 序号，用于相邻 chunk 扩展
    chunk_index: int | None = None


# 检索结果容器（含状态、查询、chunk 列表与耗时）
class RetrievalResult(BaseModel):
    """检索结果容器。

    status 语义：
      ok          — 索引正常，至少返回一条 chunk
      partial     — 部分检索通道不可用，但仍有可用结果
      empty       — 索引正常，但没有匹配结果
      unavailable — 所有检索通道不可用
    """

    status: RetrievalStatus
    query: str
    chunks: list[RetrievedChunk] = Field(default_factory=list)
    elapsed_ms: int = 0
    message: str = ""

    # 通道状态（用于 provenance 和降级提示）
    dense_status: ChannelStatus = "not_ready"
    bm25_status: ChannelStatus = "not_ready"

    # 课程过滤模式
    course_filter_mode: CourseFilterMode = "none"
