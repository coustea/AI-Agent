"""真实旁白合成；失败交还 agent，不用静音替代。"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from mutagen import File as MutagenFile
from pydantic import BaseModel, Field
from app.infra.logging import get_logger
from app.shared.tools.registry import Tool
from app.shared.tools.sandbox import resolve_sandbox_path

logger = get_logger(__name__)


class SpeechArgs(BaseModel):
    text: str = Field(min_length=1)
    output_path: str = Field(description="工作目录内的 MP3 相对路径")


def build_speech_tool(workdir: Path, *, voice: str, pace: str) -> Tool:
    """构造供视频 Agent 合成真实中文旁白音频的 synthesize_speech 工具。"""
    async def synthesize_speech(text: str, output_path: str) -> dict[str, Any]:
        """调用 Edge TTS 将旁白文本合成为 MP3 音频并测量精确时长。"""
        import time
        import edge_tts

        path = resolve_sandbox_path(workdir, output_path)
        if path.suffix != ".mp3":
            raise ValueError("配音输出必须为 .mp3")
        path.parent.mkdir(parents=True, exist_ok=True)
        selected = {"teacher": "zh-CN-XiaoxiaoNeural", "coach": "zh-CN-YunxiNeural"}[voice]
        rate = {"fast": "+22%", "balanced": "+10%", "calm": "+0%"}[pace]
        text_preview = text.strip().replace("\n", " ")
        if len(text_preview) > 40:
            text_preview = f"{text_preview[:37]}..."

        start_time = time.perf_counter()
        logger.info(
            "[SpeechTool] 开始合成中文旁白: voice={} rate={} output={} text={!r} (共 {} 字符)",
            selected, rate, output_path, text_preview, len(text),
        )
        try:
            async with asyncio.timeout(60):
                await edge_tts.Communicate(text, selected, rate=rate).save(str(path))
            audio = MutagenFile(path)
            duration = float(audio.info.length) if audio and audio.info else 0
            if duration <= 0:
                raise ValueError("音频文件生成为空或无法读取有效时长")
        except BaseException as exc:
            cost_ms = round((time.perf_counter() - start_time) * 1000)
            path.unlink(missing_ok=True)
            logger.error(
                "[SpeechTool] 旁白合成失败 (耗时 {}ms): output={} error={}",
                cost_ms, output_path, exc,
            )
            raise
        cost_ms = round((time.perf_counter() - start_time) * 1000)
        duration_ms = round(duration * 1000)
        logger.info(
            "[SpeechTool] 旁白合成成功 (耗时 {}ms): output={} 音频时长={}ms",
            cost_ms, output_path, duration_ms,
        )
        return {"audio_path": path.relative_to(workdir).as_posix(), "duration_ms": duration_ms}

    return Tool(name="synthesize_speech", description="合成中文旁白 MP3 并返回实际时长；按时长安排场景和字幕。", args_model=SpeechArgs, handler=synthesize_speech)
