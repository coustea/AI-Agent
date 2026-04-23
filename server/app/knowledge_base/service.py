"""ChatDoc RAG 服务封装。

提供用户知识库管理、文档上传、检索问答等功能。
用于 TutorAgent 集成。
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, BinaryIO

from app.config import CHATDOC_API_SECRET, CHATDOC_APP_ID, CHATDOC_ENABLED
from app.infra.logging import get_logger
from app.knowledge_base.client import ChatDocClient
from app.knowledge_base.exceptions import ChatDocError
from app.knowledge_base.models import FileInfo, Repo

logger = get_logger(__name__)

GLOBAL_REPO_NAME = "global_cs_ai_knowledge_base"
GLOBAL_REPO_DESC = "计算机科学与人工智能全局学习知识库"
GLOBAL_REPO_TAGS = ["computer-science", "artificial-intelligence", "global"]


class ChatDocService:
    """ChatDoc RAG 服务封装。

    功能：
    - 单例管理 ChatDoc 客户端
    - 用户知识库自动创建/获取
    - 文档上传并关联到知识库
    - 基于知识库的检索问答

    Example:
        service = ChatDocService.get_shared()

        # 上传文档
        file_id = await service.upload_document(user_id=1, file=open("doc.pdf", "rb"), filename="doc.pdf")

        # 检索
        results = await service.search(user_id=1, query="关键词")

        # 问答
        async for chunk in service.chat(user_id=1, query="文档主要内容是什么？"):
            print(chunk, end="")
    """

    _instance: ChatDocService | None = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __init__(self) -> None:
        self._client: ChatDocClient | None = None
        self._user_repos: dict[int, str] = {}  # user_id -> repo_id
        self._user_files: dict[int, list[str]] = {}  # user_id -> [file_ids]
        self._global_repo_id: str | None = None
        self._initialized = False

    @classmethod
    def get_shared(cls) -> ChatDocService:
        """获取全局单例。"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def enabled(self) -> bool:
        """检查 ChatDoc 是否启用。"""
        return CHATDOC_ENABLED and bool(CHATDOC_APP_ID) and bool(CHATDOC_API_SECRET)

    async def _ensure_client(self) -> ChatDocClient:
        """确保客户端已初始化。"""
        if self._client is not None:
            return self._client

        async with self._lock:
            if self._client is not None:
                return self._client

            if not self.enabled:
                raise ChatDocError("ChatDoc 未启用，请检查配置")

            self._client = ChatDocClient(CHATDOC_APP_ID, CHATDOC_API_SECRET)
            self._initialized = True
            logger.info("[ChatDocService] 客户端初始化完成")
            return self._client

    async def close(self) -> None:
        """关闭客户端。"""
        if self._client:
            await self._client.close()
            self._client = None
            self._initialized = False

    # ------------------------------------------------------------------
    # 知识库管理
    # ------------------------------------------------------------------
    async def get_or_create_global_repo(self) -> str:
        """获取或创建全局计算机/AI 学习知识库。"""
        if self._global_repo_id:
            return self._global_repo_id

        client = await self._ensure_client()
        repos = await client.repo.list(name=GLOBAL_REPO_NAME)
        for repo in repos:
            if repo.repo_name == GLOBAL_REPO_NAME:
                self._global_repo_id = repo.repo_id
                logger.info("[ChatDocService] 复用全局知识库 repo_id=%s", repo.repo_id)
                return repo.repo_id

        repo = await client.repo.create(
            name=GLOBAL_REPO_NAME,
            desc=GLOBAL_REPO_DESC,
            tags=GLOBAL_REPO_TAGS,
        )
        self._global_repo_id = repo.repo_id
        logger.info("[ChatDocService] 创建全局知识库 repo_id=%s", repo.repo_id)
        return repo.repo_id

    async def get_global_repo_file_ids(self, repo_id: str | None = None) -> list[str]:
        """返回全局知识库中的文件 ID 列表。"""
        client = await self._ensure_client()
        effective_repo_id = repo_id or await self.get_or_create_global_repo()
        files = await client.repo.list_files(effective_repo_id, page_size=100)
        return [item.file_id for item in files if item.file_id]

    async def get_or_create_user_repo(self, user_id: int) -> str:
        """获取或创建用户专属知识库。

        Args:
            user_id: 用户 ID

        Returns:
            知识库 ID (repo_id)
        """
        if user_id in self._user_repos:
            return self._user_repos[user_id]

        client = await self._ensure_client()

        # 尝试查找现有知识库
        repo_name = f"user_{user_id}"
        repos = await client.repo.list(name=repo_name)

        for repo in repos:
            if repo.repo_name == repo_name:
                self._user_repos[user_id] = repo.repo_id
                logger.info("[ChatDocService] 复用知识库 user_id=%s repo_id=%s", user_id, repo.repo_id)
                return repo.repo_id

        # 创建新知识库
        repo = await client.repo.create(
            name=repo_name,
            desc=f"用户 {user_id} 的专属知识库",
        )
        self._user_repos[user_id] = repo.repo_id
        logger.info("[ChatDocService] 创建知识库 user_id=%s repo_id=%s", user_id, repo.repo_id)
        return repo.repo_id

    async def get_user_repo(self, user_id: int) -> Repo | None:
        """获取用户知识库详情。

        Args:
            user_id: 用户 ID

        Returns:
            知识库详情，不存在返回 None
        """
        client = await self._ensure_client()

        if user_id in self._user_repos:
            return await client.repo.get(self._user_repos[user_id])

        repo_name = f"user_{user_id}"
        repos = await client.repo.list(name=repo_name)

        for repo in repos:
            if repo.repo_name == repo_name:
                self._user_repos[user_id] = repo.repo_id
                return repo

        return None

    # ------------------------------------------------------------------
    # 文档管理
    # ------------------------------------------------------------------
    async def upload_document(
        self,
        user_id: int,
        file: BinaryIO | None = None,
        filename: str = "",
        file_url: str | None = None,
        *,
        auto_add_to_repo: bool = True,
    ) -> str:
        """上传文档到 ChatDoc。

        Args:
            user_id: 用户 ID
            file: 文件二进制流（本地文件）
            filename: 文件名
            file_url: 文件 URL（网络文件）
            auto_add_to_repo: 是否自动添加到用户知识库

        Returns:
            文件 ID (file_id)
        """
        client = await self._ensure_client()

        # 上传文件
        if file_url:
            result = await client.file.upload_from_url(
                url=file_url,
                filename=filename or Path(file_url).name,
            )
        elif file:
            result = await client.file.upload(
                file=file,
                filename=filename,
            )
        else:
            raise ValueError("必须提供 file 或 file_url")

        file_id = result.file_id
        logger.info("[ChatDocService] 文档上传成功 user_id=%s file_id=%s", user_id, file_id)

        # 添加到用户知识库
        if auto_add_to_repo:
            repo_id = await self.get_or_create_user_repo(user_id)
            await client.repo.add_files(repo_id, [file_id])
            logger.info("[ChatDocService] 文档已加入知识库 user_id=%s repo_id=%s", user_id, repo_id)

        # 记录用户文件
        if user_id not in self._user_files:
            self._user_files[user_id] = []
        self._user_files[user_id].append(file_id)

        return file_id

    async def get_user_files(self, user_id: int) -> list[FileInfo]:
        """获取用户上传的所有文档。

        Args:
            user_id: 用户 ID

        Returns:
            文档列表
        """
        client = await self._ensure_client()
        return await client.file.list()

    async def delete_document(self, user_id: int, file_id: str) -> bool:
        """删除文档。

        Args:
            user_id: 用户 ID
            file_id: 文件 ID

        Returns:
            是否成功
        """
        client = await self._ensure_client()
        result = await client.file.delete([file_id])

        # 从缓存中移除
        if user_id in self._user_files and file_id in self._user_files[user_id]:
            self._user_files[user_id].remove(file_id)

        logger.info("[ChatDocService] 文档删除 user_id=%s file_id=%s success=%s", user_id, file_id, result.success)
        return result.success

    async def get_document_status(self, file_ids: list[str]) -> list[dict[str, Any]]:
        """查询文档处理状态。

        Args:
            file_ids: 文件 ID 列表

        Returns:
            状态列表
        """
        client = await self._ensure_client()
        statuses = await client.file.get_status(file_ids)
        return [
            {
                "file_id": s.file_id,
                "file_name": s.file_name,
                "status": s.status,
                "status_desc": s.status_desc,
            }
            for s in statuses
        ]

    # ------------------------------------------------------------------
    # 检索与问答
    # ------------------------------------------------------------------
    async def search_global(
        self,
        query: str,
        *,
        top_k: int = 5,
        filter_score: float = 0.82,
    ) -> list[dict[str, Any]]:
        """在全局计算机/AI 学习知识库中检索相关内容。"""
        client = await self._ensure_client()
        repo_id = await self.get_or_create_global_repo()
        file_ids = await self.get_global_repo_file_ids(repo_id)
        if not file_ids:
            logger.info("[ChatDocService] 全局知识库暂无文档 query=%s", query[:50])
            return []

        result = await client.file.search(
            file_ids=file_ids,
            content=query,
            wiki_filter_score=filter_score,
        )
        logger.info("[ChatDocService] 全局检索完成 query=%s hits=%d", query[:50], len(result.chunks))

        return [
            {
                "chunk_id": chunk.chunk_id,
                "content": chunk.content,
                "score": chunk.score,
            }
            for chunk in result.chunks[:top_k]
        ]

    async def search(
        self,
        user_id: int,
        query: str,
        *,
        file_ids: list[str] | None = None,
        top_k: int = 5,
        filter_score: float = 0.82,
    ) -> list[dict[str, Any]]:
        """在知识库中检索相关内容。

        Args:
            user_id: 用户 ID
            query: 检索查询
            file_ids: 指定文件 ID（可选，默认搜索用户所有文件）
            top_k: 返回数量
            filter_score: 相似度阈值

        Returns:
            检索结果列表
        """
        client = await self._ensure_client()

        # 使用用户所有文件或指定文件
        target_files = file_ids or self._user_files.get(user_id, [])
        if not target_files:
            logger.warning("[ChatDocService] 无可用文档 user_id=%s", user_id)
            return []

        result = await client.file.search(
            file_ids=target_files,
            content=query,
            wiki_filter_score=filter_score,
        )

        logger.info("[ChatDocService] 检索完成 user_id=%s query=%s hits=%d", user_id, query[:50], len(result.chunks))

        return [
            {
                "chunk_id": chunk.chunk_id,
                "content": chunk.content,
                "score": chunk.score,
            }
            for chunk in result.chunks[:top_k]
        ]

    async def chat(
        self,
        user_id: int,
        query: str,
        *,
        file_ids: list[str] | None = None,
        temperature: float = 0.5,
        filter_score: float = 0.83,
    ) -> AsyncIterator[str]:
        """基于知识库的流式问答。

        Args:
            user_id: 用户 ID
            query: 用户问题
            file_ids: 指定文件 ID（可选）
            temperature: 生成温度
            filter_score: 检索相似度阈值

        Yields:
            生成的文本片段
        """
        client = await self._ensure_client()

        # 使用用户所有文件或指定文件
        target_files = file_ids or self._user_files.get(user_id, [])
        if not target_files:
            yield "[知识库中暂无文档，请先上传文档]"
            return

        logger.info("[ChatDocService] 开始问答 user_id=%s query=%s files=%d", user_id, query[:50], len(target_files))

        try:
            async for chunk in client.chat.ask(
                file_ids=target_files,
                question=query,
                temperature=temperature,
                filter_score=filter_score,
            ):
                yield chunk
        except ChatDocError as e:
            logger.error("[ChatDocService] 问答失败 user_id=%s error=%s", user_id, e.message)
            yield f"[问答失败: {e.message}]"

    async def chat_once(
        self,
        user_id: int,
        query: str,
        **kwargs: Any,
    ) -> str:
        """一次性返回完整答案。

        Args:
            user_id: 用户 ID
            query: 用户问题
            **kwargs: 其他参数

        Returns:
            完整答案
        """
        result = []
        async for chunk in self.chat(user_id, query, **kwargs):
            result.append(chunk)
        return "".join(result)


# 全局单例快捷访问
def get_chatdoc_service() -> ChatDocService:
    """获取 ChatDoc 服务单例。"""
    return ChatDocService.get_shared()
