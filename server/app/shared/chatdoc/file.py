"""ChatDoc 文档操作客户端。"""

from typing import Any, BinaryIO

import httpx

from .auth import ChatDocAuth
from .exceptions import ChatDocAPIError
from .models import (
    ChunksResult,
    DeleteResult,
    EmbeddingResult,
    FileInfo,
    FileStatus,
    FileUploadResult,
    SearchResult,
    SplitResult,
    SummaryResult,
)

API_BASE = "https://chatdoc.xfyun.cn/openapi/v1"


class FileClient:
    """文档操作客户端。

    提供文档上传、切分、向量化、检索、删除等功能。
    """

    def __init__(self, http: httpx.AsyncClient, auth: ChatDocAuth):
        self._http = http
        self._auth = auth

    async def _request(
        self,
        method: str,
        path: str,
        json_data: dict | None = None,
        data: dict | None = None,
        files: dict | None = None,
    ) -> dict[str, Any]:
        """发送请求并处理响应。"""
        headers = self._auth.get_headers()
        url = f"{API_BASE}{path}"

        resp = await self._http.request(
            method,
            url,
            headers=headers,
            json=json_data,
            data=data,
            files=files,
        )

        result = resp.json()

        if result.get("code", 0) != 0:
            raise ChatDocAPIError(
                message=result.get("message", "API error"),
                code=result.get("code", -1),
                http_status=resp.status_code,
            )

        return result.get("data", result)

    async def upload(
        self,
        file: BinaryIO,
        filename: str,
        file_type: str = "wiki",
        *,
        callback_url: str = "",
        need_summary: bool = False,
        step_by_step: bool = False,
    ) -> FileUploadResult:
        """上传本地文件。

        Args:
            file: 文件二进制流
            filename: 文件名
            file_type: 文件类型，默认 "wiki"
            callback_url: 回调地址
            need_summary: 是否需要总结
            step_by_step: 是否分步处理

        Returns:
            上传结果，包含 file_id
        """
        data = {
            "fileName": filename,
            "fileType": file_type,
            "callbackUrl": callback_url,
            "needSummary": need_summary,
            "stepByStep": step_by_step,
        }
        files = {"file": (filename, file)}

        result = await self._request("POST", "/file/upload", data=data, files=files)
        return FileUploadResult(**result)

    async def upload_from_url(
        self,
        url: str,
        filename: str,
        file_type: str = "wiki",
        *,
        callback_url: str = "",
    ) -> FileUploadResult:
        """从 URL 上传文件。

        Args:
            url: 文件 URL
            filename: 文件名
            file_type: 文件类型
            callback_url: 回调地址

        Returns:
            上传结果
        """
        data = {
            "url": url,
            "fileName": filename,
            "fileType": file_type,
            "callbackUrl": callback_url,
        }

        result = await self._request("POST", "/file/upload", json_data=data)
        return FileUploadResult(**result)

    async def split(
        self,
        file_ids: list[str],
        *,
        split_type: str = "wiki",
        chunk_size: int = 2000,
        min_chunk_size: int = 100,
        chunk_separators: list[str] | None = None,
    ) -> SplitResult:
        """文档切分。

        Args:
            file_ids: 文件 ID 列表
            split_type: 切分类型
            chunk_size: 分块大小
            min_chunk_size: 最小分块大小
            chunk_separators: 切分符列表

        Returns:
            切分结果
        """
        body: dict[str, Any] = {
            "splitType": split_type,
            "isSplitDefault": chunk_separators is None,
            "fileIds": file_ids,
        }

        if chunk_separators:
            import base64

            encoded = [base64.b64encode(s.encode()).decode() for s in chunk_separators]
            body["wikiSplitExtends"] = {
                "chunkSeparators": encoded,
                "minChunkSize": min_chunk_size,
                "chunkSize": chunk_size,
            }

        result = await self._request("POST", "/file/split", json_data=body)
        return SplitResult(**result)

    async def embedding(self, file_ids: list[str]) -> EmbeddingResult:
        """文档向量化。

        Args:
            file_ids: 文件 ID 列表

        Returns:
            向量化结果
        """
        result = await self._request("POST", "/file/embedding", data={"fileIds": file_ids})
        return EmbeddingResult(**result)

    async def get_status(self, file_ids: list[str]) -> list[FileStatus]:
        """查询文档状态。

        Args:
            file_ids: 文件 ID 列表

        Returns:
            文件状态列表
        """
        result = await self._request("POST", "/file/status", data={"fileIds": file_ids})
        return [FileStatus(**item) for item in result.get("list", [])]

    async def search(
        self,
        file_ids: list[str],
        content: str,
        *,
        wiki_filter_score: float = 0.82,
        es_filter_score: int = 10,
    ) -> SearchResult:
        """文档内容检索。

        Args:
            file_ids: 文件 ID 列表
            content: 检索内容
            wiki_filter_score: 相似度阈值
            es_filter_score: ES 过滤分数

        Returns:
            检索结果
        """
        body = {
            "fileIds": file_ids,
            "content": content,
            "chatExtends": {
                "wikiFilterScore": wiki_filter_score,
                "esFilterScore": es_filter_score,
            },
        }

        result = await self._request("POST", "/vector/search", json_data=body)
        chunks = [FileChunk(**item) for item in result.get("list", [])]
        return SearchResult(chunks=chunks, total=len(chunks))

    async def get_chunks(self, file_id: str) -> list[dict[str, Any]]:
        """获取文件分块内容。

        Args:
            file_id: 文件 ID

        Returns:
            分块列表
        """
        result = await self._request("POST", "/file/chunks", data={"fileId": file_id})
        return result.get("list", [])

    async def get_summary(self, file_id: str) -> SummaryResult:
        """查询文档总结。

        Args:
            file_id: 文件 ID

        Returns:
            总结结果
        """
        result = await self._request("POST", "/file/summary/query", data={"fileId": file_id})
        return SummaryResult(**result)

    async def start_summary(self, file_id: str) -> dict[str, Any]:
        """发起文档总结。

        Args:
            file_id: 文件 ID

        Returns:
            操作结果
        """
        return await self._request("POST", "/file/summary/start", data={"fileId": file_id})

    async def get_info(self, file_id: str) -> FileInfo:
        """查询文件详情。

        Args:
            file_id: 文件 ID

        Returns:
            文件详情
        """
        result = await self._request("POST", "/file/info", data={"fileId": file_id})
        return FileInfo(**result)

    async def list(
        self,
        *,
        file_name: str = "",
        ext_name: str = "",
        current_page: int = 1,
        page_size: int = 10,
    ) -> list[FileInfo]:
        """查询 appId 下的文档列表。

        Args:
            file_name: 文件名模糊查询
            ext_name: 文件扩展名
            current_page: 当前页
            page_size: 每页数量

        Returns:
            文件列表
        """
        body = {
            "fileName": file_name,
            "extName": ext_name,
            "currentPage": current_page,
            "pageSize": page_size,
        }

        result = await self._request("POST", "/file/list", json_data=body)
        return [FileInfo(**item) for item in result.get("list", [])]

    async def delete(self, file_ids: list[str]) -> DeleteResult:
        """删除文档。

        Args:
            file_ids: 文件 ID 列表

        Returns:
            删除结果
        """
        result = await self._request("POST", "/file/del", data={"fileIds": file_ids})
        return DeleteResult(success=result.get("code", -1) == 0, message=result.get("message", ""))
