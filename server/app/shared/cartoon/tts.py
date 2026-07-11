"""TTS synthesis for cartoon animation videos."""

from __future__ import annotations

import asyncio
import shutil
import tempfile
from pathlib import Path

from mutagen import File as MutagenFile

from app.infra.logging import get_logger
from app.shared.cartoon.schemas import AudioSynthesis

logger = get_logger(__name__)


_EDGE_VOICES = {
    "teacher": "zh-CN-XiaoxiaoNeural",
    "coach": "zh-CN-YunxiNeural",
}

_SAY_VOICES = {
    "teacher": "Tingting",
    "coach": "Sin-ji",
}


class CartoonTtsService:
    """Synthesize narration clips with edge-tts and a local macOS fallback."""

    def __init__(
        self,
        *,
        provider: str = "edge",
        retries: int = 2,
        timeout_seconds: int = 120,
    ) -> None:
        self.provider = provider
        self.retries = max(1, retries)
        self.timeout_seconds = max(10, timeout_seconds)

    async def synthesize(
        self,
        text: str,
        output_path: Path,
        voice: str = "teacher",
    ) -> AudioSynthesis:
        narration = " ".join(str(text or "").split())
        if not narration:
            raise ValueError("TTS text is empty")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        if self.provider == "edge":
            try:
                return await self._synthesize_edge(narration, output_path, voice)
            except Exception as exc:
                logger.warning("edge-tts failed, trying local fallback: %s", exc)
                if shutil.which("say"):
                    return await self._synthesize_say(narration, output_path, voice)
                raise

        if self.provider == "say":
            return await self._synthesize_say(narration, output_path, voice)

        raise ValueError(f"Unsupported TTS provider: {self.provider}")

    async def _synthesize_edge(
        self,
        text: str,
        output_path: Path,
        voice: str,
    ) -> AudioSynthesis:
        import edge_tts

        selected_voice = _EDGE_VOICES.get(voice, _EDGE_VOICES["teacher"])
        last_error: Exception | None = None

        for attempt in range(self.retries):
            try:
                communicate = edge_tts.Communicate(text, selected_voice)
                await asyncio.wait_for(
                    communicate.save(str(output_path)),
                    timeout=self.timeout_seconds,
                )
                duration_ms = _audio_duration_ms(output_path)
                return AudioSynthesis(
                    path=output_path,
                    duration_ms=duration_ms,
                    text=text,
                    provider="edge",
                    voice=selected_voice,
                )
            except Exception as exc:
                last_error = exc
                if output_path.exists():
                    output_path.unlink(missing_ok=True)
                if attempt + 1 < self.retries:
                    await asyncio.sleep(1.2 * (attempt + 1))

        assert last_error is not None
        raise last_error

    async def _synthesize_say(
        self,
        text: str,
        output_path: Path,
        voice: str,
    ) -> AudioSynthesis:
        selected_voice = _SAY_VOICES.get(voice, _SAY_VOICES["teacher"])
        m4a_path = output_path.with_suffix(".m4a")

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as handle:
            handle.write(text)
            text_path = Path(handle.name)

        try:
            command = [
                "say",
                "-v",
                selected_voice,
                "-f",
                str(text_path),
                "-o",
                str(m4a_path),
            ]
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout_seconds,
            )
            if process.returncode != 0:
                message = (stderr or stdout).decode("utf-8", errors="ignore").strip()
                raise RuntimeError(message or "macOS say command failed")

            duration_ms = _audio_duration_ms(m4a_path)
            return AudioSynthesis(
                path=m4a_path,
                duration_ms=duration_ms,
                text=text,
                provider="say",
                voice=selected_voice,
            )
        finally:
            text_path.unlink(missing_ok=True)


def _audio_duration_ms(path: Path) -> int:
    if not path.is_file() or path.stat().st_size <= 0:
        raise RuntimeError(f"TTS output is missing or empty: {path}")

    audio = MutagenFile(path)
    if audio is None or audio.info is None:
        raise RuntimeError(f"Unable to read audio duration: {path}")

    duration = float(getattr(audio.info, "length", 0.0) or 0.0)
    if duration <= 0:
        raise RuntimeError(f"Invalid audio duration: {path}")

    return max(1, int(round(duration * 1000)))
