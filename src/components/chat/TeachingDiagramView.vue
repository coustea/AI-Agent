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

    <!-- contrast: 双向条形图 -->
    <section v-if="contrastPayload" class="chart-section animate-block" style="animation-delay: 0.2s;">
      <v-chart class="diagram-chart" :option="contrastOption" :autoresize="true" />
      <p class="board-result">{{ contrastPayload.scenario_conclusion }}</p>
    </section>

    <!-- journey: 桑基图 -->
    <section v-else-if="journeyPayload" class="chart-section animate-block" style="animation-delay: 0.2s;">
      <div class="journey-goal">目标：{{ journeyPayload.goal }}</div>
      <v-chart class="diagram-chart" :option="journeyOption" :autoresize="true" />
      <div class="step-details" v-if="!props.compact">
        <el-collapse>
          <el-collapse-item v-for="(step, i) in journeyPayload.steps" :key="i" :title="`${i + 1}. ${step.title}`">
            <p><strong>动作：</strong>{{ step.action }}</p>
            <p><strong>原理：</strong>{{ step.rationale }}</p>
            <p><strong>产出：</strong>{{ step.output }}</p>
            <p v-if="step.warning" class="warning-text"><strong>注意：</strong>{{ step.warning }}</p>
          </el-collapse-item>
        </el-collapse>
      </div>
      <p class="board-result">{{ journeyPayload.result }}</p>
    </section>

    <!-- anatomy: 树图 -->
    <section v-else-if="anatomyPayload" class="chart-section animate-block" style="animation-delay: 0.2s;">
      <v-chart class="diagram-chart" :option="anatomyOption" :autoresize="true" />
      <p class="board-result">{{ anatomyPayload.interaction_summary }}</p>
    </section>

    <!-- simulation: 阶梯线图 -->
    <section v-else-if="simulationPayload" class="chart-section animate-block" style="animation-delay: 0.2s;">
      <div class="sim-header-info">
        <span>{{ simulationPayload.scenario }}</span>
        <small>初始状态：{{ simulationPayload.initial_state }}</small>
      </div>
      <v-chart class="diagram-chart" :option="simulationOption" :autoresize="true" />
      <div class="frame-details" v-if="!props.compact">
        <el-collapse>
          <el-collapse-item v-for="(frame, i) in simulationPayload.frames" :key="i" :title="frame.stage">
            <p><strong>状态快照：</strong>{{ frame.state }}</p>
            <p><strong>变化：</strong>{{ frame.changed }}</p>
            <p><strong>触发原因：</strong>{{ frame.reason }}</p>
            <p class="focus-text"><strong>观察重点：</strong>{{ frame.learner_focus }}</p>
          </el-collapse-item>
        </el-collapse>
      </div>
      <p class="board-result">{{ simulationPayload.result }}</p>
    </section>

    <footer v-if="!props.compact" class="canvas-footer animate-block" style="animation-delay: 0.8s;">
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
    </footer>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, SankeyChart, TreeChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, TitleComponent } from 'echarts/components'

import type { TeachingDiagram } from '@/api/chat'

use([CanvasRenderer, BarChart, SankeyChart, TreeChart, LineChart, GridComponent, TooltipComponent, TitleComponent])

// ---- 配色 ----
const C = {
  primary: '#4F46E5',
  primarySoft: '#EEF2FF',
  green: '#10B981',
  greenSoft: '#ECFDF5',
  blue: '#3B82F6',
  blueSoft: '#EFF6FF',
  amber: '#F59E0B',
  amberSoft: '#FFFBEB',
  red: '#EF4444',
  ink: '#0F172A',
  muted: '#64748B',
  border: '#E2E8F0',
  bg: '#F8FAFC',
}

const GRADIENT = ['#4F46E5', '#6366F1', '#818CF8', '#3B82F6', '#0EA5E9', '#14B8A6']

// ---- 类型定义 ----
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

// ---- payload computed ----
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

// ---- contrast option ----
const contrastOption = computed(() => {
  if (!contrastPayload.value) return {}
  const p = contrastPayload.value
  const dims = ['定义', ...p.left.signals, '示例']
  const leftVals = [-1, ...p.left.signals.map(() => -1), -1]
  const rightVals = [1, ...p.right.signals.map(() => 1), 1]
  return {
    tooltip: {
      trigger: 'axis' as const,
      axisPointer: { type: 'shadow' as const },
      formatter: (params: any) => {
        if (!Array.isArray(params)) return ''
        const dim = params[0]?.name || ''
        const l = p.left
        const r = p.right
        let html = `<b>${dim}</b><br/>`
        if (dim === '定义') {
          html += `<span style="color:${C.primary}">◆ ${l.label}：</span>${l.definition}<br/>`
          html += `<span style="color:${C.green}">◆ ${r.label}：</span>${r.definition}`
        } else if (dim === '示例') {
          html += `<span style="color:${C.primary}">◆ ${l.label}：</span>${l.example}<br/>`
          html += `<span style="color:${C.green}">◆ ${r.label}：</span>${r.example}`
        } else {
          const idx = l.signals.indexOf(dim)
          if (idx >= 0) html += `<span style="color:${C.primary}">◆ ${l.label} 特征</span><br/>`
          const ridx = r.signals.indexOf(dim)
          if (ridx >= 0) html += `<span style="color:${C.green}">◆ ${r.label} 特征</span>`
        }
        return html
      }
    },
    grid: { left: 80, right: 80, top: 30, bottom: 20 },
    xAxis: {
      type: 'value' as const,
      max: 1.2,
      min: -1.2,
      axisLabel: { show: false },
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'category' as const,
      data: dims,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        color: C.muted,
        fontSize: 12,
        formatter: (val: string) => val.length > 8 ? val.slice(0, 8) + '…' : val
      },
    },
    series: [
      {
        name: p.left.label,
        type: 'bar' as const,
        stack: 'total',
        data: leftVals,
        itemStyle: { color: C.primary, borderRadius: [0, 0, 0, 4] },
        barWidth: 20,
        label: {
          show: true,
          position: 'insideLeft' as const,
          color: '#fff',
          fontSize: 11,
          fontWeight: 600,
          formatter: (params: any) => params.dataIndex === 0 ? p.left.label : ''
        },
      },
      {
        name: p.right.label,
        type: 'bar' as const,
        stack: 'total',
        data: rightVals,
        itemStyle: { color: C.green, borderRadius: [0, 4, 0, 0] },
        barWidth: 20,
        label: {
          show: true,
          position: 'insideRight' as const,
          color: '#fff',
          fontSize: 11,
          fontWeight: 600,
          formatter: (params: any) => params.dataIndex === 0 ? p.right.label : ''
        },
      },
    ],
  }
})

// ---- journey option (sankey) ----
const journeyOption = computed(() => {
  if (!journeyPayload.value) return {}
  const steps = journeyPayload.value.steps
  const nodes = steps.map((s, i) => ({
    name: s.title,
    itemStyle: { color: GRADIENT[i % GRADIENT.length] },
  }))
  // add "结果" node
  nodes.push({ name: journeyPayload.value.result.slice(0, 12) + '…', itemStyle: { color: GRADIENT[5] } })
  const links = steps.slice(0, -1).map((step, i) => ({
    source: step.title,
    target: steps[i + 1]?.title ?? '',
    value: 1,
  }))
  // last step → result
  const lastStep = steps[steps.length - 1]
  links.push({
    source: lastStep?.title ?? '',
    target: nodes[nodes.length - 1]?.name ?? '',
    value: 1,
  })
  return {
    tooltip: {
      trigger: 'item' as const,
      formatter: (params: any) => {
        if (params.dataType === 'node') {
          const idx = steps.findIndex(st => st.title === params.name)
          if (idx < 0) return params.name
          const step = steps[idx]
          if (!step) return params.name
          return `<b>${idx + 1}. ${step.title}</b><br/>动作：${step.action}<br/>原理：${step.rationale}<br/>产出：${step.output}`
        }
        return ''
      }
    },
    series: [{
      type: 'sankey' as const,
      layout: 'none' as const,
      nodeWidth: 22,
      nodeGap: 14,
      layoutIterations: 32,
      emphasis: { focus: 'adjacency' as const },
      lineStyle: { color: 'gradient' as const, opacity: 0.35 },
      label: { color: C.ink, fontSize: 12, fontWeight: 600 },
      nodes,
      links,
    }],
  }
})

// ---- anatomy option (tree) ----
const anatomyOption = computed(() => {
  if (!anatomyPayload.value) return {}
  const p = anatomyPayload.value
  const children = p.parts.map((part, i) => {
    const keywords = part.detail.length > 60
      ? part.detail.split(/[，,。.；;、]/).filter(Boolean).slice(0, 4)
      : [part.detail]
    return {
      name: part.name,
      value: part.responsibility,
      children: keywords.map(k => ({ name: k.slice(0, 16), value: '' })),
      itemStyle: { color: GRADIENT[(i + 1) % GRADIENT.length] },
      label: { color: C.ink, fontSize: 12 },
    }
  })
  return {
    tooltip: {
      trigger: 'item' as const,
      triggerOn: 'mousemove' as const,
      formatter: (params: any) => {
        const d = params.data
        if (!d.children?.length) return d.name
        const part = p.parts.find(pt => pt.name === d.name)
        if (!part) return d.name
        let html = `<b>${part.name}</b><br/>职责：${part.responsibility}`
        if (part.interaction_cue) html += `<br/>交互：${part.interaction_cue}`
        return html
      }
    },
    series: [{
      type: 'tree' as const,
      data: [{
        name: p.subject,
        children,
        itemStyle: { color: C.primary },
        label: { color: C.primary, fontSize: 14, fontWeight: 700 },
      }],
      orient: 'LR' as const,
      edgeShape: 'polyline' as const,
      edgeForkPosition: '63%',
      roam: true,
      initialTreeDepth: 2,
      symbolSize: 9,
      lineStyle: { color: C.border, width: 1.5 },
      label: {
        color: C.ink,
        fontSize: 12,
        backgroundColor: '#fff',
        padding: [3, 6],
        borderRadius: 4,
        rich: {},
      },
      leaves: {
        label: { color: C.muted, fontSize: 11 }
      },
      expandAndCollapse: true,
      animationDuration: 450,
    }],
  }
})

// ---- simulation option (step line) ----
const simulationOption = computed(() => {
  if (!simulationPayload.value) return {}
  const p = simulationPayload.value
  const stages = p.frames.map(f => f.stage)
  const changedMarks: any[] = []
  const focusAreas: any[] = []
  p.frames.forEach((f, i) => {
    changedMarks.push({
      coord: [f.stage, i + 1],
      value: f.changed.length > 30 ? f.changed.slice(0, 30) + '…' : f.changed,
      itemStyle: { color: C.amber },
    })
    focusAreas.push({
      name: f.learner_focus,
      xAxis: f.stage,
    })
  })
  return {
    tooltip: {
      trigger: 'axis' as const,
      formatter: (params: any) => {
        if (!Array.isArray(params) || !params.length) return ''
        const idx = params[0].dataIndex
        const f = p.frames[idx]
        if (!f) return ''
        return `<b>${f.stage}</b><br/>`
          + `状态：${f.state}<br/>`
          + `变化：<span style="color:${C.amber}">${f.changed}</span><br/>`
          + `原因：${f.reason}<br/>`
          + `<span style="color:${C.primary}">观察：${f.learner_focus}</span>`
      }
    },
    grid: { left: 60, right: 24, top: 20, bottom: 36 },
    xAxis: {
      type: 'category' as const,
      data: stages,
      axisLine: { lineStyle: { color: C.border } },
      axisTick: { show: false },
      axisLabel: { color: C.muted, fontSize: 11 },
    },
    yAxis: {
      type: 'value' as const,
      min: 0,
      max: p.frames.length + 1,
      axisLabel: { show: false },
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: C.border, type: 'dashed' as const } },
    },
    series: [{
      type: 'line' as const,
      step: 'middle' as const,
      data: p.frames.map((_, i) => i + 1),
      lineStyle: { color: C.primary, width: 2.5 },
      areaStyle: {
        color: {
          type: 'linear' as const,
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(79,70,229,0.25)' },
            { offset: 1, color: 'rgba(79,70,229,0.02)' },
          ],
        }
      },
      itemStyle: { color: C.primary },
      symbol: 'circle',
      symbolSize: 10,
      markPoint: {
        data: changedMarks,
        symbol: 'pin',
        symbolSize: 42,
        label: { fontSize: 9, color: '#fff' },
        animation: true,
      },
    }],
  }
})

// ---- 图板类型标签 ----
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
  100% { opacity: 1;transform: translateY(0); }
}

.animate-block { animation: slideUpFade 0.6s cubic-bezier(0.16, 1, 0.3, 1) both; }

.insight-canvas {
  --c-primary: #4F46E5;
  --c-primary-soft: #EEF2FF;
  --c-green: #10B981;
  --c-amber: #F59E0B;
  --c-ink: #0F172A;
  --c-muted: #64748B;
  --c-border: #E2E8F0;
  --c-bg: #F8FAFC;
  display: grid;
  gap: 18px;
  padding: clamp(18px, 3vw, 30px);
  color: var(--c-ink);
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
  color: var(--c-primary);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: .16em;
}

h3, h4, p { margin: 0; }

h3 {
  font-size: clamp(20px, 3vw, 26px);
  letter-spacing: -.03em;
  color: var(--c-ink);
}

.focus-question {
  max-width: 45%;
  padding: 10px 14px;
  color: var(--c-muted);
  background: var(--c-bg);
  border: 1px solid var(--c-border);
  border-radius: 14px;
  font-size: 14px;
  line-height: 1.5;
}

.takeaway {
  display: flex;
  gap: 14px;
  align-items: center;
  padding: 14px 18px;
  background: var(--c-primary-soft);
  color: var(--c-ink);
  border: 1px solid #C7D2FE;
  border-radius: 16px;
  box-shadow: 0 2px 8px rgba(79, 70, 229, 0.04);
}

.takeaway-label, .footer-label {
  flex-shrink: 0;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: .05em;
  color: var(--c-primary);
}

.takeaway strong {
  font-weight: 600;
  line-height: 1.5;
}

/* ---- chart area ---- */
.chart-section {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.diagram-chart {
  width: 100%;
  height: 340px;
  min-height: 240px;
}

.board-result {
  padding: 14px 18px;
  color: var(--c-ink);
  background: var(--c-bg);
  border: 1px solid var(--c-border);
  border-radius: 14px;
  font-weight: 500;
  font-size: 14px;
  line-height: 1.6;
}

.journey-goal {
  padding: 14px 18px;
  color: var(--c-ink);
  font-weight: 600;
  background: var(--c-primary-soft);
  border: 1px solid #C7D2FE;
  border-radius: 14px;
  font-size: 15px;
}

.sim-header-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px 18px;
  background: var(--c-primary-soft);
  border: 1px solid #C7D2FE;
  border-radius: 14px;
  font-size: 14px;
  color: var(--c-ink);
}

.sim-header-info small {
  color: var(--c-muted);
  font-size: 13px;
}

.warning-text { color: var(--c-amber); }
.focus-text { color: var(--c-primary); }

/* ---- step / frame details (collapsible) ---- */
.step-details :deep(.el-collapse),
.frame-details :deep(.el-collapse) {
  border: 1px solid var(--c-border);
  border-radius: 14px;
  overflow: hidden;
}

.step-details :deep(.el-collapse-item__header),
.frame-details :deep(.el-collapse-item__header) {
  font-weight: 600;
  font-size: 14px;
  color: var(--c-ink);
  padding: 0 16px;
}

.step-details :deep(.el-collapse-item__content),
.frame-details :deep(.el-collapse-item__content) {
  padding: 8px 16px 16px;
  font-size: 14px;
  line-height: 1.7;
  color: var(--c-muted);
}

.step-details p, .frame-details p {
  margin-bottom: 6px;
}

/* ---- footer ---- */
.canvas-footer {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  padding-top: 6px;
}

.canvas-footer > div {
  min-height: 90px;
  padding: 16px;
  background: var(--c-bg);
  border: 1px solid var(--c-border);
  border-radius: 16px;
  transition: background 0.3s ease;
}

.canvas-footer > div:hover {
  background: #ffffff;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.03);
}

.canvas-footer p {
  margin-top: 8px;
  color: var(--c-muted);
  font-size: 14px;
  line-height: 1.6;
}

.pitfall-label { color: var(--c-amber) !important; }

/* ---- compact mode ---- */
.compact { gap: 14px; padding: 16px; border: 0; border-radius: 0; box-shadow: none; }
.compact .canvas-header { align-items: start; }
.compact h3 { font-size: 18px; }
.compact .focus-question { display: none; }
.compact .diagram-chart { height: 220px; min-height: 180px; }

/* ---- responsive ---- */
@media (max-width: 640px) {
  .canvas-header, .takeaway { flex-direction: column; align-items: start; }
  .focus-question { max-width: none; }
  .canvas-footer { grid-template-columns: 1fr; }
  .diagram-chart { height: 260px; }
}

@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; transition: none !important; }
}
</style>