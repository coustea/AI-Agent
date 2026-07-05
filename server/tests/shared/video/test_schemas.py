from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.shared.video.schemas import (
    CaptionChunk,
    RenderSettings,
    VideoPlan,
    VideoScene,
    VideoStyleDecision,
    VisualCue,
)


def _scene(
    *,
    scene_id: str = "scene-1",
    index: int = 1,
    start_ms: int = 0,
    duration_ms: int = 2400,
) -> VideoScene:
    return VideoScene(
        scene_id=scene_id,
        index=index,
        role="hook" if index == 1 else "recap",
        title="什么是进程",
        learning_objective="理解进程的基本定义",
        visual_type="concept_explain",
        visual={"main_concept": "进程", "definition": "程序的一次执行过程"},
        narration="进程是程序的一次执行过程。",
        audio_src="/static/videos/job/scene-1.mp3",
        start_ms=start_ms,
        duration_ms=duration_ms,
        audio_duration_ms=2000,
        captions=[
            CaptionChunk(text="进程是程序的一次执行过程", start_ms=0, end_ms=2000)
        ],
        visual_cues=[
            VisualCue(
                id="cue-1",
                kind="define",
                target="main_concept",
                summary="显示进程定义",
                start_ms=0,
                end_ms=2000,
            )
        ],
    )


def _plan(*scenes: VideoScene) -> VideoPlan:
    return VideoPlan(
        schema_version="video/v2",
        title="进程基础",
        topic="操作系统进程",
        language="zh-CN",
        aspect_ratio="16:9",
        style=VideoStyleDecision(
            id="systems_dark",
            rationale="操作系统结构适合系统图谱风格",
        ),
        render=RenderSettings(width=1920, height=1080, fps=30),
        scenes=list(scenes),
    )


def test_video_plan_accepts_only_video_v2() -> None:
    data = _plan(_scene()).model_dump()
    data["schema_version"] = "video/v1"
    with pytest.raises(ValidationError, match="video/v2"):
        VideoPlan.model_validate(data)


def test_style_decision_accepts_only_three_shared_styles() -> None:
    with pytest.raises(ValidationError):
        VideoStyleDecision(id="cyberpunk", rationale="旧风格")


def test_scene_caption_cannot_outlive_measured_audio() -> None:
    data = _scene().model_dump()
    data["captions"] = [
        CaptionChunk(text="越界字幕", start_ms=1800, end_ms=2200).model_dump()
    ]
    with pytest.raises(ValidationError, match="caption"):
        VideoScene.model_validate(data)


def test_scene_visual_cue_cannot_outlive_measured_audio() -> None:
    data = _scene().model_dump()
    data["visual_cues"] = [
        VisualCue(
            id="cue-overflow",
            kind="recap",
            target="summary",
            summary="越界事件",
            start_ms=1900,
            end_ms=2100,
        ).model_dump()
    ]
    with pytest.raises(ValidationError, match="visual cue"):
        VideoScene.model_validate(data)


def test_video_plan_requires_contiguous_scene_starts() -> None:
    first = _scene()
    second = _scene(
        scene_id="scene-2",
        index=2,
        start_ms=2500,
        duration_ms=2400,
    )

    with pytest.raises(ValidationError, match="contiguous"):
        _plan(first, second)
