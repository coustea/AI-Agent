"""ChatDoc SDK - 讯飞 ChatDoc API 异步客户端。

提供文档管理、知识库管理、文档问答等功能。

Example:
    from app.shared.chatdoc import ChatDocClient

    async with ChatDocClient(app_id, api_secret) as client:
        # 上传文档
        result = await client.file.upload(open("doc.pdf", "rb"), "doc.pdf")

        # 创建知识库并添加文档
        repo = await client.repo.create("我的知识库")
        await client.repo.add_files(repo.repo_id, [result.file_id])

        # 文档问答
        async for chunk in client.chat.ask([result.file_id], "文档主要内容是什么？"):
            print(chunk, end="")
"""

from .auth import ChatDocAuth
from .chat import ChatClient
from .client import ChatDocClient
from .exceptions import ChatDocAPIError, ChatDocAuthError, ChatDocError, ChatDocWebSocketError
from .file import FileClient
from .importer import KnowledgeImporter
from .models import (
    AddFilesResult,
    ChatExtends,
    ChatMessage,
    DeleteResult,
    EmbeddingResult,
    FileChunk,
    FileInfo,
    FileStatus,
    FileUploadResult,
    RemoveFilesResult,
    Repo,
    RepoDetail,
    RepoFile,
    SearchResult,
    SplitResult,
    SummaryResult,
)
from .repo import RepoClient
from .service import ChatDocService, get_chatdoc_service

__all__ = [
    # 主客户端
    "ChatDocClient",
    # 子客户端
    "FileClient",
    "RepoClient",
    "ChatClient",
    # 认证
    "ChatDocAuth",
    # 异常
    "ChatDocError",
    "ChatDocAuthError",
    "ChatDocAPIError",
    "ChatDocWebSocketError",
    # 模型
    "FileUploadResult",
    "FileStatus",
    "FileInfo",
    "FileChunk",
    "SearchResult",
    "SplitResult",
    "EmbeddingResult",
    "SummaryResult",
    "DeleteResult",
    "Repo",
    "RepoDetail",
    "RepoFile",
    "AddFilesResult",
    "RemoveFilesResult",
    "ChatMessage",
    "ChatExtends",
    # 服务层
    "ChatDocService",
    "get_chatdoc_service",
    # 批量导入
    "KnowledgeImporter",
]

__version__ = "1.0.0"
