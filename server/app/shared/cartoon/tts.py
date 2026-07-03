"""Edge TTS synthesis with reusable audio and word-boundary metadata."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

import edge_tts
from mutagen.mp3 import MP3

from app.config import WORKPLACE_DIR
from app.infra.logging import get_logger
from app.shared.cartoon.schemas import CaptionWord

logger = get_logger(__name__)

VOICE_ALIASES = {
    "teacher": "zh-CN-XiaoxiaoNeural",
    "coach": "zh-CN-YunxiNeural",
}


class CartoonTtsService:
    """Synthesize every cartoon narration with Edge TTS only."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir or WORKPLACE_DIR / "tts_cache" / "cartoon_edge"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def synthesize(
        self,
        text: str,
        output_path: Path,
        voice: str = "teacher",
    ) -> tuple[int, list[CaptionWord]]:
        narration = text.strip()
        if not narration:
            raise ValueError("动画场景旁白不能为空")

        edge_voice = self.resolve_voice(voice)
        digest = hashlib.sha256(
            f"cartoon-edge-v2:{edge_voice}:{narration}".encode("utf-8")
        ).hexdigest()
        cache_audio = self.cache_dir / f"{digest}.mp3"
        cache_metadata = self.cache_dir / f"{digest}.json"
        cached = self._read_cache(cache_audio, cache_metadata, output_path)
        if cached is not None:
            return cached

        output_path.parent.mkdir(parents=True, exist_ok=True)
        duration_ms, words = await self._synthesize_edge(
            narration,
            output_path,
            edge_voice,
        )
        if not words:
            words = self._fallback_boundaries(narration, duration_ms)
        self._write_cache(cache_audio, cache_metadata, output_path, duration_ms, words)
        return duration_ms, words

    @staticmethod
    def resolve_voice(voice: str) -> str:
        candidate = voice.strip()
        if candidate in VOICE_ALIASES:
            return VOICE_ALIASES[candidate]
        if candidate.startswith("zh-") and candidate.endswith("Neural"):
            return candidate
        raise ValueError(f"不支持的 Edge TTS 发音人: {voice}")

    def _read_cache(
        self,
        cache_audio: Path,
        cache_metadata: Path,
        output_path: Path,
    ) -> tuple[int, list[CaptionWord]] | None:
        if not cache_audio.is_file() or not cache_metadata.is_file():
            return None
        try:
            metadata = json.loads(cache_metadata.read_text(encoding="utf-8"))
            duration_ms = int(metadata["duration_ms"])
            words = [
                CaptionWord.model_validate(item)
                for item in metadata["words"]
            ]
            if duration_ms <= 0 or not words:
                return None
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(cache_audio, output_path)
            logger.info("复用 Edge TTS 缓存: %s", cache_audio.name)
            return duration_ms, words
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            logger.warning("忽略损坏的 Edge TTS 缓存 %s: %s", cache_audio.name, exc)
            return None

    @staticmethod
    async def _synthesize_edge(
        text: str,
        output_path: Path,
        voice: str,
    ) -> tuple[int, list[CaptionWord]]:
        communicate = edge_tts.Communicate(text=text, voice=voice)
        words: list[CaptionWord] = []
        audio_chunks: list[bytes] = []

        async for event in communicate.stream():
            event_type = event.get("type")
            if event_type == "WordBoundary":
                word_text = str(event.get("text", "")).strip()
                if not word_text:
                    continue
                offset = int(event.get("offset", 0))
                duration = max(1, int(event.get("duration", 0)))
                words.append(
                    CaptionWord(
                        text=word_text,
                        start_ms=max(0, offset // 10_000),
                        end_ms=max(1, (offset + duration) // 10_000),
                    )
                )
            elif event_type == "audio":
                chunk = event.get("data")
                if chunk:
                    audio_chunks.append(chunk)

        if not audio_chunks:
            raise RuntimeError("Edge TTS 未返回音频数据")
        output_path.write_bytes(b"".join(audio_chunks))
        duration_ms = round(MP3(output_path).info.length * 1000)
        if duration_ms <= 0:
            raise RuntimeError("Edge TTS 返回了无效音频时长")
        return duration_ms, words

    @staticmethod
    def _fallback_boundaries(text: str, duration_ms: int) -> list[CaptionWord]:
        """Fallback only when Edge omits boundary events; audio still comes from Edge."""
        tokens = re.findall(
            r"[\u4e00-\u9fff]|[A-Za-z0-9_+#.-]+|[，。！？；：、,.!?;:]",
            text,
        )
        if not tokens:
            return [CaptionWord(text=text, start_ms=0, end_ms=max(1, duration_ms))]
        weights = [
            1.8 if token in "。！？.!?" else 1.35 if token in "，；：、,;:" else max(1, len(token))
            for token in tokens
        ]
        total_weight = sum(weights)
        words: list[CaptionWord] = []
        cursor = 0
        elapsed_weight = 0.0
        for index, (token, weight) in enumerate(zip(tokens, weights)):
            elapsed_weight += weight
            end = (
                duration_ms
                if index == len(tokens) - 1
                else round(duration_ms * elapsed_weight / total_weight)
            )
            end = max(cursor + 1, min(duration_ms, end))
            words.append(CaptionWord(text=token, start_ms=cursor, end_ms=end))
            cursor = end
        return words

    @staticmethod
    def _write_cache(
        cache_audio: Path,
        cache_metadata: Path,
        output_path: Path,
        duration_ms: int,
        words: list[CaptionWord],
    ) -> None:
        try:
            shutil.copy2(output_path, cache_audio)
            cache_metadata.write_text(
                json.dumps(
                    {
                        "duration_ms": duration_ms,
                        "words": [word.model_dump() for word in words],
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("写入 Edge TTS 缓存失败: %s", exc)
