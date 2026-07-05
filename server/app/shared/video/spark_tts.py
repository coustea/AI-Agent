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


def create_ssl_context() -> ssl.SSLContext:
    """Create the default verified TLS context for the TTS WebSocket."""
    return ssl.create_default_context()


class CaptionWord:
    """Word caption containing text, start_ms, and end_ms."""
    __slots__ = ("text", "start_ms", "end_ms")

    def __init__(self, text: str, start_ms: int, end_ms: int):
        self.text = text
        self.start_ms = start_ms
        self.end_ms = end_ms

    def to_dict(self) -> dict:
        return {"text": self.text, "start_ms": self.start_ms, "end_ms": self.end_ms}


class TtsResult:
    """TTS synthesis result containing duration and word captions."""
    __slots__ = ("duration", "captions")

    def __init__(self, duration: float, captions: list[CaptionWord]):
        self.duration = duration
        self.captions = captions

    def to_dict(self) -> list[dict]:
        return [c.to_dict() for c in self.captions]


class SparkTtsService:
    """Spark TTS Service wrapping iFlytek WebSocket TTS API."""

    @staticmethod
    def _create_auth_url(host: str = "ws-api.xfyun.cn") -> str:
        """Create RFC1123 signed URL for connection."""
        if not SPARK_TTS_APP_ID or not SPARK_TTS_API_KEY or not SPARK_TTS_API_SECRET:
            raise ValueError("Missing Spark TTS configuration in config.yaml")

        url = "wss://tts-api.xfyun.cn/v2/tts"
        # RFC1123 timestamp
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        # Signature string
        signature_origin = f"host: {host}\n"
        signature_origin += f"date: {date}\n"
        signature_origin += "GET /v2/tts HTTP/1.1"

        # HMAC-SHA256
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

    @classmethod
    async def synthesize(
        cls,
        text: str,
        file_path: Path,
        voice: str = "x4_yezi",
    ) -> float:
        """Synthesize text to MP3 file. Returns duration in seconds."""
        if not text or not text.strip():
            logger.warning("Empty text passed to SparkTtsService. Skip synthesis.")
            return 0.0

        file_path.parent.mkdir(parents=True, exist_ok=True)
        url = cls._create_auth_url()

        # base64 encoded text
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
        logger.info("Connecting to Spark TTS WebSocket API...")
        audio_data = bytearray()

        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                async with websockets.connect(url, ssl=create_ssl_context()) as ws:
                    await ws.send(json.dumps(request_payload))
                    logger.info("Spark TTS request sent, waiting for audio frames...")

                    async for message in ws:
                        resp = json.loads(message)
                        code = resp.get("code")
                        if code != 0:
                            err_msg = resp.get("message", "Unknown error")
                            raise RuntimeError(f"Spark TTS API returned error code {code}: {err_msg}")

                        data = resp.get("data", {})
                        audio_b64 = data.get("audio", "")
                        if audio_b64:
                            audio_data.extend(base64.b64decode(audio_b64))

                        status = data.get("status")
                        if status == 2:  # Last frame
                            logger.info("Received last audio frame from Spark TTS")
                            break
                break  # Succeeded, exit retry loop
            except Exception as e:
                if attempt == max_retries:
                    raise
                wait_time = attempt * 2.0
                logger.warning(
                    "Spark TTS connection failed (attempt %d/%d): %s. Retrying in %.1fs...",
                    attempt, max_retries, e, wait_time
                )
                audio_data.clear()
                await asyncio.sleep(wait_time)

        file_path.write_bytes(bytes(audio_data))
        logger.info("Saved Spark TTS output to %s", file_path)

        # Parse duration from generated MP3
        audio = MP3(str(file_path))
        return audio.info.length

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

        # 1. 计算 Hash
        payload_str = f"spark:caption-v2:{voice}:{text.strip()}"
        sha256_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

        # 缓存路径
        cache_dir = WORKPLACE_DIR / "tts_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_mp3_path = cache_dir / f"tts_{sha256_hash}.mp3"
        cache_meta_path = cache_dir / f"tts_{sha256_hash}.json"

        # 2. 如果缓存存在，直接使用缓存
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

                logger.info("Spark TTS Cache Hit! Reused audio cache: %s", cache_mp3_path.name)
                return TtsResult(duration=duration, captions=captions)
            except Exception as e:
                logger.warning("Failed to load Spark TTS cache: %s", e)

        # 3. 缓存未置，执行合成
        duration = await cls.synthesize(text, file_path, voice)
        captions = cls._estimate_captions(text, duration)

        # 4. 写入缓存
        try:
            shutil.copy2(str(file_path), str(cache_mp3_path))
            meta_data = {
                "duration": duration,
                "captions": [c.to_dict() for c in captions]
            }
            cache_meta_path.write_text(json.dumps(meta_data, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info("Spark TTS Cache Saved: %s", cache_mp3_path.name)
        except Exception as e:
            logger.warning("Failed to save Spark TTS cache: %s", e)

        return TtsResult(duration=duration, captions=captions)

    @staticmethod
    def _estimate_captions(text: str, duration: float) -> list[CaptionWord]:
        """Estimate caption timing when Spark does not return word boundaries.

        Sentence punctuation is retained and receives extra timing weight so
        downstream subtitle chunks preserve natural pause boundaries.
        """
        import re

        tokens = re.findall(
            r"[\u4e00-\u9fff]|[a-zA-Z0-9]+|[，。？！、；：,.?!;:]",
            text,
        )
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
        weights = [
            pause_weights.get(token, max(1.0, len(token) * 0.65))
            for token in tokens
        ]
        total_weight = sum(weights)

        captions: list[CaptionWord] = []
        current_ms = 0
        elapsed_weight = 0.0
        for index, (token, weight) in enumerate(zip(tokens, weights)):
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
