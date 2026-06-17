from __future__ import annotations

from pathlib import Path
import edge_tts
from mutagen.mp3 import MP3
from app.infra.logging import get_logger

logger = get_logger(__name__)


class CaptionWord:
    __slots__ = ("text", "start_ms", "end_ms")

    def __init__(self, text: str, start_ms: int, end_ms: int):
        self.text = text
        self.start_ms = start_ms
        self.end_ms = end_ms

    def to_dict(self) -> dict:
        return {"text": self.text, "start_ms": self.start_ms, "end_ms": self.end_ms}


class TtsResult:
    __slots__ = ("duration", "captions")

    def __init__(self, duration: float, captions: list[CaptionWord]):
        self.duration = duration
        self.captions = captions

    def to_dict(self) -> list[dict]:
        return [c.to_dict() for c in self.captions]


def _parse_vtt_captions(vtt_text: str) -> list[CaptionWord]:
    """Parse WebVTT subtitle output from edge-tts into CaptionWord list."""
    captions: list[CaptionWord] = []
    lines = vtt_text.strip().splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # Look for timestamp lines: 00:00:00.000 --> 00:00:01.500
        if "-->" in line:
            parts = line.split("-->")
            if len(parts) == 2:
                start_ms = _parse_timestamp(parts[0].strip())
                end_ms = _parse_timestamp(parts[1].strip())
                # Next line(s) are the text
                i += 1
                text_parts: list[str] = []
                while i < len(lines) and lines[i].strip() and "-->" not in lines[i]:
                    text_parts.append(lines[i].strip())
                    i += 1
                text = " ".join(text_parts).strip()
                if text and start_ms is not None and end_ms is not None:
                    captions.append(CaptionWord(text=text, start_ms=start_ms, end_ms=end_ms))
                continue
        i += 1
    return captions


def _parse_timestamp(ts: str) -> int | None:
    """Parse HH:MM:SS.mmm or MM:SS.mmm timestamp to milliseconds."""
    try:
        ts = ts.strip()
        parts = ts.split(":")
        if len(parts) == 3:
            h, m, s = parts
            return int(h) * 3600000 + int(m) * 60000 + int(float(s) * 1000)
        elif len(parts) == 2:
            m, s = parts
            return int(m) * 60000 + int(float(s) * 1000)
    except (ValueError, IndexError):
        pass
    return None


class TtsService:
    @staticmethod
    async def synthesize(
        text: str,
        file_path: Path,
        voice: str = "zh-CN-XiaoxiaoNeural",
    ) -> float:
        """Synthesize text to MP3 and return its duration in seconds."""
        if not text or not text.strip():
            logger.warning("Empty text passed to TtsService. Skip synthesis.")
            return 0.0

        file_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info("Starting TTS synthesis for text (len=%d) to %s", len(text), file_path)

        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(str(file_path))

        if not file_path.exists():
            raise FileNotFoundError(f"Failed to generate TTS file at {file_path}")

        audio = MP3(str(file_path))
        duration = audio.info.length
        logger.info("TTS synthesis complete. Duration: %.2fs", duration)
        return duration

    @staticmethod
    async def synthesize_with_captions(
        text: str,
        file_path: Path,
        voice: str = "zh-CN-XiaoxiaoNeural",
    ) -> TtsResult:
        """Synthesize text to MP3 with word-level caption timestamps.

        Returns a TtsResult containing both duration and caption timing data.
        """
        if not text or not text.strip():
            logger.warning("Empty text passed to TtsService. Skip synthesis.")
            return TtsResult(duration=0.0, captions=[])

        file_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info("Starting TTS+captions synthesis for text (len=%d)", len(text))

        communicate = edge_tts.Communicate(text, voice)

        # Collect word-level boundary events and audio bytes in a single pass
        word_captions: list[CaptionWord] = []
        audio_chunks: list[bytes] = []

        async for event in communicate.stream():
            if event["type"] == "WordBoundary":
                offset = event.get("offset", 0)  # in 100-nanosecond units
                duration_ns = event.get("duration", 0)
                word_text = event.get("text", "")
                start_ms = offset // 10000  # 100ns -> ms
                end_ms = (offset + duration_ns) // 10000
                if word_text.strip():
                    word_captions.append(
                        CaptionWord(text=word_text.strip(), start_ms=start_ms, end_ms=end_ms)
                    )
            elif event["type"] == "audio":
                audio_chunks.append(event["data"])

        # Write collected audio bytes to file
        with open(str(file_path), "wb") as f:
            for chunk in audio_chunks:
                f.write(chunk)

        if not file_path.exists():
            raise FileNotFoundError(f"Failed to generate TTS file at {file_path}")

        audio = MP3(str(file_path))
        duration = audio.info.length
        logger.info("TTS+captions synthesis complete. Duration: %.2fs, %d caption words", duration, len(word_captions))
        return TtsResult(duration=duration, captions=word_captions)
