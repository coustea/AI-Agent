"""Turn teaching intent into a stateful, replayable animation lesson.

The language model chooses the pedagogical sequence.  This module owns the
executable representation: every planned beat becomes a visible state and a
separate narrated action.  No teaching information is silently collapsed.
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.infra.llm import get_llm
from app.shared.cartoon.schemas import (
    MECHANISM_KINDS,
    CartoonBrief,
    LessonOutline,
    SceneOutline,
    TeachingLesson,
    TeachingScene,
)


class CartoonPlanningError(RuntimeError):
    """Raised when the teaching outline cannot be generated or compiled."""


class SceneCompiler:
    """Compile every outline beat into an evolving visual state."""

    _VISUAL_KINDS = {
        "tree_growth": "tree",
        "graph_traversal": "graph",
        "memory_change": "memory",
        "state_transition": "state-machine",
        "timeline": "state-machine",
        "message_exchange": "network",
        "comparison": "comparison",
    }
    _NODE_KINDS = {
        "tree_growth": "tree_node",
        "graph_traversal": "graph_node",
        "memory_change": "memory_block",
        "message_exchange": "packet",
        "pipeline": "pipeline_stage",
        "comparison": "data",
        "state_transition": "state",
    }
    _MODES = {
        "comparison": "comparison",
        "tree_growth": "algorithm",
        "graph_traversal": "algorithm",
        "container_operation": "algorithm",
        "sequence": "algorithm",
        "message_exchange": "protocol",
        "data_flow": "protocol",
        "pipeline": "architecture",
        "state_transition": "state-machine",
        "timeline": "state-machine",
        "memory_change": "state-machine",
    }

    @classmethod
    def compile(cls, outline: SceneOutline) -> TeachingScene:
        node_kind = cls._NODE_KINDS.get(outline.mechanism, "process")
        visual_kind = cls._VISUAL_KINDS.get(outline.mechanism, "flow")
        beats = [cls._text(beat, "过程变化", 72) for beat in outline.process_beats]
        node_ids = ["anchor", *[f"beat-{index + 1:02d}" for index in range(len(beats))], "outcome"]
        narration_budget = max(48, min(120, 48 + len(beats) * 12))
        nodes = [
            {
                "id": "anchor",
                "label": cls._text(outline.entry_state, "起始状态", 72),
                "detail": cls._text(outline.key_points[0], "观察起点", 88),
                "kind": node_kind,
                "state": "active",
            }
        ]
        nodes.extend(
            {
                "id": node_id,
                "label": beat,
                "detail": cls._text(outline.objective, "推进教学过程", 88),
                "kind": node_kind,
                "initially_visible": False,
            }
            for node_id, beat in zip(node_ids[1:-1], beats, strict=True)
        )
        nodes.append(
            {
                "id": "outcome",
                "label": cls._text(outline.exit_state, "最终状态", 72),
                "detail": "形成可复述的结论",
                "kind": node_kind,
                "initially_visible": False,
            }
        )
        edges = [
            {
                "source_id": source,
                "target_id": destination,
                "kind": "transition" if outline.mechanism in {"state_transition", "timeline"} else "directed",
            }
            for source, destination in zip(node_ids, node_ids[1:])
        ]
        steps = [
            {
                "id": "orient",
                "narration": cls._narration("先建立起点", outline.entry_state, outline.objective, narration_budget),
                "focus_ids": ["anchor"],
                "actions": [{"kind": "focus", "target_ids": ["anchor"], "note": "建立观察起点", "duration_ms": 900}],
            }
        ]
        previous_id = "anchor"
        for index, (node_id, beat) in enumerate(zip(node_ids[1:-1], beats, strict=True), 1):
            steps.append(cls._beat_step(outline, previous_id, node_id, beat, index, narration_budget))
            previous_id = node_id
        steps.append(cls._outcome_step(outline, previous_id, narration_budget))
        return TeachingScene.model_validate(
            {
                "id": outline.id,
                "title": outline.title,
                "objective": outline.objective,
                "mode": cls._MODES.get(outline.mechanism, "concept"),
                "mechanism": outline.mechanism,
                "tag": cls._text(outline.key_points[0], "教学过程", 36),
                "visual_model": {"kind": visual_kind, "label": outline.title, "nodes": nodes, "edges": edges},
                "steps": steps,
            }
        )

    @classmethod
    def _beat_step(cls, outline: SceneOutline, source: str, target: str, beat: str, index: int, budget: int) -> dict[str, Any]:
        actions: list[dict[str, Any]] = [{"kind": "reveal", "target_ids": [target], "note": "呈现新的过程状态", "duration_ms": 720}]
        patches: list[dict[str, Any]] = []
        if outline.mechanism == "comparison":
            actions.append({"kind": "compare", "target_ids": [source, target], "note": "辨析前后差异", "duration_ms": 1050})
        elif outline.mechanism == "graph_traversal":
            actions.append({"kind": "traverse", "target_ids": [source, target], "note": "沿路径推进", "duration_ms": 1050})
        elif outline.mechanism in {"state_transition", "memory_change", "container_operation"}:
            actions.append({"kind": "mutate", "target_ids": [target], "note": "状态发生改变", "duration_ms": 980})
            patches.append({"op": "set_state", "after_action_index": 1, "target_id": target, "value": "changed"})
        elif outline.mechanism == "tree_growth":
            actions.append({"kind": "connect", "target_ids": [source, target], "source_id": source, "destination_id": target, "note": "展开新的结构关系", "duration_ms": 980})
        else:
            actions.append({"kind": "transfer", "target_ids": [source, target], "source_id": source, "destination_id": target, "note": "沿关系推动过程", "duration_ms": 1050})
        return {
            "id": f"beat-{index:02d}",
            "narration": cls._narration(f"第 {index} 步", beat, outline.objective, budget),
            "focus_ids": [source, target],
            "actions": actions,
            "patches": patches,
        }

    @classmethod
    def _outcome_step(cls, outline: SceneOutline, source: str, budget: int) -> dict[str, Any]:
        return {
            "id": "conclude",
            "narration": cls._narration("最后得到结论", outline.exit_state, outline.objective, budget),
            "focus_ids": [source, "outcome"],
            "actions": [
                {"kind": "reveal", "target_ids": ["outcome"], "note": "呈现结论", "duration_ms": 720},
                {"kind": "transfer", "target_ids": [source, "outcome"], "source_id": source, "destination_id": "outcome", "note": "收束为结论", "duration_ms": 1050},
                {"kind": "highlight", "target_ids": ["outcome"], "note": "巩固核心结论", "duration_ms": 840, "intensity": "strong"},
            ],
        }

    @staticmethod
    def _text(value: str, fallback: str, limit: int) -> str:
        normalized = " ".join(value.split())[:limit]
        return normalized or fallback

    @classmethod
    def _narration(cls, prefix: str, detail: str, objective: str, budget: int) -> str:
        sentences = [
            f"{prefix}，{cls._text(detail, '过程正在变化', 72)}。",
            f"这里要抓住的是：{cls._text(objective, '理解状态之间的因果关系', 88)}。",
            "先看清当前对象，再把它和前一个状态联系起来。",
            "这样就能判断这一步为什么会推动下一步。",
        ]
        text = ""
        for sentence in sentences:
            if len(text) >= budget:
                break
            text += sentence
        return text[:180]


class CartoonLessonPlanner:
    """Generate a duration-aware outline, then compile executable scenes."""

    async def plan(self, brief: CartoonBrief) -> TeachingLesson:
        try:
            outline = await self._invoke_outline(brief)
            scenes = [SceneCompiler.compile(scene) for scene in outline.scenes]
            return TeachingLesson.model_validate({"title": outline.title, "course": outline.course, "scenes": [scene.model_dump(mode="json") for scene in scenes]})
        except Exception as exc:
            raise CartoonPlanningError(f"无法生成可回放的教学动画: {exc}") from exc

    async def _invoke_outline(self, brief: CartoonBrief) -> LessonOutline:
        response = await get_llm().ainvoke_json(LessonOutline, self._outline_messages(brief), temperature=0.12, max_tokens=2600)
        return response if isinstance(response, LessonOutline) else LessonOutline.model_validate(response)

    def _outline_messages(self, brief: CartoonBrief) -> list[Any]:
        config = brief.configuration
        source = self._source(brief, 6000)
        return [
            SystemMessage(content=(
                "你是高校计算机课程教学动画的总导演。只输出 LessonOutline JSON。\n"
                "你负责教学结构：每个 process_beats 都必须是可被单独演示的连续因果步骤，不能写泛泛总结。\n"
                f"mechanism 只能取：{'、'.join(MECHANISM_KINDS)}。场景数量为 2-6 个，至少一个必须展示真实过程。"
                "每场景给出 entry_state、2-6 个连续 process_beats 和 exit_state。"
            )),
            HumanMessage(content=(
                f"学习需求：{brief.learning_need}\n目标时长：{config.target_duration_seconds} 秒（最少 90 秒）。\n"
                f"知识点：{'、'.join(brief.knowledge_points)}\n薄弱知识点：{'、'.join(brief.weak_knowledge_points)}\教学材料：\n{source}"
            )),
        ]

    @staticmethod
    def _source(brief: CartoonBrief, limit: int) -> str:
        text = "\n\n".join(part for part in (brief.teaching_plan, brief.tutorial_markdown, "、".join(brief.knowledge_points)) if part.strip())
        return text[:limit]
