"""ChatDoc SDK 主客户端。"""

import httpx

from .auth import ChatDocAuth
from .chat import ChatClient
from .file import FileClient
from .repo import RepoClient


class ChatDocClient:
    """讯飞 ChatDoc API 客户端。

    提供文档管理、知识库管理、文档问答等功能。

    Example:
        async with ChatDocClient(app_id, api_secret) as client:
            # 上传文档
            result = await client.file.upload(open("doc.pdf", "rb"), "doc.pdf")

            # 创建知识库
            repo = await client.repo.create("我的知识库")

            # 添加文档到知识库
            await client.repo.add_files(repo.repo_id, [result.file_id])

            # 问答
            async for chunk in client.chat.ask([result.file_id], "文档主要内容是什么？"):
                print(chunk, end="")
    """

    def __init__(self, app_id: str, api_secret: str):
        """初始化客户端。

        Args:
            app_id: 讯飞开放平台应用 ID
            api_secret: 讯飞开放平台 API Secret
        """
        self._auth = ChatDocAuth(app_id, api_secret)
        self._http = httpx.AsyncClient(timeout=30.0)
        self.file = FileClient(self._http, self._auth)
        self.repo = RepoClient(self._http, self._auth)
        self.chat = ChatClient(self._auth)

    async def close(self) -> None:
        """关闭客户端，释放资源。"""
        await self._http.aclose()

    async def __aenter__(self) -> "ChatDocClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()
