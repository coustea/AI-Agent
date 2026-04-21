"""ChatDoc 知识库操作客户端。"""

from __future__ import annotations

from typing import Any

import httpx

from .auth import ChatDocAuth
from .exceptions import ChatDocAPIError
from .models import (
    AddFilesResult,
    DeleteResult,
    RemoveFilesResult,
    Repo,
    RepoDetail,
    RepoFile,
)

API_BASE = "https://chatdoc.xfyun.cn/openapi/v1"


class RepoClient:
    """知识库操作客户端。

    提供知识库创建、查询、删除，以及文件关联管理功能。
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
        )

        result = resp.json()

        if result.get("code", 0) != 0:
            raise ChatDocAPIError(
                message=result.get("message", "API error"),
                code=result.get("code", -1),
                http_status=resp.status_code,
            )

        return result.get("data", result)

    async def create(
        self,
        name: str,
        *,
        desc: str = "",
        tags: list[str] | None = None,
    ) -> Repo:
        """创建知识库。

        Args:
            name: 知识库名称
            desc: 知识库描述
            tags: 标签列表

        Returns:
            创建的知识库信息
        """
        body = {
            "repoName": name,
            "repoDesc": desc,
            "repoTags": tags or [],
        }

        result = await self._request("POST", "/repo/create", json_data=body)
        return Repo(**result)

    async def list(
        self,
        *,
        name: str = "",
        current_page: int = 1,
        page_size: int = 10,
    ) -> list[Repo]:
        """查询知识库列表。

        Args:
            name: 知识库名称模糊查询
            current_page: 当前页
            page_size: 每页数量

        Returns:
            知识库列表
        """
        body = {
            "repoName": name,
            "currentPage": current_page,
            "pageSize": page_size,
        }

        result = await self._request("POST", "/repo/list", json_data=body)
        return [Repo(**item) for item in result.get("list", [])]

    async def get(self, repo_id: str) -> RepoDetail:
        """查询知识库详情。

        Args:
            repo_id: 知识库 ID

        Returns:
            知识库详情
        """
        result = await self._request("POST", "/repo/info", data={"repoId": repo_id})
        return RepoDetail(**result)

    async def delete(self, repo_id: str) -> DeleteResult:
        """删除知识库。

        Args:
            repo_id: 知识库 ID

        Returns:
            删除结果
        """
        result = await self._request("POST", "/repo/del", data={"repoId": repo_id})
        return DeleteResult(success=result.get("code", -1) == 0, message=result.get("message", ""))

    async def add_files(self, repo_id: str, file_ids: list[str]) -> AddFilesResult:
        """添加文件到知识库。

        Args:
            repo_id: 知识库 ID
            file_ids: 文件 ID 列表

        Returns:
            添加结果
        """
        result = await self._request(
            "POST",
            "/repo/file/add",
            json_data={"repoId": repo_id, "fileIds": file_ids},
        )
        return AddFilesResult(**result)

    async def remove_files(self, repo_id: str, file_ids: list[str]) -> RemoveFilesResult:
        """从知识库移除文件。

        Args:
            repo_id: 知识库 ID
            file_ids: 文件 ID 列表

        Returns:
            移除结果
        """
        result = await self._request(
            "POST",
            "/repo/file/remove",
            json_data={"repoId": repo_id, "fileIds": file_ids},
        )
        return RemoveFilesResult(**result)

    async def list_files(
        self,
        repo_id: str,
        *,
        file_name: str = "",
        ext_name: str = "",
        current_page: int = 1,
        page_size: int = 10,
    ) -> list[RepoFile]:
        """查询知识库文件列表。

        Args:
            repo_id: 知识库 ID
            file_name: 文件名模糊查询
            ext_name: 文件扩展名
            current_page: 当前页
            page_size: 每页数量

        Returns:
            文件列表
        """
        body = {
            "repoId": repo_id,
            "fileName": file_name,
            "extName": ext_name,
            "currentPage": current_page,
            "pageSize": page_size,
        }

        result = await self._request("POST", "/repo/file/list", json_data=body)
        return [RepoFile(**item) for item in result.get("list", [])]
