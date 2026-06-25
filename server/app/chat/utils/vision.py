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

from app.config import SPARK_API_KEY, SPARK_API_SECRET, SPARK_APP_ID, VISION_TEMPERATURE
from app.infra.llm import Llm, get_llm
from app.infra.logging import get_logger
from app.chat.utils.files import resolve_uploaded_image_path

logger = get_logger(__name__)

_SPARK_IMAGE_URL = "wss://spark-api.cn-huabei-1.xf-yun.com/v2.1/image"


def _build_image_input(url: str) -> dict | None:
    """将图片 URL 构造为 LLM vision API 可识别的 content block。

    优先读取本地文件并转为 base64 data URL，兜底直接使用原始 URL。
    """
    image_path = resolve_uploaded_image_path(url)
    if image_path and image_path.is_file():
        # 根据文件扩展名推断 MIME 类型，默认 image/png
        mime_type = guess_type(image_path.name)[0] or "image/png"
        # 将图片二进制数据编码为 base64，构造 data URL 供 LLM 直接消费
        image_b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        return {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_b64}"}}
    if not url:
        return None
    # 兜底：直接传递远程 URL，让 LLM 自行下载
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
        """生成带 HMAC-SHA256 签名的 WebSocket 鉴权 URL。

        按讯飞开放平台规范构造签名：host + date + request-line → HMAC → Base64。
        """
        now = datetime.now()
        # 格式化为 HTTP 日期格式（RFC 2822）
        date = format_date_time(mktime(now.timetuple()))
        # 构造签名原文：按讯飞规范拼接 host、date 和请求行
        signature_origin = f"host: {self.host}\ndate: {date}\nGET {self.path} HTTP/1.1"
        # 使用 API Secret 进行 HMAC-SHA256 签名
        signature_sha = hmac.new(
            self.api_secret.encode(),
            signature_origin.encode(),
            digestmod=hashlib.sha256,
        ).digest()
        # 将签名结果 Base64 编码
        signature_b64 = base64.b64encode(signature_sha).decode()
        # 构造 authorization 字段：包含 api_key、算法、签名头列表和签名值
        authorization_origin = (
            f'api_key="{self.api_key}", algorithm="hmac-sha256", '
            f'headers="host date request-line", signature="{signature_b64}"'
        )
        # 整个 authorization 也需要 Base64 编码
        authorization = base64.b64encode(authorization_origin.encode()).decode()
        # 拼接最终的鉴权 URL：基础 URL + authorization、date、host 查询参数
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
        """通过 WebSocket 调用讯飞 Spark 图片理解 API。

        Args:
            image_bytes: 图片的原始二进制数据。
            question: 对图片的提问内容。

        Returns:
            Spark 模型返回的文字描述。
        """
        if not self.configured:
            raise RuntimeError("Spark Image API 凭据未配置")

        # 生成带签名的 WebSocket 鉴权 URL
        ws_param = _WsParam(self.api_key, self.api_secret, _SPARK_IMAGE_URL)
        url = ws_param.create_url()
        # 将图片编码为 base64，讯飞 API 要求以 base64 字符串传输图片
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        # 构造讯飞 WebSocket API 请求体：header + parameter + payload
        request_body = {
            "header": {"app_id": self.appid},
            "parameter": {"chat": {"domain": "imagev3", "temperature": 0.5, "top_k": 4, "max_tokens": 2028, "auditing": "default"}},
            "payload": {"message": {"text": [{"role": "user", "content": image_b64, "content_type": "image"}, {"role": "user", "content": question}]}},
        }

        # 创建 SSL 上下文，使用系统默认 CA 证书验证
        ssl_ctx = ssl.create_default_context()

        answer = ""
        # 建立 WebSocket 连接并逐条接收流式响应
        async with websockets.connect(url, ssl=ssl_ctx, proxy=None) as ws:
            await ws.send(json.dumps(request_body))
            async for raw in ws:
                data = json.loads(raw)
                code = data["header"]["code"]
                # 非零 code 表示 API 调用错误
                if code != 0:
                    raise RuntimeError(f"Spark Image API 错误: code={code}, {data}")
                # 拼接流式返回的文本片段
                answer += data["payload"]["choices"]["text"][0]["content"]
                # status == 2 表示生成结束
                if data["payload"]["choices"]["status"] == 2:
                    break
        return answer


# 全局单例：所有模块共享同一个 Spark 图片理解服务实例
spark_image_service = SparkImageService()


# ---------------------------------------------------------------------------
# VisionService: Spark + GLM-4V 双模式
# ---------------------------------------------------------------------------


class VisionService:
    """图片分析服务，支持 Spark OCR 和 GLM-4V 双模式。"""

    def __init__(self, llm: Llm | None = None) -> None:
        """初始化视觉服务，注入 LLM 实例用于 GLM-4V 降级模式。"""
        self.llm = llm or get_llm()

    async def analyze_images(self, image_urls: list[str], question: str) -> dict:
        """分析图片，优先 Spark 模式，失败时降级到 GLM-4V。

        降级策略：Spark 可用且所有图片解析成功时使用 Spark（更快更便宜），
        否则降级到 GLM-4V（智谱视觉大模型，更通用）。
        """
        # 仅当 Spark 凭据已配置且有待分析图片时，才尝试 Spark 模式
        if spark_image_service.configured and image_urls:
            spark_results: list[str] = []
            spark_ok = True
            for url in image_urls:
                image_path = resolve_uploaded_image_path(url)
                # 本地文件解析失败，放弃 Spark 模式
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
                # 多张图片结果用双换行拼接，保持可读性
                combined = "\n\n".join(spark_results) if len(spark_results) > 1 else spark_results[0]
                return {
                    "success": True,
                    "mode": "spark",
                    "analysis_text": combined,
                    "messages": None,
                    "error": None,
                }

        # GLM-4V 降级模式：构造多模态 content blocks，图片以 base64 或 URL 传入
        content_blocks: list[dict] = [{"type": "text", "text": question or "请描述这些图片"}]
        for url in image_urls:
            image_input = _build_image_input(url)
            if image_input:
                content_blocks.append(image_input)
        # 调用 LLM 的 vision 能力（GLM-4V 或其他支持视觉的模型）
        response = await self.llm.vision(
            [HumanMessage(content=content_blocks)],
            temperature=VISION_TEMPERATURE,
        )
        return {
            "success": True,
            "mode": "glm",
            "analysis_text": response.content if isinstance(response.content, str) else str(response.content),
            "messages": [SystemMessage(content=""), response],
            "error": None,
        }


def build_vision_service(llm: Llm | None = None):
    """工厂函数：创建 VisionService 实例。

    llm 可注入自定义 LLM 实例（如测试 mock），为空时使用全局默认 LLM。
    """
    return VisionService(llm)


__all__ = ["VisionService", "build_vision_service", "spark_image_service"]
