"""Spark (iFlytek 科大讯飞) TTS synthesis service.

Uses websockets to connect to iFlytek TTS API, supports MP3 output format ('aue': 'lame'),
and provides async synthesis and caption timing estimation.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import ssl
from datetime import datetime
from pathlib import Path
from time import mktime
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time

import websockets
from mutagen.mp3 import MP3

from app.config import (
    SPARK_TTS_APP_ID,
    SPARK_TTS_API_KEY,
    SPARK_TTS_API_SECRET,
)
from app.infra.logging import get_logger

logger = get_logger(__name__)


# 创建 TTS WebSocket 使用的默认受信 TLS 上下文
def create_ssl_context() -> ssl.SSLContext:
    """Create the default verified TLS context for the TTS WebSocket."""
    return ssl.create_default_context()


# 逐词字幕类：携带文本与起止时间戳
class CaptionWord:
    """Word caption containing text, start_ms, and end_ms."""
    __slots__ = ("text", "start_ms", "end_ms")

    def __init__(self, text: str, start_ms: int, end_ms: int):
        self.text = text
        self.start_ms = start_ms
        self.end_ms = end_ms

    def to_dict(self) -> dict:
        return {"text": self.text, "start_ms": self.start_ms, "end_ms": self.end_ms}


# TTS 合成结果类：保存时长与逐词字幕
class TtsResult:
    """TTS synthesis result containing duration and word captions."""
    __slots__ = ("duration", "captions")

    def __init__(self, duration: float, captions: list[CaptionWord]):
        self.duration = duration
        self.captions = captions

    def to_dict(self) -> list[dict]:
        return [c.to_dict() for c in self.captions]


# 讯飞星火 TTS 服务：封装 WebSocket 语音合成
class SparkTtsService:
    """Spark TTS Service wrapping iFlytek WebSocket TTS API."""

    # 构造带 HMAC-SHA256 签名的鉴权 WebSocket URL
    @staticmethod
    def _create_auth_url(host: str = "ws-api.xfyun.cn") -> str:
        """Create RFC1123 signed URL for connection."""
        if not SPARK_TTS_APP_ID or not SPARK_TTS_API_KEY or not SPARK_TTS_API_SECRET:
            raise ValueError("Missing Spark TTS configuration in config.yaml")

        url = "wss://tts-api.xfyun.cn/v2/tts"
        # RFC1123 格式时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        # 拼接待签名原始串
        signature_origin = f"host: {host}\n"
        signature_origin += f"date: {date}\n"
        signature_origin += "GET /v2/tts HTTP/1.1"

        # 使用 HMAC-SHA256 计算签名
        signature_sha = hmac.new(
            SPARK_TTS_API_SECRET.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        signature_b64 = base64.b64encode(signature_sha).decode("utf-8")

        authorization_origin = (
            f'api_key="{SPARK_TTS_API_KEY}", algorithm="hmac-sha256", '
            f'headers="host date request-line", signature="{signature_b64}"'
        )
        authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")

        params = {
            "authorization": authorization,
            "date": date,
            "host": host,
        }
        return f"{url}?{urlencode(params)}"

    # 合成文本为 MP3 文件，返回音频时长（秒）
    @classmethod
    async def synthesize(
        cls,
        text: str,
        file_path: Path,
        voice: str = "x4_yezi",
    ) -> float:
        """Synthesize text to MP3 file. Returns duration in seconds."""
        if not text or not text.strip():
            logger.warning("传入空文本到 SparkTtsService, 跳过合成")
            return 0.0

        file_path.parent.mkdir(parents=True, exist_ok=True)
        url = cls._create_auth_url()

        # 将待合成文本转为 base64 编码
        text_b64 = base64.b64encode(text.encode("utf-8")).decode("utf-8")

        request_payload = {
            "common": {"app_id": SPARK_TTS_APP_ID},
            "business": {
                "aue": "lame",  # MP3 format
                "auf": "audio/L16;rate=16000",
                "vcn": voice,
                "tte": "utf8",
            },
            "data": {"status": 2, "text": text_b64},
        }

        import asyncio
        logger.info("正在连接讯飞 TTS WebSocket API...")
        audio_data = bytearray()

        # 最多重试 3 次，处理连接/网络抖动
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                # 建立 WebSocket 连接并发送合成请求
                async with websockets.connect(url, ssl=create_ssl_context()) as ws:
                    await ws.send(json.dumps(request_payload))
                    logger.info("讯飞 TTS 请求已发送, 等待音频帧...")

                    # 逐帧接收音频数据，直到最后一帧
                    async for message in ws:
                        resp = json.loads(message)
                        code = resp.get("code")
                        # 非零业务码直接抛出错误
                        if code != 0:
                            err_msg = resp.get("message", "Unknown error")
                            raise RuntimeError(f"Spark TTS API returned error code {code}: {err_msg}")

                        data = resp.get("data", {})
                        audio_b64 = data.get("audio", "")
                        # 解码并累计音频字节
                        if audio_b64:
                            audio_data.extend(base64.b64decode(audio_b64))

                        status = data.get("status")
                        # 收到末帧（status==2）即停止接收
                        if status == 2:  # Last frame
                            logger.info("已收到讯飞 TTS 最后一帧音频")
                            break
                break  # Succeeded, exit retry loop
            # 未达上限时按指数退避重试
            except Exception as e:
                if attempt == max_retries:
                    raise
                wait_time = attempt * 2.0
                logger.warning(
                    "讯飞 TTS 连接失败 (第 %d/%d 次): %s. %.1f 秒后重试...",
                    attempt, max_retries, e, wait_time
                )
                audio_data.clear()
                await asyncio.sleep(wait_time)

        # 写入音频文件并读取 MP3 时长
        file_path.write_bytes(bytes(audio_data))
        logger.info("讯飞 TTS 输出已保存到 %s", file_path)

        # Parse duration from generated MP3
        audio = MP3(str(file_path))
        return audio.info.length

    # 合成 MP3 并估算字幕时间戳（带 SHA-256 缓存）
    @classmethod
    async def synthesize_with_captions(
        cls,
        text: str,
        file_path: Path,
        voice: str = "x4_yezi",
    ) -> TtsResult:
        """Synthesize text to MP3 and estimate caption timestamps (with SHA-256 caching)."""
        if not text or not text.strip():
            return TtsResult(duration=0.0, captions=[])

        import hashlib
        import json
        import shutil
        from app.config import WORKPLACE_DIR

        # 1. 计算文本+配音的 Hash 作为缓存键
        payload_str = f"spark:caption-v2:{voice}:{text.strip()}"
        sha256_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

        # 缓存路径
        cache_dir = WORKPLACE_DIR / "tts_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_mp3_path = cache_dir / f"tts_{sha256_hash}.mp3"
        cache_meta_path = cache_dir / f"tts_{sha256_hash}.json"

        # 2. 缓存命中则直接复用音频与字幕，跳过合成
        if cache_mp3_path.exists() and cache_meta_path.exists():
            try:
                meta = json.loads(cache_meta_path.read_text(encoding="utf-8"))
                duration = meta.get("duration", 0.0)
                captions = [
                    CaptionWord(
                        text=c["text"],
                        start_ms=c["start_ms"],
                        end_ms=c["end_ms"]
                    )
                    for c in meta.get("captions", [])
                ]

                file_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(cache_mp3_path), str(file_path))

                logger.info("命中讯飞 TTS 缓存! 复用音频缓存: %s", cache_mp3_path.name)
                return TtsResult(duration=duration, captions=captions)
            except Exception as e:
                logger.warning("加载讯飞 TTS 缓存失败: %s", e)

        # 3. 缓存未命中，执行合成并估算字幕
        duration = await cls.synthesize(text, file_path, voice)
        captions = cls._estimate_captions(text, duration)

        # 4. 将合成结果写入缓存供下次复用
        try:
            shutil.copy2(str(file_path), str(cache_mp3_path))
            meta_data = {
                "duration": duration,
                "captions": [c.to_dict() for c in captions]
            }
            cache_meta_path.write_text(json.dumps(meta_data, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info("讯飞 TTS 缓存已保存: %s", cache_mp3_path.name)
        except Exception as e:
            logger.warning("保存讯飞 TTS 缓存失败: %s", e)

        return TtsResult(duration=duration, captions=captions)

    # 在讯飞不返回逐词边界时，按标点权重估算字幕时间戳
    @staticmethod
    def _estimate_captions(text: str, duration: float) -> list[CaptionWord]:
        """Estimate caption timing when Spark does not return word boundaries.

        Sentence punctuation is retained and receives extra timing weight so
        downstream subtitle chunks preserve natural pause boundaries.
        """
        import re

        # 将文本切分为中文字、英文/数字词与标点 token
        tokens = re.findall(
            r"[\u4e00-\u9fff]|[a-zA-Z0-9]+|[，。？！、；：,.?!;:]",
            text,
        )
        # 无 token 直接返回空字幕
        if not tokens:
            return []

        duration_ms = round(duration * 1000)
        if duration_ms <= 0:
            return []

        pause_weights = {
            "，": 0.7,
            ",": 0.7,
            "、": 0.45,
            "。": 1.2,
            ".": 1.2,
            "？": 1.2,
            "?": 1.2,
            "！": 1.2,
            "!": 1.2,
            "；": 0.9,
            ";": 0.9,
            "：": 0.7,
            ":": 0.7,
        }
        # 按标点或词长计算各 token 的时间权重
        weights = [
            pause_weights.get(token, max(1.0, len(token) * 0.65))
            for token in tokens
        ]
        # 权重总和用于后续按比例分配时间
        total_weight = sum(weights)

        # 按权重顺序为每个 token 分配时间区间
        captions: list[CaptionWord] = []
        current_ms = 0
        elapsed_weight = 0.0
        for index, (token, weight) in enumerate(zip(tokens, weights)):
            # 累计已分配权重，推算当前 token 结束时间
            elapsed_weight += weight
            end_ms = (
                duration_ms
                if index == len(tokens) - 1
                else round(duration_ms * elapsed_weight / total_weight)
            )
            end_ms = max(current_ms + 1, min(end_ms, duration_ms))
            captions.append(
                CaptionWord(text=token, start_ms=current_ms, end_ms=end_ms)
            )
            current_ms = end_ms

        return captions
