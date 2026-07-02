"""Self-contained TTS Service for the Cartoon generator.

Supports:
- Edge-TTS (default and fallback)
- iFlytek Spark TTS (when SPARK_TTS_APP_ID is configured)
- High-precision word timestamp estimation for Spark TTS
- SHA-256 caching for both providers to avoid API costs and latency
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import ssl
import shutil
from datetime import datetime
from pathlib import Path
from time import mktime
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time

import edge_tts
import websockets
from mutagen.mp3 import MP3

from app.config import (
    SPARK_TTS_API_KEY,
    SPARK_TTS_API_SECRET,
    SPARK_TTS_APP_ID,
    WORKPLACE_DIR,
)
from app.infra.logging import get_logger
from app.shared.cartoon.schemas import CaptionWord

logger = get_logger(__name__)


def create_ssl_context() -> ssl.SSLContext:
    """Create a verified TLS context for the iFlytek WebSocket."""
    return ssl.create_default_context()


class CartoonTtsService:
    """Orchestrates TTS synthesis and word-level timing alignment."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir or WORKPLACE_DIR / "tts_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def synthesize(
        self,
        text: str,
        output_path: Path,
        voice: str = "zh-CN-XiaoxiaoNeural",
    ) -> tuple[int, list[CaptionWord]]:
        """Synthesize text to MP3 and extract word-level timestamps.

        Selects Spark TTS if configured, otherwise falls back to Edge-TTS.
        Uses a local SHA-256 cache to prevent redundant API calls.
        """
        if not text or not text.strip():
            logger.warning("Empty text passed to TTS. Skipping synthesis.")
            return 0, []

        provider = "edge"
        if SPARK_TTS_APP_ID and SPARK_TTS_APP_ID.strip():
            provider = "spark"

        # 1. Check SHA-256 cache
        payload_str = f"cartoon:{provider}:{voice}:{text.strip()}"
        sha256_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
        
        cache_mp3_path = self.cache_dir / f"tts_{sha256_hash}.mp3"
        cache_meta_path = self.cache_dir / f"tts_{sha256_hash}.json"

        if cache_mp3_path.exists() and cache_meta_path.exists():
            try:
                meta = json.loads(cache_meta_path.read_text(encoding="utf-8"))
                duration_ms = meta.get("duration_ms", 0)
                words = [
                    CaptionWord(
                        text=w["text"],
                        start_ms=w["start_ms"],
                        end_ms=w["end_ms"],
                    )
                    for w in meta.get("words", [])
                ]
                
                output_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(cache_mp3_path), str(output_path))
                
                logger.info("Cartoon TTS Cache Hit! Reused cache: %s", cache_mp3_path.name)
                return duration_ms, words
            except Exception as e:
                logger.warning("Failed to load TTS cache, generating fresh: %s", e)

        # 2. Run synthesis based on provider
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if provider == "spark":
            logger.info("Using Spark TTS for synthesis: %s", text[:30])
            duration_ms, words = await self._synthesize_spark(text, output_path, voice="x4_yezi")
        else:
            logger.info("Using Edge-TTS for synthesis: %s", text[:30])
            edge_voice = voice if voice.startswith("zh-") else "zh-CN-XiaoxiaoNeural"
            duration_ms, words = await self._synthesize_edge(text, output_path, edge_voice)

        # 3. Save to cache
        try:
            shutil.copy2(str(output_path), str(cache_mp3_path))
            meta_data = {
                "duration_ms": duration_ms,
                "words": [w.model_dump() for w in words],
            }
            cache_meta_path.write_text(
                json.dumps(meta_data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info("Saved Cartoon TTS output to cache: %s", cache_mp3_path.name)
        except Exception as e:
            logger.warning("Failed to write TTS cache files: %s", e)

        return duration_ms, words

    async def _synthesize_edge(
        self,
        text: str,
        output_path: Path,
        voice: str,
    ) -> tuple[int, list[CaptionWord]]:
        """Synthesize audio and retrieve boundary words using Edge-TTS."""
        communicate = edge_tts.Communicate(text, voice)
        words: list[CaptionWord] = []
        audio_chunks: list[bytes] = []

        async for event in communicate.stream():
            if event["type"] == "WordBoundary":
                offset = event.get("offset", 0)  # 100-nanosecond intervals
                duration_ns = event.get("duration", 0)
                word_text = event.get("text", "")
                start_ms = offset // 10000
                end_ms = (offset + duration_ns) // 10000
                if word_text.strip():
                    words.append(
                        CaptionWord(text=word_text.strip(), start_ms=start_ms, end_ms=end_ms)
                    )
            elif event["type"] == "audio":
                audio_chunks.append(event["data"])

        # Write audio bytes to file
        with open(str(output_path), "wb") as f:
            for chunk in audio_chunks:
                f.write(chunk)

        audio = MP3(str(output_path))
        duration_ms = round(audio.info.length * 1000)
        return duration_ms, words

    async def _synthesize_spark(
        self,
        text: str,
        output_path: Path,
        voice: str,
    ) -> tuple[int, list[CaptionWord]]:
        """Synthesize audio using iFlytek Spark WebSocket and estimate word timings."""
        url = self._create_spark_auth_url()
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

        audio_data = bytearray()
        async with websockets.connect(url, ssl=create_ssl_context()) as ws:
            await ws.send(json.dumps(request_payload))
            async for message in ws:
                resp = json.loads(message)
                code = resp.get("code")
                if code != 0:
                    err_msg = resp.get("message", "Unknown error")
                    raise RuntimeError(f"Spark TTS WebSocket error {code}: {err_msg}")
                data = resp.get("data", {})
                audio_b64 = data.get("audio", "")
                if audio_b64:
                    audio_data.extend(base64.b64decode(audio_b64))
                status = data.get("status")
                if status == 2:  # Complete
                    break

        output_path.write_bytes(bytes(audio_data))
        audio = MP3(str(output_path))
        duration_sec = audio.info.length
        duration_ms = round(duration_sec * 1000)

        # Estimate word boundary timestamps since Spark WebSocket API doesn't return timings
        words = self._estimate_spark_words(text, duration_sec)
        return duration_ms, words

    @staticmethod
    def _create_spark_auth_url(host: str = "ws-api.xfyun.cn") -> str:
        """Create RFC1123 signed URL for connecting to Spark WebSocket."""
        if not SPARK_TTS_APP_ID or not SPARK_TTS_API_KEY or not SPARK_TTS_API_SECRET:
            raise ValueError("Missing Spark API credentials in config.yaml")

        url = "wss://tts-api.xfyun.cn/v2/tts"
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        signature_origin = f"host: {host}\n"
        signature_origin += f"date: {date}\n"
        signature_origin += "GET /v2/tts HTTP/1.1"

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

    @staticmethod
    def _estimate_spark_words(text: str, duration: float) -> list[CaptionWord]:
        """Estimate word timings in Chinese text by splitting characters and analyzing weights."""
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
            "，": 0.7, ",": 0.7,
            "、": 0.45,
            "。": 1.2, ".": 1.2,
            "？": 1.2, "?": 1.2,
            "！": 1.2, "!": 1.2,
            "；": 0.9, ";": 0.9,
            "：": 0.7, ":": 0.7,
        }
        weights = [
            pause_weights.get(token, max(1.0, len(token) * 0.65))
            for token in tokens
        ]
        total_weight = sum(weights)

        words: list[CaptionWord] = []
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
            words.append(
                CaptionWord(text=token, start_ms=current_ms, end_ms=end_ms)
            )
            current_ms = end_ms

        return words
