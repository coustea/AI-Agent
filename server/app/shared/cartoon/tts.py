"""真实旁白合成；失败交还 agent，不用静音替代。"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from mutagen import File as MutagenFile
from pydantic import BaseModel, Field
from app.shared.tools.registry import Tool
from app.shared.tools.sandbox import resolve_sandbox_path

class SpeechArgs(BaseModel):
    text: str = Field(min_length=1)
    output_path: str = Field(description="工作目录内的 MP3 相对路径")


def build_speech_tool(workdir: Path, *, voice: str, pace: str) -> Tool:
    """构造供视频 Agent 合成真实中文旁白音频的 synthesize_speech 工具。"""
    async def synthesize_speech(text: str, output_path: str) -> dict[str, Any]:
        """调用 Edge TTS 将旁白文本合成为 MP3 音频并测量精确时长。"""
        import edge_tts
        path = resolve_sandbox_path(workdir, output_path)
        if path.suffix != ".mp3":
            raise ValueError("配音输出必须为 .mp3")
        path.parent.mkdir(parents=True, exist_ok=True)
        selected = {"teacher": "zh-CN-XiaoxiaoNeural", "coach": "zh-CN-YunxiNeural"}[voice]
        rate = {"fast": "+22%", "balanced": "+10%", "calm": "+0%"}[pace]
        try:
            async with asyncio.timeout(60):
                await edge_tts.Communicate(text, selected, rate=rate).save(str(path))
            audio = MutagenFile(path)
            duration = float(audio.info.length) if audio and audio.info else 0
            if duration <= 0:
                raise ValueError("无法测量配音时长")
        except BaseException:
            path.unlink(missing_ok=True)
            raise
        return {"audio_path": path.relative_to(workdir).as_posix(), "duration_ms": round(duration * 1000)}

    return Tool(name="synthesize_speech", description="合成中文旁白 MP3 并返回实际时长；按时长安排场景和字幕。", args_model=SpeechArgs, handler=synthesize_speech)
