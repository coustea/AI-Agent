"""Build a step-synchronized HyperFrames composition plan."""

from __future__ import annotations

from pathlib import Path

from app.shared.cartoon.schemas import AudioSynthesis, CompositionPlan, TeachingLesson, TimedScene, TimedStep


def build_composition_plan(lesson: TeachingLesson, syntheses: dict[str, AudioSynthesis], *, transition_ms: int = 420) -> CompositionPlan:
    scenes: list[TimedScene] = []
    cursor = 0
    for index, scene in enumerate(lesson.scenes):
        timed_steps: list[TimedStep] = []
        scene_start = cursor
        for step in scene.steps:
            key = f"{scene.id}:{step.id}"
            audio = syntheses.get(key)
            if audio is None:
                raise ValueError(f"missing TTS synthesis for {key}")
            duration = max(audio.duration_ms, max(action.duration_ms for action in step.actions) + 260)
            timed_steps.append(TimedStep(scene_id=scene.id, step=step, start_ms=cursor, duration_ms=duration, audio_src=audio.path.as_posix(), audio_duration_ms=audio.duration_ms))
            cursor += duration
        cursor += transition_ms
        scenes.append(TimedScene(index=index, scene=scene, start_ms=scene_start, duration_ms=cursor - scene_start, steps=timed_steps))
    return CompositionPlan(total_duration_ms=cursor, scenes=scenes)
