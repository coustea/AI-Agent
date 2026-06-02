<template>
  <article class="insight-canvas" :class="{ compact: props.compact }">
    <header class="canvas-header animate-block">
      <div>
        <p class="canvas-kicker">{{ diagramTypeLabel(props.diagram.type) }}</p>
        <h3>{{ props.diagram.title }}</h3>
      </div>
      <p class="focus-question">{{ props.diagram.focus_question }}</p>
    </header>

    <section class="takeaway animate-block" style="animation-delay: 0.1s;">
      <span class="takeaway-label">先记住</span>
      <strong>{{ props.diagram.takeaway }}</strong>
    </section>

    <section v-if="nodeGraphPayload" class="diagram-section animate-block" style="animation-delay: 0.2s;">
      <div class="node-stage">
        <svg class="edge-layer" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          <defs>
            <marker id="arrowhead" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
              <path d="M0,0 L6,3 L0,6 Z" fill="currentColor" />
            </marker>
          </defs>
          <g v-for="edge in graphEdges" :key="edge.id" :class="['graph-edge', edge.arrowType, { flowing: edge.isFlowing, backtrack: edge.isBacktrack }]">
            <line :x1="edge.x1" :y1="edge.y1" :x2="edge.x2" :y2="edge.y2" :marker-end="edge.hasArrow ? 'url(#arrowhead)' : undefined" />
            <text v-if="edge.label" :x="edge.labelX" :y="edge.labelY">{{ edge.label }}</text>
          </g>
        </svg>
        <div
          v-for="node in nodeGraphPayload.nodes"
          :key="node.id"
          class="graph-node"
          :class="[node.shape, node.state]"
          :style="nodeStyle(node)"
          :title="node.tooltip || node.label"
        >
          <strong>{{ node.label }}</strong>
          <ul v-if="node.fields?.length">
            <li v-for="field in node.fields" :key="field">{{ field }}</li>
          </ul>
        </div>
      </div>
    </section>

    <section v-else-if="sequencePayload" class="diagram-section animate-block" style="animation-delay: 0.2s;">
      <div class="participant-row">
        <span v-for="participant in sequencePayload.participants" :key="participant">{{ participant }}</span>
      </div>
      <ol class="sequence-list">
        <li v-for="step in sequencePayload.steps" :key="step.step_index" :class="{ highlight: step.message.highlight }">
          <div class="step-index">{{ step.step_index }}</div>
          <div class="message-card">
            <span class="message-route">{{ step.message.sender }} -> {{ step.message.receiver }}</span>
            <strong>{{ step.message.label }}</strong>
            <p v-if="step.message.details">{{ step.message.details }}</p>
            <div v-if="step.active_states.length" class="state-row">
              <span v-for="state in step.active_states" :key="`${step.step_index}-${state.participant}`">
                {{ state.participant }}: {{ state.state_label }}
              </span>
            </div>
          </div>
        </li>
      </ol>
      <p class="board-result">{{ sequencePayload.final_state }}</p>
    </section>

    <section v-else-if="gridPayload" class="diagram-section animate-block" style="animation-delay: 0.2s;">
      <div class="grid-wrap">
        <table>
          <thead>
            <tr>
              <th></th>
              <th v-for="col in gridPayload.cols" :key="col">{{ col }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in gridPayload.rows" :key="row">
              <th>{{ row }}</th>
              <td v-for="col in gridPayload.cols" :key="`${row}-${col}`" :class="gridCell(row, col)?.state || 'empty'" :title="gridCell(row, col)?.tooltip || ''">
                <span>{{ gridCell(row, col)?.label || '' }}</span>
                <small v-if="gridCell(row, col)?.pointer_target">-> {{ gridCell(row, col)?.pointer_target }}</small>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="gridPayload.call_stack?.length" class="call-stack">
        <span v-for="frame in gridPayload.call_stack" :key="frame">{{ frame }}</span>
      </div>
      <p class="board-result">{{ gridPayload.timeline_summary }}</p>
    </section>

    <footer v-if="!props.compact" class="canvas-footer animate-block" style="animation-delay: 0.4s;">
      <div>
        <span class="footer-label">为什么成立</span>
        <p>{{ props.diagram.why_it_works }}</p>
      </div>
      <div v-if="props.diagram.pitfall" class="pitfall">
        <span class="footer-label pitfall-label">容易踩坑</span>
        <p>{{ props.diagram.pitfall }}</p>
      </div>
      <div class="try-it">
        <span class="footer-label">现在试试</span>
        <p>{{ props.diagram.try_it }}</p>
      </div>
      <div v-if="props.diagram.personalization_note" class="personal-note">
        <span class="footer-label">与你相关</span>
        <p>{{ props.diagram.personalization_note }}</p>
      </div>
    </footer>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import type { GraphNode, GridTimelinePayload, NodeGraphPayload, SequenceTimelinePayload, TeachingDiagram } from '@/api/chat'

const props = defineProps<{
  diagram: TeachingDiagram
  compact?: boolean
}>()

const nodeGraphPayload = computed(() => isNodeGraphPayload(props.diagram.payload) ? props.diagram.payload : null)
const sequencePayload = computed(() => isSequenceTimelinePayload(props.diagram.payload) ? props.diagram.payload : null)
const gridPayload = computed(() => isGridTimelinePayload(props.diagram.payload) ? props.diagram.payload : null)
const graphEdges = computed(() => {
  if (!nodeGraphPayload.value) return []
  const nodes = new Map(nodeGraphPayload.value.nodes.map(node => [node.id, node]))
  return nodeGraphPayload.value.edges.flatMap((edge, index) => {
    const source = nodes.get(edge.source)
    const target = nodes.get(edge.target)
    if (!source || !target) return []
    return [{
      id: `${edge.source}-${edge.target}-${index}`,
      x1: source.x,
      y1: source.y,
      x2: target.x,
      y2: target.y,
      labelX: (source.x + target.x) / 2,
      labelY: (source.y + target.y) / 2,
      label: edge.label,
      arrowType: edge.arrow_type,
      isFlowing: edge.is_flowing,
      isBacktrack: edge.is_backtrack,
      hasArrow: edge.arrow_type !== 'none',
    }]
  })
})
const gridCellMap = computed(() => {
  const payload = gridPayload.value
  if (!payload) return new Map<string, GridTimelinePayload['cells'][number]>()
  return new Map(payload.cells.map(cell => [`${cell.row_label}::${cell.col_label}`, cell]))
})

function isNodeGraphPayload(payload: TeachingDiagram['payload']): payload is NodeGraphPayload {
  return props.diagram.type === 'node_graph' && Array.isArray((payload as NodeGraphPayload).nodes)
}

function isSequenceTimelinePayload(payload: TeachingDiagram['payload']): payload is SequenceTimelinePayload {
  return props.diagram.type === 'sequence_timeline' && Array.isArray((payload as SequenceTimelinePayload).steps)
}

function isGridTimelinePayload(payload: TeachingDiagram['payload']): payload is GridTimelinePayload {
  return props.diagram.type === 'grid_timeline' && Array.isArray((payload as GridTimelinePayload).cells)
}

function nodeStyle(node: GraphNode): Record<string, string> {
  return {
    left: `${Math.max(0, Math.min(100, node.x))}%`,
    top: `${Math.max(0, Math.min(100, node.y))}%`,
  }
}

function gridCell(row: string, col: string): GridTimelinePayload['cells'][number] | undefined {
  return gridCellMap.value.get(`${row}::${col}`)
}

function diagramTypeLabel(type: TeachingDiagram['type']): string {
  return {
    node_graph: '结构图板',
    sequence_timeline: '时序图板',
    grid_timeline: '推演图板',
  }[type]
}
</script>

<style scoped>
@keyframes slideUpFade {
  0% { opacity: 0; transform: translateY(12px); }
  100% { opacity: 1; transform: translateY(0); }
}

.animate-block { animation: slideUpFade 0.45s cubic-bezier(0.16, 1, 0.3, 1) both; }

.insight-canvas {
  --c-primary: #2563EB;
  --c-teal: #0F766E;
  --c-amber: #D97706;
  --c-red: #DC2626;
  --c-ink: #111827;
  --c-muted: #64748B;
  --c-border: #D8DEE9;
  --c-bg: #F8FAFC;
  display: grid;
  gap: 16px;
  padding: clamp(16px, 3vw, 24px);
  color: var(--c-ink);
  background: #ffffff;
  border: 1px solid var(--c-border);
  border-radius: 8px;
}

.canvas-header {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: end;
}

.canvas-kicker {
  margin: 0 0 6px;
  color: var(--c-primary);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: .08em;
}

h3, p { margin: 0; }

h3 {
  color: var(--c-ink);
  font-size: clamp(19px, 3vw, 24px);
  letter-spacing: 0;
}

.focus-question {
  max-width: 45%;
  padding: 9px 12px;
  color: var(--c-muted);
  background: var(--c-bg);
  border: 1px solid var(--c-border);
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.5;
}

.takeaway {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 12px 14px;
  background: #EFF6FF;
  border: 1px solid #BFDBFE;
  border-radius: 8px;
}

.takeaway-label, .footer-label {
  flex-shrink: 0;
  color: var(--c-primary);
  font-size: 13px;
  font-weight: 700;
}

.takeaway strong {
  font-weight: 650;
  line-height: 1.5;
}

.diagram-section {
  display: grid;
  gap: 12px;
}

.node-stage {
  position: relative;
  height: clamp(260px, 42vw, 420px);
  overflow: hidden;
  background:
    linear-gradient(#E5E7EB 1px, transparent 1px),
    linear-gradient(90deg, #E5E7EB 1px, transparent 1px),
    #F9FAFB;
  background-size: 32px 32px;
  border: 1px solid var(--c-border);
  border-radius: 8px;
}

.edge-layer {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  color: #475569;
}

.graph-edge line {
  stroke: currentColor;
  stroke-width: 1.2;
  vector-effect: non-scaling-stroke;
}

.graph-edge text {
  fill: #334155;
  font-size: 3px;
  paint-order: stroke;
  stroke: #F9FAFB;
  stroke-width: .8px;
}

.graph-edge.dependency line { stroke-dasharray: 4 3; }
.graph-edge.inheritance { color: var(--c-primary); }
.graph-edge.aggregation, .graph-edge.composition { color: var(--c-teal); }
.graph-edge.backtrack { color: var(--c-amber); }
.graph-edge.flowing line { stroke-width: 1.7; }

.graph-node {
  position: absolute;
  min-width: 88px;
  max-width: 150px;
  padding: 9px 10px;
  color: var(--c-ink);
  text-align: center;
  background: #ffffff;
  border: 1px solid #94A3B8;
  border-radius: 8px;
  transform: translate(-50%, -50%);
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.08);
}

.graph-node strong {
  display: block;
  overflow-wrap: anywhere;
  font-size: 13px;
  line-height: 1.35;
}

.graph-node ul {
  display: grid;
  gap: 3px;
  margin: 6px 0 0;
  padding: 6px 0 0;
  border-top: 1px solid #E2E8F0;
  list-style: none;
}

.graph-node li {
  overflow-wrap: anywhere;
  color: var(--c-muted);
  font-size: 11px;
  line-height: 1.3;
}

.graph-node.circle {
  min-width: 74px;
  min-height: 74px;
  display: grid;
  place-items: center;
  border-radius: 50%;
}

.graph-node.diamond {
  border-radius: 6px;
  transform: translate(-50%, -50%) rotate(45deg);
}

.graph-node.diamond strong,
.graph-node.diamond ul {
  transform: rotate(-45deg);
}

.graph-node.capsule { border-radius: 999px; }
.graph-node.actor { border-style: dashed; }
.graph-node.cylinder { border-bottom-width: 4px; }
.graph-node.uml_class { min-width: 128px; }
.graph-node.active { border-color: var(--c-primary); box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.16); }
.graph-node.visited { border-color: var(--c-teal); }

.participant-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.participant-row span,
.state-row span,
.call-stack span {
  padding: 6px 9px;
  color: #0F172A;
  background: #ECFDF5;
  border: 1px solid #A7F3D0;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 650;
}

.sequence-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.sequence-list li {
  display: grid;
  grid-template-columns: 34px 1fr;
  gap: 10px;
  align-items: stretch;
}

.sequence-list li.highlight .message-card {
  border-color: #93C5FD;
  background: #EFF6FF;
}

.step-index {
  display: grid;
  place-items: center;
  color: #ffffff;
  background: var(--c-primary);
  border-radius: 8px;
  font-weight: 800;
}

.message-card {
  display: grid;
  gap: 6px;
  padding: 12px 14px;
  background: var(--c-bg);
  border: 1px solid var(--c-border);
  border-radius: 8px;
}

.message-route {
  color: var(--c-muted);
  font-size: 12px;
  font-weight: 650;
}

.message-card strong {
  font-size: 16px;
}

.message-card p {
  color: var(--c-muted);
  font-size: 13px;
  line-height: 1.5;
}

.state-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.grid-wrap {
  overflow: auto;
  border: 1px solid var(--c-border);
  border-radius: 8px;
}

table {
  width: 100%;
  min-width: 520px;
  border-collapse: collapse;
}

th, td {
  min-width: 86px;
  padding: 10px;
  border: 1px solid #E2E8F0;
  text-align: center;
  vertical-align: middle;
}

th {
  color: #334155;
  background: #F1F5F9;
  font-size: 12px;
  font-weight: 750;
}

td span {
  display: block;
  overflow-wrap: anywhere;
  font-size: 13px;
  font-weight: 650;
}

td small {
  display: block;
  margin-top: 4px;
  color: var(--c-muted);
  font-size: 11px;
}

td.empty { background: #ffffff; }
td.running, td.highlight { background: #EFF6FF; color: #1D4ED8; }
td.ready, td.allocated { background: #ECFDF5; color: #047857; }
td.blocked { background: #FEF2F2; color: #B91C1C; }
td.free { background: #F8FAFC; color: #64748B; }
td.pointer { background: #FFFBEB; color: #B45309; }

.call-stack {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.board-result {
  padding: 12px 14px;
  color: var(--c-ink);
  background: var(--c-bg);
  border: 1px solid var(--c-border);
  border-radius: 8px;
  font-size: 14px;
  font-weight: 550;
  line-height: 1.6;
}

.canvas-footer {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
}

.canvas-footer > div {
  min-height: 86px;
  padding: 13px;
  background: var(--c-bg);
  border: 1px solid var(--c-border);
  border-radius: 8px;
}

.canvas-footer p {
  margin-top: 7px;
  color: var(--c-muted);
  font-size: 14px;
  line-height: 1.55;
}

.pitfall-label { color: var(--c-amber) !important; }

.compact {
  gap: 12px;
  padding: 14px;
  border: 0;
  box-shadow: none;
}

.compact .canvas-header {
  align-items: start;
}

.compact h3 {
  font-size: 18px;
}

.compact .focus-question,
.compact .canvas-kicker {
  display: none;
}

.compact .node-stage {
  height: 240px;
}

@media (max-width: 640px) {
  .canvas-header,
  .takeaway {
    flex-direction: column;
    align-items: start;
  }

  .focus-question {
    max-width: none;
  }

  .graph-node {
    min-width: 72px;
    max-width: 118px;
  }
}

@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; transition: none !important; }
}
</style>
