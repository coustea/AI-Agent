"""Build a narration-synchronized HyperFrames composition plan."""

from __future__ import annotations

from app.shared.cartoon.schemas import (
    AudioSynthesis,
    CompositionPlan,
    TeachingAction,
    TeachingLesson,
    TimedAction,
    TimedPatch,
    TimedScene,
    TimedStep,
)


_PACE = {
    "calm": {"lead": 360, "gap": 190, "tail": 520, "reinforce_gap": 2400},
    "balanced": {"lead": 260, "gap": 130, "tail": 390, "reinforce_gap": 1950},
    "fast": {"lead": 180, "gap": 90, "tail": 280, "reinforce_gap": 1550},
}

_DENSITY_REINFORCEMENTS = {
    "moderate": 0,
    "rich": 2,
    "intensive": 4,
}


def _scale_action_durations(actions: list[TeachingAction], available_ms: int, gap_ms: int) -> list[int]:
    raw = [action.duration_ms for action in actions]
    raw_total = sum(raw) + gap_ms * max(0, len(raw) - 1)
    if raw_total <= 0:
        return [500 for _ in actions]

    # Do not make a single semantic action excessively slow. Rich motion is produced
    # by the compiler/runtime preset inside this duration.
    scale = min(1.55, max(0.72, available_ms / raw_total))
    return [max(180, min(4000, round(duration * scale))) for duration in raw]


def _reinforcement_action(step, index: int) -> TeachingAction:
    targets = list(step.focus_ids)
    if not targets:
        for action in reversed(step.actions):
            targets = list(action.target_ids)
            if targets:
                break
    if not targets:
        last = step.actions[-1]
        targets = [item for item in (last.destination_id, last.source_id) if item]

    return TeachingAction(
        kind="highlight" if index % 2 == 0 else "focus",
        target_ids=targets[:3],
        note="旁白同步强化",
        duration_ms=520 if index % 2 == 0 else 620,
        intensity="subtle",
    )


def _schedule_step(
    *,
    scene_id: str,
    step,
    audio: AudioSynthesis,
    absolute_start_ms: int,
    pace: str,
    visual_density: str,
    allocated_duration_ms: int,
) -> TimedStep:
    settings = _PACE.get(pace, _PACE["balanced"])
    lead_ms = settings["lead"]
    gap_ms = settings["gap"]
    tail_ms = settings["tail"]
    reinforce_gap = settings["reinforce_gap"]

    minimum_action_window = sum(action.duration_ms for action in step.actions) + gap_ms * max(0, len(step.actions) - 1)
    available_ms = max(
        minimum_action_window,
        allocated_duration_ms - lead_ms - tail_ms,
        audio.duration_ms - lead_ms - tail_ms,
    )
    durations = _scale_action_durations(step.actions, available_ms, gap_ms)

    timed_actions: list[TimedAction] = []
    cursor = absolute_start_ms + lead_ms
    for index, (action, duration_ms) in enumerate(zip(step.actions, durations, strict=True)):
        timed_actions.append(
            TimedAction(
                action_index=index,
                action=action,
                start_ms=cursor,
                duration_ms=duration_ms,
            )
        )
        cursor += duration_ms + gap_ms

    # State changes must happen after the semantic actions, not at the beginning
    # of the narration. Small spacing keeps multiple patches deterministic.
    patch_start = max(absolute_start_ms + lead_ms, cursor - gap_ms + 60)
    timed_patches = [
        TimedPatch(
            patch_index=index,
            patch=patch,
            start_ms=patch_start + index * 45,
        )
        for index, patch in enumerate(step.patches)
    ]
    cursor = max(cursor, patch_start + len(timed_patches) * 45 + 120)

    # If narration continues after the principal mechanism has completed, insert
    # restrained focus/highlight cues. This prevents long static stretches without
    # asking the model to emit low-level animation instructions.
    audio_visual_end = absolute_start_ms + audio.duration_ms - tail_ms
    maximum_reinforcements = _DENSITY_REINFORCEMENTS.get(visual_density, 2)
    reinforcement_index = 0
    next_reinforcement = cursor + reinforce_gap
    while reinforcement_index < maximum_reinforcements and next_reinforcement < audio_visual_end:
        action = _reinforcement_action(step, reinforcement_index)
        timed_actions.append(
            TimedAction(
                action_index=len(step.actions) + reinforcement_index,
                action=action,
                start_ms=next_reinforcement,
                duration_ms=action.duration_ms,
                synthetic=True,
            )
        )
        cursor = max(cursor, next_reinforcement + action.duration_ms)
        reinforcement_index += 1
        next_reinforcement += reinforce_gap

    visual_end = max(
        cursor,
        max((patch.start_ms for patch in timed_patches), default=absolute_start_ms) + 120,
    )
    # A target duration is a production contract.  The step remains on screen
    # long enough for its voice-over, but is never shortened below its allocated
    # teaching time; the extra time is used for the mechanism to settle.
    step_end = max(
        absolute_start_ms + allocated_duration_ms,
        absolute_start_ms + audio.duration_ms,
        visual_end + tail_ms,
    )

    return TimedStep(
        scene_id=scene_id,
        step=step,
        start_ms=absolute_start_ms,
        duration_ms=step_end - absolute_start_ms,
        audio_src=audio.path.as_posix(),
        audio_duration_ms=audio.duration_ms,
        actions=timed_actions,
        patches=timed_patches,
    )


def build_composition_plan(
    lesson: TeachingLesson,
    syntheses: dict[str, AudioSynthesis],
    *,
    pace: str = "balanced",
    visual_density: str = "rich",
    target_duration_seconds: int = 90,
    transition_ms: int = 760,
) -> CompositionPlan:
    if not 90 <= target_duration_seconds <= 600:
        raise ValueError("target_duration_seconds must be between 90 and 600")

    scene_count = len(lesson.scenes)
    transition_total = transition_ms * max(0, scene_count - 1)
    target_content_ms = max(scene_count * 2_400, target_duration_seconds * 1000 - transition_total)
    steps = [step for scene in lesson.scenes for step in scene.steps]
    if not steps:
        raise ValueError("lesson must contain timed steps")
    # Longer process steps get a little more viewing time than orientation or
    # conclusion steps.  This makes pacing follow the mechanism, not file order.
    weights = [max(1, len(step.actions)) for step in steps]
    weight_total = sum(weights)
    minimum_step_ms = max(1_500, round(target_content_ms / len(steps) * 0.62))
    allocated_by_key: dict[str, int] = {}
    remaining = target_content_ms
    weighted_steps = [
        (scene, step, max(1, len(step.actions)))
        for scene in lesson.scenes
        for step in scene.steps
    ]
    for index, (scene, step, weight) in enumerate(weighted_steps):
        key = f"{scene.id}:{step.id}"
        if index == len(steps) - 1:
            allocated = remaining
        else:
            allocated = max(minimum_step_ms, round(target_content_ms * weight / weight_total))
            remaining -= allocated
        allocated_by_key[key] = allocated

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

            timed = _schedule_step(
                scene_id=scene.id,
                step=step,
                audio=audio,
                absolute_start_ms=cursor,
                pace=pace,
                visual_density=visual_density,
                allocated_duration_ms=allocated_by_key[key],
            )
            timed_steps.append(timed)
            cursor += timed.duration_ms

        if index < scene_count - 1:
            cursor += transition_ms
        scenes.append(
            TimedScene(
                index=index,
                scene=scene,
                start_ms=scene_start,
                duration_ms=cursor - scene_start,
                steps=timed_steps,
            )
        )

    return CompositionPlan(total_duration_ms=cursor, scenes=scenes)
