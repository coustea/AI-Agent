"""Create scene recipes and turn narration into a HyperFrames timeline."""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from langchain_core.messages import HumanMessage, SystemMessage

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.shared.cartoon.schemas import (
    AudioSynthesis,
    CartoonBrief,
    CartoonStoryboard,
    CompositionPlan,
    StoryboardScene,
    TeachingLesson,
    TeachingScene,
    TeachingStep,
    TimedMotion,
    TimedScene,
    TimedStep,
    connected_visual_kind_values,
    layout_guidance,
    layout_kind_values,
    motion_values,
    role_values,
    visual_kind_values,
)


logger = get_logger(__name__)


_PROMPT_VARIABLE = re.compile(r"\{\{(?P<name>[a-z_][a-z0-9_]*)\}\}")


class CartoonPlanningError(RuntimeError):
    pass


@dataclass(frozen=True)
class PromptDocument:
    """A checked prompt asset with a private, JSON-safe variable syntax.

    Prompt assets are teaching documents: they can include JSON, code, formulas,
    and learner-provided material.  They must never be interpreted as Python
    format strings.  Only ``{{lowercase_name}}`` is executable template syntax.
    """

    name: str
    content: str
    variables: frozenset[str]

    @classmethod
    def load(cls, path: Path) -> PromptDocument:
        content = path.read_text(encoding="utf-8")
        variables = frozenset(match.group("name") for match in _PROMPT_VARIABLE.finditer(content))
        remaining_delimiters = _PROMPT_VARIABLE.sub("", content)
        if "{{" in remaining_delimiters or "}}" in remaining_delimiters:
            raise CartoonPlanningError(f"提示词 {path.name} 包含未闭合的模板变量")
        return cls(name=path.name, content=content, variables=variables)

    def render(self, values: Mapping[str, object]) -> str:
        provided = frozenset(values)
        missing = self.variables - provided
        unexpected = provided - self.variables
        if missing:
            raise CartoonPlanningError(f"提示词 {self.name} 缺少变量: {', '.join(sorted(missing))}")
        if unexpected:
            raise CartoonPlanningError(f"提示词 {self.name} 收到未声明变量: {', '.join(sorted(unexpected))}")
        return _PROMPT_VARIABLE.sub(lambda match: str(values[match.group("name")]), self.content)


class CartoonLessonPlanner:
    def __init__(self, *, max_parallel_composers: int = 3) -> None:
        self._parallelism = max(1, max_parallel_composers)
        prompt_dir = Path(__file__).parent
        self._prompts = {
            name: PromptDocument.load(prompt_dir / name)
            for name in ("storyboard.md", "scene_compose.md")
        }

    async def plan(self, brief: CartoonBrief) -> TeachingLesson:
        try:
            started_at = time.perf_counter()
            storyboard = await self._create_storyboard(brief)
            logger.info(
                "[CartoonPlanner] storyboard complete: scenes=%d elapsed_ms=%d",
                len(storyboard.scenes),
                round((time.perf_counter() - started_at) * 1000),
            )
            semaphore = asyncio.Semaphore(self._parallelism)
            # A failed scene invalidates the lesson. TaskGroup cancels the
            # outstanding model calls instead of leaving them running after
            # the request has already failed.
            async with asyncio.TaskGroup() as task_group:
                scene_tasks = [
                    task_group.create_task(self._compose_scene(brief, storyboard, scene, semaphore))
                    for scene in storyboard.scenes
                ]
            scenes = [task.result() for task in scene_tasks]
            return TeachingLesson(title=storyboard.title, course=storyboard.course, scenes=scenes)
        except Exception as exc:
            details = self._exception_details(exc)
            raise CartoonPlanningError(
                "无法生成可渲染的动画教学分镜: " + " | ".join(details)
            ) from exc

    async def _create_storyboard(self, brief: CartoonBrief) -> CartoonStoryboard:
        prompt = self._prompts["storyboard.md"].render({
            "density": brief.configuration.visual_density,
            "layout_guidance": layout_guidance(),
            "layouts": layout_kind_values(),
            "visual_kinds": visual_kind_values(),
            "connected_visual_kinds": connected_visual_kind_values(),
            "source": self._source(brief, 12000),
        })
        response = await self._invoke_json(
            CartoonStoryboard,
            [SystemMessage(content=prompt), HumanMessage(content="根据素材生成整套动画分镜。")],
            temperature=0.22,
            max_tokens=2200,
            operation="storyboard",
        )
        return response if isinstance(response, CartoonStoryboard) else CartoonStoryboard.model_validate(response)

    async def _compose_scene(self, brief: CartoonBrief, storyboard: CartoonStoryboard, scene: StoryboardScene, semaphore: asyncio.Semaphore) -> TeachingScene:
        started_at = time.perf_counter()
        completed = False
        try:
            async with semaphore:
                prompt = self._prompts["scene_compose.md"].render({
                    "scene": scene.model_dump_json(),
                    "course": storyboard.course,
                    "motions": motion_values(),
                    "roles": role_values(),
                    "connected_visual_kinds": connected_visual_kind_values(),
                    "density": brief.configuration.visual_density,
                    "source": self._source(brief, 9000),
                })
                response = await self._invoke_json(
                    TeachingScene,
                    [SystemMessage(content=prompt), HumanMessage(content="只生成这个场景的 JSON。")],
                    temperature=0.28,
                    max_tokens=2400,
                    operation=f"scene:{scene.id}",
                )
                result = response if isinstance(response, TeachingScene) else TeachingScene.model_validate(response)
                if (
                    result.id != scene.id
                    or result.layout != scene.layout
                    or result.visual.kind != scene.visual_kind
                    or result.teaching_function != scene.teaching_function
                ):
                    raise CartoonPlanningError(f"场景 {scene.id} 未遵守全局分镜契约")
                completed = True
                return result
        finally:
            logger.info(
                "[CartoonPlanner] scene %s: scene_id=%s elapsed_ms=%d",
                "complete" if completed else "failed",
                scene.id,
                round((time.perf_counter() - started_at) * 1000),
            )

    @staticmethod
    def _source(brief: CartoonBrief, limit: int) -> str:
        sections = [
            f"学习主题：{brief.learning_need}",
            "教学上下文：" + json.dumps(brief.instruction_context, ensure_ascii=False, separators=(",", ":")),
            "知识点：" + "、".join(brief.knowledge_points),
            "薄弱点：" + "、".join(brief.weak_knowledge_points),
            *brief.source_materials,
        ]
        result: list[str] = []
        used = 0
        for section in sections:
            text = section.strip()
            if not text or used >= limit:
                continue
            available = limit - used
            result.append(text[:available])
            used += len(result[-1]) + 2
        return "\n\n".join(result)

    @staticmethod
    def _is_transient_error(exc: Exception) -> bool:
        if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
            return True
        message = str(exc).lower()
        return any(marker in message for marker in ("timeout", "timed out", "connection", "temporarily unavailable", "rate limit", "429", "502", "503", "504"))

    async def _invoke_json(
        self,
        schema: type[Any],
        messages: list[SystemMessage | HumanMessage],
        *,
        temperature: float,
        max_tokens: int,
        operation: str,
    ) -> Any:
        for attempt in range(1, 3):
            try:
                return await get_llm().ainvoke_json(
                    schema,
                    messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except Exception as exc:
                if not self._is_transient_error(exc) or attempt == 2:
                    raise
                delay_seconds = 0.6 * attempt
                logger.warning(
                    "[CartoonPlanner] transient LLM failure: operation=%s attempt=%d/2 retry_in=%.1fs error=%s",
                    operation,
                    attempt,
                    delay_seconds,
                    exc,
                )
                await asyncio.sleep(delay_seconds)
        raise RuntimeError("unreachable")

    @staticmethod
    def _exception_details(exc: BaseException) -> list[str]:
        if isinstance(exc, BaseExceptionGroup):
            details = [detail for nested in exc.exceptions for detail in CartoonLessonPlanner._exception_details(nested)]
            return details[:6] or [type(exc).__name__]
        message = str(exc).strip() or type(exc).__name__
        return [f"{type(exc).__name__}: {message}"]


_PACE = {
    "calm": {"lead": 420, "gap": 180, "tail": 620},
    "balanced": {"lead": 300, "gap": 120, "tail": 420},
    "fast": {"lead": 200, "gap": 90, "tail": 300},
}


def _timed_step(
    scene_id: str,
    step: TeachingStep,
    audio: AudioSynthesis,
    start_ms: int,
    allocated_ms: int,
    pace: str,
) -> TimedStep:
    rhythm = _PACE[pace]
    available = max(audio.duration_ms, allocated_ms) - rhythm["lead"] - rhythm["tail"]
    raw_total = sum(motion.duration_ms for motion in step.motions)
    scale = min(1.45, max(0.7, available / max(1, raw_total)))
    cursor = start_ms + rhythm["lead"]
    motions: list[TimedMotion] = []
    for motion in step.motions:
        duration = max(180, round(motion.duration_ms * scale))
        motions.append(TimedMotion(motion=motion, start_ms=cursor, duration_ms=duration))
        cursor += duration + rhythm["gap"]
    end_ms = max(start_ms + allocated_ms, start_ms + audio.duration_ms, cursor - rhythm["gap"] + rhythm["tail"])
    return TimedStep(scene_id=scene_id, step=step, start_ms=start_ms, duration_ms=end_ms - start_ms, audio_src=audio.path.as_posix(), audio_duration_ms=audio.duration_ms, motions=motions)


def build_composition_plan(
    lesson: TeachingLesson,
    syntheses: dict[str, AudioSynthesis],
    *,
    pace: str = "balanced",
    target_duration_seconds: int = 90,
    transition_ms: int = 680,
) -> CompositionPlan:
    """Allocate scene timing from narration before the HTML composition is built."""
    if pace not in _PACE:
        raise ValueError(f"unknown pace: {pace}")
    if not 90 <= target_duration_seconds <= 600:
        raise ValueError("target_duration_seconds must be between 90 and 600")
    all_steps = [(scene, step) for scene in lesson.scenes for step in scene.steps]
    target_content_ms = target_duration_seconds * 1000 - transition_ms * (len(lesson.scenes) - 1)
    allocated_ms = max(2400, target_content_ms // len(all_steps))
    cursor = 0
    scenes: list[TimedScene] = []
    for index, scene in enumerate(lesson.scenes):
        scene_start = cursor
        timed_steps: list[TimedStep] = []
        for step in scene.steps:
            key = f"{scene.id}:{step.id}"
            audio = syntheses.get(key)
            if audio is None:
                raise ValueError(f"missing TTS synthesis for {key}")
            timed = _timed_step(scene.id, step, audio, cursor, allocated_ms, pace)
            timed_steps.append(timed)
            cursor += timed.duration_ms
        if index < len(lesson.scenes) - 1:
            cursor += transition_ms
        scenes.append(TimedScene(index=index, scene=scene, start_ms=scene_start, duration_ms=cursor - scene_start, steps=timed_steps))
    return CompositionPlan(total_duration_ms=cursor, scenes=scenes)
