"""TTS 语音合成服务 — 基于 edge-tts 的文本转语音。

支持：
- 基础合成：文本 → MP3，返回时长
- 带字幕合成：文本 → MP3 + 逐词时间戳，用于视频字幕
"""

from __future__ import annotations

from pathlib import Path
import edge_tts
from mutagen.mp3 import MP3
from app.infra.logging import get_logger
from app.shared.video.schemas import AudioSynthesis, CaptionWord as SchemaCaptionWord

logger = get_logger(__name__)


# 逐词字幕类：携带文本与起止毫秒时间戳
class CaptionWord:
    """逐词字幕 — 包含文本和起止时间戳（毫秒）。"""
    __slots__ = ("text", "start_ms", "end_ms")

    def __init__(self, text: str, start_ms: int, end_ms: int):
        self.text = text
        self.start_ms = start_ms
        self.end_ms = end_ms

    def to_dict(self) -> dict:
        return {"text": self.text, "start_ms": self.start_ms, "end_ms": self.end_ms}


# TTS 合成结果类：保存时长与逐词字幕
class TtsResult:
    """TTS 合成结果 — 包含音频时长和逐词字幕列表。"""
    __slots__ = ("duration", "captions")

    def __init__(self, duration: float, captions: list[CaptionWord]):
        self.duration = duration
        self.captions = captions

    def to_dict(self) -> list[dict]:
        return [c.to_dict() for c in self.captions]


# 解析 edge-tts 输出的 WebVTT 字幕为 CaptionWord 列表
def _parse_vtt_captions(vtt_text: str) -> list[CaptionWord]:
    """解析 edge-tts 输出的 WebVTT 字幕为 CaptionWord 列表。"""
    captions: list[CaptionWord] = []
    lines = vtt_text.strip().splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # 识别时间戳行（含 -->）并解析左右端点
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


# 将 HH:MM:SS.mmm 或 MM:SS.mmm 时间戳解析为毫秒
def _parse_timestamp(ts: str) -> int | None:
    """将 HH:MM:SS.mmm 或 MM:SS.mmm 时间戳解析为毫秒。"""
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


# TTS 服务：封装 edge-tts 的文本转语音与字幕生成
class TtsService:
    """TTS 语音合成服务 — 封装 edge-tts 调用。"""

    # 基础合成：文本转 MP3，返回音频时长（秒）
    @staticmethod
    async def synthesize(
        text: str,
        file_path: Path,
        voice: str = "zh-CN-XiaoxiaoNeural",
    ) -> float:
        """基础合成：文本 → MP3，返回音频时长（秒）。"""
        if not text or not text.strip():
            logger.warning("传入空文本到 TtsService, 跳过合成")
            return 0.0

        file_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info("开始 TTS 合成, 文本长度=%d, 输出=%s", len(text), file_path)

        # 调用 edge-tts 合成并保存为 MP3
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(str(file_path))

        if not file_path.exists():
            raise FileNotFoundError(f"Failed to generate TTS file at {file_path}")

        audio = MP3(str(file_path))
        duration = audio.info.length
        logger.info("TTS 合成完成. 时长: %.2fs", duration)
        return duration

    # 带字幕合成：文本转 MP3 + 逐词时间戳（带 SHA-256 缓存）
    @staticmethod
    async def synthesize_with_captions(
        text: str,
        file_path: Path,
        voice: str = "zh-CN-XiaoxiaoNeural",
    ) -> TtsResult:
        """带字幕合成：文本 → MP3 + 逐词时间戳（具有 SHA-256 缓存优化）。
        
        通过 edge-tts 的 WordBoundary 事件获取每个词的起止时间。
        """
        if not text or not text.strip():
            logger.warning("传入空文本到 TtsService, 跳过合成")
            return TtsResult(duration=0.0, captions=[])

        import hashlib
        import json
        import shutil
        from app.config import WORKPLACE_DIR

        # 1. 以"配音+文本"计算 SHA-256 作为缓存键
        payload_str = f"{voice}:{text.strip()}"
        sha256_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
        
        # 缓存路径
        cache_dir = WORKPLACE_DIR / "tts_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_mp3_path = cache_dir / f"tts_{sha256_hash}.mp3"
        cache_meta_path = cache_dir / f"tts_{sha256_hash}.json"

        # 2. 缓存命中则直接复用，跳过合成
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
                
                # 确保目标文件夹存在并拷贝音频文件
                file_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(cache_mp3_path), str(file_path))
                
                logger.info("命中 TTS 缓存! 复用音频缓存: %s", cache_mp3_path.name)
                return TtsResult(duration=duration, captions=captions)
            except Exception as e:
                logger.warning("加载 TTS 缓存失败, 回退到合成: %s", e)

        # 3. 缓存未命中，执行流式合成
        file_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("开始 TTS+字幕合成, 文本长度=%d", len(text))

        communicate = edge_tts.Communicate(text, voice)

        # 单次遍历收集逐词边界事件与音频字节
        word_captions: list[CaptionWord] = []
        audio_chunks: list[bytes] = []

        async for event in communicate.stream():
            # 处理逐词边界事件，换算为毫秒时间戳
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
            # 收集音频数据帧
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
        logger.info("TTS+字幕合成完成. 时长: %.2fs, 字幕词数: %d", duration, len(word_captions))

        # 4. 将音频与字幕写入缓存供下次复用
        try:
            shutil.copy2(str(file_path), str(cache_mp3_path))
            meta_data = {
                "duration": duration,
                "captions": [c.to_dict() for c in word_captions]
            }
            cache_meta_path.write_text(json.dumps(meta_data, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info("TTS 缓存已保存: %s", cache_mp3_path.name)
        except Exception as e:
            logger.warning("保存 TTS 缓存失败: %s", e)

        return TtsResult(duration=duration, captions=word_captions)


# 视频 TTS 服务：按配置选择讯飞或 edge-tts 并返回统一音频契约
class VideoTtsService:
    """Select the configured provider and return the shared audio contract."""

    async def synthesize(
        self,
        text: str,
        output_path: Path,
        voice: str,
    ) -> AudioSynthesis:
        from app.config import SPARK_TTS_APP_ID

        # 配置了讯飞 AppID 时优先使用星火 TTS
        if SPARK_TTS_APP_ID and SPARK_TTS_APP_ID.strip():
            from app.shared.video.spark_tts import SparkTtsService

            result = await SparkTtsService.synthesize_with_captions(
                text,
                output_path,
                voice="x4_yezi",
            )
        else:
            # 否则回退到 edge-tts（非中文声音时默认中文女声）
            edge_voice = (
                voice
                if voice.startswith("zh-")
                else "zh-CN-XiaoxiaoNeural"
            )
            result = await TtsService.synthesize_with_captions(
                text,
                output_path,
                voice=edge_voice,
            )

        # 读取音频时长并过滤超出音频范围的字幕词
        audio = MP3(str(output_path))
        duration_ms = round(audio.info.length * 1000)
        if duration_ms <= 0:
            raise ValueError("TTS produced an audio file with invalid duration")
        # 仅保留落在音频时长内的逐词时间戳
        words = [
            SchemaCaptionWord.model_validate(caption.to_dict())
            for caption in result.captions
            if caption.end_ms <= duration_ms
        ]
        return AudioSynthesis(
            path=output_path,
            duration_ms=duration_ms,
            words=words,
        )
