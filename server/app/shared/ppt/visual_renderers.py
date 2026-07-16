"""SVG/HTML renderer registry for all 14 visual IR types.

Each renderer receives a validated VisualModel instance and a slide_id string,
and returns an HTML/SVG fragment that fits inside a
``<section class="visual visual-{kind}">`` container.
"""

from __future__ import annotations

import html
import math
from collections import defaultdict
from typing import Callable

from pygments import lex
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.token import Comment, Keyword, Name, Number, Operator, String
from pygments.util import ClassNotFound

from app.shared.ppt.visual_ir import (
    AlgorithmFramesVisual,
    CircuitVisual,
    CodeVisual,
    CompositeVisual,
    DataFlowVisual,
    FormulaVisual,
    GraphVisual,
    HierarchyVisual,
    MappingVisual,
    MemoryLayoutVisual,
    QuantitativeVisual,
    StateMachineVisual,
    TableMatrixVisual,
    TimelineVisual,
    VisualModel,
)

# ---------------------------------------------------------------------------
# Type alias and registry
# ---------------------------------------------------------------------------

RenderFunc = Callable[[VisualModel, str], str]

RENDERERS: dict[str, RenderFunc] = {}


def register_renderer(kind: str, func: RenderFunc) -> None:
    RENDERERS[kind] = func


def render_visual(visual: VisualModel, slide_id: str) -> str:
    renderer = RENDERERS.get(visual.kind)
    if renderer is None:
        raise ValueError(f"no renderer registered for visual kind: {visual.kind}")
    return renderer(visual, slide_id)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _paren_unit(unit: str) -> str:
    """Return `` (unit)`` if *unit* is non-empty, else empty string."""
    return f" ({_escape(unit)})" if unit.strip() else ""


def _svg_arrow_marker(marker_id: str) -> str:
    return (
        f'<marker id="{_escape(marker_id)}" markerWidth="9" markerHeight="9" '
        f'refX="7" refY="4.5" orient="auto">'
        f'<path d="M0,0 L9,4.5 L0,9 Z"/></marker>'
    )


def _svg_node(
    x: float,
    y: float,
    label: str,
    detail: str | None = None,
    tone: str = "default",
    width: float = 184,
    height: float = 92,
) -> str:
    half_w = width / 2
    half_h = height / 2
    detail_html = (
        f'<span>{_escape(detail)}</span>' if detail else ""
    )
    return (
        f'<g class="diagram-node tone-{tone}" '
        f'transform="translate({x:.1f} {y:.1f})">'
        f'<rect x="{-half_w:.1f}" y="{-half_h:.1f}" '
        f'width="{width:.1f}" height="{height:.1f}" rx="18"/>'
        f'<foreignObject x="{-half_w + 10:.1f}" y="{-half_h + 8:.1f}" '
        f'width="{width - 20:.1f}" height="{height - 16:.1f}">'
        f'<div xmlns="http://www.w3.org/1999/xhtml" class="diagram-node-copy">'
        f'<strong>{_escape(label)}</strong>{detail_html}'
        f'</div></foreignObject></g>'
    )


def _svg_edge(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    label: str | None = None,
    marker_id: str | None = None,
    curved: bool = False,
) -> str:
    marker_attr = f' marker-end="url(#{_escape(marker_id)})"' if marker_id else ""
    if curved:
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2
        dx = x2 - x1
        dy = y2 - y1
        offset = 40
        cx = mx - dy * 0.2
        cy = my + dx * 0.2
        path = (
            f'<path d="M{x1:.1f} {y1:.1f} Q{cx:.1f} {cy:.1f} {x2:.1f} {y2:.1f}"'
            f'{marker_attr}/>'
        )
        label_x = cx
        label_y = cy - 14
    else:
        path = (
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" '
            f'x2="{x2:.1f}" y2="{y2:.1f}"{marker_attr}/>'
        )
        label_x = (x1 + x2) / 2
        label_y = (y1 + y2) / 2 - 14

    label_html = ""
    if label:
        label_html = (
            f'<text x="{label_x:.1f}" y="{label_y:.1f}">'
            f'{_escape(label)}</text>'
        )
    return f'<g class="diagram-edge">{path}{label_html}</g>'


def _edge_endpoints(
    source: tuple[float, float],
    target: tuple[float, float],
    half_w: float = 92,
    half_h: float = 46,
) -> tuple[float, float, float, float]:
    sx, sy = source
    tx, ty = target
    dx = tx - sx
    dy = ty - sy
    if not dx and not dy:
        return sx, sy, tx, ty
    scale = 1 / max(abs(dx) / half_w, abs(dy) / half_h)
    return sx + dx * scale, sy + dy * scale, tx - dx * scale, ty - dy * scale


def _layout_tree(
    nodes: list[object],
    parent_index_fn: Callable[[int], int | None],
) -> dict[int, tuple[float, float]]:
    """Compute (x, y) positions for a tree layout, root at top."""
    children: dict[int, list[int]] = defaultdict(list)
    root_index: int | None = None
    for i in range(len(nodes)):
        pi = parent_index_fn(i)
        if pi is None:
            root_index = i
        else:
            children[pi].append(i)
    if root_index is None:
        root_index = 0

    # BFS to assign levels
    levels: list[list[int]] = []
    queue: list[int] = [root_index]
    visited: set[int] = set()
    while queue:
        level = [n for n in queue if n not in visited]
        if not level:
            break
        levels.append(level)
        visited.update(level)
        queue = [c for n in level for c in children[n] if c not in visited]
    # Any unvisited nodes (shouldn't happen for valid trees)
    for i in range(len(nodes)):
        if i not in visited:
            levels.append([i])

    positions: dict[int, tuple[float, float]] = {}
    for col, level in enumerate(levels):
        n = len(level)
        for row, node_idx in enumerate(level):
            x = 100 + col * 800 / max(1, len(levels) - 1) if len(levels) > 1 else 500
            y = 100 + row * 360 / max(1, n - 1) if n > 1 else 280
            positions[node_idx] = (x, y)
    return positions


def _layout_flow(
    nodes: list[object],
    edges: list[tuple[int, int]],
) -> dict[int, tuple[float, float]]:
    """Compute (x, y) positions for a left-to-right flow layout."""
    n = len(nodes)
    columns = min(4, n)
    rows_per_col = math.ceil(n / columns)
    positions: dict[int, tuple[float, float]] = {}
    for i in range(n):
        col = i % columns
        row = i // columns
        x = 120 + col * 760 / max(1, columns - 1) if columns > 1 else 500
        y = 280 if rows_per_col == 1 else 170 + row * 220
        positions[i] = (x, y)
    return positions


# ---------------------------------------------------------------------------
# SVG wrapper
# ---------------------------------------------------------------------------

_VIEWBOX = "0 0 1000 560"


def _svg_wrap(
    inner: str,
    slide_id: str,
    marker_id: str | None = None,
    aria_label: str = "diagram",
) -> str:
    defs = ""
    if marker_id:
        defs = f"<defs>{_svg_arrow_marker(marker_id)}</defs>"
    return (
        f'<svg class="diagram" viewBox="{_VIEWBOX}" role="img" '
        f'aria-label="{_escape(aria_label)}">'
        f'{defs}{inner}</svg>'
    )


# ---------------------------------------------------------------------------
# 1. hierarchy
# ---------------------------------------------------------------------------


def _render_hierarchy(visual: VisualModel, slide_id: str) -> str:
    v = visual  # type: ignore[assignment]
    assert isinstance(v, HierarchyVisual)
    positions = _layout_tree(
        v.nodes,
        parent_index_fn=lambda i: v.nodes[i].parent_index,
    )
    marker_id = f"arrow-hierarchy-{slide_id}"
    edges_html = ""
    for i, node in enumerate(v.nodes):
        if node.parent_index is not None:
            sx, sy = positions[node.parent_index]
            tx, ty = positions[i]
            ex1, ey1, ex2, ey2 = _edge_endpoints(
                (sx, sy), (tx, ty),
            )
            edges_html += _svg_edge(ex1, ey1, ex2, ey2, marker_id=marker_id)
    nodes_html = "".join(
        _svg_node(positions[i][0], positions[i][1], node.label)
        for i, node in enumerate(v.nodes)
    )
    return _svg_wrap(nodes_html + edges_html, slide_id, marker_id, "hierarchy")


register_renderer("hierarchy", _render_hierarchy)


# ---------------------------------------------------------------------------
# 2. graph
# ---------------------------------------------------------------------------


def _render_graph(visual: VisualModel, slide_id: str) -> str:
    v = visual  # type: ignore[assignment]
    assert isinstance(v, GraphVisual)
    positions = _layout_flow(
        v.nodes,
        [(e.source_index, e.target_index) for e in v.edges],
    )
    marker_id = f"arrow-graph-{slide_id}" if v.directed else None
    edges_html = ""
    for edge in v.edges:
        sx, sy = positions[edge.source_index]
        tx, ty = positions[edge.target_index]
        ex1, ey1, ex2, ey2 = _edge_endpoints((sx, sy), (tx, ty))
        edges_html += _svg_edge(
            ex1, ey1, ex2, ey2,
            label=edge.label or None,
            marker_id=marker_id,
        )
    nodes_html = "".join(
        _svg_node(positions[i][0], positions[i][1], node.label)
        for i, node in enumerate(v.nodes)
    )
    return _svg_wrap(nodes_html + edges_html, slide_id, marker_id, "graph")


register_renderer("graph", _render_graph)


# ---------------------------------------------------------------------------
# 3. state_machine
# ---------------------------------------------------------------------------


def _render_state_machine(visual: VisualModel, slide_id: str) -> str:
    v = visual  # type: ignore[assignment]
    assert isinstance(v, StateMachineVisual)
    n = len(v.states)
    cols = min(4, n)
    positions: dict[int, tuple[float, float]] = {}
    for i, state in enumerate(v.states):
        col = i % cols
        row = i // cols
        x = 120 + col * 760 / max(1, cols - 1) if cols > 1 else 500
        y = 280 if n <= cols else 170 + row * 220
        positions[i] = (x, y)

    marker_id = f"arrow-sm-{slide_id}"
    edges_html = ""
    for t in v.transitions:
        sx, sy = positions[t.source_index]
        tx, ty = positions[t.target_index]
        curved = t.source_index == t.target_index
        if curved:
            # Self-loop: draw a small loop above the node
            cx = sx
            cy = sy - 100
            edges_html += (
                f'<g class="diagram-edge">'
                f'<path d="M{sx:.1f} {sy - 46:.1f} Q{cx - 50:.1f} {cy:.1f} {sx:.1f} {sy - 46:.1f}"'
                f' marker-end="url(#{_escape(marker_id)})"/>'
                f'<text x="{cx:.1f}" y="{cy - 10:.1f}">{_escape(t.label)}</text>'
                f'</g>'
            )
        else:
            ex1, ey1, ex2, ey2 = _edge_endpoints((sx, sy), (tx, ty))
            edges_html += _svg_edge(
                ex1, ey1, ex2, ey2,
                label=t.label,
                marker_id=marker_id,
                curved=True,
            )

    # Initial state indicator: filled dot with arrow
    initial_html = ""
    for i, state in enumerate(v.states):
        if state.initial:
            ix, iy = positions[i]
            initial_html += (
                f'<circle cx="{ix - 120:.1f}" cy="{iy:.1f}" r="8" fill="var(--ink)"/>'
                f'<line x1="{ix - 112:.1f}" y1="{iy:.1f}" '
                f'x2="{ix - 92:.1f}" y2="{iy:.1f}" '
                f'marker-end="url(#{_escape(marker_id)})"/>'
            )

    nodes_html = ""
    for i, state in enumerate(v.states):
        x, y = positions[i]
        tone = "default"
        extra_attr = ""
        if state.final:
            # Double border for final state
            tone = "accent"
            extra_attr = (
                f'<rect x="{-92 + 6:.1f}" y="{-46 + 6:.1f}" '
                f'width="{184 - 12:.1f}" height="{92 - 12:.1f}" rx="14" '
                f'fill="none" stroke="var(--accent)" stroke-width="2"/>'
            )
        node_g = _svg_node(x, y, state.label, tone=tone)
        if extra_attr:
            node_g = node_g.replace("</g>", extra_attr + "</g>", 1)
        nodes_html += node_g

    return _svg_wrap(
        initial_html + nodes_html + edges_html,
        slide_id,
        marker_id,
        "state machine",
    )


register_renderer("state_machine", _render_state_machine)


# ---------------------------------------------------------------------------
# 4. timeline
# ---------------------------------------------------------------------------


def _render_timeline(visual: VisualModel, slide_id: str) -> str:
    v = visual  # type: ignore[assignment]
    assert isinstance(v, TimelineVisual)
    lane_count = len(v.lanes)
    lane_height = 60
    top_margin = 80
    lane_start_x = 160
    lane_end_x = 940
    lane_width = lane_end_x - lane_start_x

    # Determine time range
    all_starts = [e.start for e in v.events] if v.events else [0]
    all_ends = [e.end for e in v.events] if v.events else [1]
    all_ats = [m.at for m in v.messages] if v.messages else []
    min_t = min(all_starts + all_ats) if all_starts + all_ats else 0
    max_t = max(all_ends + all_ats) if all_ends + all_ats else 1
    if max_t <= min_t:
        max_t = min_t + 1

    def t_to_x(t: float) -> float:
        return lane_start_x + (t - min_t) / (max_t - min_t) * lane_width

    # Lane labels and lines
    lanes_html = ""
    for i, lane in enumerate(v.lanes):
        y = top_margin + i * lane_height
        lanes_html += (
            f'<text x="140" y="{y + 5:.1f}" text-anchor="end" '
            f'class="timeline-lane-label">{_escape(lane.label)}</text>'
            f'<line x1="{lane_start_x}" y1="{y:.1f}" '
            f'x2="{lane_end_x}" y2="{y:.1f}" '
            f'stroke="var(--line)" stroke-width="2"/>'
        )

    # Events
    events_html = ""
    for event in v.events:
        y = top_margin + event.lane_index * lane_height
        x1 = t_to_x(event.start)
        x2 = t_to_x(event.end)
        w = max(x2 - x1, 20)
        events_html += (
            f'<rect x="{x1:.1f}" y="{y - 18:.1f}" width="{w:.1f}" '
            f'height="36" rx="8" fill="var(--accent-soft)" '
            f'stroke="var(--accent)" stroke-width="1.5"/>'
            f'<text x="{x1 + w / 2:.1f}" y="{y + 5:.1f}" '
            f'text-anchor="middle" font-size="13" fill="var(--ink)">'
            f'{_escape(event.label)}</text>'
        )

    # Messages
    marker_id = f"arrow-timeline-{slide_id}"
    messages_html = ""
    for msg in v.messages:
        x = t_to_x(msg.at)
        y1 = top_margin + msg.source_lane_index * lane_height
        y2 = top_margin + msg.target_lane_index * lane_height
        messages_html += (
            f'<g class="diagram-edge">'
            f'<line x1="{x:.1f}" y1="{y1:.1f}" x2="{x:.1f}" y2="{y2:.1f}"'
            f' marker-end="url(#{_escape(marker_id)})"/>'
            f'<text x="{x + 8:.1f}" y="{(y1 + y2) / 2:.1f}" '
            f'font-size="12" fill="var(--muted)">{_escape(msg.label)}</text>'
            f'</g>'
        )

    return _svg_wrap(
        lanes_html + events_html + messages_html,
        slide_id,
        marker_id,
        "timeline",
    )


register_renderer("timeline", _render_timeline)


# ---------------------------------------------------------------------------
# 5. memory_layout
# ---------------------------------------------------------------------------


def _render_memory_layout(visual: VisualModel, slide_id: str) -> str:
    v = visual  # type: ignore[assignment]
    assert isinstance(v, MemoryLayoutVisual)
    total_size = sum(seg.size for seg in v.segments) or 1
    max_height = 440
    top_margin = 60
    left_x = 270
    seg_width = 430

    segments_html = ""
    seg_positions: dict[int, tuple[float, float, float]] = {}  # (y_center, top, bottom)
    y_cursor = top_margin
    for i, seg in enumerate(v.segments):
        h = max(seg.size / total_size * max_height, 30)
        y_center = y_cursor + h / 2
        seg_positions[i] = (y_center, y_cursor, y_cursor + h)
        segments_html += (
            f'<rect x="{left_x:.1f}" y="{y_cursor:.1f}" '
            f'width="{seg_width}" height="{h:.1f}" rx="4" '
            f'fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="1.5"/>'
            f'<text x="{left_x + seg_width / 2:.1f}" y="{y_center + 5:.1f}" '
            f'text-anchor="middle" font-size="16" fill="var(--ink)">'
            f'{_escape(seg.label)}</text>'
            f'<text x="{left_x + seg_width + 10:.1f}" y="{y_center + 5:.1f}" '
            f'font-size="13" fill="var(--muted)">{_escape(str(seg.size))}</text>'
        )
        y_cursor += h + 8

    marker_id = f"arrow-mem-{slide_id}"
    refs_html = ""
    for ref in v.references:
        _, src_top, src_bottom = seg_positions[ref.source_segment_index]
        _, tgt_top, tgt_bottom = seg_positions[ref.target_segment_index]
        connector_x = left_x + seg_width / 2
        if tgt_top >= src_bottom:
            src_y, tgt_y = src_bottom, tgt_top
        else:
            src_y, tgt_y = src_top, tgt_bottom
        refs_html += _svg_edge(
            connector_x, src_y,
            connector_x, tgt_y,
            label=ref.label or ref.relation,
            marker_id=marker_id,
        )

    return _svg_wrap(
        segments_html + refs_html,
        slide_id,
        marker_id,
        "memory layout",
    )


register_renderer("memory_layout", _render_memory_layout)


# ---------------------------------------------------------------------------
# 6. data_flow
# ---------------------------------------------------------------------------


def _render_data_flow(visual: VisualModel, slide_id: str) -> str:
    v = visual  # type: ignore[assignment]
    assert isinstance(v, DataFlowVisual)
    positions = _layout_flow(
        v.blocks,
        [(f.source_block_index, f.target_block_index) for f in v.flows],
    )
    marker_id = f"arrow-df-{slide_id}"

    # Render blocks with port dots
    blocks_html = ""
    for i, block in enumerate(v.blocks):
        x, y = positions[i]
        bw, bh = 160, 80
        half_w, half_h = bw / 2, bh / 2
        # Input ports on left
        input_dots = ""
        for pi, pname in enumerate(block.input_ports):
            py = y - half_h + (pi + 1) * bh / (len(block.input_ports) + 1)
            input_dots += (
                f'<circle cx="{x - half_w:.1f}" cy="{py:.1f}" r="5" '
                f'fill="var(--accent)"/>'
                f'<text x="{x - half_w - 8:.1f}" y="{py + 4:.1f}" '
                f'text-anchor="end" font-size="11" fill="var(--muted)">'
                f'{_escape(pname)}</text>'
            )
        # Output ports on right
        output_dots = ""
        for pi, pname in enumerate(block.output_ports):
            py = y - half_h + (pi + 1) * bh / (len(block.output_ports) + 1)
            output_dots += (
                f'<circle cx="{x + half_w:.1f}" cy="{py:.1f}" r="5" '
                f'fill="var(--accent)"/>'
                f'<text x="{x + half_w + 8:.1f}" y="{py + 4:.1f}" '
                f'font-size="11" fill="var(--muted)">{_escape(pname)}</text>'
            )
        blocks_html += (
            f'<g class="diagram-node tone-default" '
            f'transform="translate({x:.1f} {y:.1f})">'
            f'<rect x="{-half_w:.1f}" y="{-half_h:.1f}" '
            f'width="{bw:.1f}" height="{bh:.1f}" rx="12"/>'
            f'<foreignObject x="{-half_w + 8:.1f}" y="{-half_h + 8:.1f}" '
            f'width="{bw - 16:.1f}" height="{bh - 16:.1f}">'
            f'<div xmlns="http://www.w3.org/1999/xhtml" class="diagram-node-copy">'
            f'<strong>{_escape(block.label)}</strong></div></foreignObject>'
            f'</g>'
            f'{input_dots}{output_dots}'
        )

    # Render flows
    flows_html = ""
    for flow in v.flows:
        sx, sy = positions[flow.source_block_index]
        tx, ty = positions[flow.target_block_index]
        # Approximate port positions
        src_port_count = len(v.blocks[flow.source_block_index].output_ports)
        src_py = sy - 40 + (flow.source_port_index + 1) * 80 / (src_port_count + 1)
        tgt_port_count = len(v.blocks[flow.target_block_index].input_ports)
        tgt_py = ty - 40 + (flow.target_port_index + 1) * 80 / (tgt_port_count + 1)
        flows_html += _svg_edge(
            sx + 80, src_py,
            tx - 80, tgt_py,
            label=flow.label or None,
            marker_id=marker_id,
        )

    return _svg_wrap(
        blocks_html + flows_html,
        slide_id,
        marker_id,
        "data flow",
    )


register_renderer("data_flow", _render_data_flow)


# ---------------------------------------------------------------------------
# 7. mapping
# ---------------------------------------------------------------------------


def _render_mapping(visual: VisualModel, slide_id: str) -> str:
    v = visual  # type: ignore[assignment]
    assert isinstance(v, MappingVisual)
    left_count = len(v.left_elements)
    right_count = len(v.right_elements)
    max_count = max(left_count, right_count, 1)
    row_height = 115
    top_margin = 180
    left_x = 200
    right_x = 800
    svg_height = 560

    # Set labels
    labels_html = (
        f'<text x="{left_x:.1f}" y="90" text-anchor="middle" '
        f'font-size="18" font-weight="bold" fill="var(--ink)">'
        f'{_escape(v.left_set_label)}</text>'
        f'<text x="{right_x:.1f}" y="90" text-anchor="middle" '
        f'font-size="18" font-weight="bold" fill="var(--ink)">'
        f'{_escape(v.right_set_label)}</text>'
    )

    # Elements
    left_positions: dict[int, float] = {}
    right_positions: dict[int, float] = {}
    elements_html = ""
    for i, elem in enumerate(v.left_elements):
        y = top_margin + i * row_height
        left_positions[i] = y
        elements_html += (
            f'<rect x="{left_x - 110:.1f}" y="{y - 29:.1f}" '
            f'width="220" height="58" rx="12" '
            f'fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="1.5"/>'
            f'<text x="{left_x:.1f}" y="{y + 5:.1f}" text-anchor="middle" '
            f'font-size="18" fill="var(--ink)">{_escape(elem)}</text>'
        )
    for i, elem in enumerate(v.right_elements):
        y = top_margin + i * row_height
        right_positions[i] = y
        elements_html += (
            f'<rect x="{right_x - 110:.1f}" y="{y - 29:.1f}" '
            f'width="220" height="58" rx="12" '
            f'fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="1.5"/>'
            f'<text x="{right_x:.1f}" y="{y + 5:.1f}" text-anchor="middle" '
            f'font-size="18" fill="var(--ink)">{_escape(elem)}</text>'
        )

    # Pair connections
    marker_id = f"arrow-map-{slide_id}"
    pairs_html = ""
    for pair in v.pairs:
        sy = left_positions[pair.source_index]
        ty = right_positions[pair.target_index]
        pairs_html += _svg_edge(
            left_x + 110, sy,
            right_x - 110, ty,
            marker_id=marker_id,
        )

    return (
        f'<svg class="diagram" viewBox="0 0 1000 {svg_height:.0f}" '
        f'role="img" aria-label="mapping">'
        f'<defs>{_svg_arrow_marker(marker_id)}</defs>'
        f'{labels_html}{elements_html}{pairs_html}</svg>'
    )


register_renderer("mapping", _render_mapping)


# ---------------------------------------------------------------------------
# 8. table_matrix
# ---------------------------------------------------------------------------


def _render_table_matrix(visual: VisualModel, slide_id: str) -> str:
    v = visual  # type: ignore[assignment]
    assert isinstance(v, TableMatrixVisual)
    header_cells = "".join(
        f'<th>{_escape(h)}</th>' for h in v.headers
    )
    rows_html = ""
    for ri, row in enumerate(v.rows):
        row_class = "highlighted" if ri in v.highlighted_row_indices else ""
        cells_html = ""
        for ci, cell in enumerate(row.cells):
            cell_class = "highlighted" if ci in v.highlighted_column_indices else ""
            cls = f' class="{cell_class}"' if cell_class else ""
            cells_html += f'<td{cls}>{_escape(cell)}</td>'
        row_cls = f' class="{row_class}"' if row_class else ""
        rows_html += f'<tr{row_cls}>{cells_html}</tr>'

    return (
        f'<section class="table-matrix-panel">'
        f'<table><thead><tr>{header_cells}</tr></thead>'
        f'<tbody>{rows_html}</tbody></table></section>'
    )


register_renderer("table_matrix", _render_table_matrix)


# ---------------------------------------------------------------------------
# 9. algorithm_frames
# ---------------------------------------------------------------------------


def _render_algorithm_frames(visual: VisualModel, slide_id: str) -> str:
    v = visual  # type: ignore[assignment]
    assert isinstance(v, AlgorithmFramesVisual)
    frames_html = ""
    for fi, frame in enumerate(v.frames):
        cells_html = ""
        for ci, cell in enumerate(frame.cells):
            cell_cls = (
                "highlighted" if ci in frame.highlighted_cell_indices else ""
            )
            cls_attr = f' class="{cell_cls}"' if cell_cls else ""
            cells_html += f'<span{cls_attr}>{_escape(cell)}</span>'
        arrow = ""
        if fi < len(v.frames) - 1:
            arrow = '<span class="frame-arrow">&rarr;</span>'
        frames_html += (
            f'<article class="algo-frame">'
            f'<h4>{_escape(frame.title)}</h4>'
            f'<div class="algo-cells">{cells_html}</div>'
            f'</article>{arrow}'
        )
    return (
        f'<section class="algorithm-frames-panel">'
        f'<div class="frames-row">{frames_html}</div></section>'
    )


register_renderer("algorithm_frames", _render_algorithm_frames)


# ---------------------------------------------------------------------------
# 10. circuit
# ---------------------------------------------------------------------------


def _render_circuit(visual: VisualModel, slide_id: str) -> str:
    v = visual  # type: ignore[assignment]
    assert isinstance(v, CircuitVisual)
    input_count = len(v.inputs)
    gate_count = len(v.gates)
    output_count = len(v.outputs)

    left_x = 120
    gate_x = 500
    right_x = 880
    top_margin = 80
    input_spacing = 440 / max(input_count, 1)
    gate_spacing = 440 / max(gate_count, 1) if gate_count else 0
    output_spacing = 440 / max(output_count, 1)

    # Input positions
    input_positions: dict[int, tuple[float, float]] = {}
    inputs_html = ""
    for i, inp in enumerate(v.inputs):
        y = top_margin + i * input_spacing + input_spacing / 2
        input_positions[i] = (left_x, y)
        inputs_html += _svg_node(left_x, y, inp.label, width=120, height=50)

    # Gate positions
    gate_positions: dict[int, tuple[float, float]] = {}
    gates_html = ""
    for i, gate in enumerate(v.gates):
        y = top_margin + i * gate_spacing + gate_spacing / 2
        gate_positions[i] = (gate_x, y)
        gates_html += _svg_node(
            gate_x, y, gate.label, detail=gate.gate_type,
            tone="accent", width=140, height=60,
        )

    # Output positions
    output_positions: dict[int, tuple[float, float]] = {}
    outputs_html = ""
    for i, out in enumerate(v.outputs):
        y = top_margin + i * output_spacing + output_spacing / 2
        output_positions[i] = (right_x, y)
        outputs_html += _svg_node(right_x, y, out.label, width=120, height=50)

    # Wires
    marker_id = f"arrow-circuit-{slide_id}"
    wires_html = ""
    kind_positions = {"input": input_positions, "gate": gate_positions}
    target_positions = {"gate": gate_positions, "output": output_positions}
    for wire in v.wires:
        sx, sy = kind_positions[wire.source_kind][wire.source_index]
        tx, ty = target_positions[wire.target_kind][wire.target_index]
        wires_html += _svg_edge(
            sx + 60, sy,
            tx - 60, ty,
            marker_id=marker_id,
        )

    return _svg_wrap(
        wires_html + inputs_html + gates_html + outputs_html,
        slide_id,
        marker_id,
        "circuit",
    )


register_renderer("circuit", _render_circuit)


# ---------------------------------------------------------------------------
# 11. quantitative
# ---------------------------------------------------------------------------


_SERIES_COLORS = [
    "var(--accent)",
    "var(--warm)",
    "var(--warning)",
    "#6b5ce7",
    "#2d8cf0",
    "#19be6b",
]


def _render_quantitative(visual: VisualModel, slide_id: str) -> str:
    v = visual  # type: ignore[assignment]
    assert isinstance(v, QuantitativeVisual)

    # Chart area
    chart_left = 100
    chart_right = 940
    chart_top = 60
    chart_bottom = 480
    chart_w = chart_right - chart_left
    chart_h = chart_bottom - chart_top

    # Determine data range
    all_x = [p.x_value for s in v.series for p in s.points]
    all_y = [p.y_value for s in v.series for p in s.points]
    x_min, x_max = min(all_x), max(all_x)
    y_min, y_max = min(all_y), max(all_y)
    if x_max <= x_min:
        x_max = x_min + 1
    if y_max <= y_min:
        y_max = y_min + 1
    # Add 10% padding on y
    y_range = y_max - y_min
    y_min -= y_range * 0.05
    y_max += y_range * 0.05

    def x_to_px(xv: float) -> float:
        return chart_left + (xv - x_min) / (x_max - x_min) * chart_w

    def y_to_px(yv: float) -> float:
        return chart_bottom - (yv - y_min) / (y_max - y_min) * chart_h

    # Axes
    axes_html = (
        f'<line x1="{chart_left}" y1="{chart_bottom}" '
        f'x2="{chart_right}" y2="{chart_bottom}" '
        f'stroke="var(--line)" stroke-width="2"/>'
        f'<line x1="{chart_left}" y1="{chart_top}" '
        f'x2="{chart_left}" y2="{chart_bottom}" '
        f'stroke="var(--line)" stroke-width="2"/>'
        # X axis label
        f'<text x="{(chart_left + chart_right) / 2:.1f}" y="{chart_bottom + 40:.1f}" '
        f'text-anchor="middle" font-size="14" fill="var(--muted)">'
        f'{_escape(v.x_axis.label)}{_paren_unit(v.x_axis.unit)}</text>'
        # Y axis label
        f'<text x="{chart_left - 40:.1f}" y="{(chart_top + chart_bottom) / 2:.1f}" '
        f'text-anchor="middle" font-size="14" fill="var(--muted)" '
        f'transform="rotate(-90 {chart_left - 40:.1f} {(chart_top + chart_bottom) / 2:.1f})">'
        f'{_escape(v.y_axis.label)}{_paren_unit(v.y_axis.unit)}</text>'
    )

    # Grid lines (5 horizontal)
    grid_html = ""
    for i in range(5):
        gy = chart_top + i * chart_h / 4
        grid_html += (
            f'<line x1="{chart_left}" y1="{gy:.1f}" '
            f'x2="{chart_right}" y2="{gy:.1f}" '
            f'stroke="var(--line)" stroke-width="0.5" stroke-dasharray="4"/>'
        )

    # Series
    series_html = ""
    for si, series in enumerate(v.series):
        color = _SERIES_COLORS[si % len(_SERIES_COLORS)]
        points_str = " ".join(
            f"{x_to_px(p.x_value):.1f},{y_to_px(p.y_value):.1f}"
            for p in series.points
        )
        series_html += (
            f'<polyline points="{points_str}" fill="none" '
            f'stroke="{color}" stroke-width="3"/>'
        )
        # Data points
        for p in series.points:
            px = x_to_px(p.x_value)
            py = y_to_px(p.y_value)
            series_html += (
                f'<circle cx="{px:.1f}" cy="{py:.1f}" r="5" fill="{color}"/>'
            )
        # Legend
        legend_y = chart_top - 20
        legend_x = chart_left + si * 160
        series_html += (
            f'<circle cx="{legend_x:.1f}" cy="{legend_y:.1f}" r="5" fill="{color}"/>'
            f'<text x="{legend_x + 10:.1f}" y="{legend_y + 4:.1f}" '
            f'font-size="13" fill="var(--ink)">{_escape(series.label)}</text>'
        )

    return _svg_wrap(
        axes_html + grid_html + series_html,
        slide_id,
        aria_label="quantitative chart",
    )


register_renderer("quantitative", _render_quantitative)


# ---------------------------------------------------------------------------
# 12. code
# ---------------------------------------------------------------------------


def _code_token_class(token_type: object) -> str | None:
    """Map Pygments token families to the compact deck colour palette."""
    if token_type in Comment:
        return "tok-comment"
    if token_type in Keyword:
        return "tok-keyword"
    if token_type in String:
        return "tok-string"
    if token_type in Number:
        return "tok-number"
    if token_type in Operator:
        return "tok-operator"
    if token_type in Name.Function:
        return "tok-function"
    if token_type in Name.Class:
        return "tok-class"
    if token_type in Name.Builtin:
        return "tok-builtin"
    if token_type in Name.Decorator:
        return "tok-decorator"
    return None


def _highlight_code_lines(lines: list[str], language: str) -> list[str]:
    """Return escaped, syntax-coloured HTML for each source line.

    The tokenisation happens while generating the deck, so exported HTML stays
    self-contained and does not rely on a browser-side highlighting library.
    """
    source = "\n".join(lines)
    try:
        lexer = get_lexer_by_name(language, stripall=False)
    except ClassNotFound:
        lexer = TextLexer(stripall=False)

    rendered: list[list[str]] = [[]]
    for token_type, value in lex(source, lexer):
        token_class = _code_token_class(token_type)
        for fragment in value.splitlines(keepends=True):
            text = fragment.rstrip("\r\n")
            if text:
                escaped = _escape(text)
                rendered[-1].append(
                    f'<span class="{token_class}">{escaped}</span>'
                    if token_class
                    else escaped
                )
            if fragment.endswith(("\n", "\r")):
                rendered.append([])

    # Pygments preserves the input line structure, but keep the renderer
    # deterministic even if a lexer emits an unexpected trailing newline.
    return ["".join(line) for line in rendered[: len(lines)]] + [
        "" for _ in range(len(lines) - len(rendered))
    ]


def _render_code(visual: VisualModel, slide_id: str) -> str:
    v = visual  # type: ignore[assignment]
    assert isinstance(v, CodeVisual)
    highlighted_lines = set(v.highlighted_line_indices)
    panel_height = min(640, max(220, 86 + len(v.lines) * 31))
    lines_html = "\n".join(
        f'<span class="code-line{" highlighted" if index in highlighted_lines else ""}">'
        f"{line}</span>"
        for index, line in enumerate(_highlight_code_lines(v.lines, v.language))
    )
    return (
        f'<section class="code-panel" style="--code-lines:{len(v.lines)};'
        f'--code-panel-height:{panel_height}px">'
        f'<div class="code-head"><i></i><i></i><i></i>'
        f'<b>{_escape(v.language)}</b></div>'
        f'<pre><code>{lines_html}</code></pre></section>'
    )


register_renderer("code", _render_code)


# ---------------------------------------------------------------------------
# 13. formula
# ---------------------------------------------------------------------------


def _render_formula(visual: VisualModel, slide_id: str) -> str:
    v = visual  # type: ignore[assignment]
    assert isinstance(v, FormulaVisual)
    steps_html = ""
    for step in v.steps:
        steps_html += (
            f'<li><strong>{_escape(step.expression)}</strong>'
            f' &mdash; {_escape(step.explanation)}</li>'
        )
    variables_html = ""
    for var in v.variables:
        variables_html += (
            f'<dt>{_escape(var.symbol)}</dt>'
            f'<dd>{_escape(var.meaning)}</dd>'
        )
    return (
        f'<section class="formula-panel">'
        f'<div class="formula">{_escape(v.expression)}</div>'
        f'<ol>{steps_html}</ol>'
        f'<dl class="formula-variables">{variables_html}</dl>'
        f'</section>'
    )


register_renderer("formula", _render_formula)


# ---------------------------------------------------------------------------
# 14. composite
# ---------------------------------------------------------------------------


def _render_composite(visual: VisualModel, slide_id: str) -> str:
    v = visual  # type: ignore[assignment]
    assert isinstance(v, CompositeVisual)
    total_weight = sum(p.width_weight for p in v.panels) or 1
    panels_html = ""
    for panel in v.panels:
        flex_pct = panel.width_weight / total_weight * 100
        leaf_html = render_visual(panel.visual, slide_id)
        panels_html += (
            f'<article class="composite-panel" '
            f'style="flex: 0 0 {flex_pct:.1f}%;">'
            f'<h4>{_escape(panel.title)}</h4>'
            f'{leaf_html}</article>'
        )
    return (
        f'<section class="composite-visual">'
        f'<div class="composite-panels">{panels_html}</div></section>'
    )


register_renderer("composite", _render_composite)
