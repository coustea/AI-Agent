"""Deterministically compile semantic slide briefs into renderer-safe visuals.

The teaching model owns the knowledge graph and the section model owns copy.
Visual IR is a rendering contract, so it must not be another large LLM output
surface. Keeping this compiler deterministic removes cross-slide identity,
union-schema, index, and JSON-size failures from the generation path.
"""

from __future__ import annotations

from app.shared.ppt.contract import LogicRelation, SlideKind
from app.shared.ppt.models import DeckLogicModel, LogicNode, PPTStoryboard, SlideBrief
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

    def plan(
        self,
        storyboard: PPTStoryboard,
        logic_model: DeckLogicModel,
    ) -> dict[str, VisualModel]:
        visuals: dict[str, VisualModel] = {}
        nodes_by_id = {node.id: node for node in logic_model.nodes}
        for brief in storyboard.slides:
            if brief.kind in _META_KINDS:
                continue
            nodes = [nodes_by_id[node_id] for node_id in brief.logic_node_ids]
            visuals[brief.id] = self._compile_visual(brief, nodes)
        return visuals

    @classmethod
    def _compile_visual(cls, brief: SlideBrief, nodes: list[LogicNode]) -> VisualModel:
        relation = brief.logic_relation
        if relation is None:
            raise ValueError(f"content slide {brief.id} is missing its logic relation")
        if relation in {
            LogicRelation.PREREQUISITE,
            LogicRelation.DECOMPOSES,
            LogicRelation.SUMMARIZES,
        }:
            return cls._hierarchy(brief, nodes)
        if relation is LogicRelation.CAUSES:
            return cls._timeline(brief, nodes)
        if relation is LogicRelation.CONTRASTS:
            return cls._mapping(brief, nodes)
        if relation in {LogicRelation.DERIVES, LogicRelation.APPLIES}:
            return cls._algorithm_frames(brief, nodes)
        if relation in {LogicRelation.SUPPORTS, LogicRelation.VERIFIES}:
            return cls._evidence_table(brief, nodes)
        raise ValueError(f"unsupported logic relation: {relation.value}")

    @staticmethod
    def _text(value: str) -> str:
        return " ".join(value.split()) or "当前知识点"

    @classmethod
    def _facts(cls, nodes: list[LogicNode]) -> list[str]:
        return list(
            dict.fromkeys(
                fact
                for node in nodes
                for fact in (node.claim, *node.evidence)
                if fact.strip()
            )
        )

    @classmethod
    def _hierarchy(cls, brief: SlideBrief, nodes: list[LogicNode]) -> HierarchyVisual:
        facts = cls._facts(nodes)
        return HierarchyVisual(
            kind="hierarchy",
            nodes=[
                {"label": cls._text(brief.title), "parent_index": None},
                *[
                    {"label": cls._text(fact), "parent_index": 0}
                    for fact in facts[:3]
                ],
            ],
        )

    @classmethod
    def _timeline(cls, brief: SlideBrief, nodes: list[LogicNode]) -> TimelineVisual:
        facts = cls._facts(nodes)
        return TimelineVisual(
            kind="timeline",
            lanes=[{"label": "条件"}, {"label": "结果"}],
            events=[
                {
                    "lane_index": 0,
                    "start": 0.0,
                    "end": 1.0,
                    "label": cls._text(facts[0]),
                },
                {
                    "lane_index": 1,
                    "start": 1.0,
                    "end": 2.0,
                    "label": cls._text(facts[-1]),
                },
            ],
        )

    @classmethod
    def _mapping(cls, brief: SlideBrief, nodes: list[LogicNode]) -> MappingVisual:
        facts = cls._facts(nodes)
        return MappingVisual(
            kind="mapping",
            mode="relation",
            left_set_label="判断条件",
            right_set_label="对应结论",
            left_elements=[cls._text(facts[0])],
            right_elements=[cls._text(facts[-1])],
            pairs=[{"source_index": 0, "target_index": 0}],
        )

    @classmethod
    def _algorithm_frames(cls, brief: SlideBrief, nodes: list[LogicNode]) -> AlgorithmFramesVisual:
        sequence_facts = list(
            dict.fromkeys(
                evidence
                for node in nodes
                for evidence in node.evidence
                if evidence != node.claim
            )
        )
        facts = sequence_facts or cls._facts(nodes)
        while len(facts) < 3:
            facts.append(brief.claim)
        return AlgorithmFramesVisual(
            kind="algorithm_frames",
            frames=[
                {
                    "title": "起点",
                    "cells": [cls._text(facts[0])],
                    "highlighted_cell_indices": [0],
                },
                {
                    "title": "关键过程",
                    "cells": [cls._text(facts[1])],
                    "highlighted_cell_indices": [0],
                },
                {
                    "title": "结果",
                    "cells": [cls._text(facts[2])],
                    "highlighted_cell_indices": [0],
                },
            ],
        )

    @classmethod
    def _evidence_table(cls, brief: SlideBrief, nodes: list[LogicNode]) -> TableMatrixVisual:
        facts = cls._facts(nodes)
        labels = ("核心事实", "补充说明", "应用线索", "复习提示")
        return TableMatrixVisual(
            kind="table_matrix",
            headers=["要点", "说明"],
            rows=[
                {
                    "cells": [
                        labels[index],
                        cls._text(fact),
                    ]
                }
                for index, fact in enumerate(facts[:4])
            ],
            highlighted_row_indices=list(range(min(1, len(facts)))),
            highlighted_column_indices=[1],
        )
