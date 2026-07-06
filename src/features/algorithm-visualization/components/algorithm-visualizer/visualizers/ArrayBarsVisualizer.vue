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
    g.select('rect.bar-rect').attr('x', 0).attr('y', y).attr('rx', 18).attr('ry', 18).attr('width', bw).attr('height', Math.max(bh, 20))
    g.select('text.bar-value').attr('x', bw / 2).attr('y', Math.max(y - 12, 14)).attr('text-anchor', 'middle').text(d.value)
    g.select('text.bar-index').attr('x', bw / 2).attr('y', innerHeight + 28).attr('text-anchor', 'middle').text(d.index)
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
    gsap.fromTo(rects, { opacity: 0, y: 18 }, { opacity: 1, y: 0, duration: 0.45, ease: 'power2.out', stagger: 0.06 }); return
  }
  if (props.currentEvent.type === 'compare' && targets.length) {
    gsap.fromTo(targets, { y: 0, scaleY: 1 }, { y: -14, scaleY: 1.04, duration: 0.24, yoyo: true, repeat: 1, ease: 'power2.out', transformOrigin: 'center bottom' }); return
  }
  if (props.currentEvent.type === 'swap' && targets.length) {
    const [first, second] = targets
    if (first) gsap.fromTo(first, { x: 0, y: 0 }, { x: -10, y: -18, duration: 0.22, yoyo: true, repeat: 1 })
    if (second) gsap.fromTo(second, { x: 0, y: 0 }, { x: 10, y: -18, duration: 0.22, yoyo: true, repeat: 1 }); return
  }
  if (props.currentEvent.type === 'mark_sorted' && sortedTarget) {
    gsap.fromTo(sortedTarget, { scale: 1 }, { scale: 1.08, duration: 0.28, yoyo: true, repeat: 1, ease: 'power2.out', transformOrigin: 'center bottom' })
  }
}

watch(() => [props.currentStepIndex, activeArray.value.join(',')], async () => { await nextTick(); renderChart(); animateStep() }, { immediate: true })
onMounted(() => { renderChart(); animateStep() })
onBeforeUnmount(() => { if (svgRef.value) gsap.killTweensOf(svgRef.value.querySelectorAll<SVGGElement>('g.bar-group')) })
</script>

<style scoped>
.array-bars-visualizer { height: 100%; min-height: 0; display: grid; grid-template-rows: auto minmax(0, 1fr); gap: 16px; padding: 18px; background: radial-gradient(circle at top left, rgba(37, 99, 235, 0.08), transparent 26%), linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.95)); }
.visualizer-meta { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; }
.visualizer-meta h3 { margin: 0; font-size: 20px; font-weight: 760; color: #0f172a; }
.visualizer-meta p { margin: 6px 0 0; font-size: 13px; color: #64748b; }
.legend { display: flex; flex-wrap: wrap; gap: 8px; }
.legend-item { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; color: #475569; }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; }
.legend-dot.compare { background: #60a5fa; }
.legend-dot.swap { background: #f59e0b; }
.legend-dot.sorted { background: #10b981; }
.chart-shell { min-height: 0; border-radius: 24px; background: rgba(241, 245, 249, 0.62); border: 1px solid rgba(226, 232, 240, 0.96); padding: 16px; }
.chart-svg { width: 100%; height: 100%; min-height: 300px; }
:deep(.bar-rect) { fill: #cbd5e1; transition: fill 0.2s ease, opacity 0.2s ease; filter: drop-shadow(0 12px 18px rgba(15, 23, 42, 0.08)); }
:deep(.bar-value) { fill: #0f172a; font-size: 18px; font-weight: 700; }
:deep(.bar-index) { fill: #64748b; font-size: 14px; font-weight: 600; }
:deep(.bar-group[data-tone='compare'] .bar-rect) { fill: #60a5fa; }
:deep(.bar-group[data-tone='swap'] .bar-rect) { fill: #f59e0b; }
:deep(.bar-group[data-tone='sorted'] .bar-rect) { fill: #10b981; }
@media (max-width: 900px) { .visualizer-meta { flex-direction: column; } }
</style>
