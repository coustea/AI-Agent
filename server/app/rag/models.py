"""RAG 检索结果数据模型。

定义检索返回的结构化模型，隔离 ChatAgent 对底层检索实现的感知。
"""

from typing import Literal

from pydantic import BaseModel, Field

RetrievalStatus = Literal["ok", "empty", "unavailable"]

# ChromaDB collection 名（build 与 retriever 共享的索引契约，属实现细节，不暴露为运行时配置）
CHROMA_COLLECTION = "langchain"


class RetrievedChunk(BaseModel):
    """单条检索结果。

    Called by: app/rag/retriever.py _parse_chroma_results(), app/rag/tools.py _build_sources().
    Schema change: added parent_id (links to source file) and heading_path (heading hierarchy).
    Per user: "确保rag模块可以检索知识库，然后后期给我的chat模块使用".
    """

    chunk_id: str
    content: str
    source: str
    title: str
    section: str = ""
    course: str = ""
    distance: float | None = None
    parent_id: str = ""
    heading_path: str = ""


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
