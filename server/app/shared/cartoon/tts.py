"""Narration synthesis and caption-aligned timeline construction."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from mutagen import File as MutagenFile

from app.shared.cartoon.models import (
    CaptionCue,
    CartoonGenerationError,
    Lesson,
    SpeechClip,
    TimedBeat,
    Timeline,
)


_VOICES = {
    "teacher": "zh-CN-XiaoxiaoNeural",
    "coach": "zh-CN-YunxiNeural",
}
_MIN_BEAT_MS = 3_200
_MAX_BEAT_MS = 10_000
_AUDIO_TAIL_MS = 120


class _EdgeTts:
    def __init__(self, *, retries: int = 2, timeout_seconds: int = 120) -> None:
        self.retries = max(1, retries)
        self.timeout_seconds = max(10, timeout_seconds)

    async def synthesize(self, text: str, output_path: Path, voice: str) -> SpeechClip:
        import edge_tts

        selected_voice = _VOICES.get(voice, _VOICES["teacher"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.unlink(missing_ok=True)
        last_error: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                communicate = edge_tts.Communicate(text, selected_voice, rate="+12%")
                await asyncio.wait_for(
                    communicate.save(str(output_path)),
                    timeout=self.timeout_seconds,
                )
                return SpeechClip(
                    beat_id=output_path.stem,
                    path=output_path,
                    duration_ms=_audio_duration_ms(output_path),
                    provider="edge",
                    voice=selected_voice,
                )
            except Exception as exc:
                last_error = exc
                output_path.unlink(missing_ok=True)
                if attempt < self.retries:
                    await asyncio.sleep(attempt * 1.2)
        assert last_error is not None
        raise last_error


class CartoonSpeech:
    """Synthesize every teaching beat and return the canonical timeline."""

    def __init__(self, *, tts: Any | None = None, max_parallel: int = 4) -> None:
        self._tts = tts or _EdgeTts()
        self._parallelism = max(1, max_parallel)

    async def synthesize(
        self,
        lesson: Lesson,
        output_dir: Path,
        *,
        voice: str,
    ) -> Timeline:
        audio_dir = output_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        ordered_beats = [beat for scene in lesson.scenes for beat in scene.beats]
        semaphore = asyncio.Semaphore(self._parallelism)

        async def synthesize_beat(beat: Any) -> SpeechClip:
            async with semaphore:
                return await self._tts.synthesize(
                    beat.narration,
                    audio_dir / f"{beat.id}.mp3",
                    voice,
                )

        try:
            async with asyncio.TaskGroup() as group:
                tasks = [group.create_task(synthesize_beat(beat)) for beat in ordered_beats]
            clips = [task.result() for task in tasks]
        except Exception as exc:
            details = self._exception_details(exc)
            raise CartoonGenerationError(
                "旁白合成失败: " + " | ".join(details),
                stage="speech",
                problems=details,
            ) from exc

        providers = {clip.provider for clip in clips}
        if len(providers) != 1:
            raise CartoonGenerationError(
                "同一视频必须使用统一的语音提供方",
                stage="speech",
                problems=sorted(providers),
            )

        timed_beats: list[TimedBeat] = []
        captions: list[CaptionCue] = []
        cursor = 0
        for scene in lesson.scenes:
            for beat in scene.beats:
                clip = clips[len(timed_beats)]
                duration_ms = max(_MIN_BEAT_MS, clip.duration_ms + _AUDIO_TAIL_MS)
                if duration_ms > _MAX_BEAT_MS:
                    raise CartoonGenerationError(
                        f"教学节拍 {beat.id} 的旁白过长，无法保持语义动画节奏",
                        stage="speech",
                        problems=[
                            f"{beat.id}: audio={clip.duration_ms}ms, max={_MAX_BEAT_MS - _AUDIO_TAIL_MS}ms"
                        ],
                    )
                timed = TimedBeat(
                    scene_id=scene.id,
                    beat_id=beat.id,
                    start_ms=cursor,
                    duration_ms=duration_ms,
                    audio_duration_ms=clip.duration_ms,
                    audio_src=clip.path.relative_to(output_dir).as_posix(),
                )
                timed_beats.append(timed)
                captions.append(
                    CaptionCue(
                        start_ms=cursor + 100,
                        end_ms=cursor + duration_ms - 100,
                        text=beat.caption,
                    )
                )
                cursor += duration_ms

        return Timeline(duration_ms=cursor, beats=timed_beats, captions=captions)

    @classmethod
    def _exception_details(cls, exc: BaseException) -> list[str]:
        if isinstance(exc, BaseExceptionGroup):
            details = [detail for nested in exc.exceptions for detail in cls._exception_details(nested)]
            return details[:8]
        return [f"{type(exc).__name__}: {str(exc).strip() or type(exc).__name__}"]


def _audio_duration_ms(path: Path) -> int:
    if not path.is_file() or path.stat().st_size <= 0:
        raise RuntimeError(f"TTS output is missing or empty: {path}")
    audio = MutagenFile(path)
    if audio is None or audio.info is None:
        raise RuntimeError(f"Unable to read audio duration: {path}")
    duration = float(getattr(audio.info, "length", 0.0) or 0.0)
    if duration <= 0:
        raise RuntimeError(f"Invalid audio duration: {path}")
    return max(1, round(duration * 1_000))
