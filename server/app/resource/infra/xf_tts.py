"""讯飞星火 TTS 语音合成服务 — WebSocket 流式合成

支持：
- 基础合成：文本 → MP3，返回时长
- 带字幕合成：文本 → MP3 + 逐词时间戳，用于视频字幕
- 发音人选择：多种中文语音可选
"""

from __future__ import annotations

import asyncio
import base64
import datetime
import hashlib
import hmac
import json
from pathlib import Path
from typing import Literal
from urllib.parse import urlencode

import websockets
from mutagen.mp3 import MP3

from app.infra.logging import get_logger

logger = get_logger(__name__)

# 发音人类型
XfVoice = Literal[
    "xiaoyan",       # 讯飞小燕（亲和女声）
    "aisjiuxu",      # 讯飞许久（亲切女声）
    "aisxping",      # 讯飞小萍（温柔女声）
    "aisjinger",     # 讯飞小婧（柔美女声）
    "xiaoyu",        # 讯飞小宇（热情男声）
    "xiaofeng",      # 讯飞小峰（激情男声）
    "xiaomei",       # 讯飞小梅（粤语女声）
    "xiaolin",       # 讯飞小琳（台湾女声）
    "xiaorong",      # 讯飞小蓉（四川话女声）
    "xiaoqian",      # 讯飞小倩（东北话女声）
]

# 音频格式
XfAudioFormat = Literal["mp3", "pcm", "speex", "speex-wb"]


class CaptionWord:
    """逐词字幕 — 包含文本和起止时间戳（毫秒）。"""
    __slots__ = ("text", "start_ms", "end_ms")

    def __init__(self, text: str, start_ms: int, end_ms: int):
        self.text = text
        self.start_ms = start_ms
        self.end_ms = end_ms

    def to_dict(self) -> dict:
        return {"text": self.text, "start_ms": self.start_ms, "end_ms": self.end_ms}


class XfTtsResult:
    """讯飞 TTS 合成结果 — 包含音频时长和逐词字幕列表。"""
    __slots__ = ("duration", "captions")

    def __init__(self, duration: float, captions: list[CaptionWord]):
        self.duration = duration
        self.captions = captions

    def to_dict(self) -> list[dict]:
        return [c.to_dict() for c in self.captions]


class XfTtsService:
    """讯飞星火 TTS 语音合成服务 — WebSocket 流式合成。

    使用讯飞在线语音合成（流式版）WebAPI。
    文档：https://www.xfyun.cn/doc/tts/online_tts/API.html
    """

    # API 端点
    WS_URL = "wss://tts-api.xfyun.cn/v2/tts"
    HOST = "tts-api.xfyun.cn"

    def __init__(
        self,
        app_id: str,
        api_key: str,
        api_secret: str,
    ):
        self.app_id = app_id
        self.api_key = api_key
        self.api_secret = api_secret

    def _generate_auth_url(self) -> str:
        """生成带鉴权参数的 WebSocket URL。"""
        # 生成 RFC1123 格式时间戳
        now = datetime.datetime.now()
        date = now.strftime("%a, %d %b %Y %H:%M:%S GMT")

        # 拼接签名字符串
        signature_origin = f"host: {self.HOST}\ndate: {date}\nGET /v2/tts HTTP/1.1"

        # HMAC-SHA256 签名
        signature_sha = hmac.new(
            self.api_secret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        signature = base64.b64encode(signature_sha).decode("utf-8")

        # 构建 authorization
        authorization_origin = (
            f'api_key="{self.api_key}", algorithm="hmac-sha256", '
            f'headers="host date request-line", signature="{signature}"'
        )
        authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")

        # 组装 URL
        params = {
            "authorization": authorization,
            "date": date,
            "host": self.HOST,
        }
        return f"{self.WS_URL}?{urlencode(params)}"

    async def synthesize(
        self,
        text: str,
        file_path: Path,
        voice: XfVoice = "xiaoyan",
        speed: int = 50,
        volume: int = 50,
        pitch: int = 50,
        audio_format: XfAudioFormat = "mp3",
    ) -> float:
        """基础合成：文本 → MP3，返回音频时长（秒）。"""
        result = await self.synthesize_with_captions(
            text=text,
            file_path=file_path,
            voice=voice,
            speed=speed,
            volume=volume,
            pitch=pitch,
            audio_format=audio_format,
        )
        return result.duration

    async def synthesize_with_captions(
        self,
        text: str,
        file_path: Path,
        voice: XfVoice = "xiaoyan",
        speed: int = 50,
        volume: int = 50,
        pitch: int = 50,
        audio_format: XfAudioFormat = "mp3",
    ) -> XfTtsResult:
        """带字幕合成：文本 → MP3 + 逐词时间戳。"""
        if not text or not text.strip():
            logger.warning("Empty text passed to XfTtsService. Skip synthesis.")
            return XfTtsResult(duration=0.0, captions=[])

        file_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            "Starting Xunfei TTS synthesis: text_len=%d, voice=%s, output=%s",
            len(text), voice, file_path
        )

        # 生成鉴权 URL
        url = self._generate_auth_url()

        # 音频格式参数
        aue_map = {
            "mp3": "lame",
            "pcm": "raw",
            "speex": "speex",
            "speex-wb": "speex-wb",
        }
        aue = aue_map.get(audio_format, "lame")

        # 构建请求参数
        request_data = {
            "common": {"app_id": self.app_id},
            "business": {
                "aue": aue,
                "auf": "audio/L16;rate=16000",
                "vcn": voice,
                "speed": speed,
                "volume": volume,
                "pitch": pitch,
                "bgs": 0,
                "tte": "UTF8",
                "ent": "intp65",
            },
            "data": {
                "status": 2,
                "text": base64.b64encode(text.encode("utf-8")).decode("utf-8"),
            },
        }

        audio_chunks: list[bytes] = []
        captions: list[CaptionWord] = []

        try:
            async with websockets.connect(
                url,
                ping_interval=None,
                ping_timeout=None,
                close_timeout=10,
            ) as ws:
                # 发送合成请求
                await ws.send(json.dumps(request_data))

                # 接收音频流
                while True:
                    try:
                        message = await asyncio.wait_for(ws.recv(), timeout=60)
                        response = json.loads(message)

                        if response.get("code", 0) != 0:
                            error_msg = response.get("message", "Unknown error")
                            raise RuntimeError(f"Xunfei TTS error: {error_msg}")

                        data = response.get("data", {})
                        if data.get("audio"):
                            audio_data = base64.b64decode(data["audio"])
                            audio_chunks.append(audio_data)

                        if data.get("status") == 2:
                            break

                    except asyncio.TimeoutError:
                        logger.warning("Xunfei TTS WebSocket timeout")
                        break

        except Exception as e:
            logger.error("Xunfei TTS synthesis failed: %s", e)
            raise

        # 写入音频文件
        with open(file_path, "wb") as f:
            for chunk in audio_chunks:
                f.write(chunk)

        if not file_path.exists():
            raise FileNotFoundError(f"Failed to generate TTS file at {file_path}")

        # 获取音频时长
        audio = MP3(str(file_path))
        duration = audio.info.length

        # 估算词级字幕
        words = text.split()
        if words and duration > 0:
            avg_duration_ms = int((duration * 1000) / len(words))
            for i, word in enumerate(words):
                start_ms = i * avg_duration_ms
                end_ms = (i + 1) * avg_duration_ms
                captions.append(CaptionWord(text=word, start_ms=start_ms, end_ms=end_ms))

        logger.info(
            "Xunfei TTS synthesis complete. Duration: %.2fs, %d captions",
            duration, len(captions)
        )

        return XfTtsResult(duration=duration, captions=captions)


# ============ 兼容旧接口：适配 TtsService ============

class TtsService:
    """TTS 服务适配器 — 兼容原有接口，底层使用讯飞星火 TTS。"""

    _instance: XfTtsService | None = None

    @classmethod
    def _get_service(cls) -> XfTtsService:
        """获取讯飞 TTS 服务实例（延迟初始化）。"""
        if cls._instance is None:
            from app.config import settings

            app_id = settings.spark.app_id
            api_key = settings.spark.api_key
            api_secret = settings.spark.api_secret

            if not all([app_id, api_key, api_secret]):
                raise ValueError("Xunfei TTS credentials not configured in spark section")

            cls._instance = XfTtsService(
                app_id=app_id,
                api_key=api_key,
                api_secret=api_secret,
            )
        return cls._instance

    @staticmethod
    async def synthesize(
        text: str,
        file_path: Path,
        voice: str = "xiaoyan",
    ) -> float:
        """基础合成：文本 → MP3，返回音频时长（秒）。"""
        service = TtsService._get_service()
        return await service.synthesize(text=text, file_path=file_path, voice=voice)  # type: ignore

    @staticmethod
    async def synthesize_with_captions(
        text: str,
        file_path: Path,
        voice: str = "xiaoyan",
    ) -> XfTtsResult:
        """带字幕合成：文本 → MP3 + 逐词时间戳。"""
        service = TtsService._get_service()
        return await service.synthesize_with_captions(
            text=text, file_path=file_path, voice=voice  # type: ignore
        )
