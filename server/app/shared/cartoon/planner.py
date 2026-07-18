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


class CartoonPlanningError(RuntimeError):
    pass


def _depth_label(brief: CartoonBrief) -> str:
    return {
        LessonDepth.FOCUSED: "聚焦讲解",
        LessonDepth.STANDARD: "标准讲解",
        LessonDepth.DEEP: "深入讲解",
    }[brief.configuration.lesson_depth]


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


class _StoryboardSceneDraft(_Draft):
    title: str = ""
    teaching_goal: str = ""
    mode: SceneMode | str = SceneMode.CONCEPT
    topology: SceneTopology | str = SceneTopology.SPATIAL

    @field_validator("title", "teaching_goal", mode="before")
    @classmethod
    def normalize_text(cls, value: Any) -> str:
        return str(value or "").strip()


class _StoryboardDraft(_Draft):
    title: str = ""
    scenes: list[_StoryboardSceneDraft] = Field(default_factory=list)

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


def _storyboard_example_scenes() -> str:
    examples = [
        {
            "title": "核心问题与判断条件",
            "teaching_goal": "用对象和值建立本课核心问题及成立条件。",
            "mode": "concept",
            "topology": "spatial",
        },
        {
            "title": "组成结构与协作关系",
            "teaching_goal": "展示关键部件、边界和连接关系。",
            "mode": "mechanism",
            "topology": "network",
        },
        {
            "title": "状态推进过程",
            "teaching_goal": "播放同一批对象随操作发生的状态变化。",
            "mode": "execution",
            "topology": "flow",
        },
        {
            "title": "方案差异与适用条件",
            "teaching_goal": "比较两种状态或策略并明确选择依据。",
            "mode": "comparison",
            "topology": "grid",
        },
        {
            "title": "结论验证与迁移方法",
            "teaching_goal": "用可观察结果验证结论并形成判断方法。",
            "mode": "evidence",
            "topology": "sequence",
        },
    ]
    return json.dumps(examples, ensure_ascii=False, indent=2)


class CartoonPlanner:
    """Generate renderer-neutral scene programs and compile all of them alike."""

    def __init__(self, *, max_parallel_scenes: int = 3) -> None:
        self._parallelism = max(1, max_parallel_scenes)
        self._prompts = {
            name: _PromptDocument.load(_PROMPT_DIR / name)
            for name in ("storyboard.md", "scene_compose.md")
        }

    async def plan(self, brief: CartoonBrief) -> Lesson:
        try:
            storyboard = await self._create_storyboard(brief)
            semaphore = asyncio.Semaphore(self._parallelism)
            async with asyncio.TaskGroup() as group:
                tasks = [
                    group.create_task(self._compose_scene(brief, storyboard, outline, index, semaphore))
                    for index, outline in enumerate(storyboard.scenes, start=1)
                ]
            scenes = [task.result() for task in tasks]
            lesson = Lesson(title=storyboard.title, scenes=scenes)
            logger.info(
                "[CartoonPlanner] 规划完成: title=%s scenes=%d beats=%d modes=%s",
                lesson.title, len(scenes), sum(len(scene.program.beats) for scene in scenes),
                sorted({scene.mode.value for scene in scenes}),
            )
            return lesson
        except Exception as exc:
            if isinstance(exc, CartoonPlanningError):
                raise
            details = self._exception_details(exc)
            logger.error("[CartoonPlanner] 规划失败: %s", " | ".join(details))
            raise CartoonPlanningError("无法生成可渲染的语义动画分镜: " + " | ".join(details)) from exc

    async def _create_storyboard(self, brief: CartoonBrief) -> _StoryboardDraft:
        prompt = self._prompts["storyboard.md"].render({
            "lesson_depth": _depth_label(brief),
            "density": brief.configuration.visual_density,
            "example_scenes": _storyboard_example_scenes(),
        })
        response = await get_llm().ainvoke_json(
            _StoryboardDraft,
            [SystemMessage(content=prompt), self._material_message(brief, task="规划整套动画的教学推进顺序", limit=8_000)],
            temperature=0.1,
            include_schema_example=False,
        )
        if not isinstance(response, _StoryboardDraft):
            raise TypeError("storyboard payload did not validate as _StoryboardDraft")
        if not response.title.strip():
            response = response.model_copy(update={"title": brief.learning_need.strip() or "动画讲解"})
        if not response.scenes:
            response = response.model_copy(
                update={
                    "scenes": [
                        _StoryboardSceneDraft(
                            title="核心概念",
                            teaching_goal="展示学习主题的关键对象和基本关系。",
                        )
                    ]
                }
            )
        return response

    async def _compose_scene(
        self,
        brief: CartoonBrief,
        storyboard: _StoryboardDraft,
        outline: _StoryboardSceneDraft,
        scene_index: int,
        semaphore: asyncio.Semaphore,
    ) -> TeachingScene:
        mode = self._scene_mode(outline.mode)
        topology = self._scene_topology(outline.topology)
        prompt = self._prompts["scene_compose.md"].render({
            "mode": mode.value,
            "topology": topology.value,
            "density": brief.configuration.visual_density,
            "example_steps": _scene_example_steps(),
        })
        context = {
            "lesson_title": storyboard.title,
            "scene_title": outline.title,
            "teaching_goal": outline.teaching_goal,
            "mode": mode.value,
            "topology": topology.value,
        }
        async with semaphore:
            response = await get_llm().ainvoke_json(
                SemanticSceneDraft,
                [SystemMessage(content=prompt), self._material_message(brief, task="只生成当前场景的对象与可播放状态操作", limit=5_000, context=context)],
                temperature=0.12,
                validator=self._validate_scene_draft,
                include_schema_example=False,
            )
        if not isinstance(response, SemanticSceneDraft):
            raise TypeError("scene payload did not validate as SemanticSceneDraft")
        response = response.model_copy(update={"mode": mode, "topology": topology})
        return SemanticCompiler.compile(
            response,
            scene_id=f"scene-{scene_index:02d}",
            title=outline.title.strip() or f"场景 {scene_index}",
        )

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
        # The storyboard is guidance only.  The compiler owns the final scene
        # mode/topology and the payload is accepted even when the model drifts.
        SemanticCompiler.compile(value, scene_id="validation-scene", title="validation scene")

    @staticmethod
    def _material_message(
        brief: CartoonBrief,
        *,
        task: str,
        limit: int,
        context: dict[str, str] | None = None,
    ) -> HumanMessage:
        material = CartoonPlanner._teaching_material(brief)
        payload = {
            "task": task,
            "context": context or {},
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
    def _teaching_material(brief: CartoonBrief) -> str:
        sections = [
            f"学习主题：{brief.learning_need}",
            "教学上下文：" + json.dumps(brief.instruction_context, ensure_ascii=False),
            "知识点：" + "、".join(brief.knowledge_points),
            "薄弱点：" + "、".join(brief.weak_knowledge_points),
            *brief.source_materials,
        ]
        return "\n\n".join(value.strip() for value in sections if value.strip())

    @staticmethod
    def _exception_details(exc: BaseException) -> list[str]:
        if isinstance(exc, BaseExceptionGroup):
            return [detail for child in exc.exceptions for detail in CartoonPlanner._exception_details(child)]
        return [str(exc) or type(exc).__name__]
