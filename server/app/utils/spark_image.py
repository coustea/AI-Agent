"""星火图片理解 WebSocket 异步客户端。

将 demo/ImageUnderstanding.py 的同步 WebSocket 调用封装为异步接口，
供 TutorAgent 的 vision 路径使用。
"""

import base64
import hashlib
import hmac
import json
import os
import ssl
from datetime import datetime
from time import mktime
from urllib.parse import urlparse, urlencode
from wsgiref.handlers import format_date_time

import websockets

from app.core.logging import get_logger

logger = get_logger(__name__)

_SPARK_IMAGE_URL = "wss://spark-api.cn-huabei-1.xf-yun.com/v2.1/image"


class _WsParam:
    """生成星火 WebSocket 鉴权 URL。"""

    def __init__(self, api_key: str, api_secret: str, base_url: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.host = urlparse(base_url).netloc
        self.path = urlparse(base_url).path
        self.base_url = base_url

    def create_url(self) -> str:
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        signature_origin = f"host: {self.host}\ndate: {date}\nGET {self.path} HTTP/1.1"
        signature_sha = hmac.new(
            self.api_secret.encode(),
            signature_origin.encode(),
            digestmod=hashlib.sha256,
        ).digest()
        signature_b64 = base64.b64encode(signature_sha).decode()

        authorization_origin = (
            f'api_key="{self.api_key}", algorithm="hmac-sha256", '
            f'headers="host date request-line", signature="{signature_b64}"'
        )
        authorization = base64.b64encode(authorization_origin.encode()).decode()

        params = {"authorization": authorization, "date": date, "host": self.host}
        return f"{self.base_url}?{urlencode(params)}"


class SparkImageService:
    """星火图片理解异步服务。"""

    def __init__(self):
        self.appid = os.getenv("SPARK_IMAGE_APPID", "")
        self.api_key = os.getenv("SPARK_IMAGE_API_KEY", "")
        self.api_secret = os.getenv("SPARK_IMAGE_API_SECRET", "")

        if not all([self.appid, self.api_key, self.api_secret]):
            logger.warning("[SparkImage] 凭据未完整配置，图片理解将回退到 GLM")

    @property
    def configured(self) -> bool:
        return bool(self.appid and self.api_key and self.api_secret)

    async def analyze(self, image_bytes: bytes, question: str = "请描述这张图片") -> str:
        """调用星火图片理解 API，返回完整文本结果。"""
        if not self.configured:
            raise RuntimeError("Spark Image API 凭据未配置")

        ws_param = _WsParam(self.api_key, self.api_secret, _SPARK_IMAGE_URL)
        url = ws_param.create_url()

        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        text_payload = [
            {"role": "user", "content": image_b64, "content_type": "image"},
            {"role": "user", "content": question},
        ]

        request_body = {
            "header": {"app_id": self.appid},
            "parameter": {
                "chat": {
                    "domain": "imagev3",
                    "temperature": 0.5,
                    "top_k": 4,
                    "max_tokens": 2028,
                    "auditing": "default",
                }
            },
            "payload": {"message": {"text": text_payload}},
        }

        ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        answer = ""
        # 显式禁用代理，避免在存在 socks 代理环境时要求额外安装 python-socks。
        async with websockets.connect(url, ssl=ssl_ctx, proxy=None) as ws:
            await ws.send(json.dumps(request_body))

            async for raw in ws:
                data = json.loads(raw)
                code = data["header"]["code"]
                if code != 0:
                    raise RuntimeError(f"Spark Image API 错误: code={code}, {data}")

                answer += data["payload"]["choices"]["text"][0]["content"]
                if data["payload"]["choices"]["status"] == 2:
                    break

        return answer


# 全局单例
spark_image_service = SparkImageService()
