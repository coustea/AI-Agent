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
      <span>🎯 先记住</span>
      <strong>{{ props.diagram.takeaway }}</strong>
    </section>

    <section v-if="contrastPayload" class="contrast-board">
      <div class="contrast-card left animate-card" style="animation-delay: 0.2s;">
        <h4>{{ contrastPayload.left.label }}</h4>
        <p>{{ contrastPayload.left.definition }}</p>
        <ul>
          <li v-for="signal in contrastPayload.left.signals" :key="signal">{{ signal }}</li>
        </ul>
        <small>例：{{ contrastPayload.left.example }}</small>
      </div>
      <div class="decision-axis animate-block" style="animation-delay: 0.3s;">
        <span>判断线索</span>
        <p>{{ contrastPayload.decision_rule }}</p>
      </div>
      <div class="contrast-card right animate-card" style="animation-delay: 0.4s;">
        <h4>{{ contrastPayload.right.label }}</h4>
        <p>{{ contrastPayload.right.definition }}</p>
        <ul>
          <li v-for="signal in contrastPayload.right.signals" :key="signal">{{ signal }}</li>
        </ul>
        <small>例：{{ contrastPayload.right.example }}</small>
      </div>
      <p class="board-result animate-block" style="animation-delay: 0.5s;">{{ contrastPayload.scenario_conclusion }}</p>
    </section>

    <section v-else-if="journeyPayload" class="journey-board">
      <div class="journey-goal animate-block" style="animation-delay: 0.2s;">目标：{{ journeyPayload.goal }}</div>
      <ol>
        <li v-for="(step, index) in journeyPayload.steps" :key="`${index}-${step.title}`">
          <span class="step-index animate-block" :style="{ animationDelay: `${0.25 + index * 0.1}s` }">{{ index + 1 }}</span>
          <div class="step-card animate-card" :style="{ animationDelay: `${0.3 + index * 0.1}s` }">
            <h4>{{ step.title }}</h4>
            <p>{{ step.action }}</p>
            <small>{{ step.rationale }} -> {{ step.output }}</small>
            <em v-if="step.warning">注意：{{ step.warning }}</em>
          </div>
        </li>
      </ol>
      <p class="board-result animate-block" :style="{ animationDelay: `${0.4 + journeyPayload.steps.length * 0.1}s` }">{{ journeyPayload.result }}</p>
    </section>

    <section v-else-if="anatomyPayload" class="anatomy-board">
      <div class="subject-core animate-block" style="animation-delay: 0.2s;">{{ anatomyPayload.subject }}</div>
      <div class="part-grid">
        <article v-for="(part, index) in anatomyPayload.parts" :key="part.name" class="animate-card" :style="{ animationDelay: `${0.3 + index * 0.1}s` }">
          <h4>{{ part.name }}</h4>
          <strong>{{ part.responsibility }}</strong>
          <p>{{ part.detail }}</p>
          <small v-if="part.interaction_cue">{{ part.interaction_cue }}</small>
        </article>
      </div>
      <p class="board-result animate-block" :style="{ animationDelay: `${0.4 + anatomyPayload.parts.length * 0.1}s` }">{{ anatomyPayload.interaction_summary }}</p>
    </section>

    <section v-else-if="simulationPayload" class="simulation-board">
      <p class="initial-state animate-block" style="animation-delay: 0.2s;">{{ simulationPayload.scenario }}：{{ simulationPayload.initial_state }}</p>
      <div class="frame-track">
        <article v-for="(frame, index) in simulationPayload.frames" :key="frame.stage" class="animate-card" :style="{ animationDelay: `${0.3 + index * 0.1}s` }">
          <h4>{{ frame.stage }}</h4>
          <p>{{ frame.state }}</p>
          <strong>{{ frame.changed }}</strong>
          <small>{{ frame.reason }}</small>
          <em>观察：{{ frame.learner_focus }}</em>
        </article>
      </div>
      <p class="board-result animate-block" :style="{ animationDelay: `${0.4 + simulationPayload.frames.length * 0.1}s` }">{{ simulationPayload.result }}</p>
    </section>

    <footer v-if="!props.compact" class="canvas-footer animate-block" style="animation-delay: 0.8s;">
      <div>
        <span>💡 为什么成立</span>
        <p>{{ props.diagram.why_it_works }}</p>
      </div>
      <div v-if="props.diagram.pitfall" class="pitfall">
        <span>⚠️ 容易踩坑</span>
        <p>{{ props.diagram.pitfall }}</p>
      </div>
      <div class="try-it">
        <span>🚀 现在试试</span>
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
@keyframes slideUpFade {
  0% { opacity: 0; transform: translateY(16px); }
  100% { opacity: 1; transform: translateY(0); }
}

.animate-block {
  animation: slideUpFade 0.6s cubic-bezier(0.16, 1, 0.3, 1) both;
}

.animate-card {
  animation: slideUpFade 0.6s cubic-bezier(0.16, 1, 0.3, 1) both;
}

.insight-canvas {
  --canvas-ink: #1e293b;
  --canvas-muted: #64748b;
  --canvas-line: #f1f5f9;
  --canvas-accent: #0284c7;
  --canvas-warm: #ea580c;
  display: grid;
  gap: 18px;
  padding: clamp(18px, 3vw, 30px);
  color: var(--canvas-ink);
  background: #ffffff;
  border-radius: 24px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.04), 0 1px 3px rgba(0, 0, 0, 0.02);
  animation: slideUpFade 0.5s cubic-bezier(0.16, 1, 0.3, 1) both;
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
  font-size: 13px;
  font-weight: 700;
  letter-spacing: .16em;
}

h3, h4, p {
  margin: 0;
}

h3 {
  font-size: clamp(20px, 3vw, 26px);
  letter-spacing: -.03em;
  color: #0f172a;
}

.focus-question {
  max-width: 45%;
  padding: 10px 14px;
  color: var(--canvas-muted);
  background: #f8fafc;
  border: 1px solid var(--canvas-line);
  border-radius: 14px;
  font-size: 14px;
  line-height: 1.5;
}

.takeaway {
  display: flex;
  gap: 14px;
  align-items: center;
  padding: 14px 18px;
  background: #f0f9ff;
  color: #0f172a;
  border: 1px solid #e0f2fe;
  border-radius: 16px;
  box-shadow: 0 2px 8px rgba(2, 132, 199, 0.04);
}

.takeaway span, .canvas-footer span {
  flex-shrink: 0;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: .05em;
  color: var(--canvas-accent);
}

.takeaway strong {
  font-weight: 600;
  line-height: 1.5;
}

.contrast-board {
  display: grid;
  grid-template-columns: 1fr 152px 1fr;
  align-items: center;
  gap: 12px;
}

.contrast-card, .part-grid article, .frame-track article, .step-card {
  padding: 18px;
  background: #ffffff;
  border: 1px solid var(--canvas-line);
  border-radius: 16px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.03);
  transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.contrast-card:hover, .part-grid article:hover, .frame-track article:hover, .step-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.08);
}

.contrast-card h4, .part-grid h4, .step-card h4, .frame-track h4 {
  margin-bottom: 8px;
  font-size: 16px;
  color: #0f172a;
}

.contrast-card p, .part-grid p, .step-card p, .frame-track p {
  color: var(--canvas-muted);
  line-height: 1.6;
  font-size: 14px;
}

.contrast-card ul {
  margin: 12px 0;
  padding-left: 18px;
  color: #334155;
  font-size: 14px;
  line-height: 1.6;
}

.contrast-card small, .part-grid small, .step-card small, .frame-track small {
  display: block;
  margin-top: 12px;
  color: var(--canvas-accent);
  font-size: 13px;
  font-weight: 500;
}

.decision-axis {
  text-align: center;
}

.decision-axis span {
  display: inline-block;
  margin-bottom: 10px;
  padding: 6px 12px;
  color: #ffffff;
  background: var(--canvas-accent);
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  box-shadow: 0 4px 12px rgba(2, 132, 199, 0.2);
}

.decision-axis p {
  font-size: 13px;
  line-height: 1.5;
  color: #475569;
}

.board-result {
  grid-column: 1 / -1;
  padding: 14px 18px;
  color: #0f172a;
  background: #f8fafc;
  border: 1px solid var(--canvas-line);
  border-radius: 14px;
  font-weight: 500;
  font-size: 14px;
  line-height: 1.6;
}

.journey-goal, .initial-state, .subject-core {
  padding: 14px 18px;
  color: #0f172a;
  font-weight: 600;
  background: #f0f9ff;
  border: 1px solid #e0f2fe;
  border-radius: 14px;
  font-size: 15px;
}

.journey-board ol {
  display: flex;
  gap: 12px;
  margin: 18px 0;
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
  width: 28px;
  height: 28px;
  margin: 0 0 -12px 14px;
  position: relative;
  z-index: 1;
  color: #fff;
  background: var(--canvas-accent);
  border-radius: 99px;
  font-weight: 700;
  font-size: 13px;
  box-shadow: 0 4px 8px rgba(2, 132, 199, 0.3);
}

.step-card {
  min-height: 130px;
}

.step-card em, .frame-track em {
  display: block;
  margin-top: 12px;
  color: var(--canvas-warm);
  font-size: 13px;
  font-style: normal;
  font-weight: 500;
}

.part-grid, .frame-track {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 12px;
  margin: 18px 0;
}

.part-grid strong, .frame-track strong {
  display: block;
  margin-bottom: 8px;
  color: var(--canvas-accent);
  font-size: 14px;
  font-weight: 600;
}

.canvas-footer {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  padding-top: 6px;
}

.canvas-footer div {
  min-height: 90px;
  padding: 16px;
  background: #f8fafc;
  border: 1px solid var(--canvas-line);
  border-radius: 16px;
  transition: background 0.3s ease;
}

.canvas-footer div:hover {
  background: #ffffff;
  box-shadow: 0 4px 16px rgba(0,0,0,0.03);
}

.canvas-footer p {
  margin-top: 8px;
  color: var(--canvas-muted);
  font-size: 14px;
  line-height: 1.6;
}

.canvas-footer .pitfall span {
  color: var(--canvas-warm);
}

.compact {
  gap: 14px;
  padding: 16px;
  border: 0;
  border-radius: 0;
  box-shadow: none;
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
  padding-bottom: 12px;
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
    transition: none !important;
  }
}
</style>
