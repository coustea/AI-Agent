"""RAG package — local textbook knowledge retrieval.

模块结构：
  load.py       统一文档加载器
  splitter.py   文档分割器（按类型）
  metadata.py   元数据推断
  store.py      向量数据库存储
  embeddings.py 嵌入向量
  models.py     数据模型
  retriever.py  混合检索
  bm25.py       BM25 关键词索引
  tools.py      工具封装
  eval.py       检索评测
  indexing/     索引构建管道
"""

from app.rag.tools import SearchKnowledgeBaseArgs, build_knowledge_tool

__all__ = [
    "SearchKnowledgeBaseArgs",
    "build_knowledge_tool",
]
