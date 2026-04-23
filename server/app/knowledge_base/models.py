"""ChatDoc API 数据模型。"""

from typing import Any

from pydantic import BaseModel, Field


# ============ 通用响应 ============

class APIResponse(BaseModel):
    """API 通用响应。"""
    code: int = 0
    message: str = "success"
    data: Any = None


# ============ 文件相关 ============

class FileUploadResult(BaseModel):
    """文件上传结果。"""
    file_id: str = Field(..., alias="fileId")
    file_name: str = Field("", alias="fileName")
    status: int = 0  # 0=处理中, 1=成功, 2=失败

    class Config:
        populate_by_name = True


class FileStatus(BaseModel):
    """文件状态。"""
    file_id: str = Field(..., alias="fileId")
    file_name: str = Field("", alias="fileName")
    status: int  # 0=处理中, 1=成功, 2=失败
    status_desc: str = Field("", alias="statusDesc")

    class Config:
        populate_by_name = True


class FileInfo(BaseModel):
    """文件详情。"""
    file_id: str = Field(..., alias="fileId")
    file_name: str = Field("", alias="fileName")
    file_size: int = Field(0, alias="fileSize")
    ext_name: str = Field("", alias="extName")
    status: int = 0
    create_time: str = Field("", alias="createTime")
    update_time: str = Field("", alias="updateTime")

    class Config:
        populate_by_name = True


class FileChunk(BaseModel):
    """文件分块。"""
    chunk_id: str = Field(..., alias="chunkId")
    content: str
    score: float = 0.0

    class Config:
        populate_by_name = True


class SearchResult(BaseModel):
    """文档检索结果。"""
    chunks: list[FileChunk] = []
    total: int = 0


class SplitResult(BaseModel):
    """文档切分结果。"""
    success_count: int = 0
    failed_count: int = 0


class EmbeddingResult(BaseModel):
    """向量化结果。"""
    success_count: int = 0
    failed_count: int = 0


class SummaryResult(BaseModel):
    """文档总结结果。"""
    summary: str = ""
    status: int = 0


class DeleteResult(BaseModel):
    """删除结果。"""
    success: bool = False
    message: str = ""


# ============ 知识库相关 ============

class Repo(BaseModel):
    """知识库基本信息。"""
    repo_id: str = Field(..., alias="repoId")
    repo_name: str = Field("", alias="repoName")
    repo_desc: str = Field("", alias="repoDesc")
    repo_tags: list[str] = Field(default_factory=list, alias="repoTags")
    create_time: str = Field("", alias="createTime")
    update_time: str = Field("", alias="updateTime")

    class Config:
        populate_by_name = True


class RepoDetail(Repo):
    """知识库详情。"""
    file_count: int = Field(0, alias="fileCount")
    total_size: int = Field(0, alias="totalSize")

    class Config:
        populate_by_name = True


class RepoFile(BaseModel):
    """知识库中的文件。"""
    file_id: str = Field(..., alias="fileId")
    file_name: str = Field("", alias="fileName")
    status: int = 0
    add_time: str = Field("", alias="addTime")

    class Config:
        populate_by_name = True


class AddFilesResult(BaseModel):
    """添加文件到知识库结果。"""
    success_count: int = 0
    failed_count: int = 0


class RemoveFilesResult(BaseModel):
    """从知识库移除文件结果。"""
    success_count: int = 0
    failed_count: int = 0


# ============ 问答相关 ============

class ChatMessage(BaseModel):
    """聊天消息。"""
    role: str  # "user" or "assistant"
    content: str


class ChatExtends(BaseModel):
    """问答扩展配置。"""
    wiki_prompt_tpl: str = Field(
        default="请将以下内容作为已知信息：\n<wikicontent>\n请根据以上内容回答用户的问题。\n问题:<wikiquestion>\n回答:",
        alias="wikiPromptTpl",
    )
    wiki_filter_score: float = Field(default=0.83, alias="wikiFilterScore")
    temperature: float = Field(default=0.5)

    class Config:
        populate_by_name = True


class ChatRequest(BaseModel):
    """问答请求。"""
    file_ids: list[str] = Field(..., alias="fileIds")
    messages: list[ChatMessage]
    chat_extends: ChatExtends | None = Field(default=None, alias="chatExtends")

    class Config:
        populate_by_name = True
