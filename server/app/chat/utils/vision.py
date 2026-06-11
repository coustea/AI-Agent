"""图片分析服务 — Spark OCR + GLM-4V 双模式，供 chat/avatar 共享。

降级策略：优先使用讯飞 Spark 图片理解(WebSocket 实时流)，
  Spark 不可用(凭据缺失/调用失败)时降级到 GLM-4V 视觉模型。
Spark 鉴权：HMAC-SHA256 签名 + Base64 编码，按讯飞 WebSocket API 规范构造 URL。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import ssl
from mimetypes import guess_type
from datetime import datetime
from time import mktime
from urllib.parse import urlencode, urlparse
from wsgiref.handlers import format_date_time

import websockets
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import SPARK_API_KEY, SPARK_API_SECRET, SPARK_APP_ID
from app.infra.llm import Llm, get_llm
from app.infra.logging import get_logger
from app.chat.utils.files import resolve_uploaded_image_path

logger = get_logger(__name__)

_SPARK_IMAGE_URL = "wss://spark-api.cn-huabei-1.xf-yun.com/v2.1/image"


def _build_image_input(url: str) -> dict | None:
    image_path = resolve_uploaded_image_path(url)
    if image_path and image_path.is_file():
        mime_type = guess_type(image_path.name)[0] or "image/png"
        image_b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        return {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_b64}"}}
    if not url:
        return None
    return {"type": "image_url", "image_url": {"url": url}}


# ---------------------------------------------------------------------------
# Spark 图片理解 WebSocket 适配器
# ---------------------------------------------------------------------------


class _WsParam:
    """WebSocket 鉴权参数生成器。"""

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
    """讯飞 Spark 图片理解服务。"""

    def __init__(self):
        self.appid = SPARK_APP_ID
        self.api_key = SPARK_API_KEY
        self.api_secret = SPARK_API_SECRET
        if not all([self.appid, self.api_key, self.api_secret]):
            logger.warning("[SparkImage] 凭据未完整配置，图片理解将回退到 GLM")

    @property
    def configured(self) -> bool:
        return bool(self.appid and self.api_key and self.api_secret)

    async def analyze(self, image_bytes: bytes, question: str = "请描述这张图片") -> str:
        if not self.configured:
            raise RuntimeError("Spark Image API 凭据未配置")

        ws_param = _WsParam(self.api_key, self.api_secret, _SPARK_IMAGE_URL)
        url = ws_param.create_url()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        request_body = {
            "header": {"app_id": self.appid},
            "parameter": {"chat": {"domain": "imagev3", "temperature": 0.5, "top_k": 4, "max_tokens": 2028, "auditing": "default"}},
            "payload": {"message": {"text": [{"role": "user", "content": image_b64, "content_type": "image"}, {"role": "user", "content": question}]}},
        }

        ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        answer = ""
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


# ---------------------------------------------------------------------------
# VisionService: Spark + GLM-4V 双模式
# ---------------------------------------------------------------------------


class VisionService:
    """图片分析服务，支持 Spark OCR 和 GLM-4V 双模式。"""

    def __init__(self, llm: Llm | None = None) -> None:
        self.llm = llm or get_llm()

    async def analyze_images(self, image_urls: list[str], question: str) -> dict:
        """分析图片，优先 Spark 模式，失败时降级到 GLM-4V。"""
        if spark_image_service.configured and image_urls:
            spark_results: list[str] = []
            spark_ok = True
            for url in image_urls:
                image_path = resolve_uploaded_image_path(url)
                if not image_path:
                    spark_ok = False
                    break
                try:
                    image_bytes = image_path.read_bytes()
                    result = await spark_image_service.analyze(image_bytes, question)
                    if result:
                        spark_results.append(result)
                    else:
                        spark_ok = False
                        break
                except Exception as exc:
                    logger.warning("[VisionService] spark failed, fallback to glm: %s", exc)
                    spark_ok = False
                    break

            if spark_ok and spark_results:
                combined = "\n\n".join(spark_results) if len(spark_results) > 1 else spark_results[0]
                return {
                    "success": True,
                    "mode": "spark",
                    "analysis_text": combined,
                    "messages": None,
                    "error": None,
                }

        # GLM-4V 降级模式
        content_blocks: list[dict] = [{"type": "text", "text": question or "请描述这些图片"}]
        for url in image_urls:
            image_input = _build_image_input(url)
            if image_input:
                content_blocks.append(image_input)
        response = await self.llm.vision(
            [HumanMessage(content=content_blocks)],
            temperature=0.7,
        )
        return {
            "success": True,
            "mode": "glm",
            "analysis_text": response.content if isinstance(response.content, str) else str(response.content),
            "messages": [SystemMessage(content=""), response],
            "error": None,
        }


def build_vision_service(llm: Llm | None = None):
    """工厂函数：创建 VisionService 实例。"""
    return VisionService(llm)


__all__ = ["VisionService", "build_vision_service", "spark_image_service"]
