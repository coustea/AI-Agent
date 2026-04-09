"""
知识库相关的请求/响应模型
"""
from pydantic import BaseModel, Field
from typing import Optional


class KnowledgeImportRequest(BaseModel):
    """知识库导入请求"""

    directory_path: str = Field(..., description="知识文档目录路径")
    collection_name: str = Field(
        default="knowledge_base", description="向量数据库集合名称"
    )


class KnowledgeSearchRequest(BaseModel):
    """知识检索请求"""

    query: str = Field(..., description="检索查询文本")
    collection_name: str = Field(
        default="knowledge_base", description="向量数据库集合名称"
    )
    top_k: int = Field(default=5, ge=1, le=20, description="返回结果数量")


class SearchResult(BaseModel):
    """单个检索结果"""

    content: str = Field(..., description="文档内容")
    metadata: dict = Field(default_factory=dict, description="文档元数据")
    score: Optional[float] = Field(None, description="相似度分数")


class KnowledgeSearchResponse(BaseModel):
    """知识检索响应"""

    query: str
    results: list[SearchResult]
    total: int
