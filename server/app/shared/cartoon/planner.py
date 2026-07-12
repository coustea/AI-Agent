"""Compile a compact lesson outline into replayable teaching scenes.

The LLM owns teaching intent only.  Executable scene state is created here so
every video scene has the same validated, replayable contract before rendering.
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
    """Deterministically turn one teaching beat into a replayable scene."""

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
        focus_label = cls._text(outline.key_points[0], "起始对象", 72)
        process_label = cls._text(outline.process_beats[0], "处理过程", 72)
        result_label = cls._text(outline.exit_state, "教学结果", 72)
        actions, patches = cls._process_actions(outline.mechanism)
        hidden_ids = cls._initially_hidden_ids(outline.mechanism)

        return TeachingScene.model_validate(
            {
                "id": outline.id,
                "title": outline.title,
                "objective": outline.objective,
                "mode": cls._MODES.get(outline.mechanism, "concept"),
                "mechanism": outline.mechanism,
                "tag": cls._text(outline.key_points[0], "教学过程", 36),
                "visual_model": {
                    "kind": visual_kind,
                    "label": outline.title,
                    "nodes": [
                        {"id": "source", "label": focus_label, "kind": node_kind},
                        {
                            "id": "process",
                            "label": process_label,
                            "kind": node_kind,
                            "initially_visible": "process" not in hidden_ids,
                        },
                        {
                            "id": "result",
                            "label": result_label,
                            "kind": node_kind,
                            "parent_id": "source" if outline.mechanism == "tree_growth" else None,
                            "initially_visible": "result" not in hidden_ids,
                        },
                    ],
                    "edges": cls._initial_edges(outline.mechanism),
                },
                "steps": [
                    {
                        "id": "observe",
                        "narration": cls._narration("先观察", outline.entry_state),
                        "focus_ids": ["source"],
                        "actions": [
                            {
                                "kind": "focus",
                                "target_ids": ["source"],
                                "note": "建立观察起点",
                            }
                        ],
                    },
                    {
                        "id": "demonstrate",
                        "narration": cls._narration("再推进", outline.process_beats[-1]),
                        "focus_ids": ["process", "result"],
                        "actions": actions,
                        "patches": patches,
                    },
                ],
            }
        )

    @staticmethod
    def _initially_hidden_ids(mechanism: str) -> set[str]:
        if mechanism == "tree_growth":
            return {"result"}

        return set()

    @staticmethod
    def _initial_edges(mechanism: str) -> list[dict[str, Any]]:
        if mechanism in {
            "graph_traversal",
            "timeline",
        }:
            return [
                {"source_id": "source", "target_id": "process", "kind": "directed"},
                {"source_id": "process", "target_id": "result", "kind": "directed"},
            ]

        if mechanism in {
            "sequence",
            "data_flow",
            "message_exchange",
            "pipeline",
        }:
            return [
                {"source_id": "source", "target_id": "process", "kind": "directed"},
            ]

        return []

    @staticmethod
    def _process_actions(mechanism: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        if mechanism == "tree_growth":
            edge = {"source_id": "source", "target_id": "result", "kind": "directed"}
            return (
                [
                    {
                        "kind": "insert",
                        "target_ids": ["result"],
                        "note": "新对象进入结构",
                        "duration_ms": 620,
                    },
                    {
                        "kind": "connect",
                        "target_ids": ["source", "result"],
                        "source_id": "source",
                        "destination_id": "result",
                        "note": "建立结构连接",
                        "duration_ms": 620,
                    },
                ],
                [{"op": "add_edge", "after_action_index": 1, "edge": edge}],
            )
        if mechanism == "graph_traversal":
            return (
                [{"kind": "traverse", "target_ids": ["source", "process", "result"], "note": "按顺序访问节点"}],
                [],
            )
        if mechanism == "comparison":
            return (
                [{"kind": "compare", "target_ids": ["source", "process"], "note": "比较关键差异"}],
                [],
            )
        if mechanism in {"state_transition", "container_operation", "memory_change"}:
            return (
                [{"kind": "mutate", "target_ids": ["process"], "note": "更新过程状态"}],
                [{"op": "set_state", "after_action_index": 0, "target_id": "process", "value": "updated"}],
            )
        return (
            [
                {
                    "kind": "transfer",
                    "target_ids": ["source", "process"],
                    "source_id": "source",
                    "destination_id": "process",
                    "note": "推动信息流转",
                }
            ],
            [],
        )

    @staticmethod
    def _text(value: str, fallback: str, limit: int) -> str:
        normalized = " ".join(value.split())[:limit]
        return normalized or fallback

    @classmethod
    def _narration(cls, prefix: str, detail: str) -> str:
        return cls._text(f"{prefix}：{detail}。", "观察并推进教学过程。", 180)


class CartoonLessonPlanner:
    """Generate a compact outline, then compile verified executable scenes."""

    async def plan(self, brief: CartoonBrief) -> TeachingLesson:
        try:
            outline = await self._invoke_outline(brief)
            scenes = [SceneCompiler.compile(scene) for scene in outline.scenes]
            return TeachingLesson.model_validate(
                {
                    "title": outline.title,
                    "course": outline.course,
                    "topic": outline.topic,
                    "scenes": [scene.model_dump(mode="json") for scene in scenes],
                }
            )
        except Exception as exc:
            raise CartoonPlanningError(f"无法生成可回放的教学动画: {exc}") from exc

    async def _invoke_outline(self, brief: CartoonBrief) -> LessonOutline:
        response = await get_llm().ainvoke_json(
            LessonOutline,
            self._outline_messages(brief),
            temperature=0.12,
            max_tokens=2200,
        )
        return response if isinstance(response, LessonOutline) else LessonOutline.model_validate(response)

    def _outline_messages(self, brief: CartoonBrief) -> list[Any]:
        config = brief.configuration
        source = self._source(brief, 6000)
        return [
            SystemMessage(
                content=(
                    "你是高校计算机课程教学动画的总导演。只输出 LessonOutline JSON。\n"
                    "本轮只规划全局教学结构，不生成节点、边、动作、补丁、旁白、坐标、HTML 或代码。\n"
                    f"mechanism 只能取：{'、'.join(MECHANISM_KINDS)}。场景数量为 2-6 个，"
                    "至少一个必须展示真实过程。每场景给出 entry_state、2-6 个连续 process_beats 和 exit_state。"
                )
            ),
            HumanMessage(
                content=(
                    f"学习需求：{brief.learning_need}\n目标时长：{config.target_duration_seconds} 秒\n"
                    f"知识点：{'、'.join(brief.knowledge_points)}\n"
                    f"薄弱知识点：{'、'.join(brief.weak_knowledge_points)}\n教学材料：\n{source}"
                )
            ),
        ]

    @staticmethod
    def _source(brief: CartoonBrief, limit: int) -> str:
        text = "\n\n".join(
            part for part in (brief.teaching_plan, brief.tutorial_markdown, "、".join(brief.knowledge_points)) if part.strip()
        )
        return text[:limit]
