"""Audio-driven caption, visual cue, and scene timing construction."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

from app.shared.video.schemas import (
    CaptionChunk,
    CaptionWord,
    VisualCue,
    VisualCueKind,
)


# 视觉节拍模型：场景编写阶段产出的视觉关键帧
class VisualBeat(BaseModel):
    id: str = Field(min_length=1)
    kind: VisualCueKind
    target: str = ""
    text_anchor: str = Field(min_length=1)
    summary: str = ""


# 场景时间轴模型：起始、总时长与音频时长
class SceneTiming(BaseModel):
    start_ms: int = Field(ge=0)
    duration_ms: int = Field(gt=0)
    audio_duration_ms: int = Field(gt=0)


# 去除标点与空白，得到便于匹配的纯文本
def _plain_text(value: str) -> str:
    return re.sub(r"[\s，。！？；：、,.!?;:（）()《》“”\"']", "", value)


# 按句末标点将旁白切分为短语，用于字幕分段
def _phrases(narration: str) -> list[str]:
    return [
        phrase.strip()
        for phrase in re.split(r"[。！？；\n]+", narration)
        if phrase.strip()
    ]


# 无逐词时间戳时的兜底：按短语长度权重估算字幕时间
def _estimated_chunks(narration: str, audio_duration_ms: int) -> list[CaptionChunk]:
    phrases = _phrases(narration)
    if not phrases or audio_duration_ms <= 0:
        return []
    weights = [max(1, len(_plain_text(phrase))) for phrase in phrases]
    total_weight = sum(weights)
    chunks: list[CaptionChunk] = []
    cursor = 0
    for index, (phrase, weight) in enumerate(zip(phrases, weights, strict=True)):
        end = (
            audio_duration_ms
            if index == len(phrases) - 1
            else cursor + round(audio_duration_ms * weight / total_weight)
        )
        chunks.append(
            CaptionChunk(
                text=phrase,
                start_ms=cursor,
                end_ms=max(cursor + 1, end),
            )
        )
        cursor = end
    return chunks


# 构建可读短语字幕，并将最后一段对齐到音频结尾
def build_caption_chunks(
    narration: str,
    caption_words: list[CaptionWord],
    audio_duration_ms: int,
) -> list[CaptionChunk]:
    """Build readable phrase captions and pin the final phrase to audio end."""
    # 音频无效或缺少逐词时间戳时走估算路径
    if audio_duration_ms <= 0:
        return []
    if not caption_words:
        return _estimated_chunks(narration, audio_duration_ms)

    phrases = _phrases(narration)
    if not phrases:
        return []

    word_text = "".join(_plain_text(word.text) for word in caption_words)
    chunks: list[CaptionChunk] = []
    search_from = 0
    for phrase in phrases:
        plain_phrase = _plain_text(phrase)
        phrase_start = word_text.find(plain_phrase, search_from)
        if phrase_start < 0:
            return _estimated_chunks(narration, audio_duration_ms)
        phrase_end = phrase_start + len(plain_phrase)

        char_cursor = 0
        matched_words: list[CaptionWord] = []
        for word in caption_words:
            next_cursor = char_cursor + len(_plain_text(word.text))
            if next_cursor > phrase_start and char_cursor < phrase_end:
                matched_words.append(word)
            char_cursor = next_cursor

        if not matched_words:
            return _estimated_chunks(narration, audio_duration_ms)
        chunks.append(
            CaptionChunk(
                text=phrase,
                start_ms=matched_words[0].start_ms,
                end_ms=min(audio_duration_ms, matched_words[-1].end_ms),
            )
        )
        search_from = phrase_end

    # 将最后一段字幕的结束时间钉到音频末尾
    chunks[-1] = chunks[-1].model_copy(update={"end_ms": audio_duration_ms})
    return chunks


# 将视觉节拍对齐到旁白锚点，生成有序且受音频约束的视觉线索
def align_visual_cues(
    beats: list[VisualBeat],
    *,
    narration: str,
    caption_words: list[CaptionWord],
    caption_chunks: list[CaptionChunk],
    audio_duration_ms: int,
) -> list[VisualCue]:
    """Align visual beats to spoken anchors and keep cues ordered and bounded."""
    # 无节拍或音频无效时直接返回空
    if not beats or audio_duration_ms <= 0:
        return []

    plain_narration = _plain_text(narration)
    plain_words = "".join(_plain_text(word.text) for word in caption_words)
    # 在旁白中定位每个视觉节拍锚点（按出现顺序）
    located: list[tuple[VisualBeat, int]] = []
    search_from = 0
    for beat in beats:
        anchor = _plain_text(beat.text_anchor)
        position = plain_narration.find(anchor, search_from)
        # 找不到锚点则跳过该节拍
        if position < 0:
            continue
        located.append((beat, position))
        search_from = position + len(anchor)

    # 为每个定位到的节拍计算起止时间，生成视觉线索
    cues: list[VisualCue] = []
    for index, (beat, narration_position) in enumerate(located):
        start_ms: int | None = None
        # 优先依据逐词时间戳定位起始
        if caption_words and plain_words:
            word_cursor = 0
            for word in caption_words:
                next_cursor = word_cursor + len(_plain_text(word.text))
                if next_cursor > narration_position:
                    start_ms = word.start_ms
                    break
                word_cursor = next_cursor

        # 无逐词时间戳时回退到匹配字幕片段的起始
        if start_ms is None:
            matching_chunk = next(
                (
                    chunk
                    for chunk in caption_chunks
                    if _plain_text(beat.text_anchor) in _plain_text(chunk.text)
                ),
                None,
            )
            start_ms = matching_chunk.start_ms if matching_chunk else 0

        next_start = audio_duration_ms
        if index + 1 < len(located):
            next_position = located[index + 1][1]
            if caption_words and plain_words:
                word_cursor = 0
                for word in caption_words:
                    next_cursor = word_cursor + len(_plain_text(word.text))
                    if next_cursor > next_position:
                        next_start = word.start_ms
                        break
                    word_cursor = next_cursor
            else:
                next_start = round(
                    audio_duration_ms * next_position / max(1, len(plain_narration))
                )

        # 结束时间取下一节拍起点与音频时长的较小值
        end_ms = max(start_ms + 1, min(audio_duration_ms, next_start))
        cues.append(
            VisualCue(
                id=beat.id,
                kind=beat.kind,
                target=beat.target,
                summary=beat.summary,
                start_ms=start_ms,
                end_ms=end_ms,
                caption_text=beat.text_anchor,
            )
        )
    return cues


# 依据实测音频时长推导连续的场景边界（含尾部留白）
def build_scene_timing(
    audio_durations_ms: list[int],
    *,
    tail_padding_ms: int,
) -> list[SceneTiming]:
    """Derive contiguous scene boundaries from measured audio durations."""
    # 尾部留白不得为负
    if tail_padding_ms < 0:
        raise ValueError("tail_padding_ms must not be negative")

    # 顺序累加生成连续场景时间轴
    timings: list[SceneTiming] = []
    start_ms = 0
    for audio_duration_ms in audio_durations_ms:
        # 音频时长必须为正
        if audio_duration_ms <= 0:
            raise ValueError("audio duration must be positive")
        # 场景时长 = 音频时长 + 尾部留白
        duration_ms = audio_duration_ms + tail_padding_ms
        timings.append(
            SceneTiming(
                start_ms=start_ms,
                duration_ms=duration_ms,
                audio_duration_ms=audio_duration_ms,
            )
        )
        start_ms += duration_ms
    return timings
