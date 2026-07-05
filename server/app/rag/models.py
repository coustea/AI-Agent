"""RAG 检索结果数据模型。

定义检索返回的结构化模型，隔离 ChatAgent 对底层检索实现的感知。
"""

from typing import Literal

from pydantic import BaseModel, Field

RetrievalStatus = Literal["ok", "empty", "unavailable"]


class RetrievedChunk(BaseModel):
    """单条检索结果。"""

    chunk_id: str
    content: str
    source: str
    title: str
    section: str = ""
    course: str = ""
    distance: float | None = None


class RetrievalResult(BaseModel):
    """检索结果容器。

    status 语义：
      ok          — 索引正常，至少返回一条 chunk
      empty       — 索引正常，但没有匹配结果
      unavailable — 索引不存在 / 损坏 / Ollama 不可用
    """

    status: RetrievalStatus
    query: str
    chunks: list[RetrievedChunk] = Field(default_factory=list)
    elapsed_ms: int = 0
    message: str = ""
