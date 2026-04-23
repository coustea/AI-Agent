"""ChatDoc 文档问答客户端。"""

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import websockets

from .auth import ChatDocAuth
from .exceptions import ChatDocWebSocketError
from .models import ChatExtends, ChatMessage

WS_URL = "wss://chatdoc.xfyun.cn/openapi/chat"

DEFAULT_PROMPT_TEMPLATE = """请将以下内容作为已知信息：
<wikicontent>
请根据以上内容回答用户的问题。
问题:<wikiquestion>
回答:"""


class ChatClient:
    """文档问答客户端。

    基于 WebSocket 实现流式问答。
    """

    def __init__(self, auth: ChatDocAuth):
        self._auth = auth

    async def ask(
        self,
        file_ids: list[str],
        question: str,
        *,
        temperature: float = 0.5,
        filter_score: float = 0.83,
        prompt_template: str | None = None,
        history: list[ChatMessage] | None = None,
    ) -> AsyncIterator[str]:
        """基于文档进行问答（流式返回）。

        Args:
            file_ids: 文档 ID 列表
            question: 用户问题
            temperature: 生成温度
            filter_score: 检索相似度阈值
            prompt_template: 自定义 prompt 模板
            history: 历史对话记录

        Yields:
            生成的文本片段

        Example:
            async with ChatDocClient(app_id, api_secret) as client:
                async for chunk in client.chat.ask(file_ids, "文档主要内容是什么？"):
                    print(chunk, end="")
        """
        ws_url = self._auth.get_ws_url(WS_URL)

        messages = history or []
        messages.append(ChatMessage(role="user", content=question))

        body = {
            "chatExtends": {
                "wikiPromptTpl": prompt_template or DEFAULT_PROMPT_TEMPLATE,
                "wikiFilterScore": filter_score,
                "temperature": temperature,
            },
            "fileIds": file_ids,
            "messages": [msg.model_dump() for msg in messages],
        }

        queue: asyncio.Queue[str | None] = asyncio.Queue()

        async def on_message(ws: Any, message: str) -> None:
            try:
                data = json.loads(message)
                code = data.get("code", 0)

                if code != 0:
                    await queue.put(None)
                    raise ChatDocWebSocketError(
                        message=data.get("message", "WebSocket error"),
                        code=code,
                    )

                content = data.get("content", "")
                status = data.get("status", 0)

                if content:
                    await queue.put(content)

                if status == 2:  # 完成
                    await queue.put(None)

            except json.JSONDecodeError:
                pass

        async with websockets.connect(
            ws_url,
            ssl=True,
        ) as ws:
            # 发送请求
            await ws.send(json.dumps(body))

            # 接收消息
            async for message in ws:
                data = json.loads(message)
                code = data.get("code", 0)

                if code != 0:
                    raise ChatDocWebSocketError(
                        message=data.get("message", "WebSocket error"),
                        code=code,
                    )

                content = data.get("content", "")
                status = data.get("status", 0)

                if content:
                    yield content

                if status == 2:  # 完成
                    break

    async def ask_once(
        self,
        file_ids: list[str],
        question: str,
        **kwargs: Any,
    ) -> str:
        """一次性返回完整答案。

        Args:
            file_ids: 文档 ID 列表
            question: 用户问题
            **kwargs: 其他参数传递给 ask()

        Returns:
            完整的答案文本
        """
        result = []
        async for chunk in self.ask(file_ids, question, **kwargs):
            result.append(chunk)
        return "".join(result)
