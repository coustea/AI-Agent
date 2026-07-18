"""Renderer-neutral visual intermediate representation for PPT slides.

The compiler describes semantic content and zero-based relationships only.
Stable identity, geometry, CSS, and color remain renderer-owned concerns.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


TextContent = Annotated[str, Field(min_length=1)]
ShortLabel = TextContent
CompactLabel = TextContent
PortName = TextContent
NonNegativeIndex = Annotated[int, Field(ge=0)]
CellValue = str


def _require_index(index: int, size: int, reference: str) -> None:
    if index >= size:
        raise ValueError(f"{reference} index {index} is outside 0..{size - 1}")


def _require_highlight_indexes(
    indexes: list[int],
    size: int,
    reference: str,
) -> None:
    for index in indexes:
        _require_index(index, size, reference)


class VisualIRModel(BaseModel):
    """Base class for strict visual IR payloads."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        allow_inf_nan=False,
    )


class HierarchyNode(VisualIRModel):
    """One hierarchy node linked to its optional parent by list index."""

    label: ShortLabel
    parent_index: NonNegativeIndex | None


class HierarchyVisual(VisualIRModel):
    """A rooted, connected, acyclic hierarchy."""

    kind: Literal["hierarchy"]
    nodes: list[HierarchyNode] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def validate_tree(self) -> "HierarchyVisual":
        """Validate parent references and the single-root tree invariant."""

        root_indexes = [
            index for index, node in enumerate(self.nodes) if node.parent_index is None
        ]
        if len(root_indexes) != 1:
            raise ValueError("hierarchy must contain exactly one root")

        node_count = len(self.nodes)
        for index, node in enumerate(self.nodes):
            if node.parent_index is None:
                continue
            _require_index(node.parent_index, node_count, "hierarchy parent")
            if node.parent_index == index:
                raise ValueError("hierarchy node cannot be its own parent")

        root_index = root_indexes[0]
        for node_index in range(node_count):
            current_index = node_index
            visited: set[int] = set()
            while current_index != root_index:
                if current_index in visited:
                    raise ValueError("hierarchy must be acyclic")
                visited.add(current_index)
                parent_index = self.nodes[current_index].parent_index
                if parent_index is None:
                    raise ValueError("every hierarchy node must be reachable from the root")
                current_index = parent_index
        return self


class GraphNode(VisualIRModel):
    """One labelled graph node."""

    label: ShortLabel


class GraphEdge(VisualIRModel):
    """One graph edge whose endpoints are node indexes."""

    source_index: NonNegativeIndex
    target_index: NonNegativeIndex
    label: str = ""


class GraphVisual(VisualIRModel):
    """A directed or undirected semantic graph."""

    kind: Literal["graph"]
    directed: bool
    nodes: list[GraphNode] = Field(min_length=1, max_length=12)
    edges: list[GraphEdge] = Field(min_length=1, max_length=24)

    @model_validator(mode="after")
    def validate_edges(self) -> "GraphVisual":
        """Validate graph endpoints and prohibit self-loops."""

        node_count = len(self.nodes)
        for edge in self.edges:
            _require_index(edge.source_index, node_count, "graph source")
            _require_index(edge.target_index, node_count, "graph target")
            if edge.source_index == edge.target_index:
                raise ValueError("graph edges cannot connect a node to itself")
        return self


class StateNode(VisualIRModel):
    """One state with explicit initial and final roles."""

    label: ShortLabel
    initial: bool
    final: bool


class StateTransition(VisualIRModel):
    """One transition between zero-based state indexes."""

    source_index: NonNegativeIndex
    target_index: NonNegativeIndex
    label: ShortLabel


class StateMachineVisual(VisualIRModel):
    """A state diagram with one entry state and optional terminal states."""

    kind: Literal["state_machine"]
    states: list[StateNode] = Field(min_length=2, max_length=12)
    transitions: list[StateTransition] = Field(min_length=1, max_length=24)

    @model_validator(mode="after")
    def validate_state_machine(self) -> "StateMachineVisual":
        """Validate state roles and transition endpoints."""

        if sum(state.initial for state in self.states) != 1:
            raise ValueError("state machine must contain exactly one initial state")
        state_count = len(self.states)
        for transition in self.transitions:
            _require_index(transition.source_index, state_count, "transition source")
            _require_index(transition.target_index, state_count, "transition target")
        return self


class TimelineLane(VisualIRModel):
    """One participant or track in a timeline."""

    label: ShortLabel


class TimelineEvent(VisualIRModel):
    """One interval event assigned to a timeline lane."""

    lane_index: NonNegativeIndex
    start: float
    end: float
    label: ShortLabel

    @model_validator(mode="after")
    def validate_interval(self) -> "TimelineEvent":
        """Require the event interval to move forward in time."""

        if self.start >= self.end:
            raise ValueError("timeline event start must be less than end")
        return self


class TimelineMessage(VisualIRModel):
    """One point-in-time message between timeline lanes."""

    source_lane_index: NonNegativeIndex
    target_lane_index: NonNegativeIndex
    at: float
    label: ShortLabel


class TimelineVisual(VisualIRModel):
    """A lane-based timeline containing events, messages, or both."""

    kind: Literal["timeline"]
    lanes: list[TimelineLane] = Field(min_length=1, max_length=8)
    events: list[TimelineEvent] = Field(default_factory=list, max_length=24)
    messages: list[TimelineMessage] = Field(default_factory=list, max_length=24)

    @model_validator(mode="after")
    def validate_timeline(self) -> "TimelineVisual":
        """Validate timeline content and all lane references."""

        if not self.events and not self.messages:
            raise ValueError("timeline must contain at least one event or message")

        lane_count = len(self.lanes)
        for event in self.events:
            _require_index(event.lane_index, lane_count, "event lane")
        for message in self.messages:
            _require_index(message.source_lane_index, lane_count, "message source lane")
            _require_index(message.target_lane_index, lane_count, "message target lane")
        return self


class MemorySegment(VisualIRModel):
    """One positive-sized region in a memory layout."""

    label: ShortLabel
    size: float = Field(gt=0)


class MemoryReference(VisualIRModel):
    """One pointer or reference between memory segments."""

    source_segment_index: NonNegativeIndex
    target_segment_index: NonNegativeIndex
    relation: Literal["pointer", "reference"]
    label: str = ""


class MemoryLayoutVisual(VisualIRModel):
    """A bounded memory layout with index-based semantic references."""

    kind: Literal["memory_layout"]
    segments: list[MemorySegment] = Field(min_length=1, max_length=16)
    references: list[MemoryReference] = Field(default_factory=list, max_length=24)

    @model_validator(mode="after")
    def validate_references(self) -> "MemoryLayoutVisual":
        """Validate each memory reference endpoint."""

        segment_count = len(self.segments)
        for reference in self.references:
            _require_index(
                reference.source_segment_index,
                segment_count,
                "memory reference source",
            )
            _require_index(
                reference.target_segment_index,
                segment_count,
                "memory reference target",
            )
        return self


class DataFlowBlock(VisualIRModel):
    """One data-flow block with named input and output ports."""

    label: ShortLabel
    input_ports: list[PortName] = Field(default_factory=list, max_length=8)
    output_ports: list[PortName] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def validate_ports(self) -> "DataFlowBlock":
        """Require at least one unambiguous port on each block."""

        if not self.input_ports and not self.output_ports:
            raise ValueError("data-flow block must expose at least one port")
        if len(set(self.input_ports)) != len(self.input_ports):
            raise ValueError("data-flow input port names must be unique")
        if len(set(self.output_ports)) != len(self.output_ports):
            raise ValueError("data-flow output port names must be unique")
        return self


class DataFlowEdge(VisualIRModel):
    """One directed output-to-input connection between data-flow blocks."""

    source_block_index: NonNegativeIndex
    source_port_index: NonNegativeIndex
    source_port_name: PortName
    target_block_index: NonNegativeIndex
    target_port_index: NonNegativeIndex
    target_port_name: PortName
    label: str = ""


class DataFlowVisual(VisualIRModel):
    """A directed graph whose edges resolve named block ports."""

    kind: Literal["data_flow"]
    directed: Literal[True]
    blocks: list[DataFlowBlock] = Field(min_length=2, max_length=12)
    flows: list[DataFlowEdge] = Field(min_length=1, max_length=24)

    @model_validator(mode="after")
    def validate_flows(self) -> "DataFlowVisual":
        """Resolve block and port index/name pairs for every flow."""

        block_count = len(self.blocks)
        for flow in self.flows:
            _require_index(flow.source_block_index, block_count, "flow source block")
            _require_index(flow.target_block_index, block_count, "flow target block")

            source_ports = self.blocks[flow.source_block_index].output_ports
            target_ports = self.blocks[flow.target_block_index].input_ports
            _require_index(flow.source_port_index, len(source_ports), "flow source port")
            _require_index(flow.target_port_index, len(target_ports), "flow target port")
            if source_ports[flow.source_port_index] != flow.source_port_name:
                raise ValueError("flow source port index and name must reference the same port")
            if target_ports[flow.target_port_index] != flow.target_port_name:
                raise ValueError("flow target port index and name must reference the same port")
        return self


class MappingPair(VisualIRModel):
    """One relation from a left element index to a right element index."""

    source_index: NonNegativeIndex
    target_index: NonNegativeIndex


class MappingVisual(VisualIRModel):
    """A bounded relation or function between two labelled sets."""

    kind: Literal["mapping"]
    mode: Literal["relation", "function"]
    left_set_label: CompactLabel
    right_set_label: CompactLabel
    left_elements: list[ShortLabel] = Field(min_length=1, max_length=12)
    right_elements: list[ShortLabel] = Field(min_length=1, max_length=12)
    pairs: list[MappingPair] = Field(min_length=1, max_length=24)

    @model_validator(mode="after")
    def validate_pairs(self) -> "MappingVisual":
        """Validate pair indexes and the optional mathematical-function rule."""

        seen_pairs: set[tuple[int, int]] = set()
        function_images: dict[int, int] = {}
        for pair in self.pairs:
            _require_index(pair.source_index, len(self.left_elements), "mapping source")
            _require_index(pair.target_index, len(self.right_elements), "mapping target")
            pair_key = (pair.source_index, pair.target_index)
            if pair_key in seen_pairs:
                raise ValueError("mapping pairs must be unique")
            seen_pairs.add(pair_key)
            if self.mode == "function":
                prior_image = function_images.get(pair.source_index)
                if prior_image is not None and prior_image != pair.target_index:
                    raise ValueError("function mapping gives one source more than one image")
                function_images[pair.source_index] = pair.target_index
        return self


class TableRow(VisualIRModel):
    """One row of semantic table cells."""

    cells: list[CellValue] = Field(min_length=1, max_length=8)


class TableMatrixVisual(VisualIRModel):
    """A bounded rectangular table with semantic row and column highlights."""

    kind: Literal["table_matrix"]
    headers: list[ShortLabel] = Field(min_length=1, max_length=8)
    rows: list[TableRow] = Field(min_length=1, max_length=12)
    highlighted_row_indices: list[NonNegativeIndex] = Field(
        default_factory=list,
        max_length=12,
    )
    highlighted_column_indices: list[NonNegativeIndex] = Field(
        default_factory=list,
        max_length=8,
    )

    @model_validator(mode="after")
    def validate_matrix(self) -> "TableMatrixVisual":
        """Validate rectangular rows and highlight indexes."""

        column_count = len(self.headers)
        for row in self.rows:
            if len(row.cells) != column_count:
                raise ValueError("every table row must match the header column count")
        _require_highlight_indexes(
            self.highlighted_row_indices,
            len(self.rows),
            "highlighted row",
        )
        _require_highlight_indexes(
            self.highlighted_column_indices,
            column_count,
            "highlighted column",
        )
        return self


class AlgorithmFrame(VisualIRModel):
    """One bounded algorithm snapshot with highlighted cells."""

    title: CompactLabel
    cells: list[CellValue] = Field(min_length=1, max_length=16)
    highlighted_cell_indices: list[NonNegativeIndex] = Field(
        default_factory=list,
        max_length=16,
    )

    @model_validator(mode="after")
    def validate_highlights(self) -> "AlgorithmFrame":
        """Validate highlighted cell indexes against this frame."""

        _require_highlight_indexes(
            self.highlighted_cell_indices,
            len(self.cells),
            "highlighted algorithm cell",
        )
        return self


class AlgorithmFramesVisual(VisualIRModel):
    """A short sequence of algorithm snapshots."""

    kind: Literal["algorithm_frames"]
    frames: list[AlgorithmFrame] = Field(min_length=2, max_length=8)

class CircuitTerminal(VisualIRModel):
    """One labelled circuit input or output terminal."""

    label: CompactLabel


class CircuitGate(VisualIRModel):
    """One bounded logic gate in a circuit network."""

    label: CompactLabel
    gate_type: TextContent


class CircuitWire(VisualIRModel):
    """One directed circuit connection between indexed components."""

    source_kind: Literal["input", "gate"]
    source_index: NonNegativeIndex
    target_kind: Literal["gate", "output"]
    target_index: NonNegativeIndex


class CircuitVisual(VisualIRModel):
    """A bounded circuit network with explicit input-to-output direction."""

    kind: Literal["circuit"]
    inputs: list[CircuitTerminal] = Field(min_length=1, max_length=8)
    gates: list[CircuitGate] = Field(default_factory=list, max_length=12)
    outputs: list[CircuitTerminal] = Field(min_length=1, max_length=8)
    wires: list[CircuitWire] = Field(min_length=1, max_length=24)

    @model_validator(mode="after")
    def validate_wires(self) -> "CircuitVisual":
        """Validate wire endpoints and prohibit component self-connections."""

        source_sizes = {"input": len(self.inputs), "gate": len(self.gates)}
        target_sizes = {"gate": len(self.gates), "output": len(self.outputs)}
        for wire in self.wires:
            _require_index(
                wire.source_index,
                source_sizes[wire.source_kind],
                "wire source",
            )
            _require_index(
                wire.target_index,
                target_sizes[wire.target_kind],
                "wire target",
            )
            if (
                wire.source_kind == wire.target_kind
                and wire.source_index == wire.target_index
            ):
                raise ValueError("circuit wire cannot connect a component to itself")
        return self


class QuantitativeAxis(VisualIRModel):
    """One labelled quantitative axis with an optional display unit."""

    label: CompactLabel
    unit: str = ""

    @field_validator("unit", mode="before")
    @classmethod
    def normalize_unit(cls, value: object) -> object:
        """Treat a missing or JSON-null unit as the unitless default."""

        return "" if value is None else value


class QuantitativePoint(VisualIRModel):
    """One finite pair of quantitative data values."""

    x_value: float
    y_value: float


class QuantitativeSeries(VisualIRModel):
    """One bounded quantitative data series."""

    label: ShortLabel
    points: list[QuantitativePoint] = Field(min_length=1, max_length=24)


class QuantitativeVisual(VisualIRModel):
    """A finite quantitative comparison with explicit axes."""

    kind: Literal["quantitative"]
    x_axis: QuantitativeAxis
    y_axis: QuantitativeAxis
    series: list[QuantitativeSeries] = Field(min_length=1, max_length=6)


class FormulaStep(VisualIRModel):
    """One compact symbolic derivation step."""

    expression: TextContent
    explanation: TextContent


class FormulaVariable(VisualIRModel):
    """One bounded explanation of a formula symbol."""

    symbol: TextContent
    meaning: TextContent


class FormulaVisual(VisualIRModel):
    """A formula with an optional short derivation and variable glossary."""

    kind: Literal["formula"]
    expression: TextContent
    steps: list[FormulaStep] = Field(default_factory=list, max_length=4)
    variables: list[FormulaVariable] = Field(default_factory=list, max_length=12)


LeafVisualModel = Annotated[
    HierarchyVisual
    | GraphVisual
    | StateMachineVisual
    | TimelineVisual
    | MemoryLayoutVisual
    | DataFlowVisual
    | MappingVisual
    | TableMatrixVisual
    | AlgorithmFramesVisual
    | CircuitVisual
    | QuantitativeVisual
    | FormulaVisual,
    Field(discriminator="kind"),
]


def count_semantic_marks(visual: LeafVisualModel) -> int:
    """Return the visible semantic-entity count for renderer diagnostics.

    This is reporting only. It is deliberately not used to reject a visual.
    """

    if isinstance(visual, HierarchyVisual):
        return len(visual.nodes) + sum(node.parent_index is not None for node in visual.nodes)
    if isinstance(visual, GraphVisual):
        return len(visual.nodes) + len(visual.edges)
    if isinstance(visual, StateMachineVisual):
        return len(visual.states) + len(visual.transitions)
    if isinstance(visual, TimelineVisual):
        return len(visual.lanes) + len(visual.events) + len(visual.messages)
    if isinstance(visual, MemoryLayoutVisual):
        return len(visual.segments) + len(visual.references)
    if isinstance(visual, DataFlowVisual):
        ports = sum(len(block.input_ports) + len(block.output_ports) for block in visual.blocks)
        return len(visual.blocks) + ports + len(visual.flows)
    if isinstance(visual, MappingVisual):
        return 2 + len(visual.left_elements) + len(visual.right_elements) + len(visual.pairs)
    if isinstance(visual, TableMatrixVisual):
        return len(visual.headers) + sum(len(row.cells) for row in visual.rows)
    if isinstance(visual, AlgorithmFramesVisual):
        return len(visual.frames) + sum(len(frame.cells) for frame in visual.frames) + len(visual.frames) - 1
    if isinstance(visual, CircuitVisual):
        return len(visual.inputs) + len(visual.gates) + len(visual.outputs) + len(visual.wires)
    if isinstance(visual, QuantitativeVisual):
        return 2 + len(visual.series) + sum(len(series.points) for series in visual.series)
    if isinstance(visual, FormulaVisual):
        return 1 + len(visual.steps) + len(visual.variables)
    raise TypeError(f"unsupported leaf visual type: {type(visual).__name__}")


class CompositePanel(VisualIRModel):
    """One titled, positively weighted leaf visual panel."""

    title: TextContent
    width_weight: float = Field(gt=0)
    visual: LeafVisualModel


class CompositeVisual(VisualIRModel):
    """A non-recursive composition of two or three leaf visuals."""

    kind: Literal["composite"]
    purpose: TextContent
    panels: list[CompositePanel] = Field(min_length=2, max_length=3)


VisualModel = Annotated[
    HierarchyVisual
    | GraphVisual
    | StateMachineVisual
    | TimelineVisual
    | MemoryLayoutVisual
    | DataFlowVisual
    | MappingVisual
    | TableMatrixVisual
    | AlgorithmFramesVisual
    | CircuitVisual
    | QuantitativeVisual
    | FormulaVisual
    | CompositeVisual,
    Field(discriminator="kind"),
]


__all__ = [
    "AlgorithmFramesVisual",
    "CellValue",
    "CircuitVisual",
    "CompositeVisual",
    "DataFlowVisual",
    "FormulaVisual",
    "GraphVisual",
    "HierarchyVisual",
    "LeafVisualModel",
    "MappingVisual",
    "MemoryLayoutVisual",
    "QuantitativeVisual",
    "StateMachineVisual",
    "TableMatrixVisual",
    "TimelineVisual",
    "VisualModel",
    "count_semantic_marks",
]
