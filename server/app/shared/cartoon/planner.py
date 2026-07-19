"""Plan teaching videos as replayable semantic scenes, never card layouts."""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.shared.cartoon.execution import (
    SemanticCompiler,
    SemanticSceneDraft,
)
from app.shared.cartoon.models import (
    CartoonBrief,
    Lesson,
    LessonDepth,
    SceneMode,
    SceneTopology,
    TeachingScene,
)


logger = get_logger(__name__)
_PROMPT_VARIABLE = re.compile(r"\{\{(?P<name>[a-z_][a-z0-9_]*)\}\}")
_PROMPT_DIR = Path(__file__).parent
_ACTIONS_PER_STEP_GUIDANCE = 2
_TOTAL_NARRATION_GUIDANCE_CHARS = 720
_DEFAULT_TARGET_DURATION_SECONDS = 180


class CartoonPlanningError(RuntimeError):
    pass


@dataclass(frozen=True)
class _PlanningBudget:
    """Soft prompt guidance derived from lesson intent, never a JSON cutoff."""

    scene_guidance: int
    step_guidance: int
    actions_per_step_guidance: int
    total_narration_guidance_chars: int

    @classmethod
    def for_brief(cls, brief: CartoonBrief) -> "_PlanningBudget":
        base_scenes, base_steps = {
            LessonDepth.FOCUSED: (3, 3),
            LessonDepth.STANDARD: (4, 4),
            LessonDepth.DEEP: (5, 5),
        }[brief.configuration.lesson_depth]
        duration_scale = brief.configuration.target_duration_seconds / _DEFAULT_TARGET_DURATION_SECONDS
        return cls(
            scene_guidance=max(1, round(base_scenes * duration_scale)),
            step_guidance=max(2, round(base_steps * duration_scale)),
            actions_per_step_guidance=_ACTIONS_PER_STEP_GUIDANCE,
            total_narration_guidance_chars=max(1, round(_TOTAL_NARRATION_GUIDANCE_CHARS * duration_scale)),
        )


@dataclass(frozen=True)
class _PromptDocument:
    name: str
    content: str
    variables: frozenset[str]

    @classmethod
    def load(cls, path: Path) -> "_PromptDocument":
        content = path.read_text(encoding="utf-8")
        variables = frozenset(match.group("name") for match in _PROMPT_VARIABLE.finditer(content))
        if "{{" in _PROMPT_VARIABLE.sub("", content) or "}}" in _PROMPT_VARIABLE.sub("", content):
            raise CartoonPlanningError(f"提示词 {path.name} 包含未闭合变量")
        return cls(path.name, content, variables)

    def render(self, values: Mapping[str, object]) -> str:
        if frozenset(values) != self.variables:
            raise CartoonPlanningError(
                f"提示词 {self.name} 变量不一致: "
                f"missing={sorted(self.variables - frozenset(values))} "
                f"unexpected={sorted(frozenset(values) - self.variables)}"
            )
        return _PROMPT_VARIABLE.sub(lambda match: str(values[match.group("name")]), self.content)


class _Draft(BaseModel):
    model_config = ConfigDict(extra="ignore")


class _LessonOutlineScene(_Draft):
    title: str = ""
    teaching_goal: str = ""
    material_focus: str = Field(default="", max_length=160)
    mode: SceneMode | str = SceneMode.CONCEPT
    topology: SceneTopology | str = SceneTopology.SPATIAL

    @field_validator("title", "teaching_goal", "material_focus", mode="before")
    @classmethod
    def normalize_text(cls, value: Any) -> str:
        return str(value or "").strip()


class _LessonOutline(_Draft):
    title: str = ""
    scenes: list[_LessonOutlineScene] = Field(default_factory=list)

    @field_validator("title", mode="before")
    @classmethod
    def normalize_title(cls, value: Any) -> str:
        return str(value or "").strip()

    @field_validator("scenes", mode="before")
    @classmethod
    def normalize_scenes(cls, value: Any) -> Any:
        if value is None:
            return []
        return [value] if isinstance(value, dict) else value

def _scene_example_steps() -> str:
    examples = [
        {
            "narration": "任务 A 进入输入容器，因此处理流程获得了可观察的待处理状态。",
            "actions": [
                {"verb": "place", "subject": "tokenA", "target": "source", "slot": 0}
            ],
        },
        {
            "narration": "处理开始后，任务 A 的可见值随状态推进而更新。",
            "actions": [
                {"verb": "update", "subject": "tokenA", "value": "处理中"}
            ],
        },
        {
            "narration": "处理完成后，任务 A 离开输入容器并移动到输出区域。",
            "actions": [
                {"verb": "move", "subject": "tokenA", "region": "output"}
            ],
        },
    ]
    return json.dumps(examples, ensure_ascii=False, indent=2)


_SCENE_BLUEPRINTS: tuple[tuple[SceneMode, SceneTopology, str, str], ...] = (
    (SceneMode.CONCEPT, SceneTopology.SPATIAL, "核心概念", "建立关键对象、术语和成立条件。"),
    (SceneMode.MECHANISM, SceneTopology.NETWORK, "组成机制", "展示组成部分、边界和协作关系。"),
    (SceneMode.EXECUTION, SceneTopology.FLOW, "状态过程", "通过连续状态变化解释工作过程。"),
    (SceneMode.COMPARISON, SceneTopology.GRID, "判断与差异", "比较条件、结果或策略并明确选择依据。"),
    (SceneMode.EVIDENCE, SceneTopology.SEQUENCE, "结论验证", "用可观察结果验证结论并说明迁移方法。"),
)


class CartoonPlanner:
    """Generate renderer-neutral scene programs and compile all of them alike."""

    def __init__(self, *, max_parallel_scenes: int = 3) -> None:
        self._parallelism = max(1, max_parallel_scenes)
        self.last_timing: dict[str, int] = {}
        self._prompts = {
            name: _PromptDocument.load(_PROMPT_DIR / name)
            for name in ("scene_compose.md",)
        }

    async def plan(self, brief: CartoonBrief) -> Lesson:
        try:
            started = asyncio.get_running_loop().time()
            budget = _PlanningBudget.for_brief(brief)
            outline_started = started
            outline = self._create_outline(brief, budget)
            outline_ms = round((asyncio.get_running_loop().time() - outline_started) * 1000)
            scene_count = len(outline.scenes)
            semaphore = asyncio.Semaphore(self._parallelism)
            scenes_started = asyncio.get_running_loop().time()
            async with asyncio.TaskGroup() as group:
                tasks = [
                    group.create_task(
                        self._compose_scene(
                            brief,
                            outline,
                            budget,
                            scene_outline,
                            index,
                            scene_count,
                            semaphore,
                        )
                    )
                    for index, scene_outline in enumerate(outline.scenes, start=1)
                ]
            scenes = [task.result() for task in tasks]
            scene_compose_ms = round((asyncio.get_running_loop().time() - scenes_started) * 1000)
            lesson = Lesson(title=outline.title, scenes=scenes)
            self.last_timing = {
                "outline_ms": outline_ms,
                "scene_compose_wall_ms": scene_compose_ms,
                "total_ms": round((asyncio.get_running_loop().time() - started) * 1000),
                "scene_count": scene_count,
                "parallelism": self._parallelism,
                "scene_guidance": budget.scene_guidance,
                "step_guidance": budget.step_guidance,
            }
            logger.info(
                "[CartoonPlanner] 规划完成: title=%s scenes=%d beats=%d modes=%s timings=%s",
                lesson.title, len(scenes), sum(len(scene.program.beats) for scene in scenes),
                sorted({scene.mode.value for scene in scenes}),
                self.last_timing,
            )
            return lesson
        except Exception as exc:
            if isinstance(exc, CartoonPlanningError):
                raise
            details = self._exception_details(exc)
            logger.error("[CartoonPlanner] 规划失败: %s", " | ".join(details))
            raise CartoonPlanningError("无法生成可渲染的语义动画分镜: " + " | ".join(details)) from exc

    @staticmethod
    def _create_outline(
        brief: CartoonBrief,
        budget: _PlanningBudget,
    ) -> _LessonOutline:
        """Compile a stable JSON outline locally; only scene semantics need an LLM."""

        topics = CartoonPlanner._outline_topics(brief)
        scenes = []
        for index in range(budget.scene_guidance):
            mode, topology, role, goal = _SCENE_BLUEPRINTS[index % len(_SCENE_BLUEPRINTS)]
            topic = topics[index % len(topics)]
            scenes.append(
                _LessonOutlineScene(
                    title=f"{topic}：{role}",
                    teaching_goal=f"围绕“{topic}”{goal}",
                    material_focus=topic,
                    mode=mode,
                    topology=topology,
                )
            )
        return _LessonOutline(
            title=CartoonPlanner._lesson_title(brief),
            scenes=scenes,
        )

    @staticmethod
    def _outline_topics(brief: CartoonBrief) -> list[str]:
        candidates = [*brief.knowledge_points, *brief.weak_knowledge_points, brief.learning_need]
        topics: list[str] = []
        seen: set[str] = set()
        for value in candidates:
            normalized = " ".join(str(value).split()).strip("。！？!?：:；;")
            if not normalized:
                continue
            key = normalized.casefold()
            if key not in seen:
                seen.add(key)
                topics.append(normalized[:80])
        return topics or ["核心概念"]

    @staticmethod
    def _lesson_title(brief: CartoonBrief) -> str:
        title = " ".join(brief.learning_need.split()).strip("。！？!?：:；;")
        return title[:80] or "动画讲解"

    async def _compose_scene(
        self,
        brief: CartoonBrief,
        lesson_outline: _LessonOutline,
        budget: _PlanningBudget,
        outline: _LessonOutlineScene,
        scene_index: int,
        scene_count: int,
        semaphore: asyncio.Semaphore,
    ) -> TeachingScene:
        started = asyncio.get_running_loop().time()
        mode = self._scene_mode(outline.mode)
        topology = self._scene_topology(outline.topology)
        prompt = self._prompts["scene_compose.md"].render({
            "mode": mode.value,
            "topology": topology.value,
            "density": brief.configuration.visual_density,
            "example_steps": _scene_example_steps(),
            "scene_count": scene_count,
            "step_guidance": budget.step_guidance,
            "actions_per_step_guidance": budget.actions_per_step_guidance,
            "narration_guidance_chars": self._scene_narration_guidance(
                scene_count,
                budget.total_narration_guidance_chars,
            ),
            "target_duration_seconds": brief.configuration.target_duration_seconds,
        })
        context = {
            "lesson_title": lesson_outline.title,
            "scene_title": outline.title,
            "teaching_goal": outline.teaching_goal,
            "mode": mode.value,
            "topology": topology.value,
        }
        async with semaphore:
            response = await get_llm().ainvoke_json(
                SemanticSceneDraft,
                [SystemMessage(content=prompt), self._scene_material_message(brief, outline, task="只生成当前场景的对象与可播放状态操作", limit=2_500, context=context)],
                temperature=0.12,
                validator=self._validate_scene_draft,
                include_schema_example=False,
            )
        if not isinstance(response, SemanticSceneDraft):
            raise TypeError("scene payload did not validate as SemanticSceneDraft")
        response = response.model_copy(update={"mode": mode, "topology": topology})
        scene = SemanticCompiler.compile(
            response,
            scene_id=f"scene-{scene_index:02d}",
            title=outline.title.strip() or f"场景 {scene_index}",
        )
        logger.info(
            "[CartoonPlanner] 场景完成: index=%d/%d mode=%s beats=%d elapsed_ms=%d",
            scene_index,
            scene_count,
            mode.value,
            len(scene.program.beats),
            round((asyncio.get_running_loop().time() - started) * 1000),
        )
        return scene

    @staticmethod
    def _scene_mode(value: SceneMode | str) -> SceneMode:
        try:
            return SceneMode(value)
        except (TypeError, ValueError):
            return SceneMode.CONCEPT

    @staticmethod
    def _scene_topology(value: SceneTopology | str) -> SceneTopology:
        try:
            return SceneTopology(value)
        except (TypeError, ValueError):
            return SceneTopology.SPATIAL

    @staticmethod
    def _validate_scene_draft(value: BaseModel) -> None:
        if not isinstance(value, SemanticSceneDraft):
            raise ValueError("scene payload must validate as SemanticSceneDraft")
        # The local outline is guidance only.  The compiler owns the final scene
        # mode/topology and the payload is accepted even when the model drifts.
        SemanticCompiler.compile(value, scene_id="validation-scene", title="validation scene")

    @staticmethod
    def _scene_narration_guidance(
        scene_count: int,
        total_narration_guidance_chars: int = _TOTAL_NARRATION_GUIDANCE_CHARS,
    ) -> int:
        return max(1, total_narration_guidance_chars // max(1, scene_count))

    def _scene_material_message(
        self,
        brief: CartoonBrief,
        outline: _LessonOutlineScene,
        *,
        task: str,
        limit: int,
        context: dict[str, str],
    ) -> HumanMessage:
        material = self._focused_teaching_material(brief, outline)
        payload = {
            "task": task,
            "context": {**context, "material_focus": outline.material_focus},
            "teaching_material": material,
        }
        content = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        while len(content) > limit and payload["teaching_material"]:
            overflow = len(content) - limit
            payload["teaching_material"] = payload["teaching_material"][:-overflow]
            content = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        if len(content) > limit:
            raise CartoonPlanningError("场景上下文超过提示词预算")
        return HumanMessage(content=content)

    @staticmethod
    def _focused_teaching_material(
        brief: CartoonBrief,
        outline: _LessonOutlineScene,
    ) -> str:
        """Give each scene relevant source excerpts instead of the full lesson."""

        focus = " ".join((outline.title, outline.teaching_goal, outline.material_focus))
        terms = {
            value.lower()
            for value in re.findall(r"[A-Za-z0-9_]{2,}|[\u4e00-\u9fff]{2,6}", focus)
        }
        chunks: list[tuple[int, str]] = []
        for source_index, source in enumerate(brief.source_materials):
            for chunk_index, chunk in enumerate(re.split(r"\n{2,}|(?<=[。！？.!?])", source)):
                normalized = " ".join(chunk.split())
                if normalized:
                    chunks.append((source_index * 10_000 + chunk_index, normalized))

        ranked = sorted(
            chunks,
            key=lambda item: (
                -sum(term in item[1].lower() for term in terms),
                item[0],
            ),
        )
        selected = [chunk for _, chunk in ranked[:6]]
        base = [
            f"学习主题：{brief.learning_need}",
            "知识点：" + "、".join(brief.knowledge_points),
            "本幕焦点：" + focus,
            *selected,
        ]
        return "\n\n".join(value.strip() for value in base if value.strip())

    @staticmethod
    def _exception_details(exc: BaseException) -> list[str]:
        if isinstance(exc, BaseExceptionGroup):
            return [detail for child in exc.exceptions for detail in CartoonPlanner._exception_details(child)]
        return [str(exc) or type(exc).__name__]
