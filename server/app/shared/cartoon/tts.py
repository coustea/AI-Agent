"""TTS synthesis for cartoon animation videos."""

from __future__ import annotations

import asyncio
import shutil
import tempfile
from pathlib import Path

from mutagen import (
    File as MutagenFile,
)

from app.infra.logging import get_logger
from app.shared.cartoon.schemas import (
    AudioSynthesis,
)

logger = get_logger(__name__)


_EDGE_VOICES = {
    "teacher": (
        "zh-CN-XiaoxiaoNeural"
    ),
    "coach": (
        "zh-CN-YunxiNeural"
    ),
}

_SAY_VOICES = {
    "teacher": "Tingting",
    "coach": "Sin-ji",
}


class CartoonTtsService:
    """Synthesize browser-compatible MP3 narration clips."""

    def __init__(
        self,
        *,
        provider: str = "edge",
        retries: int = 2,
        timeout_seconds: int = 120,
    ) -> None:
        if provider not in {
            "edge",
            "say",
        }:
            raise ValueError(
                "Unsupported TTS provider: "
                f"{provider}"
            )

        self.provider = provider

        self.retries = max(
            1,
            retries,
        )

        self.timeout_seconds = max(
            10,
            timeout_seconds,
        )

    async def synthesize(
        self,
        text: str,
        output_path: Path,
        voice: str = "teacher",
    ) -> AudioSynthesis:
        narration = " ".join(
            str(
                text
                or ""
            ).split()
        )

        if not narration:
            raise ValueError(
                "TTS text is empty"
            )

        if (
            output_path.suffix.lower()
            != ".mp3"
        ):
            raise ValueError(
                "TTS output path must "
                "use the .mp3 suffix"
            )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path.unlink(
            missing_ok=True
        )

        if self.provider == "edge":
            try:
                return await self._synthesize_edge(
                    narration,
                    output_path,
                    voice,
                )

            except Exception as exc:
                logger.warning(
                    "edge-tts failed, "
                    "trying local fallback: %s",
                    exc,
                )

                if (
                    shutil.which("say")
                    and shutil.which(
                        "ffmpeg"
                    )
                ):
                    return await self._synthesize_say(
                        narration,
                        output_path,
                        voice,
                    )

                raise

        return await self._synthesize_say(
            narration,
            output_path,
            voice,
        )

    async def _synthesize_edge(
        self,
        text: str,
        output_path: Path,
        voice: str,
    ) -> AudioSynthesis:
        import edge_tts

        selected_voice = (
            _EDGE_VOICES.get(
                voice,
                _EDGE_VOICES[
                    "teacher"
                ],
            )
        )

        last_error: Exception | None = None

        for attempt in range(
            1,
            self.retries + 1,
        ):
            try:
                communicate = (
                    edge_tts.Communicate(
                        text,
                        selected_voice,
                    )
                )

                await asyncio.wait_for(
                    communicate.save(
                        str(
                            output_path
                        )
                    ),
                    timeout=(
                        self.timeout_seconds
                    ),
                )

                duration_ms = (
                    _audio_duration_ms(
                        output_path
                    )
                )

                return AudioSynthesis(
                    path=output_path,
                    duration_ms=(
                        duration_ms
                    ),
                    text=text,
                    provider="edge",
                    voice=selected_voice,
                )

            except Exception as exc:
                last_error = exc

                output_path.unlink(
                    missing_ok=True
                )

                if attempt < self.retries:
                    await asyncio.sleep(
                        1.2
                        * attempt
                    )

        assert last_error is not None
        raise last_error

    async def _synthesize_say(
        self,
        text: str,
        output_path: Path,
        voice: str,
    ) -> AudioSynthesis:
        say = shutil.which(
            "say"
        )

        ffmpeg = shutil.which(
            "ffmpeg"
        )

        if not say:
            raise RuntimeError(
                "macOS say command "
                "is unavailable"
            )

        if not ffmpeg:
            raise RuntimeError(
                "ffmpeg is required for "
                "the macOS TTS fallback"
            )

        selected_voice = (
            _SAY_VOICES.get(
                voice,
                _SAY_VOICES[
                    "teacher"
                ],
            )
        )

        with tempfile.TemporaryDirectory(
            prefix="cartoon-tts-"
        ) as temp_dir:
            temp_root = Path(
                temp_dir
            )

            text_path = (
                temp_root
                / "narration.txt"
            )

            aiff_path = (
                temp_root
                / "narration.aiff"
            )

            text_path.write_text(
                text,
                encoding="utf-8",
            )

            await self._run_process(
                [
                    say,
                    "-v",
                    selected_voice,
                    "-f",
                    str(
                        text_path
                    ),
                    "-o",
                    str(
                        aiff_path
                    ),
                ],
                label="macOS say",
            )

            if (
                not aiff_path.is_file()
                or aiff_path.stat().st_size
                <= 0
            ):
                raise RuntimeError(
                    "macOS say did not produce "
                    "a valid AIFF file"
                )

            await self._run_process(
                [
                    ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(
                        aiff_path
                    ),
                    "-vn",
                    "-codec:a",
                    "libmp3lame",
                    "-q:a",
                    "3",
                    str(
                        output_path
                    ),
                ],
                label=(
                    "ffmpeg TTS conversion"
                ),
            )

        duration_ms = (
            _audio_duration_ms(
                output_path
            )
        )

        return AudioSynthesis(
            path=output_path,
            duration_ms=(
                duration_ms
            ),
            text=text,
            provider="say+ffmpeg",
            voice=selected_voice,
        )

    async def _run_process(
        self,
        command: list[str],
        *,
        label: str,
    ) -> None:
        process = (
            await asyncio.create_subprocess_exec(
                *command,
                stdout=(
                    asyncio.subprocess.PIPE
                ),
                stderr=(
                    asyncio.subprocess.PIPE
                ),
            )
        )

        try:
            stdout, stderr = (
                await asyncio.wait_for(
                    process.communicate(),
                    timeout=(
                        self.timeout_seconds
                    ),
                )
            )

        except TimeoutError as exc:
            process.kill()

            await process.communicate()

            raise RuntimeError(
                f"{label} timed out"
            ) from exc

        if process.returncode != 0:
            message = (
                stderr
                or stdout
            ).decode(
                "utf-8",
                errors="replace",
            ).strip()

            raise RuntimeError(
                message
                or f"{label} failed"
            )


def _audio_duration_ms(
    path: Path,
) -> int:
    if (
        not path.is_file()
        or path.stat().st_size
        <= 0
    ):
        raise RuntimeError(
            "TTS output is missing "
            f"or empty: {path}"
        )

    audio = MutagenFile(
        path
    )

    if (
        audio is None
        or audio.info is None
    ):
        raise RuntimeError(
            "Unable to read audio "
            f"duration: {path}"
        )

    duration = float(
        getattr(
            audio.info,
            "length",
            0.0,
        )
        or 0.0
    )

    if duration <= 0:
        raise RuntimeError(
            "Invalid audio duration: "
            f"{path}"
        )

    return max(
        1,
        int(
            round(
                duration
                * 1000
            )
        ),
    )