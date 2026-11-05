"""旁白语音合成 (TTS) 与精确时间轴/字幕对齐器。"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import re
import shutil

from mutagen import File as MutagenFile

from app.infra.logging import get_logger
from app.shared.cartoon.schemas import (
    CaptionCue,
    SceneStoryboardSpec,
    SpeechClip,
    VideoDesignPlan,
)

logger = get_logger(__name__)

_VOICES = {
    "teacher": "zh-CN-XiaoxiaoNeural",
    "coach": "zh-CN-YunxiNeural",
}
_PACE_RATES = {
    "fast": "+22%",
    "balanced": "+10%",
    "calm": "+0%",
}
_MIN_SCENE_MS = 3_200
_SCENE_TAIL_MS = 280


def _measure_audio_ms(path: Path) -> int:
    """使用 mutagen 测量 MP3 精确毫秒时长。"""
    try:
        parsed = MutagenFile(path)
        length = getattr(getattr(parsed, "info", None), "length", None)
        if length and float(length) > 0:
            return max(800, round(float(length) * 1000))
    except Exception:
        pass
    return 4_000


async def _generate_fallback_mp3(text: str, output_path: Path, duration_sec: float = 4.0) -> str:
    """当 Edge TTS 网络受限时，优先使用 macOS 原生中文语音 Tingting 合成真实人声，其次使用 ffmpeg 静音音轨。"""
    ffmpeg = shutil.which("ffmpeg")
    say_bin = shutil.which("say")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if say_bin and ffmpeg and text.strip():
        aiff_path = output_path.with_suffix(".aiff")
        try:
            proc_say = await asyncio.create_subprocess_exec(
                say_bin,
                "-v",
                "Tingting",
                "-r",
                "205",
                "-o",
                str(aiff_path),
                text.strip(),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc_say.communicate(), timeout=20.0)
            if aiff_path.is_file() and aiff_path.stat().st_size > 256:
                proc_ff = await asyncio.create_subprocess_exec(
                    ffmpeg,
                    "-y",
                    "-i",
                    str(aiff_path),
                    "-acodec",
                    "libmp3lame",
                    "-q:a",
                    "4",
                    str(output_path),
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await asyncio.wait_for(proc_ff.communicate(), timeout=20.0)
                aiff_path.unlink(missing_ok=True)
                if output_path.is_file() and output_path.stat().st_size > 256:
                    return "macos-tingting"
        except Exception:
            aiff_path.unlink(missing_ok=True)

    if ffmpeg:
        proc = await asyncio.create_subprocess_exec(
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=24000:cl=mono",
            "-t",
            f"{max(2.5, duration_sec):.2f}",
            "-q:a",
            "9",
            "-acodec",
            "libmp3lame",
            str(output_path),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.communicate()
    return "fallback"


async def synthesize_scene_clip(
    scene: SceneStoryboardSpec,
    audio_dir: Path,
    *,
    voice: str = "teacher",
    pace: str = "balanced",
) -> SpeechClip:
    """合成单个场景的 MP3 配音并返回精确时长。"""
    selected_voice = _VOICES.get(voice, _VOICES["teacher"])
    rate = _PACE_RATES.get(pace, _PACE_RATES["balanced"])
    out_path = audio_dir / f"{scene.id}.mp3"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    text = scene.narration.strip() or scene.title
    try:
        import edge_tts

        communicate = edge_tts.Communicate(text, selected_voice, rate=rate)
        await asyncio.wait_for(communicate.save(str(out_path)), timeout=15.0)
        duration_ms = _measure_audio_ms(out_path)
        return SpeechClip(
            scene_id=scene.id,
            path=out_path,
            duration_ms=duration_ms,
            provider="edge",
            voice=selected_voice,
        )
    except Exception as exc:
        logger.warning("[CartoonTTS] Edge TTS 不可用 (%s)，切换本地中文语音合成: %s", scene.id, exc)
        est_sec = max(3.5, min(14.0, len(text) * 0.22))
        provider_name = await _generate_fallback_mp3(text, out_path, duration_sec=est_sec)
        duration_ms = _measure_audio_ms(out_path)
        return SpeechClip(
            scene_id=scene.id,
            path=out_path,
            duration_ms=duration_ms,
            provider=provider_name,
            voice="Tingting" if provider_name == "macos-tingting" else selected_voice,
        )


def _split_narration_cues(narration: str, start_ms: int, duration_ms: int) -> list[CaptionCue]:
    """将一个场景的旁白按标点切分为同步字幕条目。"""
    sentences = [
        s.strip()
        for s in re.split(r"(?<=[。！？；!?])", narration.strip())
        if s.strip()
    ]
    if not sentences:
        sentences = [narration.strip() or "讲解进行中"]

    total_chars = max(1, sum(len(s) for s in sentences))
    cues: list[CaptionCue] = []
    cursor = start_ms
    end_limit = start_ms + duration_ms

    for idx, sent in enumerate(sentences):
        if idx == len(sentences) - 1:
            cue_end = end_limit
        else:
            share = max(600, round(duration_ms * (len(sent) / total_chars)))
            cue_end = min(end_limit - 200, cursor + share)
        if cue_end <= cursor:
            cue_end = cursor + 500
        cues.append(CaptionCue(start_ms=cursor, end_ms=cue_end, text=sent))
        cursor = cue_end

    return cues


def _format_vtt_time(ms: int) -> str:
    hours, rem = divmod(max(0, ms), 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, millis = divmod(rem, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def write_webvtt(cues: list[CaptionCue], vtt_path: Path) -> Path:
    """写出标准 WebVTT 字幕文件 (captions.vtt)。"""
    lines = ["WEBVTT", ""]
    for idx, cue in enumerate(cues, start=1):
        lines.extend(
            [
                str(idx),
                f"{_format_vtt_time(cue.start_ms)} --> {_format_vtt_time(cue.end_ms)}",
                cue.text,
                "",
            ]
        )
    vtt_path.write_text("\n".join(lines), encoding="utf-8")
    return vtt_path


async def synthesize_plan_narration(
    plan: VideoDesignPlan,
    output_dir: Path,
    *,
    voice: str = "teacher",
    pace: str = "balanced",
) -> tuple[VideoDesignPlan, list[CaptionCue]]:
    """并行合成所有场景音频，回填精确时间轴并写出 captions.vtt 与 timeline.json。"""
    audio_dir = output_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(4)

    async def _worker(sc: SceneStoryboardSpec) -> SpeechClip:
        async with sem:
            return await synthesize_scene_clip(sc, audio_dir, voice=voice, pace=pace)

    clips = await asyncio.gather(*(_worker(sc) for sc in plan.scenes))

    cursor_ms = 0
    all_cues: list[CaptionCue] = []
    for scene, clip in zip(plan.scenes, clips, strict=True):
        scene_ms = max(_MIN_SCENE_MS, clip.duration_ms + _SCENE_TAIL_MS)
        scene.start_sec = round(cursor_ms / 1000.0, 3)
        scene.duration_sec = round(scene_ms / 1000.0, 3)
        scene.audio_duration_ms = clip.duration_ms
        scene.audio_src = f"audio/{scene.id}.mp3"

        all_cues.extend(_split_narration_cues(scene.narration, cursor_ms, scene_ms))
        cursor_ms += scene_ms

    plan.total_duration_ms = cursor_ms
    plan.total_duration_sec = round(cursor_ms / 1000.0, 3)

    write_webvtt(all_cues, output_dir / "captions.vtt")
    (output_dir / "timeline.json").write_text(
        json.dumps(
            {
                "duration_ms": plan.total_duration_ms,
                "duration_sec": plan.total_duration_sec,
                "scenes": [s.model_dump(mode="json") for s in plan.scenes],
                "captions": [c.model_dump(mode="json") for c in all_cues],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return plan, all_cues


__all__ = [
    "synthesize_plan_narration",
    "synthesize_scene_clip",
    "write_webvtt",
]
