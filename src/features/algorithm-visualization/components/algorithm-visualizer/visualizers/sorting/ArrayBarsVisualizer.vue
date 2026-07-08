<template>
  <div class="array-bars-visualizer">
    <div class="visualizer-meta">
      <div>
        <h3>数组排序可视化</h3>
        <p>使用 D3 渲染柱状图，GSAP 播放比较、交换和归位动画。</p>
      </div>
      <div class="legend">
        <span class="legend-item"><i class="legend-dot compare"></i>比较</span>
        <span class="legend-item"><i class="legend-dot swap"></i>交换</span>
        <span class="legend-item"><i class="legend-dot sorted"></i>已归位</span>
      </div>
    </div>

    <div class="chart-shell">
      <svg ref="svgRef" class="chart-svg" viewBox="0 0 860 420" preserveAspectRatio="xMidYMid meet" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as d3 from 'd3'
import gsap from 'gsap'
import type { TraceEvent } from '@/features/algorithm-visualization/types'

interface Props {
  currentEvent: TraceEvent | null
  currentStepIndex: number
  events: TraceEvent[]
}

interface BarDatum {
  id: string
  index: number
  value: number
  tone: string
}

const props = defineProps<Props>()

const svgRef = ref<SVGSVGElement | null>(null)

const activeArray = computed(() => {
  const arr = props.currentEvent?.state?.structure?.array
  if (Array.isArray(arr)) {
    return arr.map(Number).filter((item: number) => Number.isFinite(item))
  }
  const initArr = props.events[0]?.state?.structure?.array
  if (Array.isArray(initArr)) {
    return initArr.map(Number).filter((item: number) => Number.isFinite(item))
  }
  return []
})

function getIndices(event: TraceEvent | null): number[] {
  const raw = event?.targets
  if (!Array.isArray(raw)) return []
  return raw.map(Number).filter((item: number) => Number.isInteger(item))
}

function getSortedIndex(event: TraceEvent | null): number | null {
  if (event?.type === 'mark_sorted') {
    const raw = event.targets
    if (Array.isArray(raw) && raw.length > 0) return Number(raw[0])
  }
  return null
}

function getTone(index: number): string {
  const event = props.currentEvent
  const indices = getIndices(event)
  const sortedIndex = getSortedIndex(event)
  if (sortedIndex === index) return 'sorted'
  if (event?.type === 'swap' && indices.includes(index)) return 'swap'
  if (indices.includes(index)) return 'compare'
  return 'default'
}

function buildData(): BarDatum[] {
  return activeArray.value.map((value: number, index: number) => ({
    id: `bar-${index}`, index, value, tone: getTone(index),
  }))
}

function renderChart() {
  if (!svgRef.value) return
  const svg = d3.select(svgRef.value)
  const width = 860; const height = 420
  const margin = { top: 28, right: 32, bottom: 56, left: 32 }
  const innerWidth = width - margin.left - margin.right
  const innerHeight = height - margin.top - margin.bottom
  const maxValue = Math.max(...activeArray.value, 1)
  const data = buildData()

  const root = svg.selectAll('g.chart-root').data([null]).join('g')
    .attr('class', 'chart-root').attr('transform', `translate(${margin.left},${margin.top})`)

  const xScale = d3.scaleBand().domain(data.map((d: BarDatum) => d.index)).range([0, innerWidth]).padding(0.18)
  const yScale = d3.scaleLinear().domain([0, maxValue]).range([innerHeight, 0])

  root.selectAll('line.baseline').data([null]).join('line').attr('class', 'baseline')
    .attr('x1', 0).attr('x2', innerWidth).attr('y1', innerHeight).attr('y2', innerHeight)
    .attr('stroke', '#dbe3ef').attr('stroke-width', 1.5)

  const groups = root.selectAll('g.bar-group').data(data, (d: BarDatum) => d.id)
    .join((enter: any) => {
      const g = enter.append('g').attr('class', 'bar-group')
      g.append('rect').attr('class', 'bar-rect')
      g.append('text').attr('class', 'bar-value')
      g.append('text').attr('class', 'bar-index')
      return g
    })
    .attr('data-bar-id', (d: BarDatum) => d.id).attr('data-tone', (d: BarDatum) => d.tone)

  groups.each(function (this: SVGGElement, d: BarDatum) {
    const g = d3.select(this)
    const x = xScale(d.index) ?? 0; const y = yScale(d.value)
    const bw = xScale.bandwidth(); const bh = innerHeight - y
    g.attr('transform', `translate(${x}, 0)`)
    g.select('rect.bar-rect').attr('x', 0).attr('y', y).attr('rx', 3).attr('ry', 3).attr('width', bw).attr('height', Math.max(bh, 20))
    g.select('text.bar-value').attr('x', bw / 2).attr('y', Math.max(y - 8, 12)).attr('text-anchor', 'middle').text(d.value)
    g.select('text.bar-index').attr('x', bw / 2).attr('y', innerHeight + 20).attr('text-anchor', 'middle').text(d.index)
  })
}

function animateStep() {
  if (!svgRef.value || !props.currentEvent) return
  const svg = svgRef.value
  const rects = Array.from(svg.querySelectorAll<SVGRectElement>('rect.bar-rect'))
  const targets = getIndices(props.currentEvent)
    .map((i: number) => svg.querySelector<SVGRectElement>(`g[data-bar-id="bar-${i}"] rect.bar-rect`))
    .filter((e: SVGRectElement | null): e is SVGRectElement => Boolean(e))
  const sortedIdx = getSortedIndex(props.currentEvent)
  const sortedTarget = sortedIdx !== null ? svg.querySelector<SVGRectElement>(`g[data-bar-id="bar-${sortedIdx}"] rect.bar-rect`) : null

  gsap.killTweensOf(rects); gsap.set(rects, { clearProps: 'all' })

  if (props.currentEvent.type === 'init_array') {
    gsap.fromTo(rects, { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.35, ease: 'power2.out', stagger: 0.04 }); return
  }
  if (props.currentEvent.type === 'compare' && targets.length) {
    gsap.fromTo(targets, { y: 0, scaleY: 1 }, { y: -8, scaleY: 1.02, duration: 0.18, yoyo: true, repeat: 1, ease: 'power2.out', transformOrigin: 'center bottom' }); return
  }
  if (props.currentEvent.type === 'swap' && targets.length) {
    const [first, second] = targets
    if (first) gsap.fromTo(first, { x: 0, y: 0 }, { x: -6, y: -10, duration: 0.18, yoyo: true, repeat: 1 })
    if (second) gsap.fromTo(second, { x: 0, y: 0 }, { x: 6, y: -10, duration: 0.18, yoyo: true, repeat: 1 }); return
  }
  if (props.currentEvent.type === 'mark_sorted' && sortedTarget) {
    gsap.fromTo(sortedTarget, { scale: 1 }, { scale: 1.04, duration: 0.22, yoyo: true, repeat: 1, ease: 'power2.out', transformOrigin: 'center bottom' })
  }
}

watch(() => [props.currentStepIndex, activeArray.value.join(',')], async () => { await nextTick(); renderChart(); animateStep() }, { immediate: true })
onMounted(() => { renderChart(); animateStep() })
onBeforeUnmount(() => { if (svgRef.value) gsap.killTweensOf(svgRef.value.querySelectorAll<SVGGElement>('g.bar-group')) })
</script>

<style scoped>
.array-bars-visualizer {
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 12px;
  padding: 12px;
  background: #ffffff;
}

.visualizer-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--color-border-light);
}

.visualizer-meta h3 {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-strong);
}

.visualizer-meta p {
  margin: 2px 0 0;
  font-size: 11px;
  color: var(--color-text-muted);
}

.legend {
  display: flex;
  gap: 8px;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--color-text-secondary);
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.legend-dot.compare {
  background: var(--color-primary);
}

.legend-dot.swap {
  background: var(--color-warning);
}

.legend-dot.sorted {
  background: var(--color-success);
}

.chart-shell {
  min-height: 0;
  border-radius: var(--radius-sm);
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  padding: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chart-svg {
  width: 100%;
  height: 100%;
  min-height: 240px;
}

:deep(.bar-rect) {
  fill: var(--color-border-hover);
  transition: fill 0.15s ease, opacity 0.15s ease;
}

:deep(.bar-value) {
  fill: var(--color-text-strong);
  font-size: 14px;
  font-weight: 600;
}

:deep(.bar-index) {
  fill: var(--color-text-muted);
  font-size: 11px;
  font-weight: 500;
}

:deep(.bar-group[data-tone='compare'] .bar-rect) {
  fill: var(--color-primary);
}

:deep(.bar-group[data-tone='swap'] .bar-rect) {
  fill: var(--color-warning);
}

:deep(.bar-group[data-tone='sorted'] .bar-rect) {
  fill: var(--color-success);
}
</style>
