"""Deterministically compile semantic slide briefs into renderer-safe visuals.

The teaching model owns the knowledge graph and the section model owns copy.
Visual IR is a rendering contract, so it must not be another large LLM output
surface. Keeping this compiler deterministic removes cross-slide identity,
union-schema, index, and JSON-size failures from the generation path.
"""

from __future__ import annotations

from app.shared.ppt.contract import LogicRelation, SlideKind
from app.shared.ppt.models import PPTStoryboard, SlideBrief
from app.shared.ppt.visual_ir import (
    AlgorithmFramesVisual,
    HierarchyVisual,
    MappingVisual,
    TableMatrixVisual,
    TimelineVisual,
    VisualModel,
)


_META_KINDS = {SlideKind.COVER, SlideKind.ROADMAP, SlideKind.SUMMARY}


class VisualPlanner:
    """Compile one valid visual from every content-slide semantic brief."""

    def plan(self, storyboard: PPTStoryboard) -> dict[str, VisualModel]:
        visuals: dict[str, VisualModel] = {}
        for brief in storyboard.slides:
            if brief.kind in _META_KINDS:
                continue
            visuals[brief.id] = self._compile_visual(brief)
        return visuals

    @classmethod
    def _compile_visual(cls, brief: SlideBrief) -> VisualModel:
        relation = brief.logic_relation
        if relation is None:
            raise ValueError(f"content slide {brief.id} is missing its logic relation")
        if relation in {
            LogicRelation.PREREQUISITE,
            LogicRelation.DECOMPOSES,
            LogicRelation.SUMMARIZES,
        }:
            return cls._hierarchy(brief)
        if relation is LogicRelation.CAUSES:
            return cls._timeline(brief)
        if relation is LogicRelation.CONTRASTS:
            return cls._mapping(brief)
        if relation in {LogicRelation.DERIVES, LogicRelation.APPLIES}:
            return cls._algorithm_frames(brief)
        if relation in {LogicRelation.SUPPORTS, LogicRelation.VERIFIES}:
            return cls._evidence_table(brief)
        raise ValueError(f"unsupported logic relation: {relation.value}")

    @staticmethod
    def _text(value: str, limit: int) -> str:
        text = " ".join(value.split())
        return text[:limit] or "当前知识点"

    @classmethod
    def _hierarchy(cls, brief: SlideBrief) -> HierarchyVisual:
        return HierarchyVisual(
            kind="hierarchy",
            nodes=[
                {"label": cls._text(brief.title, 64), "parent_index": None},
                {"label": cls._text(brief.content_focus, 64), "parent_index": 0},
                {"label": cls._text(brief.claim, 64), "parent_index": 0},
            ],
        )

    @classmethod
    def _timeline(cls, brief: SlideBrief) -> TimelineVisual:
        return TimelineVisual(
            kind="timeline",
            lanes=[{"label": "条件"}, {"label": "结果"}],
            events=[
                {
                    "lane_index": 0,
                    "start": 0.0,
                    "end": 1.0,
                    "label": cls._text(brief.content_focus, 64),
                },
                {
                    "lane_index": 1,
                    "start": 1.0,
                    "end": 2.0,
                    "label": cls._text(brief.claim, 64),
                },
            ],
        )

    @classmethod
    def _mapping(cls, brief: SlideBrief) -> MappingVisual:
        return MappingVisual(
            kind="mapping",
            mode="relation",
            left_set_label="判断条件",
            right_set_label="对应结论",
            left_elements=[cls._text(brief.question, 64)],
            right_elements=[cls._text(brief.claim, 64)],
            pairs=[{"source_index": 0, "target_index": 0}],
        )

    @classmethod
    def _algorithm_frames(cls, brief: SlideBrief) -> AlgorithmFramesVisual:
        return AlgorithmFramesVisual(
            kind="algorithm_frames",
            frames=[
                {
                    "title": "输入",
                    "cells": [cls._text(brief.question, 48)],
                    "highlighted_cell_indices": [0],
                },
                {
                    "title": "推导",
                    "cells": [cls._text(brief.content_focus, 48)],
                    "highlighted_cell_indices": [0],
                },
                {
                    "title": "结论",
                    "cells": [cls._text(brief.claim, 48)],
                    "highlighted_cell_indices": [0],
                },
            ],
        )

    @classmethod
    def _evidence_table(cls, brief: SlideBrief) -> TableMatrixVisual:
        return TableMatrixVisual(
            kind="table_matrix",
            headers=["依据", "结论"],
            rows=[
                {
                    "cells": [
                        cls._text(brief.content_focus, 48),
                        cls._text(brief.claim, 48),
                    ]
                }
            ],
            highlighted_row_indices=[0],
            highlighted_column_indices=[1],
        )
