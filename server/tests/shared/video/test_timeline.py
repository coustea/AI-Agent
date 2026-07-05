from __future__ import annotations

from app.shared.video.schemas import CaptionWord
from app.shared.video.timeline import (
    VisualBeat,
    align_visual_cues,
    build_caption_chunks,
    build_scene_timing,
)


def _words() -> list[CaptionWord]:
    return [
        CaptionWord(text="进程", start_ms=0, end_ms=300),
        CaptionWord(text="是", start_ms=300, end_ms=450),
        CaptionWord(text="程序", start_ms=450, end_ms=800),
        CaptionWord(text="的一次", start_ms=800, end_ms=1100),
        CaptionWord(text="执行过程", start_ms=1100, end_ms=1700),
        CaptionWord(text="它拥有独立状态", start_ms=1800, end_ms=2600),
    ]


def test_caption_chunks_extend_final_phrase_to_audio_end() -> None:
    chunks = build_caption_chunks(
        "进程是程序的一次执行过程。它拥有独立状态。",
        _words(),
        audio_duration_ms=3000,
    )

    assert [chunk.text for chunk in chunks] == [
        "进程是程序的一次执行过程",
        "它拥有独立状态",
    ]
    assert chunks[-1].end_ms == 3000


def test_visual_cues_follow_real_narration_anchors_in_order() -> None:
    chunks = build_caption_chunks(
        "进程是程序的一次执行过程。它拥有独立状态。",
        _words(),
        audio_duration_ms=3000,
    )
    cues = align_visual_cues(
        [
            VisualBeat(
                id="definition",
                kind="define",
                target="definition",
                text_anchor="进程是程序的一次执行过程",
                summary="显示定义",
            ),
            VisualBeat(
                id="state",
                kind="example",
                target="state",
                text_anchor="它拥有独立状态",
                summary="显示状态",
            ),
        ],
        narration="进程是程序的一次执行过程。它拥有独立状态。",
        caption_words=_words(),
        caption_chunks=chunks,
        audio_duration_ms=3000,
    )

    assert [cue.id for cue in cues] == ["definition", "state"]
    assert cues[0].start_ms == 0
    assert cues[0].end_ms <= cues[1].start_ms
    assert cues[-1].end_ms == 3000


def test_scene_timing_uses_measured_audio_and_contiguous_starts() -> None:
    timings = build_scene_timing([2600, 4100], tail_padding_ms=400)

    assert [(item.start_ms, item.duration_ms) for item in timings] == [
        (0, 3000),
        (3000, 4500),
    ]
