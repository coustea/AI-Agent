from __future__ import annotations

from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator


DiagramType = Literal["hierarchy", "flow", "compare", "relation", "sequence", "state"]


class BaseDiagramModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class DiagramNode(BaseDiagramModel):
    id: str = Field(min_length=1, max_length=40)
    label: str = Field(min_length=1, max_length=16)
    description: Optional[str] = Field(default=None, max_length=40)


class DiagramEdge(BaseDiagramModel):
    source: str = Field(min_length=1, max_length=40)
    target: str = Field(min_length=1, max_length=40)
    label: Optional[str] = Field(default=None, max_length=16)
    description: Optional[str] = Field(default=None, max_length=40)


class HierarchyNode(BaseDiagramModel):
    id: str = Field(min_length=1, max_length=40)
    label: str = Field(min_length=1, max_length=16)
    description: Optional[str] = Field(default=None, max_length=40)
    children: list["HierarchyNode"] = Field(default_factory=list, max_length=8)


class HierarchySpec(BaseDiagramModel):
    root: HierarchyNode


class FlowStep(BaseDiagramModel):
    id: str = Field(min_length=1, max_length=40)
    label: str = Field(min_length=1, max_length=16)
    description: Optional[str] = Field(default=None, max_length=40)


class FlowEdge(BaseDiagramModel):
    source: str = Field(min_length=1, max_length=40)
    target: str = Field(min_length=1, max_length=40)
    label: Optional[str] = Field(default=None, max_length=16)


class FlowSpec(BaseDiagramModel):
    steps: list[FlowStep] = Field(min_length=1, max_length=8)
    edges: list[FlowEdge] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def validate_edges(self) -> FlowSpec:
        ids = {step.id for step in self.steps}
        for edge in self.edges:
            if edge.source not in ids or edge.target not in ids:
                raise ValueError("flow edge source/target must reference existing step ids")
        return self


class CompareItem(BaseDiagramModel):
    label: str = Field(min_length=1, max_length=16)
    description: Optional[str] = Field(default=None, max_length=40)
    points: list[str] = Field(default_factory=list, max_length=6)


class CompareSpec(BaseDiagramModel):
    items: list[CompareItem] = Field(min_length=2, max_length=6)
    dimensions: list[str] = Field(default_factory=list, max_length=8)


class RelationSpec(BaseDiagramModel):
    nodes: list[DiagramNode] = Field(min_length=1, max_length=8)
    edges: list[DiagramEdge] = Field(default_factory=list, max_length=16)

    @model_validator(mode="after")
    def validate_edges(self) -> RelationSpec:
        ids = {node.id for node in self.nodes}
        for edge in self.edges:
            if edge.source not in ids or edge.target not in ids:
                raise ValueError("relation edge source/target must reference existing node ids")
        return self


class SequenceActor(BaseDiagramModel):
    id: str = Field(min_length=1, max_length=40)
    label: str = Field(min_length=1, max_length=16)
    description: Optional[str] = Field(default=None, max_length=40)


class SequenceMessage(BaseDiagramModel):
    from_actor: str = Field(alias="from", min_length=1, max_length=40)
    to_actor: str = Field(alias="to", min_length=1, max_length=40)
    label: str = Field(min_length=1, max_length=16)
    description: Optional[str] = Field(default=None, max_length=40)


class SequenceSpec(BaseDiagramModel):
    actors: list[SequenceActor] = Field(min_length=2, max_length=6)
    messages: list[SequenceMessage] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def validate_messages(self) -> SequenceSpec:
        ids = {actor.id for actor in self.actors}
        for message in self.messages:
            if message.from_actor not in ids or message.to_actor not in ids:
                raise ValueError("sequence message from/to must reference existing actor ids")
        return self


class StateTransition(BaseDiagramModel):
    from_state: str = Field(alias="from", min_length=1, max_length=40)
    to_state: str = Field(alias="to", min_length=1, max_length=40)
    label: str = Field(min_length=1, max_length=16)
    description: Optional[str] = Field(default=None, max_length=40)


class StateSpec(BaseDiagramModel):
    states: list[DiagramNode] = Field(min_length=1, max_length=8)
    transitions: list[StateTransition] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def validate_transitions(self) -> StateSpec:
        ids = {state.id for state in self.states}
        for transition in self.transitions:
            if transition.from_state not in ids or transition.to_state not in ids:
                raise ValueError("state transition from/to must reference existing state ids")
        return self


class HierarchyDiagram(BaseDiagramModel):
    type: Literal["hierarchy"]
    title: str = Field(min_length=1, max_length=20)
    summary: Optional[str] = Field(default=None, max_length=50)
    spec: HierarchySpec


class FlowDiagram(BaseDiagramModel):
    type: Literal["flow"]
    title: str = Field(min_length=1, max_length=20)
    summary: Optional[str] = Field(default=None, max_length=50)
    spec: FlowSpec


class CompareDiagram(BaseDiagramModel):
    type: Literal["compare"]
    title: str = Field(min_length=1, max_length=20)
    summary: Optional[str] = Field(default=None, max_length=50)
    spec: CompareSpec


class RelationDiagram(BaseDiagramModel):
    type: Literal["relation"]
    title: str = Field(min_length=1, max_length=20)
    summary: Optional[str] = Field(default=None, max_length=50)
    spec: RelationSpec


class SequenceDiagram(BaseDiagramModel):
    type: Literal["sequence"]
    title: str = Field(min_length=1, max_length=20)
    summary: Optional[str] = Field(default=None, max_length=50)
    spec: SequenceSpec


class StateDiagram(BaseDiagramModel):
    type: Literal["state"]
    title: str = Field(min_length=1, max_length=20)
    summary: Optional[str] = Field(default=None, max_length=50)
    spec: StateSpec


EnabledDiagram = Annotated[
    Union[
        HierarchyDiagram,
        FlowDiagram,
        CompareDiagram,
        RelationDiagram,
        SequenceDiagram,
        StateDiagram,
    ],
    Field(discriminator="type"),
]


class DiagramDecision(BaseDiagramModel):
    need_diagram: bool
    diagram_type: Optional[DiagramType] = None
    reason: Optional[str] = Field(default=None, max_length=80)


DIAGRAM_MODEL_MAP: dict[str, type[BaseDiagramModel]] = {
    "hierarchy": HierarchyDiagram,
    "flow": FlowDiagram,
    "compare": CompareDiagram,
    "relation": RelationDiagram,
    "sequence": SequenceDiagram,
    "state": StateDiagram,
}


HierarchyNode.model_rebuild()
