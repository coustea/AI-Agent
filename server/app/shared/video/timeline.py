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


class VisualBeat(BaseModel):
    id: str = Field(min_length=1)
    kind: VisualCueKind
    target: str = ""
    text_anchor: str = Field(min_length=1)
    summary: str = ""


class SceneTiming(BaseModel):
    start_ms: int = Field(ge=0)
    duration_ms: int = Field(gt=0)
    audio_duration_ms: int = Field(gt=0)


def _plain_text(value: str) -> str:
    return re.sub(r"[\s，。！？；：、,.!?;:（）()《》“”\"']", "", value)


def _phrases(narration: str) -> list[str]:
    return [
        phrase.strip()
        for phrase in re.split(r"[。！？；\n]+", narration)
        if phrase.strip()
    ]


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


def build_caption_chunks(
    narration: str,
    caption_words: list[CaptionWord],
    audio_duration_ms: int,
) -> list[CaptionChunk]:
    """Build readable phrase captions and pin the final phrase to audio end."""
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

    chunks[-1] = chunks[-1].model_copy(update={"end_ms": audio_duration_ms})
    return chunks


def align_visual_cues(
    beats: list[VisualBeat],
    *,
    narration: str,
    caption_words: list[CaptionWord],
    caption_chunks: list[CaptionChunk],
    audio_duration_ms: int,
) -> list[VisualCue]:
    """Align visual beats to spoken anchors and keep cues ordered and bounded."""
    if not beats or audio_duration_ms <= 0:
        return []

    plain_narration = _plain_text(narration)
    plain_words = "".join(_plain_text(word.text) for word in caption_words)
    located: list[tuple[VisualBeat, int]] = []
    search_from = 0
    for beat in beats:
        anchor = _plain_text(beat.text_anchor)
        position = plain_narration.find(anchor, search_from)
        if position < 0:
            continue
        located.append((beat, position))
        search_from = position + len(anchor)

    cues: list[VisualCue] = []
    for index, (beat, narration_position) in enumerate(located):
        start_ms: int | None = None
        if caption_words and plain_words:
            word_cursor = 0
            for word in caption_words:
                next_cursor = word_cursor + len(_plain_text(word.text))
                if next_cursor > narration_position:
                    start_ms = word.start_ms
                    break
                word_cursor = next_cursor

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


def build_scene_timing(
    audio_durations_ms: list[int],
    *,
    tail_padding_ms: int,
) -> list[SceneTiming]:
    """Derive contiguous scene boundaries from measured audio durations."""
    if tail_padding_ms < 0:
        raise ValueError("tail_padding_ms must not be negative")

    timings: list[SceneTiming] = []
    start_ms = 0
    for audio_duration_ms in audio_durations_ms:
        if audio_duration_ms <= 0:
            raise ValueError("audio duration must be positive")
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
