<template>
  <article class="insight-canvas" :class="{ compact: props.compact }">
    <header class="canvas-header">
      <div>
        <p class="canvas-kicker">{{ diagramTypeLabel(props.diagram.type) }}</p>
        <h3>{{ props.diagram.title }}</h3>
      </div>
      <p class="focus-question">{{ props.diagram.focus_question }}</p>
    </header>

    <section class="takeaway">
      <span>先记住</span>
      <strong>{{ props.diagram.takeaway }}</strong>
    </section>

    <section v-if="contrastPayload" class="contrast-board">
      <div class="contrast-card left">
        <h4>{{ contrastPayload.left.label }}</h4>
        <p>{{ contrastPayload.left.definition }}</p>
        <ul>
          <li v-for="signal in contrastPayload.left.signals" :key="signal">{{ signal }}</li>
        </ul>
        <small>例：{{ contrastPayload.left.example }}</small>
      </div>
      <div class="decision-axis">
        <span>判断线索</span>
        <p>{{ contrastPayload.decision_rule }}</p>
      </div>
      <div class="contrast-card right">
        <h4>{{ contrastPayload.right.label }}</h4>
        <p>{{ contrastPayload.right.definition }}</p>
        <ul>
          <li v-for="signal in contrastPayload.right.signals" :key="signal">{{ signal }}</li>
        </ul>
        <small>例：{{ contrastPayload.right.example }}</small>
      </div>
      <p class="board-result">{{ contrastPayload.scenario_conclusion }}</p>
    </section>

    <section v-else-if="journeyPayload" class="journey-board">
      <div class="journey-goal">目标：{{ journeyPayload.goal }}</div>
      <ol>
        <li v-for="(step, index) in journeyPayload.steps" :key="`${index}-${step.title}`">
          <span class="step-index">{{ index + 1 }}</span>
          <div class="step-card">
            <h4>{{ step.title }}</h4>
            <p>{{ step.action }}</p>
            <small>{{ step.rationale }} -> {{ step.output }}</small>
            <em v-if="step.warning">注意：{{ step.warning }}</em>
          </div>
        </li>
      </ol>
      <p class="board-result">{{ journeyPayload.result }}</p>
    </section>

    <section v-else-if="anatomyPayload" class="anatomy-board">
      <div class="subject-core">{{ anatomyPayload.subject }}</div>
      <div class="part-grid">
        <article v-for="part in anatomyPayload.parts" :key="part.name">
          <h4>{{ part.name }}</h4>
          <strong>{{ part.responsibility }}</strong>
          <p>{{ part.detail }}</p>
          <small v-if="part.interaction_cue">{{ part.interaction_cue }}</small>
        </article>
      </div>
      <p class="board-result">{{ anatomyPayload.interaction_summary }}</p>
    </section>

    <section v-else-if="simulationPayload" class="simulation-board">
      <p class="initial-state">{{ simulationPayload.scenario }}：{{ simulationPayload.initial_state }}</p>
      <div class="frame-track">
        <article v-for="frame in simulationPayload.frames" :key="frame.stage">
          <h4>{{ frame.stage }}</h4>
          <p>{{ frame.state }}</p>
          <strong>{{ frame.changed }}</strong>
          <small>{{ frame.reason }}</small>
          <em>观察：{{ frame.learner_focus }}</em>
        </article>
      </div>
      <p class="board-result">{{ simulationPayload.result }}</p>
    </section>

    <footer v-if="!props.compact" class="canvas-footer">
      <div>
        <span>为什么成立</span>
        <p>{{ props.diagram.why_it_works }}</p>
      </div>
      <div v-if="props.diagram.pitfall" class="pitfall">
        <span>容易踩坑</span>
        <p>{{ props.diagram.pitfall }}</p>
      </div>
      <div class="try-it">
        <span>现在试试</span>
        <p>{{ props.diagram.try_it }}</p>
      </div>
    </footer>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import type { TeachingDiagram } from '@/api/chat'

interface ContrastPayload {
  decision_rule: string
  left: { label: string; definition: string; signals: string[]; example: string }
  right: { label: string; definition: string; signals: string[]; example: string }
  scenario_conclusion: string
}

interface JourneyPayload {
  goal: string
  steps: Array<{ title: string; action: string; rationale: string; output: string; warning?: string | null }>
  result: string
}

interface AnatomyPayload {
  subject: string
  parts: Array<{ name: string; responsibility: string; detail: string; interaction_cue?: string | null }>
  interaction_summary: string
}

interface SimulationPayload {
  scenario: string
  initial_state: string
  frames: Array<{ stage: string; state: string; changed: string; reason: string; learner_focus: string }>
  result: string
}

const props = defineProps<{
  diagram: TeachingDiagram
  compact?: boolean
}>()

const contrastPayload = computed(() => props.diagram.type === 'contrast'
  ? props.diagram.payload as unknown as ContrastPayload
  : null)
const journeyPayload = computed(() => props.diagram.type === 'journey'
  ? props.diagram.payload as unknown as JourneyPayload
  : null)
const anatomyPayload = computed(() => props.diagram.type === 'anatomy'
  ? props.diagram.payload as unknown as AnatomyPayload
  : null)
const simulationPayload = computed(() => props.diagram.type === 'simulation'
  ? props.diagram.payload as unknown as SimulationPayload
  : null)

function diagramTypeLabel(type: TeachingDiagram['type']): string {
  return {
    contrast: '辨析图板',
    journey: '过程图板',
    anatomy: '结构图板',
    simulation: '推演图板',
  }[type]
}
</script>

<style scoped>
.insight-canvas {
  --canvas-ink: #16263d;
  --canvas-muted: #5c718c;
  --canvas-line: #d9e4ee;
  --canvas-accent: #087f76;
  --canvas-warm: #f47a52;
  display: grid;
  gap: 18px;
  padding: clamp(18px, 3vw, 30px);
  color: var(--canvas-ink);
  background:
    radial-gradient(circle at 92% 8%, rgba(244, 122, 82, 0.14), transparent 28%),
    linear-gradient(135deg, #fffdf9, #f1f8f7);
  border: 1px solid var(--canvas-line);
  border-radius: 24px;
}

.canvas-header {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: end;
}

.canvas-kicker {
  margin: 0 0 7px;
  color: var(--canvas-accent);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: .16em;
}

h3, h4, p {
  margin: 0;
}

h3 {
  font-size: clamp(20px, 3vw, 26px);
  letter-spacing: -.04em;
}

.focus-question {
  max-width: 45%;
  padding: 10px 14px;
  color: var(--canvas-muted);
  background: rgba(255,255,255,.7);
  border-radius: 14px;
}

.takeaway {
  display: flex;
  gap: 14px;
  align-items: center;
  padding: 13px 16px;
  background: #12333b;
  color: #f7fbf9;
  border-radius: 16px;
}

.takeaway span, .canvas-footer span {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: .09em;
  color: #78d5c7;
}

.contrast-board {
  display: grid;
  grid-template-columns: 1fr 152px 1fr;
  align-items: center;
  gap: 12px;
}

.contrast-card, .part-grid article, .frame-track article, .step-card {
  padding: 15px;
  background: rgba(255,255,255,.76);
  border: 1px solid var(--canvas-line);
  border-radius: 16px;
}

.contrast-card h4, .part-grid h4, .step-card h4, .frame-track h4 {
  margin-bottom: 8px;
  font-size: 16px;
}

.contrast-card p, .part-grid p, .step-card p, .frame-track p {
  color: var(--canvas-muted);
  line-height: 1.5;
}

.contrast-card ul {
  margin: 12px 0;
  padding-left: 18px;
  color: var(--canvas-ink);
}

.contrast-card small, .part-grid small, .step-card small, .frame-track small {
  display: block;
  margin-top: 9px;
  color: var(--canvas-accent);
}

.decision-axis {
  text-align: center;
}

.decision-axis span {
  display: inline-block;
  margin-bottom: 8px;
  padding: 5px 10px;
  color: var(--canvas-accent);
  background: #dff4ef;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.decision-axis p {
  font-size: 13px;
  line-height: 1.45;
}

.board-result {
  grid-column: 1 / -1;
  padding: 12px 15px;
  color: #914728;
  background: #fff0e7;
  border-radius: 13px;
}

.journey-goal, .initial-state, .subject-core {
  padding: 11px 15px;
  color: var(--canvas-accent);
  font-weight: 650;
  background: #e8f5f1;
  border-radius: 13px;
}

.journey-board ol {
  display: flex;
  gap: 10px;
  margin: 14px 0;
  padding: 0;
  list-style: none;
}

.journey-board li {
  position: relative;
  flex: 1;
}

.step-index {
  display: inline-grid;
  place-items: center;
  width: 27px;
  height: 27px;
  margin: 0 0 -10px 13px;
  position: relative;
  z-index: 1;
  color: #fff;
  background: var(--canvas-accent);
  border-radius: 99px;
}

.step-card {
  min-height: 122px;
}

.step-card em, .frame-track em {
  display: block;
  margin-top: 9px;
  color: #a45233;
  font-size: 12px;
  font-style: normal;
}

.part-grid, .frame-track {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 10px;
  margin: 14px 0;
}

.part-grid strong, .frame-track strong {
  display: block;
  margin-bottom: 7px;
  color: var(--canvas-accent);
  font-size: 13px;
}

.canvas-footer {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  padding-top: 3px;
}

.canvas-footer div {
  min-height: 84px;
  padding: 13px 14px;
  background: rgba(255,255,255,.64);
  border-radius: 14px;
}

.canvas-footer span {
  color: var(--canvas-accent);
}

.canvas-footer p {
  margin-top: 7px;
  color: var(--canvas-muted);
  font-size: 13px;
  line-height: 1.45;
}

.canvas-footer .pitfall span {
  color: var(--canvas-warm);
}

.compact {
  gap: 12px;
  padding: 15px;
  border: 0;
  border-radius: 0;
}

.compact .canvas-header {
  align-items: start;
}

.compact h3 {
  font-size: 18px;
}

.compact .focus-question {
  display: none;
}

.compact .journey-board ol {
  overflow-x: auto;
}

@media (max-width: 640px) {
  .canvas-header, .takeaway {
    flex-direction: column;
    align-items: start;
  }

  .focus-question {
    max-width: none;
  }

  .contrast-board, .canvas-footer {
    grid-template-columns: 1fr;
  }

  .journey-board ol {
    flex-direction: column;
  }
}

@media (prefers-reduced-motion: reduce) {
  * {
    animation: none !important;
  }
}
</style>
